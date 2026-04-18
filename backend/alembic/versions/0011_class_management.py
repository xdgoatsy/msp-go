"""新增班级管理与学生绑定

Revision ID: 0011_class_management
Revises: 0010_nullable_max_tokens_top_p
Create Date: 2026-02-04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0011_class_management"
down_revision: str | None = "0010_nullable_max_tokens_top_p"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "classes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=12), nullable=False),
        sa.Column("teacher_id", sa.String(length=36), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"]),
    )
    op.create_index("ix_classes_code", "classes", ["code"], unique=True)
    op.create_index("ix_classes_teacher_id", "classes", ["teacher_id"], unique=False)

    op.create_table(
        "class_enrollments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("class_id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column("joined_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["class_id"], ["classes.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"]),
        sa.UniqueConstraint("class_id", "student_id", name="uq_class_enrollment"),
        sa.UniqueConstraint("student_id", name="uq_class_enrollment_student"),
    )
    op.create_index(
        "ix_class_enrollments_class_id",
        "class_enrollments",
        ["class_id"],
        unique=False,
    )
    op.create_index(
        "ix_class_enrollments_student_id",
        "class_enrollments",
        ["student_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_class_enrollments_student_id", table_name="class_enrollments")
    op.drop_index("ix_class_enrollments_class_id", table_name="class_enrollments")
    op.drop_table("class_enrollments")
    op.drop_index("ix_classes_teacher_id", table_name="classes")
    op.drop_index("ix_classes_code", table_name="classes")
    op.drop_table("classes")
