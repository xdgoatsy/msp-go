"""
LangGraph 节点定义

4 节点统一工作流的节点函数：
- entry_node: 入口节点（初始化 + 纯函数路由）
- math_solver_node: 数学求解节点
- tutor_node: 导师节点（教学 + 规划）
- diagnostician_node: 诊断节点
- tracker_node: 学习追踪节点（零 LLM）

每个节点接收 StreamingState，返回更新后的 StreamingState。
内容智能体节点支持通过 StreamWriter 发送流式内容。
"""

import logging
import time
import uuid
from typing import Any

from langgraph.types import StreamWriter

from app.agents.core.router import classify_intent, get_target_node
from app.agents.core.state import StreamingState

logger = logging.getLogger(__name__)


# ========== 智能体工厂（按需创建实例） ==========


class AgentFactory:
    """
    智能体工厂

    按需创建智能体实例，避免全局单例的并发问题。
    精简为 4 个核心智能体。
    """

    # 智能体类映射（懒加载）
    _agent_classes: dict[str, type] = {}

    @classmethod
    def _load_agent_class(cls, name: str) -> type:
        """懒加载智能体类"""
        if name not in cls._agent_classes:
            if name == "math_solver":
                from app.agents.roles.math_solver import MathSolverAgent
                cls._agent_classes[name] = MathSolverAgent
            elif name == "tutor":
                from app.agents.roles.tutor import TutorAgent
                cls._agent_classes[name] = TutorAgent
            elif name == "diagnostician":
                from app.agents.roles.diagnostician import DiagnosticianAgent
                cls._agent_classes[name] = DiagnosticianAgent
            elif name == "tracker":
                from app.agents.roles.tracker import TrackerAgent
                cls._agent_classes[name] = TrackerAgent
            else:
                raise ValueError(f"未知的智能体: {name}")

        return cls._agent_classes[name]

    @classmethod
    def create(cls, name: str, instance_id: str | None = None) -> Any:
        """
        创建智能体实例

        Args:
            name: 智能体名称
            instance_id: 实例 ID（用于追踪）

        Returns:
            智能体实例
        """
        agent_class = cls._load_agent_class(name)
        agent = agent_class()

        # 添加实例追踪信息
        agent._instance_id = instance_id or str(uuid.uuid4())[:8]
        agent._created_at = time.time()

        logger.debug(f"创建智能体实例: {name}#{agent._instance_id}")
        return agent


def _get_agent(name: str, state: StreamingState | None = None) -> Any:
    """
    获取智能体实例

    为每个请求创建新实例，避免状态污染

    Args:
        name: 智能体名称
        state: 当前状态（用于提取 session_id 作为实例标识）

    Returns:
        智能体实例
    """
    instance_id = None
    if state:
        session_id = state.get("session_id", "")
        if session_id:
            instance_id = f"{session_id[:8]}"

    return AgentFactory.create(name, instance_id)


# ========== 入口节点 ==========


async def entry_node(state: StreamingState) -> StreamingState:
    """
    入口节点

    职责：
    1. 初始化会话状态
    2. 纯函数意图分类（零 LLM 调用）
    3. 设置 intent 供条件路由使用

    Args:
        state: 当前状态

    Returns:
        更新后的状态
    """
    logger.info(
        f"[Entry] 会话开始: session_id={state.get('session_id')}"
    )

    # 记录开始时间
    if not state.get("session_start_time"):
        state["session_start_time"] = time.time()

    # 纯函数意图分类（零 LLM 调用）
    message = state.get("last_message", "")
    attachments = state.get("attachments", [])
    intent = classify_intent(message, attachments)

    state["intent"] = intent.value
    logger.info(f"[Entry] 意图分类: {intent.value} → {get_target_node(intent)}")

    return state


# ========== 数学求解节点 ==========


