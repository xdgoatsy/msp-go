"""
导师智能体 (Tutor)

统一教学智能体，合并了原 Tutor + Planner 的能力：
- TEACH 模式：概念讲解、苏格拉底式引导、一般对话
- PLAN 模式：学习路径规划、练习推荐

单次 LLM 调用，通过 system prompt 切换模式。
资源中心推荐由会话服务在主回答后追加，避免工具调用阻塞首字。
"""

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.agents.core.base import AgentType, BaseAgent
from app.agents.core.llm_client import (
    ConfigurableLLMClient,
    LLMClient,
    get_agent_llm_client,
)
from app.agents.core.state import StreamingState
from app.agents.core.utils import (
    estimate_difficulty,
    extract_concepts_from_text,
    format_conversation_history,
)

logger = logging.getLogger(__name__)


# ========== Tutor 模式 ==========


class TutorMode(StrEnum):
    """Tutor 子模式"""

    TEACH = "teach"  # 概念讲解 / 一般对话 / 提示
    PLAN = "plan"  # 学习路径规划 / 练习推荐


# ========== Prompt 模板 ==========

TUTOR_BASE_PROMPT = """你是一位耐心、专业的高等数学导师。

教学原则：
1. 采用苏格拉底式教学法，通过提问引导学生思考
2. 不直接给出答案，而是提供脚手架式的提示
3. 根据学生水平调整解释深度
4. 使用具体例子和类比帮助理解
5. 鼓励学生，保持积极的学习氛围
6. 数学公式请使用 KaTeX 兼容的 Markdown 语法：行内公式用 `$...$`，块级公式用 `$$...$$`；不要使用 `\\(...\\)` / `\\[...\\]`
7. 使用 Markdown 进行排版（标题/列表/加粗等），不要把 `**` 等 Markdown 标记转义为 `\\*\\*`

**资源推荐指导**：
- 如果学生主动询问资源、资料、视频或课件，可以先回答学习建议，并说明会在回答后附上资源中心结果
- 不要自行生成 `### 推荐资源` 标题、资源列表、资源 ID 或链接
- 不要编造资源名称或链接，真实资源推荐由系统在回答结束后追加

{student_context}"""


TEACH_PROMPT = """请回答学生的问题。

对话历史：
{history}

{image_context}

学生消息：{message}

请回答学生的问题：
1. 直接回应学生的疑问
2. 使用清晰的语言和例子
3. 如果问题涉及概念，解释清楚
4. 如果问题涉及解题，给出思路而非直接答案
5. 最后可以提一个引导性问题，促进深入思考"""

PLAN_PATH_PROMPT = """学生希望规划学习路径。

学生消息：{message}
学生当前掌握情况：
{mastery_info}

请为学生规划学习路径：
1. 列出需要学习的知识点序列（从基础到进阶）
2. 考虑知识点之间的先修关系
3. 每个知识点给出简短说明
4. 给出预估学习时间
5. 如果学生有薄弱环节，优先安排巩固"""

PLAN_EXERCISE_PROMPT = """学生希望做练习题。

学生消息：{message}
知识点：{concept}
学生水平：{level}

请为学生推荐一道练习题：
1. 题目难度适合学生水平
2. 题目能够检验对该知识点的理解
3. 题目表述清晰，使用 LaTeX 格式
4. 给出题目后，不要直接给答案"""


# ========== 数据类 ==========


@dataclass
class TutorResponse:
    """导师回复"""

    content: str
    mode: TutorMode
    related_concepts: list[str] = field(default_factory=list)
    follow_up_questions: list[str] = field(default_factory=list)


# ========== 自适应 Prompt 生成 ==========


def build_student_context(student_ctx: dict[str, Any] | None = None) -> str:
    """根据学生画像生成自适应上下文"""
    if not student_ctx:
        return ""

    parts = []

    mastery = student_ctx.get("mastery_vector", {})
    if mastery:
        avg = sum(mastery.values()) / len(mastery) if mastery else 0.5
        if avg < 0.3:
            parts.append("学生是初学者，请使用简单的语言，避免专业术语，多举基础例子。")
        elif avg > 0.7:
            parts.append("学生基础扎实，可以使用更严谨的数学语言，适当增加挑战性。")
        else:
            parts.append("学生有一定基础，可以逐步引入专业术语，注意概念的连贯性。")

    return "\n".join(parts) if parts else ""


# ========== TutorAgent ==========


