"""
学习追踪智能体 (Tracker)

零 LLM 调用，纯数据处理。
在每次交互后自动更新学生画像数据。

职责：
1. 更新 mastery_vector（知识点掌握度）
2. 更新 error_tendency（错误倾向）
3. 更新 recent_concepts（最近学习的知识点）
4. 更新 total_exercises / correct_count
5. 更新 consecutive_errors
"""

import logging
from typing import Any

from app.agents.core.base import AgentType, BaseAgent
from app.agents.core.state import StreamingState

logger = logging.getLogger(__name__)

# 学习率基础值
_BASE_ALPHA = 0.1


class TrackerAgent(BaseAgent):
    """
    学习追踪智能体

    零 LLM 调用。从 state["tracking_data"] 中读取本次交互的结构化数据，
    计算 profile_updates 写入 state，由 session_service 统一写回数据库。
    """

    @property
    def name(self) -> str:
        return "tracker"

    @property
    def description(self) -> str:
        return "学习追踪智能体，零 LLM 调用，更新学生画像数据"

    @property
    def agent_type(self) -> AgentType:
        return AgentType.TRACKER

    async def process(self, state: StreamingState) -> StreamingState:
        """
        处理追踪数据，生成 profile_updates。

        不直接访问数据库，而是将更新指令写入 state["profile_updates"]，
        由 session_service 在工作流完成后统一写入。
        """
        tracking = state.get("tracking_data", {})
        student_ctx = state.get("student_context", {})

        if not tracking:
            logger.debug("无追踪数据，跳过")
            return state

        updates: dict[str, Any] = {}

        # 1. 更新 mastery_vector
        mastery_updates = self._compute_mastery_updates(tracking, student_ctx)
        if mastery_updates:
            updates["mastery_vector"] = mastery_updates

        # 2. 更新 error_tendency
        error_type = tracking.get("error_type")
        if error_type:
            current_tendency = dict(student_ctx.get("error_tendency", {}))
            current_tendency[error_type] = current_tendency.get(error_type, 0) + 1
            updates["error_tendency"] = current_tendency

        # 3. 更新 recent_concepts
        concepts = tracking.get("concepts_involved", [])
        if concepts:
            recent = list(student_ctx.get("recent_concepts", []))
            for c in concepts:
                if c in recent:
                    recent.remove(c)
                recent.insert(0, c)
            updates["recent_concepts"] = recent[:20]  # 保留最近 20 个

        # 4. 更新 total_exercises / correct_count
        interaction_type = tracking.get("interaction_type")
        is_correct = tracking.get("is_correct")

        if interaction_type == "diagnose" and is_correct is not None:
            updates["total_exercises_delta"] = 1
            if is_correct:
                updates["correct_count_delta"] = 1

        # 5. 更新 consecutive_errors
        if is_correct is True:
            updates["consecutive_errors"] = 0
        elif is_correct is False:
            updates["consecutive_errors"] = state.get("consecutive_errors", 0) + 1

        # 写入 state
        state["profile_updates"] = updates

        logger.info(f"Tracker 生成更新: {list(updates.keys())}")
        return state

    def _compute_mastery_updates(
        self,
        tracking: dict[str, Any],
        student_ctx: dict[str, Any],
    ) -> dict[str, float]:
        """
        计算 mastery_vector 更新。

        使用简化贝叶斯更新：
            new_mastery = old_mastery + α × (outcome - old_mastery)
            α = BASE_ALPHA × (1 + difficulty)

        为未来 DKT 模型预留接口。

        Args:
            tracking: 本次交互的追踪数据
            student_ctx: 学生上下文

        Returns:
            更新后的 mastery_vector
        """
        concepts = tracking.get("concepts_involved", [])
        is_correct = tracking.get("is_correct")
        difficulty = tracking.get("difficulty_level", 0.5)

        if not concepts or is_correct is None:
            return {}

        current_mastery = dict(student_ctx.get("mastery_vector", {}))
        outcome = 1.0 if is_correct else 0.0
        alpha = _BASE_ALPHA * (1 + difficulty)

        for concept in concepts:
            old = current_mastery.get(concept, 0.5)
            new = old + alpha * (outcome - old)
            # 限制在 [0, 1] 范围内
            current_mastery[concept] = max(0.0, min(1.0, new))

        return current_mastery
