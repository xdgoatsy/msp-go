"""
意图路由器 (Router)

纯函数实现，零 LLM 调用。
从用户消息中通过关键词匹配识别意图，路由到对应智能体节点。
"""

import logging
from enum import StrEnum
from typing import Literal

logger = logging.getLogger(__name__)


class IntentType(StrEnum):
    """用户意图类型（精简版）"""

    SOLVE = "solve"  # 求解数学问题
    TEACH = "teach"  # 概念讲解 / 一般对话 / 请求提示
    DIAGNOSE = "diagnose"  # 提交答案 / 上传图片 / 错误分析
    PLAN = "plan"  # 学习路径 / 练习推荐


# 节点名称类型
NodeName = Literal["math_solver", "tutor", "diagnostician"]

# 意图 -> 工作流节点名称
INTENT_NODE_MAP: dict[IntentType, NodeName] = {
    IntentType.SOLVE: "math_solver",
    IntentType.TEACH: "tutor",
    IntentType.DIAGNOSE: "diagnostician",
    IntentType.PLAN: "tutor",  # Tutor PLAN 模式
}

# 关键词 -> 意图映射（按优先级排列）
_KEYWORD_MAP: list[tuple[str, IntentType]] = [
    # DIAGNOSE（提交答案 / 图片分析）
    ("我的答案", IntentType.DIAGNOSE),
    ("我算出来", IntentType.DIAGNOSE),
    ("答案是", IntentType.DIAGNOSE),
    ("我做的", IntentType.DIAGNOSE),
    ("帮我看看", IntentType.DIAGNOSE),
    ("对不对", IntentType.DIAGNOSE),
    ("批改", IntentType.DIAGNOSE),
    ("检查", IntentType.DIAGNOSE),
    # SOLVE（求解问题）
    ("计算", IntentType.SOLVE),
    ("求解", IntentType.SOLVE),
    ("求导", IntentType.SOLVE),
    ("积分", IntentType.SOLVE),
    ("解方程", IntentType.SOLVE),
    ("化简", IntentType.SOLVE),
    ("求极限", IntentType.SOLVE),
    ("求和", IntentType.SOLVE),
    ("展开", IntentType.SOLVE),
    ("因式分解", IntentType.SOLVE),
    ("行列式", IntentType.SOLVE),
    ("特征值", IntentType.SOLVE),
    # PLAN（学习路径 / 练习推荐）
    ("学习路径", IntentType.PLAN),
    ("学习计划", IntentType.PLAN),
    ("怎么学", IntentType.PLAN),
    ("学习顺序", IntentType.PLAN),
    ("练习", IntentType.PLAN),
    ("题目", IntentType.PLAN),
    ("出一道", IntentType.PLAN),
    ("做题", IntentType.PLAN),
    ("推荐", IntentType.PLAN),
    # TEACH（概念讲解 / 提示 / 一般对话）
    ("什么是", IntentType.TEACH),
    ("定义", IntentType.TEACH),
    ("解释", IntentType.TEACH),
    ("怎么理解", IntentType.TEACH),
    ("是什么意思", IntentType.TEACH),
    ("为什么", IntentType.TEACH),
    ("提示", IntentType.TEACH),
    ("帮助", IntentType.TEACH),
    ("怎么做", IntentType.TEACH),
    ("怎么入手", IntentType.TEACH),
    ("不会做", IntentType.TEACH),
    ("谢谢", IntentType.TEACH),
    ("你好", IntentType.TEACH),
    ("再见", IntentType.TEACH),
    ("好的", IntentType.TEACH),
]

_RESOURCE_REQUEST_KEYWORDS = (
    "资源",
    "资料",
    "视频",
    "文档",
    "课件",
    "材料",
)
_RESOURCE_REQUEST_ACTION_KEYWORDS = (
    "推荐",
    "有没有",
    "有吗",
    "哪些",
    "找",
    "查",
    "需要",
    "想要",
    "给我",
    "发",
)
_DIRECT_SOLVE_CONTEXT_KEYWORDS = (
    "这份",
    "这个",
    "里面",
    "里的",
    "中的",
    "怎么求",
    "怎么算",
    "求解",
    "计算",
)


def _looks_like_resource_request(message_lower: str) -> bool:
    """判断学生是否明确在要资源，避免被数学关键词误路由到求解器。"""
    has_resource_word = any(
        keyword in message_lower for keyword in _RESOURCE_REQUEST_KEYWORDS
    )
    if not has_resource_word:
        return False
    if any(keyword in message_lower for keyword in _RESOURCE_REQUEST_ACTION_KEYWORDS):
        return True
    has_direct_solve_context = any(
        keyword in message_lower for keyword in _DIRECT_SOLVE_CONTEXT_KEYWORDS
    )
    return len(message_lower) <= 20 and not has_direct_solve_context


def classify_intent(
    message: str,
    attachments: list[str] | None = None,
) -> IntentType:
    """
    纯函数意图分类，零 LLM 调用。

    分类优先级：
    1. 有附件 → DIAGNOSE
    2. 明确请求学习资源 → TEACH
    3. 关键词匹配；求解类关键词只有在包含数学表达式时才进入 SOLVE
    4. 包含数学表达式 → SOLVE
    5. 默认 → TEACH

    Args:
        message: 用户消息
        attachments: 附件列表

    Returns:
        IntentType
    """
    # 1. 有附件 → 诊断（图片分析）
    if attachments:
        return IntentType.DIAGNOSE

    message_lower = message.lower().strip()

    # 2. 明确请求学习资源 → 教学对话，避免“积分资料”误入求解器
    if _looks_like_resource_request(message_lower):
        logger.debug("资源请求检测 -> teach")
        return IntentType.TEACH

    from app.agents.core.utils import is_math_expression

    has_math_expression = is_math_expression(message)

    # 3. 关键词匹配
    for keyword, intent in _KEYWORD_MAP:
        if keyword in message_lower:
            if intent == IntentType.SOLVE and not has_math_expression:
                logger.debug(
                    f"求解关键词匹配但无数学表达式: '{keyword}' -> teach"
                )
                return IntentType.TEACH
            logger.debug(f"关键词匹配: '{keyword}' -> {intent.value}")
            return intent

    # 4. 检查是否包含数学表达式
    if has_math_expression:
        logger.debug("数学表达式检测 -> solve")
        return IntentType.SOLVE

    # 5. 默认 → 教学对话
    logger.debug("默认路由 -> teach")
    return IntentType.TEACH


def get_target_node(intent: IntentType) -> NodeName:
    """
    根据意图获取目标工作流节点名称。

    Args:
        intent: 意图类型

    Returns:
        节点名称
    """
    return INTENT_NODE_MAP.get(intent, "tutor")
