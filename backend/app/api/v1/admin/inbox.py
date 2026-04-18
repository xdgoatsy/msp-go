"""管理员信箱 API - 密码重置审批"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import AdminUserId, DbSession
from app.api.v1.schemas.password_reset import (
    PasswordResetListResponse,
    PasswordResetRequestItem,
    PasswordResetReviewRequest,
    PasswordResetReviewResponse,
)
from app.domain.models.password_reset import PasswordResetStatus
from app.services.password_reset_service import PasswordResetService

router = APIRouter()


def get_password_reset_service(db: DbSession) -> PasswordResetService:
    """获取密码重置服务"""
    return PasswordResetService(db)


PasswordResetServiceDep = Annotated[
    PasswordResetService, Depends(get_password_reset_service)
]


@router.get("", response_model=PasswordResetListResponse)
async def list_password_reset_requests(
    admin_id: AdminUserId,
    service: PasswordResetServiceDep,
    status: Annotated[str | None, Query(description="状态筛选: pending/approved/rejected")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PasswordResetListResponse:
    """获取密码重置申请列表"""
    status_filter = PasswordResetStatus(status) if status else None
    items, total, pending_count = await service.list_requests(
        status_filter=status_filter, page=page, page_size=page_size
    )
    return PasswordResetListResponse(
        items=[PasswordResetRequestItem.model_validate(item) for item in items],
        total=total,
        pending_count=pending_count,
    )


@router.get("/pending-count")
async def get_pending_count(
    admin_id: AdminUserId,
    service: PasswordResetServiceDep,
) -> dict[str, int]:
    """获取待处理申请数量（用于侧边栏徽标）"""
    count = await service.get_pending_count()
    return {"pending_count": count}


@router.post("/{request_id}/review", response_model=PasswordResetReviewResponse)
async def review_password_reset(
    request_id: str,
    body: PasswordResetReviewRequest,
    admin_id: AdminUserId,
    service: PasswordResetServiceDep,
) -> PasswordResetReviewResponse:
    """审批密码重置申请"""
    success, message, temp_password = await service.review_request(
        request_id=request_id,
        admin_id=admin_id,
        action=body.action,
        reject_reason=body.reject_reason,
    )
    return PasswordResetReviewResponse(
        success=success,
        message=message,
        temp_password=temp_password,
    )
