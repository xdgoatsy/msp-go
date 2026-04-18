"""
SQLAlchemy ORM 模型

定义数据库表结构
"""

from datetime import datetime
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.content import (
    AclPermission,
    AssetKind,
    AuditAction,
    ContentStatus,
    ContentType,
    ImportJobKind,
    ImportJobStatus,
    OutboxEventType,
)
from app.domain.models.embedding import DistanceMetric
from app.domain.models.exercise import ErrorType
from app.domain.models.knowledge_node import NodeType, RelationType
from app.domain.models.learning_session import AgentType, MessageRole
from app.domain.models.password_reset import PasswordResetStatus
from app.domain.models.security_log import SecurityEventType, SecuritySeverity
from app.domain.models.student import UserRole, UserStatus
from app.infrastructure.database.session import Base


def generate_uuid() -> str:
    """生成 UUID 字符串"""
    return str(uuid4())


# =============================================================================
# 用户与学生画像
# =============================================================================


class UserModel(Base):
    """用户表"""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.STUDENT)
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus), default=UserStatus.ACTIVE, index=True
    )
    display_name: Mapped[str | None] = mapped_column(String(100))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)

    # 关系
    profile: Mapped["StudentProfileModel"] = relationship(back_populates="student")
    sessions: Mapped[list["LearningSessionModel"]] = relationship(
        back_populates="student"
    )
    owned_contents: Mapped[list["ContentModel"]] = relationship(
        back_populates="owner", foreign_keys="ContentModel.owner_teacher_id"
    )
    favorites: Mapped[list["UserFavoriteModel"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    xidian_account: Mapped["XidianAccountModel"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    teaching_classes: Mapped[list["ClassModel"]] = relationship(
        back_populates="teacher", cascade="all, delete-orphan"
    )
    class_enrollment: Mapped["ClassEnrollmentModel | None"] = relationship(
        back_populates="student", uselist=False, cascade="all, delete-orphan"
    )


class StudentProfileModel(Base):
    """学生画像表"""

    __tablename__ = "student_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), unique=True
    )

    # JSON 字段存储复杂数据
    mastery_vector: Mapped[dict] = mapped_column(JSON, default=dict)
    error_tendency: Mapped[dict] = mapped_column(JSON, default=dict)

    preferred_difficulty: Mapped[float] = mapped_column(Float, default=0.5)
    learning_pace: Mapped[float] = mapped_column(Float, default=1.0)

    total_exercises: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    total_study_time_minutes: Mapped[int] = mapped_column(Integer, default=0)

    recent_concepts: Mapped[list] = mapped_column(JSON, default=list)

    # 学生画像（AI 生成）
    portrait_content: Mapped[str | None] = mapped_column(Text, default=None)
    portrait_generated_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    portrait_version: Mapped[int] = mapped_column(Integer, default=0)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    # 关系
    student: Mapped["UserModel"] = relationship(back_populates="profile")


class ConceptBKTParamModel(Base):
    """知识点 BKT 默认参数表"""

    __tablename__ = "concept_bkt_params"

    # 与 content.concept_ids 保持兼容，不强制外键约束
    concept_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    p_l0: Mapped[float] = mapped_column(Float, default=0.25)
    p_t: Mapped[float] = mapped_column(Float, default=0.12)
    p_g: Mapped[float] = mapped_column(Float, default=0.20)
    p_s: Mapped[float] = mapped_column(Float, default=0.10)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class StudentConceptBKTStateModel(Base):
    """学生-知识点 BKT 状态表"""

    __tablename__ = "student_concept_bkt_states"
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "concept_id",
            name="uq_student_concept_bkt_state",
        ),
        Index("ix_bkt_student", "student_id"),
        Index("ix_bkt_concept", "concept_id"),
        Index("ix_bkt_updated_at", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    student_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    concept_id: Mapped[str] = mapped_column(String(128))

    mastery_prob: Mapped[float] = mapped_column(Float, default=0.25)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    incorrect_count: Mapped[int] = mapped_column(Integer, default=0)

    p_l0: Mapped[float] = mapped_column(Float, default=0.25)
    p_t: Mapped[float] = mapped_column(Float, default=0.12)
    p_g: Mapped[float] = mapped_column(Float, default=0.20)
    p_s: Mapped[float] = mapped_column(Float, default=0.10)

    last_outcome: Mapped[bool | None] = mapped_column(Boolean)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )


# =============================================================================
# 班级管理
# =============================================================================


class ClassModel(Base):
    """班级表"""

    __tablename__ = "classes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    teacher_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), index=True
    )
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    teacher: Mapped["UserModel"] = relationship(
        back_populates="teaching_classes", foreign_keys=[teacher_id]
    )
    enrollments: Mapped[list["ClassEnrollmentModel"]] = relationship(
        back_populates="class_info", cascade="all, delete-orphan"
    )


