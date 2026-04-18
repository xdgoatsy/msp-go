"""
认证相关接口

处理用户登录、注册、Token 刷新等
"""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel

from app.api.deps import CurrentUserId, DbSession
from app.config import settings
from app.core.security import decode_token
from app.domain.models.student import UserRole
from app.services.auth_service import AuthService
from app.services.password_reset_service import PasswordResetService
from app.services.system_setting_service import SystemSettingService

router = APIRouter()


# =============================================================================
# 请求/响应模型
# =============================================================================


class LoginRequest(BaseModel):
    """登录请求"""

    username: str
    password: str


class LoginResponse(BaseModel):
    """登录响应"""

    access_token: str
    token_type: str = "bearer"
    user: dict


class RefreshResponse(BaseModel):
    """Token 刷新响应"""

    access_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""

    old_password: str
    new_password: str


class MessageResponse(BaseModel):
    """通用消息响应"""

    message: str


class RegisterRequest(BaseModel):
    """注册请求"""

    username: str
    email: str
    password: str
    role: str = "student"


# =============================================================================
# 依赖注入
# =============================================================================


def get_auth_service(db: DbSession) -> AuthService:
    """获取认证服务"""
    return AuthService(db)


def get_system_setting_service(db: DbSession) -> SystemSettingService:
    """获取系统配置服务"""
    return SystemSettingService(db)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
SystemSettingServiceDep = Annotated[
    SystemSettingService, Depends(get_system_setting_service)
]


def get_password_reset_service(db: DbSession) -> PasswordResetService:
    """获取密码重置服务"""
    return PasswordResetService(db)


PasswordResetServiceDep = Annotated[
    PasswordResetService, Depends(get_password_reset_service)
]


# =============================================================================
# API 端点
# =============================================================================


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    response: Response,
    service: AuthServiceDep,
) -> LoginResponse:
    """
    用户登录

    验证用户名和密码，返回访问令牌
    Refresh Token 通过 HttpOnly Cookie 返回
    """
    result = await service.authenticate(request.username, request.password)

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result.error,
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 设置 refresh token 为 HttpOnly Cookie
    response.set_cookie(
        key="refresh_token",
        value=result.refresh_token,  # type: ignore
        httponly=True,
        secure=settings.environment != "development",  # 生产环境启用 HTTPS
        samesite="lax",
        path="/api/v1/auth",  # 仅认证接口发送
        max_age=settings.jwt_refresh_token_expire_days * 24 * 60 * 60,
    )

    return LoginResponse(
        access_token=result.access_token,  # type: ignore
        user={
            "id": result.user_id,
            "username": result.username,
            "email": result.email,
            "role": result.role,
        },
    )


