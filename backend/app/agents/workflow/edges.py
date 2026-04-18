"""
LangGraph 边与路由定义

精简版：仅保留 route_by_intent 纯函数路由
"""

import logging

from app.agents.core.router import (
    IntentType,
    NodeName,
    classify_intent,
    get_target_node,
)
from app.agents.core.state import StreamingState

logger = logging.getLogger(__name__)


def route_by_intent(
    state: StreamingState,
) -> NodeName:
    """
    根据意图路由到对应内容智能体节点

    使用纯函数 classify_intent 进行意图分类，零 LLM 调用。

    Args:
        state: 当前状态

    Returns:
        下一个节点名称
    """
    intent_str = state.get("intent")

    # 如果 entry 节点已经设置了 intent，直接使用
    if intent_str:
        try:
            intent = IntentType(intent_str)
            target = get_target_node(intent)
        except ValueError:
            target = "tutor"
    else:
        # 兜底：从消息重新分类
        message = state.get("last_message", "")
        attachments = state.get("attachments", [])
        intent = classify_intent(message, attachments)
        target = get_target_node(intent)

    logger.debug(f"[RouteByIntent] intent={intent_str} → target={target}")
    return target