class ClassEnrollmentModel(Base):
    """班级学生绑定表（学生只能加入一个班级）"""

    __tablename__ = "class_enrollments"
    __table_args__ = (
        UniqueConstraint("class_id", "student_id", name="uq_class_enrollment"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    class_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("classes.id"), index=True
    )
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), unique=True, index=True
    )
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    class_info: Mapped["ClassModel"] = relationship(back_populates="enrollments")
    student: Mapped["UserModel"] = relationship(back_populates="class_enrollment")


# =============================================================================
# 西电账号绑定
# =============================================================================


class XidianAccountModel(Base):
    """西电账号绑定表"""

    __tablename__ = "xidian_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), unique=True, index=True
    )
    username: Mapped[str] = mapped_column(String(50), index=True)
    encrypted_password: Mapped[str] = mapped_column(Text)
    is_postgraduate: Mapped[bool | None] = mapped_column(Boolean, default=None)
    status: Mapped[str] = mapped_column(String(20), default="active")
    session_cookies: Mapped[dict | None] = mapped_column(JSON, default=None)
    cookies_updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    user: Mapped["UserModel"] = relationship(back_populates="xidian_account")


class XidianSnapshotModel(Base):
    """西电教务数据快照表"""

    __tablename__ = "xidian_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), index=True
    )
    data_type: Mapped[str] = mapped_column(String(20), index=True)
    semester_code: Mapped[str | None] = mapped_column(String(20))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# =============================================================================
# 知识图谱
# =============================================================================


class KnowledgeNodeModel(Base):
    """知识节点表"""

    __tablename__ = "knowledge_nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(200), index=True)
    name_en: Mapped[str | None] = mapped_column(String(200))
    node_type: Mapped[NodeType] = mapped_column(Enum(NodeType))
    description: Mapped[str] = mapped_column(Text, default="")
    chapter: Mapped[str | None] = mapped_column(String(100))
    section: Mapped[str | None] = mapped_column(String(100))
    difficulty: Mapped[float] = mapped_column(Float, default=0.5)
    latex_formula: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )


class KnowledgeRelationModel(Base):
    """知识关系表"""

    __tablename__ = "knowledge_relations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    source_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_nodes.id"), index=True
    )
    target_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_nodes.id"), index=True
    )
    relation_type: Mapped[RelationType] = mapped_column(Enum(RelationType))
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# =============================================================================
# 内容管理（核心）
# =============================================================================


class ContentModel(Base):
    """
    内容表

    统一管理题目、讲义、视频等内容
    约束：对外展示/检索必须满足 status='published' AND deleted_at IS NULL
    """

    __tablename__ = "contents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    type: Mapped[ContentType] = mapped_column(Enum(ContentType), index=True)
    owner_teacher_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), index=True
    )
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus), default=ContentStatus.DRAFT, index=True
    )

    title: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text)  # 支持 LaTeX/Markdown

    difficulty: Mapped[float] = mapped_column(Float, default=0.5)
    concept_ids: Mapped[list] = mapped_column(JSON, default=list)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)  # 扩展元数据

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)

    # 关系
    owner: Mapped["UserModel"] = relationship(
        back_populates="owned_contents", foreign_keys=[owner_teacher_id]
    )
    assets: Mapped[list["ContentAssetModel"]] = relationship(
        back_populates="content", cascade="all, delete-orphan"
    )
    acl_entries: Mapped[list["ContentAclModel"]] = relationship(
        back_populates="content", cascade="all, delete-orphan"
    )
    favorited_by: Mapped[list["UserFavoriteModel"]] = relationship(
        back_populates="content", cascade="all, delete-orphan"
    )

    # 复合索引：公开内容查询优化
    __table_args__ = (
        Index("ix_contents_published", "status", "deleted_at"),
        Index("ix_contents_owner_status", "owner_teacher_id", "status"),
    )


