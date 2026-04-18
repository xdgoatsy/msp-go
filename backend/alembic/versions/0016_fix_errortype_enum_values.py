"""fix_errortype_enum_values

Revision ID: 0016_fix_errortype_enum_values
Revises: 0015_mistake_book_indexes
Create Date: 2026-02-14 13:04:04.738010

修复 errortype 枚举值：
1. 将大写值改为小写（CONCEPTUAL -> conceptual）
2. 添加缺失的 calculation 值
"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0016_fix_errortype_enum_values'
down_revision: str | None = '0015_mistake_book_indexes'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # PostgreSQL 枚举类型修改需要特殊处理
    # 步骤：
    # 1. 创建新的枚举类型（小写 + calculation）
    # 2. 修改列类型为新枚举
    # 3. 删除旧枚举类型

    # 创建新的枚举类型
    op.execute("CREATE TYPE errortype_new AS ENUM ('conceptual', 'procedural', 'logical', 'symbolic', 'calculation')")

    # 修改列类型（使用 USING 子句转换现有值）
    op.execute("""
        ALTER TABLE diagnosis_reports
        ALTER COLUMN error_type TYPE errortype_new
        USING (
            CASE error_type::text
                WHEN 'CONCEPTUAL' THEN 'conceptual'::errortype_new
                WHEN 'PROCEDURAL' THEN 'procedural'::errortype_new
                WHEN 'LOGICAL' THEN 'logical'::errortype_new
                WHEN 'SYMBOLIC' THEN 'symbolic'::errortype_new
                ELSE NULL
            END
        )
    """)

    # 删除旧枚举类型
    op.execute("DROP TYPE errortype")

    # 重命名新枚举类型
    op.execute("ALTER TYPE errortype_new RENAME TO errortype")


def downgrade() -> None:
    # 回滚：将小写改回大写，移除 calculation
    op.execute("CREATE TYPE errortype_old AS ENUM ('CONCEPTUAL', 'PROCEDURAL', 'LOGICAL', 'SYMBOLIC')")

    op.execute("""
        ALTER TABLE diagnosis_reports
        ALTER COLUMN error_type TYPE errortype_old
        USING (
            CASE error_type::text
                WHEN 'conceptual' THEN 'CONCEPTUAL'::errortype_old
                WHEN 'procedural' THEN 'PROCEDURAL'::errortype_old
                WHEN 'logical' THEN 'LOGICAL'::errortype_old
                WHEN 'symbolic' THEN 'SYMBOLIC'::errortype_old
                WHEN 'calculation' THEN NULL
                ELSE NULL
            END
        )
    """)

    op.execute("DROP TYPE errortype")
    op.execute("ALTER TYPE errortype_old RENAME TO errortype")
