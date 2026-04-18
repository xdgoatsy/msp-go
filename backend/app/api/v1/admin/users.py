"""
管理员用户管理 API

提供用户账户管理的接口，仅管理员可访问
"""

import csv
import io
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse

from app.api.deps import AdminUserId, DbSession
from app.api.v1.schemas.admin_users import (
    UserAccountStats,
    UserCreateRequest,
    UserCreateResponse,
    UserDeleteResponse,
    UserImportResponse,
    UserItem,
    UserListResponse,
    UserStatusUpdate,
    UserStatusUpdateResponse,
    UserUpdateRequest,
    UserUpdateResponse,
)
from app.domain.models.student import UserStatus
from app.services.admin_user_service import AdminUserService

logger = logging.getLogger(__name__)

router = APIRouter()


# ========== 依赖注入 ==========


async def get_admin_user_service(db: DbSession) -> AdminUserService:
    """获取管理员用户服务"""
    return AdminUserService(db=db)


AdminUserServiceDep = Annotated[AdminUserService, Depends(get_admin_user_service)]


# ========== API 端点 ==========


@router.get(
    "/stats",
    response_model=UserAccountStats,
    summary="获取账户统计",
    description="获取各状态账户数量统计",
)
async def get_account_stats(
    _admin_id: AdminUserId,
    service: AdminUserServiceDep,
) -> UserAccountStats:
    """获取账户统计数据"""
    stats = await service.get_account_stats()
    return UserAccountStats(**stats)


@router.get(
    "",
    response_model=UserListResponse,
    summary="获取用户列表",
    description="分页获取用户列表，支持搜索和筛选",
)
async def list_users(
    _admin_id: AdminUserId,
    service: AdminUserServiceDep,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    search: str | None = Query(None, description="搜索关键词（用户名、邮箱、姓名）"),
    role: str | None = Query(None, description="角色筛选: all/student/teacher/admin"),
    status: str | None = Query(None, description="状态筛选: all/active/suspended"),
) -> UserListResponse:
    """获取用户列表"""
    result = await service.list_users(
        page=page,
        page_size=page_size,
        search=search,
        role=role,
        status=status,
    )

    return UserListResponse(
        items=[UserItem(**item) for item in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"],
    )


@router.patch(
    "/{user_id}/status",
    response_model=UserStatusUpdateResponse,
    summary="更新用户状态",
    description="更新用户状态（锁定/解锁）",
    responses={404: {"description": "用户不存在"}},
)
async def update_user_status(
    user_id: str,
    data: UserStatusUpdate,
    _admin_id: AdminUserId,
    service: AdminUserServiceDep,
) -> UserStatusUpdateResponse:
    """更新用户状态"""
    user = await service.update_user_status(user_id, data.status)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    logger.info(f"管理员更新用户状态: user_id={user_id}, status={data.status}")

    # 构建状态消息
    status_messages = {
        UserStatus.ACTIVE.value: "用户已解锁",
        UserStatus.SUSPENDED.value: "用户已停用",
    }
    message = status_messages.get(data.status, "用户状态已更新")

    return UserStatusUpdateResponse(
        success=True,
        message=message,
        user=UserItem(
            id=user.id,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            role=user.role.value,
            status=user.status.value if user.status else UserStatus.ACTIVE.value,
            created_at=user.created_at,
        ),
    )


@router.put(
    "/{user_id}",
    response_model=UserUpdateResponse,
    summary="更新用户信息",
    description="更新用户信息（显示名称、密码）",
    responses={404: {"description": "用户不存在"}},
)
async def update_user(
    user_id: str,
    data: UserUpdateRequest,
    _admin_id: AdminUserId,
    service: AdminUserServiceDep,
) -> UserUpdateResponse:
    """更新用户信息"""
    user, message = await service.update_user(
        user_id=user_id,
        display_name=data.display_name,
        password=data.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )

    logger.info(f"管理员更新用户信息: user_id={user_id}")

    return UserUpdateResponse(
        success=True,
        message=message,
        user=UserItem(
            id=user.id,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            role=user.role.value,
            status=user.status.value if user.status else UserStatus.ACTIVE.value,
            created_at=user.created_at,
        ),
    )


@router.delete(
    "/{user_id}",
    response_model=UserDeleteResponse,
    summary="删除用户",
    description="删除用户（软删除，设置状态为已停用）",
    responses={404: {"description": "用户不存在"}},
)
async def delete_user(
    user_id: str,
    _admin_id: AdminUserId,
    service: AdminUserServiceDep,
) -> UserDeleteResponse:
    """删除用户"""
    result = await service.delete_user(user_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    logger.info(f"管理员删除用户: user_id={user_id}")

    return UserDeleteResponse(
        success=True,
        message="用户已删除",
    )


@router.post(
    "",
    response_model=UserCreateResponse,
    summary="创建用户",
    description="管理员创建新用户",
    responses={400: {"description": "创建失败"}},
)
async def create_user(
    data: UserCreateRequest,
    _admin_id: AdminUserId,
    service: AdminUserServiceDep,
) -> UserCreateResponse:
    """创建新用户"""
    user, message = await service.create_user(
        username=data.username,
        email=data.email,
        password=data.password,
        role=data.role,
        display_name=data.display_name,
    )

    if user is None:
        return UserCreateResponse(
            success=False,
            message=message,
            user=None,
        )

    logger.info(f"管理员创建用户: username={data.username}")

    return UserCreateResponse(
        success=True,
        message=message,
        user=UserItem(
            id=user.id,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            role=user.role.value,
            status=user.status.value if user.status else UserStatus.ACTIVE.value,
            created_at=user.created_at,
        ),
    )


@router.get(
    "/export",
    summary="导出用户",
    description="导出用户列表为 CSV 文件",
)
async def export_users(
    _admin_id: AdminUserId,
    service: AdminUserServiceDep,
    search: str | None = Query(None, description="搜索关键词"),
    role: str | None = Query(None, description="角色筛选"),
    status: str | None = Query(None, description="状态筛选"),
) -> StreamingResponse:
    """导出用户列表为 CSV"""
    users = await service.export_users(search=search, role=role, status=status)

    # 生成 CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # 写入表头
    writer.writerow(["用户名", "邮箱", "显示名称", "角色", "状态", "创建时间"])

    # 写入数据
    for user in users:
        writer.writerow([
            user["username"],
            user["email"],
            user["display_name"],
            user["role"],
            user["status"],
            user["created_at"],
        ])

    output.seek(0)

    # 添加 BOM 以支持 Excel 正确识别 UTF-8 编码
    csv_content = '\ufeff' + output.getvalue()

    logger.info(f"管理员导出用户: count={len(users)}")

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=users_export.csv",
        },
    )


