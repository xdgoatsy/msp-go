"""密码重置 API Schema"""

from datetime import datetime

from pydantic import BaseModel, Field

# =============================================================================
# 用户端（公开接口）
# =============================================================================


class PasswordResetSubmitRequest(BaseModel):
    """提交密码重置申请"""

    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: str = Field(..., description="注册邮箱")
    reason: str = Field("", max_length=500, description="申请理由")


class PasswordResetSubmitResponse(BaseModel):
    """提交申请响应"""

    success: bool
    message: str
    request_id: str | None = None


class PasswordResetStatusResponse(BaseModel):
    """查询申请状态响应"""

    has_pending: bool = Field(..., description="是否有待处理的申请")
    status: str | None = Field(None, description="最近一次申请状态")
    created_at: datetime | None = Field(None, description="申请时间")


# =============================================================================
# 管理员端
# =============================================================================


class PasswordResetRequestItem(BaseModel):
    """管理员查看的申请列表项"""

    id: str
    user_id: str
    username: str
    email: str
    reason: str
    status: str
    created_at: datetime
    reviewed_at: datetime | None = None

    model_config = {"from_attributes": True}


class PasswordResetListResponse(BaseModel):
    """申请列表响应"""

    items: list[PasswordResetRequestItem]
    total: int
    pending_count: int


class PasswordResetReviewRequest(BaseModel):
    """审批请求"""

    action: str = Field(..., pattern="^(approve|reject)$", description="approve 或 reject")
    reject_reason: str | None = Field(None, max_length=500, description="拒绝理由")


class PasswordResetReviewResponse(BaseModel):
    """审批响应"""

    success: bool
    message: str
    temp_password: str | None = None
