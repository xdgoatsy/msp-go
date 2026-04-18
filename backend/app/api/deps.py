"""
API 依赖注入

提供路由处理函数所需的公共依赖。
Token 解析包含黑名单检查和标准声明验证。
"""

import logging
from collections.abc import AsyncGenerator
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import _JWT_AUDIENCE, _JWT_ISSUER, audit_token_algorithm
from app.infrastructure.database.session import get_session

logger = logging.getLogger(__name__)

# OAuth2 密码流
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_prefix}/auth/login",
    auto_error=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话依赖"""
    async for session in get_session():
        yield session


# 类型别名
DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_token_payload(
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> dict[str, Any] | None:
    """从 JWT Token 中解析 payload（含黑名单检查）"""
    if token is None:
        return None

    try:
        if not audit_token_algorithm(token, source="api.get_current_token_payload"):
            return None
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=_JWT_AUDIENCE,
            issuer=_JWT_ISSUER,
        )
        if not isinstance(payload, dict):
            return None

        # Token 黑名单检查
        jti = payload.get("jti")
        if jti:
            try:
                from app.core.security import is_token_blacklisted
                if await is_token_blacklisted(jti):
                    logger.info("已撤销的 Token 被使用: jti=%s", jti)
                    return None
            except Exception:
                pass  # Redis 不可用时放行

        return payload
    except InvalidTokenError:
        return None


async def get_current_user_id(
    payload: Annotated[dict[str, Any] | None, Depends(get_current_token_payload)],
) -> str | None:
    """
    从 JWT Token 中解析当前用户 ID

    Returns:
        用户 ID，如果未认证则返回 None
    """
    if payload is None:
        return None

    user_id = payload.get("sub")
    return user_id if isinstance(user_id, str) else None


async def require_current_user(
    user_id: Annotated[str | None, Depends(get_current_user_id)],
) -> str:
    """
    要求用户必须登录

    Raises:
        HTTPException: 401 如果用户未认证
    """
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证，请先登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


# 类型别名
CurrentUserId = Annotated[str, Depends(require_current_user)]
OptionalUserId = Annotated[str | None, Depends(get_current_user_id)]


async def get_current_user_role(
    payload: Annotated[dict[str, Any] | None, Depends(get_current_token_payload)],
) -> str | None:
    """
    从 JWT Token 中解析当前用户角色

    Returns:
        用户角色，如果未认证则返回 None
    """
    if payload is None:
        return None

    role = payload.get("role")
    return role if isinstance(role, str) else None


async def require_admin_user(
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    role: Annotated[str | None, Depends(get_current_user_role)],
) -> str:
    """
    要求用户必须是管理员

    Raises:
        HTTPException: 401 如果用户未认证
        HTTPException: 403 如果用户不是管理员
    """
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证，请先登录",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要管理员权限",
        )

    return user_id


# 管理员类型别名
AdminUserId = Annotated[str, Depends(require_admin_user)]


async def require_teacher_user(
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    role: Annotated[str | None, Depends(get_current_user_role)],
) -> str:
    """
    要求用户必须是教师或管理员

    Raises:
        HTTPException: 401 如果用户未认证
        HTTPException: 403 如果用户不是教师或管理员
    """
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证，请先登录",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if role not in ("teacher", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要教师权限",
        )

    return user_id


# 教师类型别名
TeacherUserId = Annotated[str, Depends(require_teacher_user)]


async def require_student_user(
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    role: Annotated[str | None, Depends(get_current_user_role)],
) -> str:
    """
    要求用户必须是学生

    Raises:
        HTTPException: 401 如果用户未认证
        HTTPException: 403 如果用户不是学生
    """
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证，请先登录",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要学生权限",
        )

    return user_id


# 学生类型别名
StudentUserId = Annotated[str, Depends(require_student_user)]
