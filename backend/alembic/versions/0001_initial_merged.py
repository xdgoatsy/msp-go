"""initial merged schema

Revision ID: 0001_initial_merged
Revises:
Create Date: 2026-01-27

合并迁移内容：
1. AI 配置相关表
2. 核心业务表
3. users.status + users.last_login_at
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial_merged"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1) AI 配置相关表
    op.create_table(
        "llm_providers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "name",
            sa.String(100),
            unique=True,
            nullable=False,
            index=True,
            comment="显示名称，如 DeepSeek",
        ),
        sa.Column(
            "code",
            sa.String(50),
            unique=True,
            nullable=False,
            index=True,
            comment="代码标识，如 deepseek",
        ),
        sa.Column(
            "base_url",
            sa.String(500),
            nullable=False,
            comment="API Base URL",
        ),
        sa.Column(
            "encrypted_api_key",
            sa.Text,
            nullable=False,
            comment="Fernet 加密的 API Key",
        ),
        sa.Column(
            "is_active",
            sa.Boolean,
            default=True,
            nullable=False,
            comment="是否启用",
        ),
        sa.Column("description", sa.Text, nullable=True, comment="描述信息"),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    op.create_table(
        "llm_models",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "provider_id",
            sa.String(36),
            sa.ForeignKey("llm_providers.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "name",
            sa.String(100),
            nullable=False,
            comment="显示名称，如 DeepSeek Chat",
        ),
        sa.Column(
            "model_id",
            sa.String(100),
            nullable=False,
            comment="API 模型 ID，如 deepseek-chat",
        ),
        sa.Column(
            "default_temperature",
            sa.Float,
            default=0.7,
            nullable=False,
            comment="默认温度参数",
        ),
        sa.Column(
            "default_max_tokens",
            sa.Integer,
            default=2048,
            nullable=False,
            comment="默认最大 Token 数",
        ),
        sa.Column(
            "default_top_p",
            sa.Float,
            default=0.9,
            nullable=False,
            comment="默认 Top P 参数",
        ),
        sa.Column(
            "default_timeout",
            sa.Integer,
            default=60,
            nullable=False,
            comment="默认超时时间（秒）",
        ),
        sa.Column(
            "default_max_retries",
            sa.Integer,
            default=3,
            nullable=False,
            comment="默认最大重试次数",
        ),
        sa.Column(
            "is_active",
            sa.Boolean,
            default=True,
            nullable=False,
            comment="是否启用",
        ),
        sa.Column(
            "is_default",
            sa.Boolean,
            default=False,
            nullable=False,
            comment="是否为全局默认模型",
        ),
        sa.Column(
            "capabilities",
            sa.JSON,
            default=dict,
            nullable=False,
            comment="模型能力标签，如 {chat: true, vision: false}",
        ),
        sa.Column("description", sa.Text, nullable=True, comment="描述信息"),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.UniqueConstraint("provider_id", "model_id", name="uq_provider_model"),
    )

    op.create_table(
        "agent_model_configs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "agent_type",
            sa.String(50),
            unique=True,
            nullable=False,
            index=True,
            comment="智能体类型，如 orchestrator, solver",
        ),
        sa.Column(
            "model_id",
            sa.String(36),
            sa.ForeignKey("llm_models.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
            comment="关联的模型 ID",
        ),
        sa.Column(
            "temperature_override",
            sa.Float,
            nullable=True,
            comment="温度参数覆盖",
        ),
        sa.Column(
            "max_tokens_override",
            sa.Integer,
            nullable=True,
            comment="最大 Token 数覆盖",
        ),
        sa.Column(
            "top_p_override",
            sa.Float,
            nullable=True,
            comment="Top P 覆盖",
        ),
        sa.Column(
            "timeout_override",
            sa.Integer,
            nullable=True,
            comment="超时时间覆盖（秒）",
        ),
        sa.Column(
            "max_retries_override",
            sa.Integer,
            nullable=True,
            comment="最大重试次数覆盖",
        ),
        sa.Column(
            "extra_config",
            sa.JSON,
            default=dict,
            nullable=False,
            comment="智能体特定的额外配置",
        ),
        sa.Column(
            "is_active",
            sa.Boolean,
            default=True,
            nullable=False,
            comment="是否启用",
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # 2) 核心业务表
    # 注意: content_embeddings 表需要 pgvector 扩展，暂时跳过
    # 如需启用向量检索功能，请先在 PostgreSQL 上安装 pgvector 扩展:
    # 1. 安装 pgvector: https://github.com/pgvector/pgvector
    # 2. 执行: CREATE EXTENSION IF NOT EXISTS vector;
    # 3. 取消下方 content_embeddings 表创建的注释

    op.create_table(
        "content_audit",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("content_id", sa.String(length=36), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=False),
        sa.Column(
            "action",
            sa.Enum(
                "CREATE",
                "UPDATE",
                "PUBLISH",
                "ARCHIVE",
                "DELETE",
                "BULK_IMPORT",
                "ACL_GRANT",
                "ACL_REVOKE",
                name="auditaction",
            ),
            nullable=False,
        ),
        sa.Column("at", sa.DateTime(), nullable=False),
        sa.Column("diff", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_content_audit_actor_user_id"),
        "content_audit",
        ["actor_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_content_audit_at"),
        "content_audit",
        ["at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_content_audit_content_id"),
        "content_audit",
        ["content_id"],
        unique=False,
    )

    op.create_table(
        "embedding_models",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("dim", sa.Integer(), nullable=False),
        sa.Column(
            "distance",
            sa.Enum("COSINE", "L2", "IP", name="distancemetric"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("name"),
    )
    op.create_index(
        op.f("ix_embedding_models_is_active"),
        "embedding_models",
        ["is_active"],
        unique=False,
    )

    op.create_table(
        "knowledge_nodes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("name_en", sa.String(length=200), nullable=True),
        sa.Column(
            "node_type",
            sa.Enum(
                "CONCEPT",
                "THEOREM",
                "METHOD",
                "PROBLEM",
                "MISCONCEPTION",
                "RESOURCE",
                name="nodetype",
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("chapter", sa.String(length=100), nullable=True),
        sa.Column("section", sa.String(length=100), nullable=True),
        sa.Column("difficulty", sa.Float(), nullable=False),
        sa.Column("latex_formula", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_knowledge_nodes_name"),
        "knowledge_nodes",
        ["name"],
        unique=False,
    )

    op.create_table(
        "outbox_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "CONTENT_CHANGED",
                "CONTENT_DELETED",
                "CONTENT_PUBLISHED",
                "CONTENT_ARCHIVED",
                "CONTENT_KNOWLEDGE_LINKED",
                "EMBEDDING_REQUIRED",
                name="outboxeventtype",
            ),
            nullable=False,
        ),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_outbox_events_processed_at"),
        "outbox_events",
        ["processed_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_outbox_events_type"),
        "outbox_events",
        ["type"],
        unique=False,
    )
    op.create_index(
        "ix_outbox_pending",
        "outbox_events",
        ["processed_at", "created_at"],
        unique=False,
    )
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE userstatus AS ENUM ('ACTIVE', 'INACTIVE', 'SUSPENDED');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    userstatus_enum = pg.ENUM(
        "ACTIVE",
        "INACTIVE",
        "SUSPENDED",
        name="userstatus",
        create_type=False,
    )

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=100), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("STUDENT", "TEACHER", "ADMIN", name="userrole",create_type=False),
            nullable=False,
        ),
        sa.Column("display_name", sa.String(length=100), nullable=True),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "status",
            userstatus_enum,
            nullable=False,
        ),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    op.create_index(op.f("ix_users_status"), "users", ["status"], unique=False)
    op.create_index(
        op.f("ix_users_last_login_at"),
        "users",
        ["last_login_at"],
        unique=False,
    )

    op.create_table(
        "contents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "type",
            sa.Enum("PROBLEM", "NOTE", "VIDEO", "ARTICLE", name="contenttype"),
            nullable=False,
        ),
        sa.Column("owner_teacher_id", sa.String(length=36), nullable=False),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "PUBLISHED", "ARCHIVED", name="contentstatus"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("difficulty", sa.Float(), nullable=False),
        sa.Column("concept_ids", sa.JSON(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["owner_teacher_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_contents_deleted_at"),
        "contents",
        ["deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_contents_owner_status",
        "contents",
        ["owner_teacher_id", "status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_contents_owner_teacher_id"),
        "contents",
        ["owner_teacher_id"],
        unique=False,
    )
    op.create_index(
        "ix_contents_published",
        "contents",
        ["status", "deleted_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_contents_status"),
        "contents",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_contents_type"),
        "contents",
        ["type"],
        unique=False,
    )

    op.create_table(
        "import_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "PROBLEMS_BULK_UPSERT",
                "PROBLEMS_BULK_DELETE",
                "NOTES_BULK_UPSERT",
                name="importjobkind",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "RUNNING",
                "SUCCEEDED",
                "FAILED",
                "CANCELLED",
                name="importjobstatus",
            ),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("stats", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_import_jobs_created_by"),
        "import_jobs",
        ["created_by"],
        unique=False,
    )
    op.create_index(
        op.f("ix_import_jobs_status"),
        "import_jobs",
        ["status"],
        unique=False,
    )

    op.create_table(
        "knowledge_relations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_id", sa.String(length=36), nullable=False),
        sa.Column("target_id", sa.String(length=36), nullable=False),
        sa.Column(
            "relation_type",
            sa.Enum(
                "HAS_PREREQUISITE",
                "IS_A_SPECIAL_CASE_OF",
                "USED_IN",
                "PRONE_TO_ERROR",
                "RELATED_TO",
                name="relationtype",
            ),
            nullable=False,
        ),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["knowledge_nodes.id"]),
        sa.ForeignKeyConstraint(["target_id"], ["knowledge_nodes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_knowledge_relations_source_id"),
        "knowledge_relations",
        ["source_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_relations_target_id"),
        "knowledge_relations",
        ["target_id"],
        unique=False,
    )

    op.create_table(
        "learning_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("current_topic", sa.String(length=36), nullable=True),
        sa.Column("current_content_id", sa.String(length=36), nullable=True),
        sa.Column("contents_attempted", sa.JSON(), nullable=False),
        sa.Column("concepts_discussed", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_learning_sessions_student_id"),
        "learning_sessions",
        ["student_id"],
        unique=False,
    )

    op.create_table(
        "student_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column("mastery_vector", sa.JSON(), nullable=False),
        sa.Column("error_tendency", sa.JSON(), nullable=False),
        sa.Column("preferred_difficulty", sa.Float(), nullable=False),
        sa.Column("learning_pace", sa.Float(), nullable=False),
        sa.Column("total_exercises", sa.Integer(), nullable=False),
        sa.Column("correct_count", sa.Integer(), nullable=False),
        sa.Column("total_study_time_minutes", sa.Integer(), nullable=False),
        sa.Column("recent_concepts", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id"),
    )

    op.create_table(
        "content_acl",
        sa.Column("content_id", sa.String(length=36), nullable=False),
        sa.Column("teacher_id", sa.String(length=36), nullable=False),
        sa.Column(
            "permission",
            sa.Enum("EDITOR", "ADMIN", name="aclpermission"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["content_id"], ["contents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("content_id", "teacher_id"),
    )
    op.create_index(
        op.f("ix_content_acl_teacher_id"),
        "content_acl",
        ["teacher_id"],
        unique=False,
    )

    op.create_table(
        "content_assets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("content_id", sa.String(length=36), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "VIDEO",
                "IMAGE",
                "PDF",
                "AUDIO",
                "ATTACHMENT",
                name="assetkind",
            ),
            nullable=False,
        ),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["content_id"], ["contents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_content_assets_content_id"),
        "content_assets",
        ["content_id"],
        unique=False,
    )

    op.create_table(
        "content_attempts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("content_id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column("student_answer", sa.Text(), nullable=False),
        sa.Column("student_steps", sa.JSON(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("time_spent_seconds", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["content_id"], ["contents.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_content_attempts_content_id"),
        "content_attempts",
        ["content_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_content_attempts_student_id"),
        "content_attempts",
        ["student_id"],
        unique=False,
    )

    # 注意: content_embeddings 表需要 pgvector 扩展，暂时跳过
    # op.create_table(
    #     "content_embeddings",
    #     sa.Column("content_id", sa.String(length=36), nullable=False),
    #     sa.Column("model_name", sa.String(length=100), nullable=False),
    #     sa.Column("embedding", Vector(1536), nullable=True),
    #     sa.Column("updated_at", sa.DateTime(), nullable=False),
    #     sa.ForeignKeyConstraint(["content_id"], ["contents.id"], ondelete="CASCADE"),
    #     sa.ForeignKeyConstraint(["model_name"], ["embedding_models.name"]),
    #     sa.PrimaryKeyConstraint("content_id", "model_name"),
    # )

    op.create_table(
        "session_messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column(
            "role",
            sa.Enum("USER", "ASSISTANT", "SYSTEM", name="messagerole"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "agent_type",
            sa.Enum(
                "ORCHESTRATOR",
                "SOLVER",
                "DIAGNOSTICIAN",
                "TUTOR",
                "PLANNER",
                name="agenttype",
            ),
            nullable=True,
        ),
        sa.Column("attachments", sa.JSON(), nullable=False),
        sa.Column("related_concept_ids", sa.JSON(), nullable=False),
        sa.Column("related_content_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["learning_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_session_messages_session_id"),
        "session_messages",
        ["session_id"],
        unique=False,
    )

    op.create_table(
        "diagnosis_reports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("attempt_id", sa.String(length=36), nullable=False),
        sa.Column("error_step_index", sa.Integer(), nullable=True),
        sa.Column("bifurcation_point", sa.Text(), nullable=True),
        sa.Column(
            "error_type",
            sa.Enum(
                "CONCEPTUAL",
                "PROCEDURAL",
                "LOGICAL",
                "SYMBOLIC",
                name="errortype",
            ),
            nullable=True,
        ),
        sa.Column("error_subtype", sa.String(length=100), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("related_concept_ids", sa.JSON(), nullable=False),
        sa.Column("related_misconception_ids", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("suggestion", sa.Text(), nullable=False),
        sa.Column("recommended_resources", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["attempt_id"], ["content_attempts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("attempt_id"),
    )


def downgrade() -> None:
    op.drop_table("diagnosis_reports")
    op.drop_index(op.f("ix_session_messages_session_id"), table_name="session_messages")
    op.drop_table("session_messages")
    # op.drop_table("content_embeddings")  # 需要 pgvector 扩展
    op.drop_index(op.f("ix_content_attempts_student_id"), table_name="content_attempts")
    op.drop_index(op.f("ix_content_attempts_content_id"), table_name="content_attempts")
    op.drop_table("content_attempts")
    op.drop_index(op.f("ix_content_assets_content_id"), table_name="content_assets")
    op.drop_table("content_assets")
    op.drop_index(op.f("ix_content_acl_teacher_id"), table_name="content_acl")
    op.drop_table("content_acl")
    op.drop_table("student_profiles")
    op.drop_index(
        op.f("ix_learning_sessions_student_id"), table_name="learning_sessions"
    )
    op.drop_table("learning_sessions")
    op.drop_index(
        op.f("ix_knowledge_relations_target_id"), table_name="knowledge_relations"
    )
    op.drop_index(
        op.f("ix_knowledge_relations_source_id"), table_name="knowledge_relations"
    )
    op.drop_table("knowledge_relations")
    op.drop_index(op.f("ix_import_jobs_status"), table_name="import_jobs")
    op.drop_index(op.f("ix_import_jobs_created_by"), table_name="import_jobs")
    op.drop_table("import_jobs")
    op.drop_index(op.f("ix_contents_type"), table_name="contents")
    op.drop_index(op.f("ix_contents_status"), table_name="contents")
    op.drop_index("ix_contents_published", table_name="contents")
    op.drop_index(op.f("ix_contents_owner_teacher_id"), table_name="contents")
    op.drop_index("ix_contents_owner_status", table_name="contents")
    op.drop_index(op.f("ix_contents_deleted_at"), table_name="contents")
    op.drop_table("contents")
    op.drop_index(op.f("ix_users_last_login_at"), table_name="users")
    op.drop_index(op.f("ix_users_status"), table_name="users")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    userstatus_enum = sa.Enum("ACTIVE", "INACTIVE", "SUSPENDED", name="userstatus")
    userstatus_enum.drop(op.get_bind(), checkfirst=True)
    op.drop_index("ix_outbox_pending", table_name="outbox_events")
    op.drop_index(op.f("ix_outbox_events_type"), table_name="outbox_events")
    op.drop_index(op.f("ix_outbox_events_processed_at"), table_name="outbox_events")
    op.drop_table("outbox_events")
    op.drop_index(op.f("ix_knowledge_nodes_name"), table_name="knowledge_nodes")
    op.drop_table("knowledge_nodes")
    op.drop_index(op.f("ix_embedding_models_is_active"), table_name="embedding_models")
    op.drop_table("embedding_models")
    op.drop_index(op.f("ix_content_audit_content_id"), table_name="content_audit")
    op.drop_index(op.f("ix_content_audit_at"), table_name="content_audit")
    op.drop_index(op.f("ix_content_audit_actor_user_id"), table_name="content_audit")
    op.drop_table("content_audit")
    op.drop_table("agent_model_configs")
    op.drop_table("llm_models")
    op.drop_table("llm_providers")
