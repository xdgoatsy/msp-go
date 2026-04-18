"""新增用户收藏表

Revision ID: 0004_user_favorites
Revises: 0003_security_logs
Create Date: 2026-01-28

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_user_favorites"
down_revision: str | None = "0003_security_logs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 创建用户收藏表
    op.create_table(
        "user_favorites",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "content_id",
            sa.String(36),
            sa.ForeignKey("contents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # 创建索引
    op.create_index("ix_user_favorites_user_id", "user_favorites", ["user_id"])
    op.create_index("ix_user_favorites_content_id", "user_favorites", ["content_id"])
    op.create_index(
        "ix_user_favorites_user_content",
        "user_favorites",
        ["user_id", "content_id"],
        unique=True,
    )


def downgrade() -> None:
    # 删除索引
    op.drop_index("ix_user_favorites_user_content", table_name="user_favorites")
    op.drop_index("ix_user_favorites_content_id", table_name="user_favorites")
    op.drop_index("ix_user_favorites_user_id", table_name="user_favorites")

    # 删除表
    op.drop_table("user_favorites")
