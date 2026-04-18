"""
LangGraph 工作流编译

4 节点统一工作流：entry → [math_solver|tutor|diagnostician] → tracker → END

设计原则：
1. 单一工作流，删除高级工作流
2. 纯函数路由，零 LLM 调用
3. 每次请求 1-2 次 LLM 调用（由内容智能体决定）
4. Tracker 节点自动追踪学习数据
"""

import logging
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.core.state import StreamingState
from app.agents.workflow.edges import route_by_intent
from app.agents.workflow.nodes import (
    diagnostician_node,
    entry_node,
    math_solver_node,
    tracker_node,
    tutor_node,
)

logger = logging.getLogger(__name__)

# 内容智能体节点集合（用于流式输出识别）
CONTENT_AGENTS = {"math_solver", "tutor", "diagnostician"}

# 辅助节点集合
AUXILIARY_NODES = {"entry", "tracker"}


def _use_redis_checkpoint() -> bool:
    """检查是否使用 Redis 检查点"""
    from app.config import settings
    return getattr(settings, "redis_checkpoint_enabled", True)


def create_workflow() -> StateGraph:
    """
    创建 4 节点统一工作流

    工作流结构：
    ```
    START
      │
      ▼
    entry (初始化 + 纯函数路由)
      │
      ├── SOLVE ──────────► math_solver ──┐
      │                                    │
      ├── TEACH/PLAN ─────► tutor ────────┤
      │                                    │
      └── DIAGNOSE ───────► diagnostician ─┤
                                           │
                                   ┌───────┘
                                   ▼
                               tracker (学习追踪, 零LLM)
                                   │
                                   ▼
                                  END
    ```

    Returns:
        StateGraph 实例
    """
    workflow = StateGraph(StreamingState)

    # ========== 添加节点 ==========
    workflow.add_node("entry", entry_node)
    workflow.add_node("math_solver", math_solver_node)
    workflow.add_node("tutor", tutor_node)
    workflow.add_node("diagnostician", diagnostician_node)
    workflow.add_node("tracker", tracker_node)

    # ========== 设置入口 ==========
    workflow.add_edge(START, "entry")

    # ========== entry → 条件路由到内容智能体 ==========
    workflow.add_conditional_edges(
        "entry",
        route_by_intent,
        {
            "math_solver": "math_solver",
            "tutor": "tutor",
            "diagnostician": "diagnostician",
        },
    )

    # ========== 内容智能体 → tracker ==========
    workflow.add_edge("math_solver", "tracker")
    workflow.add_edge("tutor", "tracker")
    workflow.add_edge("diagnostician", "tracker")

    # ========== tracker → END ==========
    workflow.add_edge("tracker", END)

    logger.info("4 节点统一工作流创建完成")
    return workflow


def compile_workflow(
    workflow: StateGraph | None = None,
    checkpointer: Any | None = None,
    use_memory: bool = True,
) -> Any:
    """
    编译工作流

    Args:
        workflow: 工作流实例，None 则创建默认工作流
        checkpointer: 检查点保存器
        use_memory: 是否使用内存检查点

    Returns:
        编译后的工作流应用
    """
    if workflow is None:
        workflow = create_workflow()

    if checkpointer is None and use_memory:
        if _use_redis_checkpoint():
            checkpointer = None
            logger.info("工作流将使用 Redis 检查点（延迟初始化）")
        else:
            checkpointer = MemorySaver()
            logger.info("工作流使用内存检查点")

    app = workflow.compile(checkpointer=checkpointer)
    logger.info("工作流编译完成")
    return app


# ========== 全局工作流实例 ==========

_workflow_app: Any | None = None
_redis_checkpointer: Any | None = None


async def _get_checkpointer() -> Any:
    """获取检查点存储器"""
    global _redis_checkpointer

    if _use_redis_checkpoint():
        if _redis_checkpointer is None:
            try:
                from app.agents.workflow.checkpointer import get_redis_checkpointer
                _redis_checkpointer = await get_redis_checkpointer(ttl=3600)
                logger.info("Redis 检查点初始化成功")
            except Exception as e:
                logger.warning(f"Redis 检查点初始化失败，回退到内存检查点: {e}")
                _redis_checkpointer = MemorySaver()
        return _redis_checkpointer
    else:
        return MemorySaver()


def get_workflow_app() -> Any:
    """
    获取工作流应用实例（单例，同步版本）

    注意：此方法不支持 Redis 检查点，推荐使用 get_workflow_app_async

    Returns:
        编译后的工作流应用
    """
    global _workflow_app

    if _workflow_app is None:
        workflow = create_workflow()
        _workflow_app = compile_workflow(workflow, use_memory=not _use_redis_checkpoint())
    return _workflow_app


