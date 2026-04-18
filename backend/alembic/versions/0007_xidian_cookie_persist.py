"""XidianAccountModel 新增 Cookie 持久化字段

Revision ID: 0007_xidian_cookie_persist
Revises: 0006_xidian_integration
Create Date: 2026-02-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007_xidian_cookie_persist"
down_revision: str | None = "0006_xidian_integration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "xidian_accounts",
        sa.Column("session_cookies", sa.JSON(), nullable=True),
    )
    op.add_column(
        "xidian_accounts",
        sa.Column("cookies_updated_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("xidian_accounts", "cookies_updated_at")
    op.drop_column("xidian_accounts", "session_cookies")
