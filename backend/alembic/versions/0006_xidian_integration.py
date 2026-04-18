"""新增西电账号绑定与教务数据快照

Revision ID: 0006_xidian_integration
Revises: 0005_performance_indexes
Create Date: 2026-02-04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006_xidian_integration"
down_revision: str | None = "0005_performance_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "xidian_accounts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("encrypted_password", sa.Text(), nullable=False),
        sa.Column("is_postgraduate", sa.Boolean(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("last_verified_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index(
        "ix_xidian_accounts_user_id",
        "xidian_accounts",
        ["user_id"],
        unique=True,
    )
    op.create_index(
        "ix_xidian_accounts_username",
        "xidian_accounts",
        ["username"],
        unique=False,
    )

    op.create_table(
        "xidian_snapshots",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("data_type", sa.String(length=20), nullable=False),
        sa.Column("semester_code", sa.String(length=20), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index(
        "ix_xidian_snapshots_user_type_fetched",
        "xidian_snapshots",
        ["user_id", "data_type", "fetched_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_xidian_snapshots_user_type_fetched", table_name="xidian_snapshots")
    op.drop_table("xidian_snapshots")
    op.drop_index("ix_xidian_accounts_username", table_name="xidian_accounts")
    op.drop_index("ix_xidian_accounts_user_id", table_name="xidian_accounts")
    op.drop_table("xidian_accounts")
