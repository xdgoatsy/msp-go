"""Phase 3: 性能优化索引补充

Revision ID: 0019_performance_indexes_phase3
Revises: 0018_add_bkt_tables
Create Date: 2026-02-22
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0019_performance_indexes_phase3"
down_revision: str | None = "0018_add_bkt_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 自适应选题热路径：按教师+状态+类型+难度筛选
    op.create_index(
        "ix_contents_teacher_published_difficulty",
        "contents",
        ["owner_teacher_id", "status", "type", "difficulty"],
        postgresql_where="deleted_at IS NULL",
    )

    # 学生最近作答：用于排除已做题目
    op.create_index(
        "ix_content_attempts_student_recent",
        "content_attempts",
        ["student_id", "started_at"],
        postgresql_ops={"started_at": "DESC"},
    )

    # BKT 状态查询优化
    op.create_index(
        "ix_student_concept_bkt_student",
        "student_concept_bkt_states",
        ["student_id"],
    )

    # 管理员统计：按角色+活跃+创建时间
    op.create_index(
        "ix_users_role_active_created",
        "users",
        ["role", "is_active", "created_at"],
        postgresql_where="is_active = true",
    )


def downgrade() -> None:
    op.drop_index("ix_users_role_active_created", table_name="users")
    op.drop_index("ix_student_concept_bkt_student", table_name="student_concept_bkt_states")
    op.drop_index("ix_content_attempts_student_recent", table_name="content_attempts")
    op.drop_index("ix_contents_teacher_published_difficulty", table_name="contents")
