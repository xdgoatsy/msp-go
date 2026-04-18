"""knowledge_graph_seed_data

Revision ID: 0012_knowledge_graph_seed_data
Revises: 0011_class_management
Create Date: 2026-02-09 00:48:18.721167

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0012_knowledge_graph_seed_data'
down_revision: str | None = '0011_class_management'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """导入初始知识图谱数据"""

    # 使用原生 SQL 插入数据，通过 CAST 转换枚举类型
    conn = op.get_bind()

    # 插入知识节点
    conn.execute(sa.text("""
        INSERT INTO knowledge_nodes (id, name, name_en, node_type, description, chapter, section, difficulty, latex_formula, tags, created_at, updated_at)
        VALUES
        (gen_random_uuid(), '极限', 'Limit', 'CONCEPT'::nodetype, '极限是微积分的基础概念，描述函数在某点附近的变化趋势。', '第一章', '1.1', 0.4, '\\lim_{x \\to a} f(x) = L', '["基础概念", "微积分"]'::jsonb, NOW(), NOW()),
        (gen_random_uuid(), '导数', 'Derivative', 'CONCEPT'::nodetype, '导数描述函数在某点的瞬时变化率，是微分学的核心概念。', '第二章', '2.1', 0.5, 'f''(x) = \\lim_{h \\to 0} \\frac{f(x+h) - f(x)}{h}', '["基础概念", "微分学"]'::jsonb, NOW(), NOW()),
        (gen_random_uuid(), '洛必达法则', 'L''Hôpital''s Rule', 'THEOREM'::nodetype, '洛必达法则用于求解不定式极限，通过求导简化计算。', '第二章', '2.3', 0.6, '\\lim_{x \\to a} \\frac{f(x)}{g(x)} = \\lim_{x \\to a} \\frac{f''(x)}{g''(x)}', '["定理", "极限计算"]'::jsonb, NOW(), NOW()),
        (gen_random_uuid(), '泰勒公式', 'Taylor Formula', 'THEOREM'::nodetype, '泰勒公式将函数展开为多项式形式，用于函数逼近和误差分析。', '第三章', '3.2', 0.7, 'f(x) = \\sum_{n=0}^{\\infty} \\frac{f^{(n)}(a)}{n!}(x-a)^n', '["定理", "级数展开"]'::jsonb, NOW(), NOW()),
        (gen_random_uuid(), '不定积分', 'Indefinite Integral', 'CONCEPT'::nodetype, '不定积分是导数的逆运算，求原函数的过程。', '第四章', '4.1', 0.5, '\\int f(x) dx = F(x) + C', '["基础概念", "积分学"]'::jsonb, NOW(), NOW()),
        (gen_random_uuid(), '分部积分法', 'Integration by Parts', 'METHOD'::nodetype, '分部积分法用于求解复杂函数的积分，是处理乘积函数的导数的重要方法。', '第四章', '4.3', 0.6, '\\int u dv = uv - \\int v du', '["积分方法", "技巧"]'::jsonb, NOW(), NOW()),
        (gen_random_uuid(), '定积分', 'Definite Integral', 'CONCEPT'::nodetype, '定积分表示函数在区间上的累积量，具有明确的几何和物理意义。', '第五章', '5.1', 0.6, '\\int_a^b f(x) dx', '["基础概念", "积分学"]'::jsonb, NOW(), NOW()),
        (gen_random_uuid(), '微分中值定理', 'Mean Value Theorem', 'THEOREM'::nodetype, '微分中值定理揭示了函数在区间上的平均变化率与某点导数的关系。', '第二章', '2.4', 0.6, 'f''(c) = \\frac{f(b) - f(a)}{b - a}', '["定理", "微分学"]'::jsonb, NOW(), NOW())
    """))

    # 获取插入的节点 ID（通过名称查询）
    result = conn.execute(sa.text("""
        SELECT id, name FROM knowledge_nodes
        WHERE name IN ('极限', '导数', '洛必达法则', '泰勒公式', '不定积分', '分部积分法', '定积分', '微分中值定理')
    """))

    node_map = {row[1]: row[0] for row in result}

    # 插入知识关系
    conn.execute(sa.text("""
        INSERT INTO knowledge_relations (id, source_id, target_id, relation_type, weight, description, created_at)
        VALUES
        (gen_random_uuid(), :limit_id, :derivative_id, 'HAS_PREREQUISITE'::relationtype, 0.9, '极限是导数的前置知识', NOW()),
        (gen_random_uuid(), :derivative_id, :lhopital_id, 'USED_IN'::relationtype, 0.8, '导数用于洛必达法则', NOW()),
        (gen_random_uuid(), :derivative_id, :mvt_id, 'USED_IN'::relationtype, 0.85, '导数用于微分中值定理', NOW()),
        (gen_random_uuid(), :lhopital_id, :taylor_id, 'HAS_PREREQUISITE'::relationtype, 0.7, '洛必达法则是泰勒公式的前置知识', NOW()),
        (gen_random_uuid(), :derivative_id, :indefinite_id, 'HAS_PREREQUISITE'::relationtype, 0.9, '导数是不定积分的前置知识', NOW()),
        (gen_random_uuid(), :indefinite_id, :parts_id, 'USED_IN'::relationtype, 0.8, '不定积分用于分部积分法', NOW()),
        (gen_random_uuid(), :indefinite_id, :definite_id, 'HAS_PREREQUISITE'::relationtype, 0.95, '不定积分是定积分的前置知识', NOW())
    """), {
        'limit_id': node_map['极限'],
        'derivative_id': node_map['导数'],
        'lhopital_id': node_map['洛必达法则'],
        'taylor_id': node_map['泰勒公式'],
        'indefinite_id': node_map['不定积分'],
        'parts_id': node_map['分部积分法'],
        'definite_id': node_map['定积分'],
        'mvt_id': node_map['微分中值定理'],
    })


def downgrade() -> None:
    """删除初始知识图谱数据"""
    conn = op.get_bind()

    # 删除知识关系
    conn.execute(sa.text("DELETE FROM knowledge_relations"))

    # 删除知识节点
    conn.execute(sa.text("DELETE FROM knowledge_nodes"))
