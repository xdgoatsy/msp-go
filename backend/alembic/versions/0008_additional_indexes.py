"""添加额外性能优化索引

Revision ID: 0008_additional_indexes
Revises: 0007_xidian_cookie_persist
Create Date: 2026-02-06

为用户状态统计和活跃会话查询添加复合索引
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008_additional_indexes"
down_revision: str | None = "0007_xidian_cookie_persist"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # users(status, role) - 用户状态统计查询优化
    # 用于 get_account_stats 按 status 分组统计
    op.create_index(
        "ix_users_status_role",
        "users",
        ["status", "role"],
        unique=False,
    )

    # learning_sessions(student_id, is_active) - 活跃会话查询优化
    # 用于查询某学生的活跃会话
    op.create_index(
        "ix_learning_sessions_student_active",
        "learning_sessions",
        ["student_id", "is_active"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_learning_sessions_student_active", table_name="learning_sessions")
    op.drop_index("ix_users_status_role", table_name="users")
