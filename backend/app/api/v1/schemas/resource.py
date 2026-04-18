"""
资源 Schema

定义资源相关的请求/响应模型
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ResourceType(str, Enum):
    """资源类型"""

    VIDEO = "video"
    DOCUMENT = "document"


class StorageType(str, Enum):
    """存储类型"""

    LOCAL = "local"  # 本地文件系统
    CLOUD = "cloud"  # 云存储
    EXTERNAL = "external"  # 外部链接


# =============================================================================
# 请求模型
# =============================================================================


class ResourceCreate(BaseModel):
    """创建资源请求"""

    title: str = Field(..., min_length=1, max_length=500, description="资源标题")
    type: ResourceType = Field(..., description="资源类型")
    body: str = Field(default="", description="资源描述/内容")
    chapter: str | None = Field(default=None, max_length=100, description="所属章节")
    topic: str | None = Field(default=None, max_length=100, description="主题")
    tags: list[str] = Field(default_factory=list, description="标签")
    difficulty: float = Field(default=0.5, ge=0, le=1, description="难度系数")

    # 附件信息
    storage_type: StorageType = Field(
        default=StorageType.EXTERNAL, description="存储类型"
    )
    url: str | None = Field(default=None, description="资源 URL")
    duration: str | None = Field(default=None, description="视频时长")
    pages: int | None = Field(default=None, ge=1, description="文档页数")
    source: str | None = Field(default=None, max_length=200, description="来源")


class ResourceUpdate(BaseModel):
    """更新资源请求"""

    title: str | None = Field(default=None, min_length=1, max_length=500)
    type: ResourceType | None = None
    body: str | None = None
    chapter: str | None = None
    topic: str | None = None
    tags: list[str] | None = None
    difficulty: float | None = Field(default=None, ge=0, le=1)
    storage_type: StorageType | None = None
    url: str | None = None
    duration: str | None = None
    pages: int | None = Field(default=None, ge=1)
    source: str | None = None


class ResourceFilter(BaseModel):
    """资源筛选参数"""

    type: ResourceType | None = None
    chapter: str | None = None
    topic: str | None = None
    search: str | None = Field(default=None, description="搜索关键词")
    favorites_only: bool = Field(default=False, description="仅显示收藏")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


# =============================================================================
# 响应模型
# =============================================================================


class ResourceAsset(BaseModel):
    """资源附件信息"""

    id: str
    kind: str
    url: str
    storage_type: StorageType
    meta: dict[str, Any] = Field(default_factory=dict)


class ResourceResponse(BaseModel):
    """资源响应"""

    id: str
    title: str
    type: ResourceType
    body: str = ""  # 列表查询时可能为空，详情查询时包含完整内容
    chapter: str | None
    topic: str | None
    tags: list[str]
    difficulty: float
    source: str | None

    # 附件信息
    url: str | None
    storage_type: StorageType | None
    duration: str | None
    pages: int | None

    # 统计信息
    views: int
    likes: int

    # 收藏状态
    is_favorite: bool

    # 创建者信息
    owner_id: str
    owner_name: str | None

    # 时间戳
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ResourceListResponse(BaseModel):
    """资源列表响应"""

    items: list[ResourceResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class ResourceStats(BaseModel):
    """资源统计"""

    total: int
    videos: int
    documents: int
    favorites: int


class FavoriteToggleResponse(BaseModel):
    """收藏切换响应"""

    resource_id: str
    is_favorite: bool
    message: str