class TutorAgent(BaseAgent):
    """
    统一教学智能体

    支持两种模式：
    - TEACH：概念讲解、苏格拉底式引导、一般对话
    - PLAN：学习路径规划、练习推荐

    单次 LLM 调用，通过 system prompt 切换模式。
    """

    def __init__(self, llm_client: LLMClient | ConfigurableLLMClient | None = None):
        self.llm = llm_client or get_agent_llm_client("tutor")

    @property
    def name(self) -> str:
        return "tutor"

    @property
    def description(self) -> str:
        return "统一教学智能体，支持概念讲解、苏格拉底式引导和学习规划"

    @property
    def agent_type(self) -> AgentType:
        return AgentType.TUTOR

    def _determine_mode(self, state: StreamingState) -> TutorMode:
        """根据 state 中的 intent 决定 Tutor 子模式"""
        intent = state.get("intent", "teach")
        if intent == "plan":
            return TutorMode.PLAN
        return TutorMode.TEACH

    def _build_system_prompt(self, student_ctx: dict[str, Any] | None = None) -> str:
        """构建系统提示"""
        ctx_str = build_student_context(student_ctx)
        return TUTOR_BASE_PROMPT.format(student_context=ctx_str)

    def _build_user_prompt(
        self,
        mode: TutorMode,
        message: str,
        state: StreamingState,
    ) -> str:
        """根据模式构建用户 prompt"""
        history = state.get("interaction_history", [])
        history_str = format_conversation_history(history, max_messages=5) if history else "（无历史记录）"
        student_ctx = state.get("student_context", {})

        if mode == TutorMode.PLAN:
            # 判断是练习推荐还是路径规划
            msg_lower = message.lower()
            is_exercise = any(kw in msg_lower for kw in ["练习", "题目", "出一道", "做题"])

            if is_exercise:
                concept = state.get("current_concept") or "微积分"
                mastery = student_ctx.get("mastery_vector", {})
                level = mastery.get(concept, 0.5)
                level_desc = "初级" if level < 0.3 else "中级" if level < 0.7 else "高级"
                return PLAN_EXERCISE_PROMPT.format(
                    message=message,
                    concept=concept,
                    level=level_desc,
                )
            else:
                mastery = student_ctx.get("mastery_vector", {})
                mastery_info = []
                for concept, m in mastery.items():
                    status = "已掌握" if m >= 0.7 else "需加强"
                    mastery_info.append(f"- {concept}: {m:.0%} ({status})")
                mastery_str = "\n".join(mastery_info) if mastery_info else "（暂无记录）"
                return PLAN_PATH_PROMPT.format(
                    message=message,
                    mastery_info=mastery_str,
                )
        else:
            # TEACH 模式
            attachments = state.get("attachments", [])
            image_context = ""
            if attachments:
                image_context = "学生上传了图片，请仔细查看图片内容并结合问题进行回答。"

            return TEACH_PROMPT.format(
                history=history_str,
                image_context=image_context,
                message=message,
            )

    async def process(self, state: StreamingState) -> StreamingState:
        """处理教学请求"""
        message = state.get("last_message", "")
        mode = self._determine_mode(state)
        student_ctx = state.get("student_context", {})

        system_prompt = self._build_system_prompt(student_ctx)
        user_prompt = self._build_user_prompt(mode, message, state)

        try:
            response = await self.llm.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.7,
            )
        except Exception as e:
            logger.error(f"Tutor 生成失败: {e}")
            response = "抱歉，我暂时无法回答这个问题。你能换一种方式描述你的疑问吗？"

        state["message_stream"] = [
            self.create_message(response, msg_type="teaching", mode=mode.value)
        ]

        state["agent_outputs"] = {
            "tutor": {
                "mode": mode.value,
                "related_concepts": [],
            }
        }

        # 写入追踪数据
        state["tracking_data"] = {
            "interaction_type": mode.value,
            "concepts_involved": extract_concepts_from_text(message),
            "is_correct": None,
            "difficulty_level": estimate_difficulty(message),
        }

        return state

    async def stream_process(
        self, state: StreamingState
    ) -> AsyncIterator[dict[str, Any]]:
        """流式处理教学请求，直接透传 LLM chunk 以优化首字速度。"""
        message = state.get("last_message", "")
        mode = self._determine_mode(state)
        student_ctx = state.get("student_context", {})

        system_prompt = self._build_system_prompt(student_ctx)
        user_prompt = self._build_user_prompt(mode, message, state)

        state["agent_outputs"] = {
            "tutor": {
                "mode": mode.value,
                "related_concepts": [],
            }
        }
        state["tracking_data"] = {
            "interaction_type": mode.value,
            "concepts_involved": extract_concepts_from_text(message),
            "is_correct": None,
            "difficulty_level": estimate_difficulty(message),
        }

        try:
            emitted = False
            async for chunk in self.llm.stream_generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.7,
            ):
                if not chunk:
                    continue
                emitted = True
                yield {
                    "type": "chunk",
                    "content": chunk,
                    "agent": self.agent_type.value,
                    "metadata": {"mode": mode.value},
                }

            if not emitted:
                yield {
                    "type": "chunk",
                    "content": "抱歉，我暂时无法回答这个问题。你能换一种方式描述你的疑问吗？",
                    "agent": self.agent_type.value,
                    "metadata": {"mode": mode.value},
                }

        except Exception as e:
            logger.error(f"Tutor 流式生成失败: {e}", exc_info=True)
            yield {
                "type": "chunk",
                "content": "抱歉，我暂时无法回答这个问题。你能换一种方式描述你的疑问吗？",
                "agent": self.agent_type.value,
                "metadata": {"mode": mode.value},
            }
