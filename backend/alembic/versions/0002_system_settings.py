"""创建系统配置表

Revision ID: 0002_system_settings
Revises: 0001_initial_merged
Create Date: 2026-01-27

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_system_settings"
down_revision: str | None = "0001_initial_merged"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 创建系统配置表
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("description", sa.String(500), nullable=False, server_default=""),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # 插入默认配置
    op.execute(
        """
        INSERT INTO system_settings (key, value, description, updated_at)
        VALUES
            ('allow_student_registration', 'true', '是否允许学生注册', NOW()),
            ('allow_teacher_registration', 'true', '是否允许教师注册', NOW())
        """
    )


def downgrade() -> None:
    op.drop_table("system_settings")