class ContentAssetModel(Base):
    """
    内容附件表

    视频、图片、PDF 等附件元数据
    """

    __tablename__ = "content_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    content_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contents.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[AssetKind] = mapped_column(Enum(AssetKind))
    url: Mapped[str] = mapped_column(String(1000))  # 对象存储 URL
    meta: Mapped[dict] = mapped_column(JSON, default=dict)  # 时长、封面、大小等
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # 关系
    content: Mapped["ContentModel"] = relationship(back_populates="assets")


class ContentAclModel(Base):
    """
    内容协作权限表

    用于多人协作编辑场景
    """

    __tablename__ = "content_acl"

    content_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contents.id", ondelete="CASCADE"), primary_key=True
    )
    teacher_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), primary_key=True, index=True
    )
    permission: Mapped[AclPermission] = mapped_column(Enum(AclPermission))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # 关系
    content: Mapped["ContentModel"] = relationship(back_populates="acl_entries")


# =============================================================================
# 向量检索
# =============================================================================


class EmbeddingModelModel(Base):
    """
    Embedding 模型版本表

    管理不同维度/版本的 embedding 模型
    约束：同时只能有一个 is_active=True 的模型用于在线写入
    """

    __tablename__ = "embedding_models"

    name: Mapped[str] = mapped_column(String(100), primary_key=True)
    dim: Mapped[int] = mapped_column(Integer)
    distance: Mapped[DistanceMetric] = mapped_column(
        Enum(DistanceMetric), default=DistanceMetric.COSINE
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class ContentEmbeddingModel(Base):
    """
    内容向量表

    存储内容的 embedding 向量
    使用 pgvector/VectorChord 的 vector 类型
    """

    __tablename__ = "content_embeddings"

    content_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contents.id", ondelete="CASCADE"), primary_key=True
    )
    model_name: Mapped[str] = mapped_column(
        String(100), ForeignKey("embedding_models.name"), primary_key=True
    )
    # 使用 pgvector 的 Vector 类型，维度 1536 (OpenAI 兼容)
    embedding = mapped_column(Vector(1536))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )


# =============================================================================
# 审计与导入
# =============================================================================


class ContentAuditModel(Base):
    """
    内容审计日志表

    记录所有变更操作
    """

    __tablename__ = "content_audit"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    content_id: Mapped[str] = mapped_column(String(36), index=True)  # 不设外键，保留已删除内容的审计
    actor_user_id: Mapped[str] = mapped_column(String(36), index=True)
    action: Mapped[AuditAction] = mapped_column(Enum(AuditAction))
    at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    diff: Mapped[dict] = mapped_column(JSON, default=dict)  # 变更详情


class ImportJobModel(Base):
    """
    批量导入任务表

    支持大批量数据导入的任务管理
    """

    __tablename__ = "import_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    kind: Mapped[ImportJobKind] = mapped_column(Enum(ImportJobKind))
    status: Mapped[ImportJobStatus] = mapped_column(
        Enum(ImportJobStatus), default=ImportJobStatus.PENDING, index=True
    )
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)

    params: Mapped[dict] = mapped_column(JSON, default=dict)
    stats: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    error_message: Mapped[str | None] = mapped_column(Text)


class OutboxEventModel(Base):
    """
    事件发件箱表

    用于可靠的事件发布，支持重试和回放
    """

    __tablename__ = "outbox_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    type: Mapped[OutboxEventType] = mapped_column(Enum(OutboxEventType), index=True)
    payload: Mapped[dict] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)

    # 索引：待处理事件查询
    __table_args__ = (Index("ix_outbox_pending", "processed_at", "created_at"),)


# =============================================================================
# 学习会话
# =============================================================================


class LearningSessionModel(Base):
    """学习会话表"""

    __tablename__ = "learning_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    current_topic: Mapped[str | None] = mapped_column(String(36))
    current_content_id: Mapped[str | None] = mapped_column(String(36))
    contents_attempted: Mapped[list] = mapped_column(JSON, default=list)
    concepts_discussed: Mapped[list] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)

    # 关系
    student: Mapped["UserModel"] = relationship(back_populates="sessions")
    messages: Mapped[list["SessionMessageModel"]] = relationship(
        back_populates="session"
    )


