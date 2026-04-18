"""Add indexes for mistake book queries

Revision ID: 0015_mistake_book_indexes
Revises: 0014_password_reset_requests
Create Date: 2026-02-13

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0015_mistake_book_indexes'
down_revision: str | None = '0014_password_reset_requests'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 为 content_attempts 表添加复合索引，优化错题查询
    op.create_index(
        'ix_content_attempts_student_submitted',
        'content_attempts',
        ['student_id', 'submitted_at'],
        unique=False
    )

    # 为 content_attempts 表添加 is_correct 索引，快速筛选错题
    op.create_index(
        'ix_content_attempts_is_correct',
        'content_attempts',
        ['is_correct'],
        unique=False
    )

    # 为 diagnosis_reports 表添加 attempt_id 索引，优化联表查询
    op.create_index(
        'ix_diagnosis_reports_attempt_id',
        'diagnosis_reports',
        ['attempt_id'],
        unique=False
    )

    # 为 diagnosis_reports 表添加 error_type 索引，支持按错误类型筛选
    op.create_index(
        'ix_diagnosis_reports_error_type',
        'diagnosis_reports',
        ['error_type'],
        unique=False
    )

    # 为 diagnosis_reports 表添加 severity 索引，支持按严重程度排序
    op.create_index(
        'ix_diagnosis_reports_severity',
        'diagnosis_reports',
        ['severity'],
        unique=False
    )


def downgrade() -> None:
    # 删除所有创建的索引
    op.drop_index('ix_diagnosis_reports_severity', table_name='diagnosis_reports')
    op.drop_index('ix_diagnosis_reports_error_type', table_name='diagnosis_reports')
    op.drop_index('ix_diagnosis_reports_attempt_id', table_name='diagnosis_reports')
    op.drop_index('ix_content_attempts_is_correct', table_name='content_attempts')
    op.drop_index('ix_content_attempts_student_submitted', table_name='content_attempts')
