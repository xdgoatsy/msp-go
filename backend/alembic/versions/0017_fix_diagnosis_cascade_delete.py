"""fix diagnosis cascade delete

Revision ID: 0017
Revises: 0016
Create Date: 2026-02-14 15:30:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0017_diagnosis_cascade'
down_revision: str | None = '0016_fix_errortype_enum_values'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """添加级联删除到 diagnosis_reports.attempt_id 外键"""
    # 1. 删除旧的外键约束
    op.drop_constraint(
        'diagnosis_reports_attempt_id_fkey',
        'diagnosis_reports',
        type_='foreignkey'
    )

    # 2. 创建新的外键约束，添加 CASCADE 删除
    op.create_foreign_key(
        'diagnosis_reports_attempt_id_fkey',
        'diagnosis_reports',
        'content_attempts',
        ['attempt_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """回滚：移除级联删除"""
    # 1. 删除带 CASCADE 的外键约束
    op.drop_constraint(
        'diagnosis_reports_attempt_id_fkey',
        'diagnosis_reports',
        type_='foreignkey'
    )

    # 2. 恢复原来的外键约束（无 CASCADE）
    op.create_foreign_key(
        'diagnosis_reports_attempt_id_fkey',
        'diagnosis_reports',
        'content_attempts',
        ['attempt_id'],
        ['id']
    )
