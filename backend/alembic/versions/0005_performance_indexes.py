"""添加性能优化索引

Revision ID: 0005_performance_indexes
Revises: 0004_user_favorites
Create Date: 2026-01-28

为高频查询添加复合索引，提升查询性能
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_performance_indexes"
down_revision: str | None = "0004_user_favorites"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. learning_sessions(student_id, started_at) - 活跃度查询优化
    # 用于统计今日活跃用户、用户学习历史等查询
    op.create_index(
        "ix_learning_sessions_student_started",
        "learning_sessions",
        ["student_id", "started_at"],
        unique=False,
    )

    # 2. contents(owner_teacher_id, deleted_at) - 教师资源查询优化
    # 用于教师查看自己的资源列表
    op.create_index(
        "ix_contents_owner_deleted",
        "contents",
        ["owner_teacher_id", "deleted_at"],
        unique=False,
    )

    # 3. contents(status, deleted_at, type) - 资源列表查询优化
    # 用于学生浏览已发布资源
    op.create_index(
        "ix_contents_status_deleted_type",
        "contents",
        ["status", "deleted_at", "type"],
        unique=False,
    )

    # 4. security_logs(user_id, created_at) - 用户安全日志查询优化
    op.create_index(
        "ix_security_logs_user_created",
        "security_logs",
        ["user_id", "created_at"],
        unique=False,
    )

    # 5. security_logs(event_type, created_at) - 按事件类型查询优化
    op.create_index(
        "ix_security_logs_event_created",
        "security_logs",
        ["event_type", "created_at"],
        unique=False,
    )

    # 6. users(is_active, role) - 用户统计查询优化
    # 用于管理员统计各角色用户数
    op.create_index(
        "ix_users_active_role",
        "users",
        ["is_active", "role"],
        unique=False,
    )

    # 7. users(created_at, is_active) - 用户增长趋势查询优化
    op.create_index(
        "ix_users_created_active",
        "users",
        ["created_at", "is_active"],
        unique=False,
    )

    # 注意: user_favorites(user_id, content_id) 索引已在 0004 迁移中通过唯一约束创建
    # 无需重复创建


def downgrade() -> None:
    op.drop_index("ix_users_created_active", table_name="users")
    op.drop_index("ix_users_active_role", table_name="users")
    op.drop_index("ix_security_logs_event_created", table_name="security_logs")
    op.drop_index("ix_security_logs_user_created", table_name="security_logs")
    op.drop_index("ix_contents_status_deleted_type", table_name="contents")
    op.drop_index("ix_contents_owner_deleted", table_name="contents")
    op.drop_index("ix_learning_sessions_student_started", table_name="learning_sessions")