async def math_solver_node(
    state: StreamingState, writer: StreamWriter
) -> StreamingState:
    """
    数学求解节点

    处理数学问题求解，支持流式输出。
    内含安全检查和结果验证（零额外 LLM 调用）。

    Args:
        state: 当前状态
        writer: 流式写入器

    Returns:
        更新后的状态
    """
    logger.info(
        f"[MathSolver] 开始求解: "
        f"{(state.get('current_problem') or state.get('last_message', ''))[:50]}..."
    )

    solver = _get_agent("math_solver", state)

    full_content = ""
    stream_completed = False
    try:
        async for chunk in solver.stream_process(state):
            content = chunk.get("content", "")
            if content:
                full_content += content
                writer({
                    "type": "stream",
                    "content": content,
                    "agent": "math_solver",
                })
        stream_completed = True
    except Exception as e:
        logger.error(f"[MathSolver] 流式处理失败: {e}", exc_info=True)
        state = await solver.process(state)
        full_content = ""
        for msg in state.get("message_stream", []):
            full_content += msg.get("content", "")

    if full_content:
        state["message_stream"] = [
            solver.create_message(
                full_content,
                msg_type="solution",
                streaming=stream_completed,
            )
        ]

    return state


# ========== 导师节点 ==========


async def tutor_node(
    state: StreamingState, writer: StreamWriter
) -> StreamingState:
    """
    导师节点

    处理教学交互（TEACH 模式）和学习规划（PLAN 模式），
    支持流式输出和图片理解。

    Args:
        state: 当前状态
        writer: 流式写入器

    Returns:
        更新后的状态
    """
    logger.info(f"[Tutor] 开始教学: intent={state.get('intent')}")

    tutor = _get_agent("tutor", state)

    full_content = ""
    stream_completed = False
    try:
        async for chunk in tutor.stream_process(state):
            content = chunk.get("content", "")
            if content:
                full_content += content
                writer({
                    "type": "stream",
                    "content": content,
                    "agent": "tutor",
                })
        stream_completed = True
    except Exception as e:
        logger.error(f"[Tutor] 流式处理失败: {e}", exc_info=True)
        state = await tutor.process(state)
        full_content = ""
        for msg in state.get("message_stream", []):
            full_content += msg.get("content", "")

    if full_content:
        state["message_stream"] = [
            tutor.create_message(
                full_content,
                msg_type="teaching",
                streaming=stream_completed,
            )
        ]

    return state


# ========== 诊断节点 ==========


async def diagnostician_node(
    state: StreamingState, writer: StreamWriter
) -> StreamingState:
    """
    诊断节点

    分析学生解答，定位错误，支持流式输出。
    自动输出 tracking_data 供 Tracker 使用。

    Args:
        state: 当前状态
        writer: 流式写入器

    Returns:
        更新后的状态
    """
    logger.info("[Diagnostician] 开始诊断")

    diagnostician = _get_agent("diagnostician", state)

    full_content = ""
    stream_completed = False
    try:
        async for chunk in diagnostician.stream_process(state):
            content = chunk.get("content", "")
            if content:
                full_content += content
                writer({
                    "type": "stream",
                    "content": content,
                    "agent": "diagnostician",
                })
        stream_completed = True
    except Exception as e:
        logger.error(
            f"[Diagnostician] 流式处理失败: {e}", exc_info=True
        )
        state = await diagnostician.process(state)
        full_content = ""
        for msg in state.get("message_stream", []):
            full_content += msg.get("content", "")

    if full_content:
        state["message_stream"] = [
            diagnostician.create_message(
                full_content,
                msg_type="diagnosis",
                streaming=stream_completed,
            )
        ]

    return state


# ========== 学习追踪节点 ==========


async def tracker_node(state: StreamingState) -> StreamingState:
    """
    学习追踪节点

    零 LLM 调用。从 state["tracking_data"] 中读取本次交互的结构化数据，
    计算 profile_updates 写入 state，由 session_service 统一写回数据库。

    同时更新交互计数。

    Args:
        state: 当前状态

    Returns:
        更新后的状态
    """
    logger.info("[Tracker] 开始学习追踪")

    tracker = _get_agent("tracker", state)
    state = await tracker.process(state)

    # 更新交互计数
    state["total_interactions"] = state.get("total_interactions", 0) + 1

    return state
