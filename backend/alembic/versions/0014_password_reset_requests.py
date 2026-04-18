"""password_reset_requests

Revision ID: 0014_password_reset_requests
Revises: 0013_cleanup_agent_types
Create Date: 2026-02-12 12:00:00.000000

新增密码重置申请表，支持用户提交重置申请、管理员审批
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0014_password_reset_requests"
down_revision: str | None = "0013_cleanup_agent_types"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 创建密码重置申请表（枚举类型由 create_table 自动创建）
    password_reset_status = sa.Enum(
        "pending", "approved", "rejected", name="passwordresetstatus"
    )

    op.create_table(
        "password_reset_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("email", sa.String(100), nullable=False),
        sa.Column("reason", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "status",
            password_reset_status,
            server_default="pending",
            nullable=False,
        ),
        sa.Column("reviewed_by", sa.String(36), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # 创建索引
    op.create_index("ix_password_reset_user_id", "password_reset_requests", ["user_id"])
    op.create_index("ix_password_reset_status", "password_reset_requests", ["status"])
    op.create_index(
        "ix_password_reset_created_at", "password_reset_requests", ["created_at"]
    )
    op.create_index(
        "ix_password_reset_status_created",
        "password_reset_requests",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_password_reset_status_created", "password_reset_requests")
    op.drop_index("ix_password_reset_created_at", "password_reset_requests")
    op.drop_index("ix_password_reset_status", "password_reset_requests")
    op.drop_index("ix_password_reset_user_id", "password_reset_requests")
    op.drop_table("password_reset_requests")

    # 删除枚举类型
    sa.Enum(name="passwordresetstatus").drop(op.get_bind(), checkfirst=True)
