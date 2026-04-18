"""
BKT 状态仓储

负责学生-知识点 BKT 状态与知识点参数的读写。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.bkt import BKTParameters
from app.infrastructure.cache.redis import get_redis_client_safe
from app.infrastructure.database.models import (
    ConceptBKTParamModel,
    KnowledgeNodeModel,
    StudentConceptBKTStateModel,
)

logger = logging.getLogger(__name__)


class BKTRepository:
    """BKT 数据访问仓储。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_student_states(
        self,
        student_id: str,
        concept_ids: list[str] | None = None,
    ) -> list[StudentConceptBKTStateModel]:
        """获取学生 BKT 状态列表。"""
        stmt = select(StudentConceptBKTStateModel).where(
            StudentConceptBKTStateModel.student_id == student_id,
        )

        if concept_ids is not None:
            if not concept_ids:
                return []
            stmt = stmt.where(StudentConceptBKTStateModel.concept_id.in_(concept_ids))

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_student_state_map(
        self,
        student_id: str,
        concept_ids: list[str],
    ) -> dict[str, StudentConceptBKTStateModel]:
        """按 concept_id 返回学生 BKT 状态映射。"""
        rows = await self.get_student_states(student_id=student_id, concept_ids=concept_ids)
        return {row.concept_id: row for row in rows}

    async def get_concept_params_map(
        self,
        concept_ids: list[str],
    ) -> dict[str, BKTParameters]:
        """按 concept_id 批量获取知识点参数。"""
        if not concept_ids:
            return {}

        stmt = select(ConceptBKTParamModel).where(
            ConceptBKTParamModel.concept_id.in_(concept_ids),
        )
        result = await self.db.execute(stmt)
        rows = result.scalars().all()

        return {
            row.concept_id: BKTParameters(
                p_l0=float(row.p_l0),
                p_t=float(row.p_t),
                p_g=float(row.p_g),
                p_s=float(row.p_s),
            )
            for row in rows
        }

    async def get_concept_params_map_cached(
        self, concept_ids: list[str]
    ) -> dict[str, BKTParameters]:
        """获取概念 BKT 参数映射（Redis 缓存版，TTL 1h）"""
        from app.domain.models.bkt import BKTParameters

        if not concept_ids:
            return {}

        # 尝试 Redis 缓存
        cache_key = f"msp:bkt:params:{','.join(sorted(concept_ids))}"
        try:
            redis = await get_redis_client_safe()
            if redis:
                cached = await redis.get(cache_key)
                if cached:
                    data = json.loads(cached)
                    return {
                        k: BKTParameters(**v) for k, v in data.items()
                    }
        except Exception:
            pass  # 缓存失败不影响业务

        # 缓存未命中，查询 DB
        result = await self.get_concept_params_map(concept_ids)

        # 写入 Redis 缓存
        try:
            redis = await get_redis_client_safe()
            if redis:
                serialized = {}
                for k, v in result.items():
                    serialized[k] = {
                        "p_l0": v.p_l0,
                        "p_t": v.p_t,
                        "p_g": v.p_g,
                        "p_s": v.p_s,
                    }
                await redis.setex(cache_key, 3600, json.dumps(serialized))
        except Exception:
            pass

        return result

    async def bulk_upsert_student_states(
        self,
        rows: list[dict],
    ) -> None:
        """批量写入学生 BKT 状态（UPSERT）。"""
        if not rows:
            return

        now = datetime.now()
        normalized_rows = [
            {
                **row,
                "updated_at": row.get("updated_at", now),
                "created_at": row.get("created_at", now),
            }
            for row in rows
        ]

        stmt = insert(StudentConceptBKTStateModel).values(normalized_rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_student_concept_bkt_state",
            set_={
                "mastery_prob": stmt.excluded.mastery_prob,
                "attempt_count": stmt.excluded.attempt_count,
                "correct_count": stmt.excluded.correct_count,
                "incorrect_count": stmt.excluded.incorrect_count,
                "confidence": stmt.excluded.confidence,
                "p_l0": stmt.excluded.p_l0,
                "p_t": stmt.excluded.p_t,
                "p_g": stmt.excluded.p_g,
                "p_s": stmt.excluded.p_s,
                "last_outcome": stmt.excluded.last_outcome,
                "last_attempt_at": stmt.excluded.last_attempt_at,
                "updated_at": stmt.excluded.updated_at,
            },
        )
        await self.db.execute(stmt)

    # =========================================================================
    # BKT 参数管理
    # =========================================================================

    async def seed_default_params(self) -> int:
        """为缺少 BKT 参数的知识点批量插入默认值，返回新增数量。"""
        # 查询所有知识点 ID
        node_stmt = select(KnowledgeNodeModel.id)
        node_result = await self.db.execute(node_stmt)
        all_node_ids = {row[0] for row in node_result.all()}

        if not all_node_ids:
            return 0

        # 查询已有参数的知识点 ID
        existing_stmt = select(ConceptBKTParamModel.concept_id)
        existing_result = await self.db.execute(existing_stmt)
        existing_ids = {row[0] for row in existing_result.all()}

        # 计算缺失的
        missing_ids = all_node_ids - existing_ids
        if not missing_ids:
            return 0

        defaults = BKTParameters()
        now = datetime.now()
        rows = [
            {
                "concept_id": cid,
                "p_l0": defaults.p_l0,
                "p_t": defaults.p_t,
                "p_g": defaults.p_g,
                "p_s": defaults.p_s,
                "created_at": now,
                "updated_at": now,
            }
            for cid in missing_ids
        ]

        stmt = insert(ConceptBKTParamModel).values(rows)
        stmt = stmt.on_conflict_do_nothing(index_elements=["concept_id"])
        await self.db.execute(stmt)
        return len(rows)

    async def get_all_concept_params(
        self,
        offset: int = 0,
        limit: int = 50,
    ) -> list[ConceptBKTParamModel]:
        """分页获取所有知识点 BKT 参数。"""
        stmt = (
            select(ConceptBKTParamModel)
            .order_by(ConceptBKTParamModel.concept_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_concept_params(self) -> int:
        """统计知识点 BKT 参数总数。"""
        from sqlalchemy import func

        stmt = select(func.count(ConceptBKTParamModel.concept_id))
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def get_concept_param(
        self, concept_id: str
    ) -> ConceptBKTParamModel | None:
        """获取单个知识点 BKT 参数。"""
        stmt = select(ConceptBKTParamModel).where(
            ConceptBKTParamModel.concept_id == concept_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_concept_param(
        self,
        concept_id: str,
        *,
        p_l0: float | None = None,
        p_t: float | None = None,
        p_g: float | None = None,
        p_s: float | None = None,
    ) -> ConceptBKTParamModel | None:
        """更新单个知识点 BKT 参数，返回更新后的记录。"""
        row = await self.get_concept_param(concept_id)
        if row is None:
            return None

        if p_l0 is not None:
            row.p_l0 = p_l0
        if p_t is not None:
            row.p_t = p_t
        if p_g is not None:
            row.p_g = p_g
        if p_s is not None:
            row.p_s = p_s
        row.updated_at = datetime.now()
        await self.db.flush()
        return row

    async def reset_concept_param(
        self, concept_id: str
    ) -> ConceptBKTParamModel | None:
        """将知识点 BKT 参数重置为默认值。"""
        defaults = BKTParameters()
        return await self.update_concept_param(
            concept_id,
            p_l0=defaults.p_l0,
            p_t=defaults.p_t,
            p_g=defaults.p_g,
            p_s=defaults.p_s,
        )