@router.put("/change-password", response_model=MessageResponse)
async def change_password(
    request: ChangePasswordRequest,
    user_id: CurrentUserId,
    service: AuthServiceDep,
) -> MessageResponse:
    """
    修改密码

    需要登录，验证旧密码后更新为新密码
    """
    success, message = await service.change_password(
        user_id=user_id,
        old_password=request.old_password,
        new_password=request.new_password,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    return MessageResponse(message=message)


@router.post("/register", response_model=LoginResponse)
async def register(
    request: RegisterRequest,
    response: Response,
    auth_service: AuthServiceDep,
    system_setting_service: SystemSettingServiceDep,
) -> LoginResponse:
    """
    用户注册

    - 根据角色检查是否允许注册
    - 创建用户
    - 返回与登录相同格式的访问令牌和用户信息
    """
    # 只允许 student / teacher 通过开放注册
    if request.role not in {"student", "teacher"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持学生或教师角色注册",
        )

    # 检查注册开关
    if request.role == "student":
        allowed = await system_setting_service.is_student_registration_allowed()
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="当前不允许学生注册",
            )
    else:
        allowed = await system_setting_service.is_teacher_registration_allowed()
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="当前不允许教师注册",
            )

    # 创建用户
    result = await auth_service.register(
        username=request.username,
        email=request.email,
        password=request.password,
        role=UserRole.STUDENT if request.role == "student" else UserRole.TEACHER,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error or "注册失败",
        )

    # Fail fast: registration "success" must include tokens and user fields
    if (
        not result.access_token
        or not result.refresh_token
        or not result.user_id
        or not result.username
        or result.email is None
        or not result.role
    ):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册成功但未能生成登录凭证，请稍后重试",
        )

    # Set refresh token Cookie only when we have a non-empty token
    response.set_cookie(
        key="refresh_token",
        value=result.refresh_token,
        httponly=True,
        secure=settings.environment != "development",
        samesite="lax",
        path="/api/v1/auth",
        max_age=settings.jwt_refresh_token_expire_days * 24 * 60 * 60,
    )

    return LoginResponse(
        access_token=result.access_token,
        user={
            "id": result.user_id,
            "username": result.username,
            "email": result.email,
            "role": result.role,
        },
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(
    response: Response,
    service: AuthServiceDep,
    refresh_token: str | None = Cookie(default=None),
) -> RefreshResponse:
    """
    刷新 Token

    从 HttpOnly Cookie 读取 refresh token，验证后返回新的 access token
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token 不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 解码并验证 refresh token
    payload = decode_token(refresh_token)
    if not payload:
        # 清除无效的 cookie
        response.delete_cookie(
            key="refresh_token",
            path="/api/v1/auth",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token 无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 验证 token 类型
    if payload.get("type") != "refresh":
        response.delete_cookie(
            key="refresh_token",
            path="/api/v1/auth",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 token 类型",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 中缺少用户信息",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 生成新的 access token
    new_access_token, new_refresh_token = await service.refresh_tokens(user_id)

    if not new_access_token or not new_refresh_token:
        response.delete_cookie(
            key="refresh_token",
            path="/api/v1/auth",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 轮换 refresh token（更安全）
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=settings.environment != "development",
        samesite="lax",
        path="/api/v1/auth",
        max_age=settings.jwt_refresh_token_expire_days * 24 * 60 * 60,
    )

    return RefreshResponse(access_token=new_access_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response) -> MessageResponse:
    """
    用户登出

    清除 refresh token Cookie
    """
    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth",
    )
    return MessageResponse(message="登出成功")


class UserInfoResponse(BaseModel):
    """用户信息响应"""

    id: str
    username: str
    email: str
    role: str


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(
    user_id: CurrentUserId,
    service: AuthServiceDep,
) -> UserInfoResponse:
    """
    获取当前用户信息

    需要登录，返回当前用户的基本信息
    用于页面刷新后恢复用户状态
    """
    user = await service.get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    return UserInfoResponse(
        id=str(user.id),
        username=user.username,
        email=user.email or "",
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
    )


# =============================================================================
# 公开配置接口
# =============================================================================


class RegistrationStatusResponse(BaseModel):
    """注册状态响应"""

    allow_student: bool
    allow_teacher: bool


@router.get("/registration-status", response_model=RegistrationStatusResponse)
async def get_registration_status(
    service: SystemSettingServiceDep,
) -> RegistrationStatusResponse:
    """
    获取注册状态

    公开接口，无需认证
    返回当前系统是否允许学生和教师注册
    """
    settings = await service.get_registration_settings()
    return RegistrationStatusResponse(**settings)


# =============================================================================
# 忘记密码
# =============================================================================


class ForgotPasswordRequest(BaseModel):
    """忘记密码请求"""

    username: str
    email: str
    reason: str = ""


class ForgotPasswordResponse(BaseModel):
    """忘记密码响应"""

    success: bool
    message: str
    request_id: str | None = None


class ForgotPasswordStatusResponse(BaseModel):
    """忘记密码状态响应"""

    has_pending: bool
    status: str | None = None
    created_at: str | None = None


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    service: PasswordResetServiceDep,
) -> ForgotPasswordResponse:
    """
    提交密码重置申请（无需登录）

    用户提供用户名和注册邮箱，提交重置申请后等待管理员审批
    """
    success, message, request_id = await service.submit_request(
        username=request.username,
        email=request.email,
        reason=request.reason,
    )
    return ForgotPasswordResponse(
        success=success, message=message, request_id=request_id
    )


@router.get("/forgot-password/status", response_model=ForgotPasswordStatusResponse)
async def forgot_password_status(
    username: str,
    email: str,
    service: PasswordResetServiceDep,
) -> ForgotPasswordStatusResponse:
    """
    查询密码重置申请状态（无需登录）
    """
    has_pending, status_val, created_at = await service.get_user_request_status(
        username=username, email=email
    )
    return ForgotPasswordStatusResponse(
        has_pending=has_pending,
        status=status_val,
        created_at=created_at.isoformat() if created_at else None,
    )


