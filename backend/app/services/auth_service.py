"""认证服务。"""

import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.password_validator import validate_password_strength
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from app.domain.models.student import UserRole, UserStatus
from app.infrastructure.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

_LOGIN_FAIL_PREFIX = "msp:login_fail:"
_LOGIN_LOCK_PREFIX = "msp:login_lock:"


@dataclass
class AuthResult:
    """认证结果。"""

    success: bool
    access_token: str | None = None
    refresh_token: str | None = None
    user_id: str | None = None
    username: str | None = None
    email: str | None = None
    role: str | None = None
    error: str | None = None


class AuthService:
    """认证服务。"""

    _local_fail_counts: dict[str, list[float]] = {}

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def register(
        self,
        username: str,
        email: str,
        password: str,
        role: UserRole,
    ) -> AuthResult:
        """注册用户并返回登录态。"""
        is_valid, errors = validate_password_strength(password)
        if not is_valid:
            return AuthResult(success=False, error="；".join(errors))

        if await self.user_repo.get_by_username(username):
            return AuthResult(success=False, error="用户名已存在")

        if await self.user_repo.get_by_email(email):
            return AuthResult(success=False, error="邮箱已被注册")

        user = await self.user_repo.create(
            obj_in={
                "username": username,
                "email": email,
                "hashed_password": get_password_hash(password),
                "role": role,
                "status": UserStatus.ACTIVE,
                "is_active": True,
            }
        )
        await self.db.commit()
        await self.db.refresh(user)

        access_token = create_access_token(
            subject=user.id,
            extra_claims={"role": user.role.value},
        )
        refresh_token = create_refresh_token(subject=user.id)

        logger.info("新用户注册成功: %s (%s)", username, role.value)
        return AuthResult(
            success=True,
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user.id,
            username=user.username,
            email=user.email,
            role=user.role.value,
        )

    async def authenticate(self, username: str, password: str) -> AuthResult:
        """账号认证（含登录失败锁定保护）。"""
        if await self._is_account_locked(username):
            return AuthResult(
                success=False,
                error=f"账户已被临时锁定，请 {settings.login_lockout_minutes} 分钟后重试",
            )

        user = await self.user_repo.get_by_username(username)
        if not user:
            await self._record_login_failure(username)
            return AuthResult(success=False, error="用户名或密码错误")

        if not verify_password(password, user.hashed_password):
            await self._record_login_failure(username)
            return AuthResult(success=False, error="用户名或密码错误")

        if not user.is_active:
            return AuthResult(success=False, error="账户已被禁用")

        await self._clear_login_failures(username)

        access_token = create_access_token(
            subject=user.id,
            extra_claims={"role": user.role.value},
        )
        refresh_token = create_refresh_token(subject=user.id)
        return AuthResult(
            success=True,
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user.id,
            username=user.username,
            email=user.email,
            role=user.role.value,
        )

    async def change_password(
        self,
        user_id: str,
        old_password: str,
        new_password: str,
    ) -> tuple[bool, str]:
        """修改密码。"""
        user = await self.user_repo.get(user_id)
        if not user:
            return False, "用户不存在"

        if not verify_password(old_password, user.hashed_password):
            return False, "原密码错误"

        is_valid, errors = validate_password_strength(new_password)
        if not is_valid:
            return False, "；".join(errors)

        await self.user_repo.update_password(user_id, get_password_hash(new_password))
        await self.db.commit()
        return True, "密码修改成功"

    async def init_admin(self) -> bool:
        """按配置初始化管理员。"""
        if await self.user_repo.get_by_username(settings.admin_username):
            logger.info("管理员账户已存在: %s", settings.admin_username)
            return False

        await self.user_repo.create(
            obj_in={
                "username": settings.admin_username,
                "email": settings.admin_email,
                "hashed_password": get_password_hash(settings.admin_password),
                "role": UserRole.ADMIN,
                "display_name": "系统管理员",
                "is_active": True,
            }
        )
        await self.db.commit()
        logger.info("已创建管理员账户: %s", settings.admin_username)
        return True

    async def get_user_by_id(self, user_id: str):
        """按 ID 获取用户。"""
        return await self.user_repo.get(user_id)

    async def refresh_tokens(self, user_id: str) -> tuple[str | None, str | None]:
        """刷新 access/refresh token。"""
        user = await self.user_repo.get(user_id)
        if not user or not user.is_active:
            return None, None

        access_token = create_access_token(
            subject=user.id,
            extra_claims={"role": user.role.value},
        )
        refresh_token = create_refresh_token(subject=user.id)
        return access_token, refresh_token

    async def _get_redis_safe(self):
        """安全获取 Redis 客户端。"""
        try:
            from app.infrastructure.cache.redis import get_redis_client_safe

            return await get_redis_client_safe()
        except Exception:
            return None

    async def _is_account_locked(self, username: str) -> bool:
        """检查账号是否被锁定。"""
        redis = await self._get_redis_safe()
        if not redis:
            import time

            now = time.time()
            window = settings.login_lockout_minutes * 60
            attempts = self._local_fail_counts.get(username, [])
            recent_attempts = [timestamp for timestamp in attempts if now - timestamp < window]
            self._local_fail_counts[username] = recent_attempts
            return len(recent_attempts) >= settings.login_max_attempts

        try:
            return await redis.exists(f"{_LOGIN_LOCK_PREFIX}{username}") > 0
        except Exception:
            return False

    async def _record_login_failure(self, username: str) -> None:
        """记录登录失败。"""
        redis = await self._get_redis_safe()
        if not redis:
            import time

            self._local_fail_counts.setdefault(username, []).append(time.time())
            if len(self._local_fail_counts[username]) >= settings.login_max_attempts:
                logger.warning("账户 '%s' 因连续登录失败被锁定（内存降级模式）", username)
            return

        try:
            fail_key = f"{_LOGIN_FAIL_PREFIX}{username}"
            count = await redis.incr(fail_key)
            await redis.expire(fail_key, settings.login_lockout_minutes * 60)
            if count < settings.login_max_attempts:
                return

            await redis.set(
                f"{_LOGIN_LOCK_PREFIX}{username}",
                "1",
                ex=settings.login_lockout_minutes * 60,
            )
            logger.warning(
                "账户 '%s' 因连续 %d 次登录失败被锁定 %d 分钟",
                username,
                count,
                settings.login_lockout_minutes,
            )
        except Exception as exc:
            logger.error("记录登录失败异常: %s", exc)

    async def _clear_login_failures(self, username: str) -> None:
        """清除登录失败计数。"""
        self._local_fail_counts.pop(username, None)
        redis = await self._get_redis_safe()
        if not redis:
            return

        try:
            await redis.delete(
                f"{_LOGIN_FAIL_PREFIX}{username}",
                f"{_LOGIN_LOCK_PREFIX}{username}",
            )
        except Exception:
            pass


async def clear_login_failures_for_username(username: str) -> None:
    """在重置密码后清除指定用户的登录失败状态。"""
    try:
        from app.infrastructure.cache.redis import get_redis_client_safe

        redis = await get_redis_client_safe()
        if redis:
            await redis.delete(
                f"{_LOGIN_FAIL_PREFIX}{username}",
                f"{_LOGIN_LOCK_PREFIX}{username}",
            )
    except Exception:
        pass
