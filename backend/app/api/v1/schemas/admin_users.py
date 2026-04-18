"""
管理员用户管理 API Schema

定义用户管理 API 请求和响应的数据结构
"""

from datetime import datetime

from pydantic import BaseModel, Field

# ========== 统计 Schema ==========


class UserAccountStats(BaseModel):
    """用户账户统计"""

    total: int = Field(..., description="总账户数")
    active: int = Field(..., description="活跃账户数")
    suspended: int = Field(..., description="已停用账户数")


# ========== 用户列表 Schema ==========


class UserItem(BaseModel):
    """用户列表项"""

    id: str = Field(..., description="用户 ID")
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱")
    display_name: str | None = Field(None, description="显示名称")
    role: str = Field(..., description="角色: student/teacher/admin")
    status: str = Field(..., description="状态: active/suspended")
    created_at: datetime = Field(..., description="创建时间")

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """用户列表响应（分页）"""

    items: list[UserItem] = Field(..., description="用户列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    total_pages: int = Field(..., description="总页数")


# ========== 状态更新 Schema ==========


class UserStatusUpdate(BaseModel):
    """用户状态更新请求"""

    status: str = Field(
        ...,
        pattern=r"^(active|suspended)$",
        description="新状态: active/suspended",
    )


class UserStatusUpdateResponse(BaseModel):
    """用户状态更新响应"""

    success: bool = Field(True, description="是否成功")
    message: str = Field(..., description="消息")
    user: UserItem = Field(..., description="更新后的用户信息")


# ========== 删除 Schema ==========


class UserDeleteResponse(BaseModel):
    """用户删除响应"""

    success: bool = Field(True, description="是否成功")
    message: str = Field(..., description="消息")


# ========== 更新用户 Schema ==========


class UserUpdateRequest(BaseModel):
    """更新用户请求"""

    display_name: str | None = Field(None, max_length=100, description="显示名称")
    password: str | None = Field(None, min_length=6, description="新密码（可选，不填则不修改）")


class UserUpdateResponse(BaseModel):
    """更新用户响应"""

    success: bool = Field(True, description="是否成功")
    message: str = Field(..., description="消息")
    user: UserItem = Field(..., description="更新后的用户信息")


# ========== 创建用户 Schema ==========


class UserCreateRequest(BaseModel):
    """创建用户请求"""

    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: str = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, description="密码")
    role: str = Field(
        "student",
        pattern=r"^(student|teacher|admin)$",
        description="角色: student/teacher/admin",
    )
    display_name: str | None = Field(None, max_length=100, description="显示名称")


class UserCreateResponse(BaseModel):
    """创建用户响应"""

    success: bool = Field(True, description="是否成功")
    message: str = Field(..., description="消息")
    user: UserItem | None = Field(None, description="创建的用户信息")


# ========== 导入用户 Schema ==========


class UserImportResult(BaseModel):
    """单个用户导入结果"""

    row: int = Field(..., description="行号")
    username: str = Field(..., description="用户名")
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="结果消息")


class UserImportResponse(BaseModel):
    """用户导入响应"""

    success: bool = Field(..., description="整体是否成功")
    total: int = Field(..., description="总行数")
    created: int = Field(..., description="成功创建数")
    failed: int = Field(..., description="失败数")
    skipped: int = Field(..., description="跳过数（已存在）")
    details: list[UserImportResult] = Field(default_factory=list, description="详细结果")
