"""将 llm_models 表的 default_max_tokens 和 default_top_p 改为 nullable

Revision ID: 0010_nullable_max_tokens_top_p
Revises: 0009_student_portrait_fields
Create Date: 2026-02-07

允许模型级别的 max_tokens 和 top_p 为空，
当为空时 LLM API 调用不传递这两个参数，让模型使用自身默认值。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0010_nullable_max_tokens_top_p"
down_revision: str | None = "0009_student_portrait_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "llm_models",
        "default_max_tokens",
        existing_type=sa.Integer(),
        nullable=True,
        existing_comment="默认最大 Token 数",
    )
    op.alter_column(
        "llm_models",
        "default_top_p",
        existing_type=sa.Float(),
        nullable=True,
        existing_comment="默认 Top P 参数",
    )


def downgrade() -> None:
    # 回滚时将 NULL 值填充为默认值，然后改回 NOT NULL
    op.execute("UPDATE llm_models SET default_max_tokens = 2048 WHERE default_max_tokens IS NULL")
    op.alter_column(
        "llm_models",
        "default_max_tokens",
        existing_type=sa.Integer(),
        nullable=False,
        existing_comment="默认最大 Token 数",
    )
    op.execute("UPDATE llm_models SET default_top_p = 0.9 WHERE default_top_p IS NULL")
    op.alter_column(
        "llm_models",
        "default_top_p",
        existing_type=sa.Float(),
        nullable=False,
        existing_comment="默认 Top P 参数",
    )
