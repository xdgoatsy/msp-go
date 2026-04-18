"""
BKT 服务

在低算力 CPU 环境下提供学生知识状态实时预测。
"""

from __future__ import annotations

import time
from datetime import datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.middleware.metrics import record_bkt_update
from app.domain.models.bkt import (
    BKTParameters,
    apply_forgetting,
    bkt_update,
    clamp_probability,
)
from app.infrastructure.cache.memory import bkt_state_cache
from app.infrastructure.repositories.bkt_repository import BKTRepository


class BKTService:
    """BKT 核心服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = BKTRepository(db)

    @staticmethod
    def _cache_key(student_id: str, concept_ids: list[str] | None = None) -> str:
        if not concept_ids:
            return f"bkt:mastery:{student_id}:all"
        ordered = ",".join(sorted(set(concept_ids)))
        return f"bkt:mastery:{student_id}:{ordered}"

    async def get_mastery_map(
        self,
        *,
        student_id: str,
        concept_ids: list[str] | None = None,
        fallback_mastery: dict[str, float] | None = None,
    ) -> dict[str, float]:
        """获取学生掌握度映射（优先 BKT，回退 profile）。"""
        fallback = dict(fallback_mastery or {})
        _start = time.monotonic()

        # 仅在全量场景使用缓存，避免组合 key 爆炸
        if concept_ids is None:
            cache_key = self._cache_key(student_id)
            cached = bkt_state_cache.get(cache_key)
            if cached is not None:
                record_bkt_update("get_mastery", time.monotonic() - _start)
                return cached

        rows = await self.repository.get_student_states(
            student_id=student_id,
            concept_ids=concept_ids,
        )

        mastery = dict(fallback)
        now = datetime.now()
        for row in rows:
            raw_mastery = float(row.mastery_prob)
            # 应用遗忘因子：基于距上次练习的天数衰减掌握度
            if row.last_attempt_at is not None:
                days_since = (now - row.last_attempt_at).total_seconds() / 86400.0
                raw_mastery = apply_forgetting(
                    raw_mastery, days_since, floor=float(row.p_l0),
                )
            mastery[row.concept_id] = round(raw_mastery, 4)

        if concept_ids is not None:
            for concept_id in concept_ids:
                mastery.setdefault(concept_id, fallback.get(concept_id, 0.5))

        if concept_ids is None:
            bkt_state_cache.set(self._cache_key(student_id), mastery)

        record_bkt_update("get_mastery", time.monotonic() - _start)
        return mastery

    async def get_mastery_confidence_map(
        self,
        *,
        student_id: str,
        concept_ids: list[str] | None = None,
    ) -> dict[str, float]:
        """获取掌握度置信度映射。"""
        rows = await self.repository.get_student_states(
            student_id=student_id,
            concept_ids=concept_ids,
        )
        return {row.concept_id: round(float(row.confidence), 4) for row in rows}

    async def get_attempt_count_map(
        self,
        *,
        student_id: str,
        concept_ids: list[str] | None = None,
    ) -> dict[str, int]:
        """获取每知识点练习次数映射。"""
        rows = await self.repository.get_student_states(
            student_id=student_id,
            concept_ids=concept_ids,
        )
        return {row.concept_id: int(row.attempt_count) for row in rows}

    async def update_after_attempt(
        self,
        *,
        student_id: str,
        concept_ids: list[str],
        is_correct: bool,
        difficulty: float,
        preferred_difficulty: float,
        learning_pace: float,
        error_type: str | None = None,
        fallback_mastery: dict[str, float] | None = None,
    ) -> dict[str, dict[str, float] | str]:
        """在一次作答后更新 BKT 状态。"""
        unique_concepts = sorted({cid for cid in concept_ids if cid})
        if not unique_concepts:
            return {
                "model": "bkt",
                "mastery_update": {},
                "confidence": {},
            }

        _start = time.monotonic()
        state_map = await self.repository.get_student_state_map(
            student_id=student_id,
            concept_ids=unique_concepts,
        )
        concept_params = await self.repository.get_concept_params_map_cached(unique_concepts)

        fallback = dict(fallback_mastery or {})
        now = datetime.now()
        rows: list[dict] = []
        mastery_update: dict[str, float] = {}
        confidence_map: dict[str, float] = {}

        for concept_id in unique_concepts:
            state = state_map.get(concept_id)
            base_params = concept_params.get(concept_id, BKTParameters())
            personalized = base_params.personalized(
                preferred_difficulty=preferred_difficulty,
                learning_pace=learning_pace,
                item_difficulty=clamp_probability(difficulty, floor=0.0, ceiling=1.0),
                error_type=error_type,
            )

            if state is None:
                prior = fallback.get(concept_id, personalized.p_l0)
                attempt_count = 0
                correct_count = 0
                incorrect_count = 0
                state_id = str(uuid4())
            else:
                prior = float(state.mastery_prob)
                # 更新前先应用遗忘因子
                if state.last_attempt_at is not None:
                    days_since = (now - state.last_attempt_at).total_seconds() / 86400.0
                    prior = apply_forgetting(
                        prior, days_since, floor=float(state.p_l0),
                    )
                attempt_count = int(state.attempt_count)
                correct_count = int(state.correct_count)
                incorrect_count = int(state.incorrect_count)
                state_id = state.id

            result = bkt_update(
                prior_mastery=prior,
                is_correct=is_correct,
                params=personalized,
                attempt_count=attempt_count,
            )

            next_attempt_count = attempt_count + 1
            next_correct_count = correct_count + (1 if is_correct else 0)
            next_incorrect_count = incorrect_count + (0 if is_correct else 1)

            next_mastery = round(float(result.posterior_after_transition), 4)
            mastery_update[concept_id] = next_mastery
            confidence_map[concept_id] = round(float(result.confidence), 4)

            rows.append(
                {
                    "id": state_id,
                    "student_id": student_id,
                    "concept_id": concept_id,
                    "mastery_prob": next_mastery,
                    "confidence": confidence_map[concept_id],
                    "attempt_count": next_attempt_count,
                    "correct_count": next_correct_count,
                    "incorrect_count": next_incorrect_count,
                    "p_l0": round(float(personalized.p_l0), 4),
                    "p_t": round(float(personalized.p_t), 4),
                    "p_g": round(float(personalized.p_g), 4),
                    "p_s": round(float(personalized.p_s), 4),
                    "last_outcome": is_correct,
                    "last_attempt_at": now,
                    "updated_at": now,
                    "created_at": state.created_at if state is not None else now,
                }
            )

        await self.repository.bulk_upsert_student_states(rows)
        bkt_state_cache.delete(self._cache_key(student_id))

        record_bkt_update("update_after_attempt", time.monotonic() - _start)
        return {
            "model": "bkt",
            "mastery_update": mastery_update,
            "confidence": confidence_map,
        }
