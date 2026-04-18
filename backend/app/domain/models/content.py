"""
内容领域模型

定义内容、附件、权限、审计、导入任务、事件等实体
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ContentType(str, Enum):
    """内容类型"""

    PROBLEM = "problem"  # 题目
    NOTE = "note"  # 讲义/笔记
    VIDEO = "video"  # 视频
    ARTICLE = "article"  # 文章


class ContentStatus(str, Enum):
    """内容状态"""

    DRAFT = "draft"  # 草稿
    PUBLISHED = "published"  # 已发布
    ARCHIVED = "archived"  # 已归档


class AssetKind(str, Enum):
    """附件类型"""

    VIDEO = "video"
    IMAGE = "image"
    PDF = "pdf"
    AUDIO = "audio"
    ATTACHMENT = "attachment"  # 其他附件


class AclPermission(str, Enum):
    """协作权限"""

    EDITOR = "editor"  # 可编辑
    ADMIN = "admin"  # 可管理（含删除、授权）


class AuditAction(str, Enum):
    """审计动作"""

    CREATE = "create"
    UPDATE = "update"
    PUBLISH = "publish"
    ARCHIVE = "archive"
    DELETE = "delete"
    BULK_IMPORT = "bulk_import"
    ACL_GRANT = "acl_grant"
    ACL_REVOKE = "acl_revoke"


class ImportJobKind(str, Enum):
    """导入任务类型"""

    PROBLEMS_BULK_UPSERT = "problems_bulk_upsert"
    PROBLEMS_BULK_DELETE = "problems_bulk_delete"
    NOTES_BULK_UPSERT = "notes_bulk_upsert"


class ImportJobStatus(str, Enum):
    """导入任务状态"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OutboxEventType(str, Enum):
    """事件类型"""

    CONTENT_CHANGED = "content_changed"
    CONTENT_DELETED = "content_deleted"
    CONTENT_PUBLISHED = "content_published"
    CONTENT_ARCHIVED = "content_archived"
    CONTENT_KNOWLEDGE_LINKED = "content_knowledge_linked"
    EMBEDDING_REQUIRED = "embedding_required"


@dataclass
class Content:
    """
    内容实体

    核心业务对象，包含题目、讲义、视频等
    """

    id: str
    type: ContentType
    owner_teacher_id: str
    status: ContentStatus
    title: str
    body: str  # 支持 LaTeX/Markdown

    # 可选字段
    difficulty: float = 0.5  # 0-1 难度系数
    concept_ids: list[str] = field(default_factory=list)  # 关联知识点
    tags: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)  # 扩展元数据

    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    published_at: datetime | None = None
    deleted_at: datetime | None = None

    @property
    def is_visible(self) -> bool:
        """是否对外可见"""
        return self.status == ContentStatus.PUBLISHED and self.deleted_at is None


@dataclass
class ContentAsset:
    """
    内容附件

    视频、图片、PDF 等附件元数据
    """

    id: str
    content_id: str
    kind: AssetKind
    url: str  # 对象存储 URL
    meta: dict[str, Any] = field(default_factory=dict)  # 时长、封面、大小等
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ContentAcl:
    """
    内容协作权限

    用于多人协作编辑场景
    """

    content_id: str
    teacher_id: str
    permission: AclPermission
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ContentAudit:
    """
    内容审计日志

    记录所有变更操作
    """

    id: str
    content_id: str
    actor_user_id: str
    action: AuditAction
    at: datetime = field(default_factory=datetime.now)
    diff: dict[str, Any] = field(default_factory=dict)  # 变更详情


@dataclass
class ImportJob:
    """
    批量导入任务

    支持大批量数据导入的任务管理
    """

    id: str
    kind: ImportJobKind
    status: ImportJobStatus
    created_by: str  # 创建者 user_id

    params: dict[str, Any] = field(default_factory=dict)  # 导入参数
    stats: dict[str, Any] = field(default_factory=dict)  # 统计信息

    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str | None = None


@dataclass
class OutboxEvent:
    """
    事件发件箱

    用于可靠的事件发布，支持重试和回放
    """

    id: str
    type: OutboxEventType
    payload: dict[str, Any]

    created_at: datetime = field(default_factory=datetime.now)
    processed_at: datetime | None = None
    retry_count: int = 0
    last_error: str | None = None

    @property
    def is_pending(self) -> bool:
        """是否待处理"""
        return self.processed_at is None
