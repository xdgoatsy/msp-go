"""
安全相关工具

JWT Token 生成与验证、密码哈希等。
Token 黑名单基于 Redis 实现，支持登出即时失效。
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.config import settings

logger = logging.getLogger(__name__)

# JWT 标准声明
_JWT_ISSUER = "math-study-platform"
_JWT_AUDIENCE = "msp-api"


def _extract_unverified_algorithm(token: str) -> str | None:
    """从 JWT Header 中提取算法字段（不校验签名）。"""
    try:
        header = jwt.get_unverified_header(token)
    except Exception:
        return None
    algorithm = header.get("alg")
    return algorithm.upper() if isinstance(algorithm, str) else None


def audit_token_algorithm(token: str, source: str) -> bool:
    """
    审计算法并拒绝非白名单算法。

    说明:
        该检查用于限制 ECDSA/RSA 等非 HMAC 算法暴露面，并记录审计日志。
    """
    algorithm = _extract_unverified_algorithm(token)
    allowed_algorithm = settings.jwt_algorithm
    if algorithm is None:
        logger.warning("JWT Header 缺少 alg 字段: source=%s", source)
        return False
    if algorithm != allowed_algorithm:
        logger.warning(
            "拒绝 JWT 算法: source=%s alg=%s allowed=%s token_prefix=%s",
            source,
            algorithm,
            allowed_algorithm,
            token[:16],
        )
        return False
    return True


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_access_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    创建访问令牌

    Args:
        subject: 令牌主体（通常是用户 ID）
        expires_delta: 过期时间增量
        extra_claims: 额外的声明

    Returns:
        JWT 令牌字符串
    """
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )

    to_encode: dict[str, Any] = {
        "exp": expire,
        "iat": now,
        "sub": str(subject),
        "iss": _JWT_ISSUER,
        "aud": _JWT_AUDIENCE,
        "jti": uuid.uuid4().hex,
        "type": "access",
    }

    if extra_claims:
        to_encode.update(extra_claims)

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    return encoded_jwt


def create_refresh_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
) -> str:
    """
    创建刷新令牌

    Args:
        subject: 令牌主体
        expires_delta: 过期时间增量

    Returns:
        JWT 令牌字符串
    """
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(
            days=settings.jwt_refresh_token_expire_days
        )

    to_encode: dict[str, Any] = {
        "exp": expire,
        "iat": now,
        "sub": str(subject),
        "iss": _JWT_ISSUER,
        "aud": _JWT_AUDIENCE,
        "jti": uuid.uuid4().hex,
        "type": "refresh",
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    return encoded_jwt


def decode_token(token: str) -> dict[str, Any] | None:
    """
    解码 JWT 令牌

    Args:
        token: JWT 令牌字符串

    Returns:
        解码后的声明字典，如果无效则返回 None
    """
    try:
        if not audit_token_algorithm(token, source="core.decode_token"):
            return None
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=_JWT_AUDIENCE,
            issuer=_JWT_ISSUER,
        )
        return payload
    except Exception:
        return None


# ========== Token 黑名单（基于 Redis） ==========

_TOKEN_BLACKLIST_PREFIX = "msp:token_blacklist:"


async def blacklist_token(jti: str, expires_in: int) -> None:
    """
    将 Token 加入黑名单

    Args:
        jti: Token 的唯一标识
        expires_in: 剩余有效期（秒），用于自动过期
    """
    try:
        from app.infrastructure.cache.redis import get_redis_client_safe
        redis = await get_redis_client_safe()
        if redis:
            await redis.set(
                f"{_TOKEN_BLACKLIST_PREFIX}{jti}",
                "1",
                ex=max(expires_in, 1),
            )
    except Exception as e:
        logger.warning("Token 黑名单写入失败: %s", e)


async def is_token_blacklisted(jti: str) -> bool:
    """检查 Token 是否在黑名单中"""
    try:
        from app.infrastructure.cache.redis import get_redis_client_safe
        redis = await get_redis_client_safe()
        if redis:
            return await redis.exists(f"{_TOKEN_BLACKLIST_PREFIX}{jti}") > 0
    except Exception:
        pass
    return False
