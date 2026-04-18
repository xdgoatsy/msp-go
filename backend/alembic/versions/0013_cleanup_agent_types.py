"""cleanup_agent_types

Revision ID: 0013_cleanup_agent_types
Revises: 0012_knowledge_graph_seed_data
Create Date: 2026-02-12 00:00:00.000000

清理废弃的智能体类型配置：
- 删除旧的 solver 记录（math_solver 已存在）
- 删除 6 个废弃类型的配置记录
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0013_cleanup_agent_types"
down_revision: str | None = "0012_knowledge_graph_seed_data"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 废弃的智能体类型（含旧的 solver，因为 math_solver 已存在）
DEPRECATED_TYPES = (
    "orchestrator",
    "solver",
    "planner",
    "verifier",
    "reflection",
    "emotion_detector",
    "safety",
)


def upgrade() -> None:
    op.execute(
        f"DELETE FROM agent_model_configs WHERE agent_type IN ({', '.join(repr(t) for t in DEPRECATED_TYPES)})"
    )


def downgrade() -> None:
    # 废弃类型的配置记录无法恢复（已删除），无操作
    pass