async def get_workflow_app_async() -> Any:
    """
    获取工作流应用实例（单例，异步版本，支持 Redis 检查点）

    Returns:
        编译后的工作流应用
    """
    global _workflow_app

    checkpointer = await _get_checkpointer()

    if _workflow_app is None:
        workflow = create_workflow()
        _workflow_app = workflow.compile(checkpointer=checkpointer)
        logger.info("工作流编译完成（异步）")
    return _workflow_app


async def run_workflow(
    session_id: str,
    student_id: str,
    message: str,
    attachments: list[str] | None = None,
    student_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    运行工作流

    Args:
        session_id: 会话 ID
        student_id: 学生 ID
        message: 用户消息
        attachments: 附件列表
        student_profile: 学生画像（用于初始化学生上下文）

    Returns:
        工作流执行结果
    """
    from app.agents.core.state import create_initial_state

    app = await get_workflow_app_async()

    initial_state = create_initial_state(
        session_id=session_id,
        student_id=student_id,
        student_profile=student_profile,
    )
    initial_state["last_message"] = message
    initial_state["attachments"] = attachments or []

    config = {"configurable": {"thread_id": session_id}}
    result = await app.ainvoke(initial_state, config=config)
    return result


async def stream_workflow(
    session_id: str,
    student_id: str,
    message: str,
    attachments: list[str] | None = None,
    student_profile: dict[str, Any] | None = None,
    db_session: Any | None = None,
):
    """
    流式执行工作流

    使用 astream 的 custom 模式获取节点发送的流式内容，
    可以在 LLM 生成过程中逐 token 返回内容。

    Args:
        session_id: 会话 ID
        student_id: 学生 ID
        message: 用户消息
        attachments: 附件列表
        student_profile: 学生画像
        db_session: 数据库会话（用于工具调用）

    Yields:
        工作流状态更新
    """
    from app.agents.core.state import create_initial_state

    app = await get_workflow_app_async()

    initial_state = create_initial_state(
        session_id=session_id,
        student_id=student_id,
        student_profile=student_profile,
        db_session=db_session,
    )
    initial_state["last_message"] = message
    initial_state["attachments"] = attachments or []

    config = {"configurable": {"thread_id": session_id}}

    try:
        async for namespace, chunk in app.astream(
            initial_state, config=config, stream_mode=["custom", "updates"]
        ):
            if namespace == "custom":
                # 自定义流式内容（来自 StreamWriter）
                if isinstance(chunk, dict):
                    chunk_type = chunk.get("type")
                    if chunk_type == "stream":
                        content = chunk.get("content", "")
                        agent = chunk.get("agent")
                        if content:
                            yield {
                                "type": "message",
                                "content": content,
                                "metadata": {
                                    "agent_type": agent,
                                    "streaming": True,
                                },
                            }

            elif namespace == "updates":
                # 节点状态更新
                if isinstance(chunk, dict):
                    for node_name, node_output in chunk.items():
                        if node_name in CONTENT_AGENTS:
                            if isinstance(node_output, dict):
                                # 非流式消息回退
                                message_stream = node_output.get(
                                    "message_stream", []
                                )
                                for msg in message_stream:
                                    content = msg.get("content", "")
                                    metadata = msg.get("metadata", {})
                                    if content and not metadata.get(
                                        "streaming"
                                    ):
                                        yield {
                                            "type": "message",
                                            "role": msg.get(
                                                "role", "assistant"
                                            ),
                                            "content": content,
                                            "metadata": {
                                                **metadata,
                                                "agent_type": node_name,
                                                "streaming": False,
                                            },
                                        }

                                # 智能体输出
                                agent_outputs = node_output.get(
                                    "agent_outputs", {}
                                )
                                if agent_outputs:
                                    yield {
                                        "type": "agent_output",
                                        "outputs": agent_outputs,
                                    }

                            yield {
                                "type": "node_end",
                                "node": node_name,
                            }

                        # tracker 节点完成时，发送 profile_updates
                        if node_name == "tracker" and isinstance(
                            node_output, dict
                        ):
                            profile_updates = node_output.get(
                                "profile_updates", {}
                            )
                            if profile_updates:
                                yield {
                                    "type": "profile_updates",
                                    "updates": profile_updates,
                                }

    except Exception as e:
        logger.error(f"流式工作流执行失败: {e}", exc_info=True)
        yield {
            "type": "error",
            "content": f"工作流执行出错: {str(e)}",
            "metadata": {"error": True},
        }