class SessionMessageModel(Base):
    """会话消息表"""

    __tablename__ = "session_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("learning_sessions.id"), index=True
    )
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole))
    content: Mapped[str] = mapped_column(Text)
    agent_type: Mapped[AgentType | None] = mapped_column(Enum(AgentType))
    attachments: Mapped[list] = mapped_column(JSON, default=list)
    related_concept_ids: Mapped[list] = mapped_column(JSON, default=list)
    related_content_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # 关系
    session: Mapped["LearningSessionModel"] = relationship(back_populates="messages")


# =============================================================================
# 练习尝试与诊断（保留，关联到 Content）
# =============================================================================


class ContentAttemptModel(Base):
    """
    内容尝试记录表

    记录学生对题目的作答
    """

    __tablename__ = "content_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    content_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contents.id"), index=True
    )
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), index=True
    )
    student_answer: Mapped[str] = mapped_column(Text)
    student_steps: Mapped[list] = mapped_column(JSON, default=list)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0)


class DiagnosisReportModel(Base):
    """诊断报告表"""

    __tablename__ = "diagnosis_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    attempt_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("content_attempts.id", ondelete="CASCADE"), unique=True
    )
    error_step_index: Mapped[int | None] = mapped_column(Integer)
    bifurcation_point: Mapped[str | None] = mapped_column(Text)
    # 使用 Enum.value（如 "procedural"）而不是 Enum.name（如 "PROCEDURAL"），
    # 以匹配数据库 errortype 枚举（小写）以及领域模型的定义。
    error_type: Mapped[ErrorType | None] = mapped_column(
        Enum(ErrorType, values_callable=lambda x: [e.value for e in x])
    )
    error_subtype: Mapped[str | None] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    related_concept_ids: Mapped[list] = mapped_column(JSON, default=list)
    related_misconception_ids: Mapped[list] = mapped_column(JSON, default=list)
    explanation: Mapped[str] = mapped_column(Text, default="")
    suggestion: Mapped[str] = mapped_column(Text, default="")
    recommended_resources: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# =============================================================================
# 系统配置
# =============================================================================


class SystemSettingModel(Base):
    """
    系统配置表

    存储系统级别的配置项，如注册开关等
    """

    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text)  # JSON 字符串
    description: Mapped[str] = mapped_column(String(500), default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )


# =============================================================================
# 安全日志
# =============================================================================


class SecurityLogModel(Base):
    """
    安全日志表

    记录系统安全事件：异常登录、请求异常、服务异常等
    无异常时每日生成安全报告
    """

    __tablename__ = "security_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    event_type: Mapped[SecurityEventType] = mapped_column(
        Enum(SecurityEventType, values_callable=lambda x: [e.value for e in x]),
        index=True,
    )
    severity: Mapped[SecuritySeverity] = mapped_column(
        Enum(SecuritySeverity, values_callable=lambda x: [e.value for e in x]),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    ip_address: Mapped[str | None] = mapped_column(String(45))  # 支持 IPv6
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    username: Mapped[str | None] = mapped_column(String(50))  # 冗余存储，便于查询
    extra_data: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, index=True
    )

    # 复合索引：按日期和类型查询
    __table_args__ = (
        Index("ix_security_logs_date_type", "created_at", "event_type"),
        Index("ix_security_logs_archived_date", "archived", "created_at"),
    )


# =============================================================================
# 用户收藏
# =============================================================================


class UserFavoriteModel(Base):
    """
    用户收藏表

    记录用户收藏的资源内容
    """

    __tablename__ = "user_favorites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    content_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contents.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # 关系
    user: Mapped["UserModel"] = relationship(back_populates="favorites")
    content: Mapped["ContentModel"] = relationship(back_populates="favorited_by")

    # 联合唯一约束
    __table_args__ = (
        Index("ix_user_favorites_user_content", "user_id", "content_id", unique=True),
    )


# =============================================================================
# 密码重置申请
# =============================================================================


class PasswordResetRequestModel(Base):
    """
    密码重置申请表

    用户提交申请后由管理员审批，审批通过后密码重置为默认值
    """

    __tablename__ = "password_reset_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    username: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(100))
    reason: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[PasswordResetStatus] = mapped_column(
        Enum(PasswordResetStatus, values_callable=lambda x: [e.value for e in x]),
        default=PasswordResetStatus.PENDING,
        index=True,
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(36))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    reject_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, index=True
    )

    __table_args__ = (
        Index("ix_password_reset_status_created", "status", "created_at"),
    )