@router.post(
    "/import",
    response_model=UserImportResponse,
    summary="导入用户",
    description="从 CSV 文件批量导入用户",
)
async def import_users(
    _admin_id: AdminUserId,
    service: AdminUserServiceDep,
    file: Annotated[UploadFile, File(..., description="CSV 文件")],
) -> UserImportResponse:
    """从 CSV 文件导入用户"""
    # 验证文件类型
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请上传 CSV 格式的文件",
        )

    # 读取文件内容
    try:
        content = await file.read()
        # 尝试不同编码
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("gbk")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件读取失败: {str(e)}",
        ) from e

    # 解析 CSV
    try:
        reader = csv.DictReader(io.StringIO(text))
        users_data = []

        # 字段映射（支持中英文表头）
        field_mapping = {
            "用户名": "username",
            "username": "username",
            "邮箱": "email",
            "email": "email",
            "密码": "password",
            "password": "password",
            "角色": "role",
            "role": "role",
            "显示名称": "display_name",
            "display_name": "display_name",
        }

        for row in reader:
            user_data = {}
            for key, value in row.items():
                mapped_key = field_mapping.get(key.strip().lower(), key.strip().lower())
                if mapped_key in ["username", "email", "password", "role", "display_name"]:
                    user_data[mapped_key] = value
            users_data.append(user_data)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV 解析失败: {str(e)}",
        ) from e

    if not users_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV 文件为空或格式不正确",
        )

    # 执行导入
    result = await service.import_users(users_data)

    logger.info(
        f"管理员导入用户: total={result['total']}, "
        f"created={result['created']}, failed={result['failed']}"
    )

    return UserImportResponse(
        success=result["failed"] == 0,
        total=result["total"],
        created=result["created"],
        failed=result["failed"],
        skipped=result["skipped"],
        details=result["details"],
    )
