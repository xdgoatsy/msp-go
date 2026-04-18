"""add BKT tables

Revision ID: 0018
Revises: 0017
Create Date: 2026-02-17 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0018_add_bkt_tables'
down_revision: str | None = '0017_diagnosis_cascade'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建 BKT 相关表：concept_bkt_params 和 student_concept_bkt_states"""

    # 1. 知识点 BKT 默认参数表
    op.create_table(
        'concept_bkt_params',
        sa.Column('concept_id', sa.String(128), primary_key=True),
        sa.Column('p_l0', sa.Float(), nullable=False, server_default='0.25'),
        sa.Column('p_t', sa.Float(), nullable=False, server_default='0.12'),
        sa.Column('p_g', sa.Float(), nullable=False, server_default='0.20'),
        sa.Column('p_s', sa.Float(), nullable=False, server_default='0.10'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # 2. 学生-知识点 BKT 状态表
    op.create_table(
        'student_concept_bkt_states',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('student_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('concept_id', sa.String(128), nullable=False),
        sa.Column('mastery_prob', sa.Float(), nullable=False, server_default='0.25'),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('correct_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('incorrect_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('p_l0', sa.Float(), nullable=False, server_default='0.25'),
        sa.Column('p_t', sa.Float(), nullable=False, server_default='0.12'),
        sa.Column('p_g', sa.Float(), nullable=False, server_default='0.20'),
        sa.Column('p_s', sa.Float(), nullable=False, server_default='0.10'),
        sa.Column('last_outcome', sa.Boolean(), nullable=True),
        sa.Column('last_attempt_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # 3. 唯一约束：每个学生每个知识点只有一条状态记录
    op.create_unique_constraint(
        'uq_student_concept_bkt_state',
        'student_concept_bkt_states',
        ['student_id', 'concept_id'],
    )

    # 4. 索引
    op.create_index('ix_bkt_student', 'student_concept_bkt_states', ['student_id'])
    op.create_index('ix_bkt_concept', 'student_concept_bkt_states', ['concept_id'])
    op.create_index('ix_bkt_updated_at', 'student_concept_bkt_states', ['updated_at'])


def downgrade() -> None:
    """删除 BKT 相关表"""
    op.drop_index('ix_bkt_updated_at', table_name='student_concept_bkt_states')
    op.drop_index('ix_bkt_concept', table_name='student_concept_bkt_states')
    op.drop_index('ix_bkt_student', table_name='student_concept_bkt_states')
    op.drop_constraint('uq_student_concept_bkt_state', 'student_concept_bkt_states', type_='unique')
    op.drop_table('student_concept_bkt_states')
    op.drop_table('concept_bkt_params')
