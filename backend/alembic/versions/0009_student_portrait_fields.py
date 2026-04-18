"""添加学生画像字段

Revision ID: 0009_student_portrait_fields
Revises: 0008_additional_indexes
Create Date: 2026-02-07

在 student_profiles 表上新增 AI 生成画像相关字段
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009_student_portrait_fields"
down_revision: str | None = "0008_additional_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "student_profiles",
        sa.Column("portrait_content", sa.Text(), nullable=True),
    )
    op.add_column(
        "student_profiles",
        sa.Column("portrait_generated_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "student_profiles",
        sa.Column(
            "portrait_version", sa.Integer(), nullable=False, server_default="0"
        ),
    )


def downgrade() -> None:
    op.drop_column("student_profiles", "portrait_version")
    op.drop_column("student_profiles", "portrait_generated_at")
    op.drop_column("student_profiles", "portrait_content")
