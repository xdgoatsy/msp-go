"""
LangGraph 流式状态定义

定义多智能体协作的全局状态结构

设计原则：
1. 不可变性 - 每次更新返回新状态
2. 类型安全 - 使用 TypedDict 强类型
3. 可序列化 - 支持持久化到数据库
"""

import operator
import time
from typing import Annotated, Any, TypedDict


def merge_dicts(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """
    字典合并 reducer

    用于 Annotated 类型的状态字段，实现增量更新

    Args:
        a: 原字典
        b: 新字典

    Returns:
        合并后的字典，b 覆盖 a 中的同名键
    """
    return {**a, **b}


class StreamingState(TypedDict, total=False):
    """
    LangGraph 全局状态（精简版）

    从 9 智能体架构精简为 4 智能体架构后的核心状态。
    删除了未使用的字段，新增了学习追踪相关字段。

    设计说明：
    - 使用 total=False 允许部分初始化
    - 使用 Annotated 支持增量更新（如 message_stream）
    - 字段按功能分组，便于理解和维护
    """

    # ========== 会话标识 ==========
    session_id: str  # 会话唯一标识
    student_id: str  # 学生唯一标识

    # ========== 消息流（流式推送） ==========
    message_stream: Annotated[list[dict[str, Any]], operator.add]

    # ========== 路由控制 ==========
    intent: str | None  # 用户意图 (solve / teach / diagnose / plan)
    tutor_mode: str | None  # Tutor 子模式 (teach / plan)

    # ========== 教学上下文 ==========
    last_message: str  # 最后一条用户消息
    current_concept: str | None  # 当前学习的知识点
    current_problem: str | None  # 当前问题
    interaction_history: list[dict[str, Any]]  # 完整的交互记录
    attachments: list[str]  # 附件路径列表（如图片）

    # ========== 学生上下文（entry 时从 DB 加载） ==========
    student_context: dict[str, Any]  # 从 StudentProfile 加载的上下文快照
    consecutive_errors: int  # 连续错误次数

    # ========== 智能体输出 ==========
    agent_outputs: Annotated[dict[str, Any], merge_dicts]  # 各智能体的输出缓存

    # ========== 追踪数据（新增） ==========
    tracking_data: dict[str, Any]  # 本次交互的追踪数据
    profile_updates: dict[str, Any]  # Tracker 生成的画像更新指令

    # ========== 数据库会话（用于工具调用） ==========
    db_session: Any  # 数据库会话，用于工具调用访问数据

    # ========== 元数据 ==========
    session_start_time: float  # 会话开始时间（Unix 时间戳）
    total_interactions: int  # 总交互次数


def create_initial_state(
    session_id: str,
    student_id: str,
    current_concept: str | None = None,
    current_problem: str | None = None,
    student_profile: dict[str, Any] | None = None,
    db_session: Any | None = None,
) -> StreamingState:
    """
    创建初始状态

    工厂函数，用于创建一个完整初始化的状态对象

    Args:
        session_id: 会话 ID
        student_id: 学生 ID
        current_concept: 当前学习的概念（可选）
        current_problem: 当前问题（可选）
        student_profile: 学生画像（可选，用于初始化学生上下文）
        db_session: 数据库会话（可选，用于工具调用）

    Returns:
        初始化的 StreamingState
    """
    # 从学生画像构建学生上下文
    student_context: dict[str, Any] = {}
    if student_profile:
        student_context = {
            "mastery_vector": student_profile.get("mastery_vector", {}),
            "error_tendency": student_profile.get("error_tendency", {}),
            "preferred_difficulty": student_profile.get("preferred_difficulty", 0.5),
            "learning_pace": student_profile.get("learning_pace", 1.0),
            "total_exercises": student_profile.get("total_exercises", 0),
            "correct_count": student_profile.get("correct_count", 0),
        }

    return StreamingState(
        # 会话标识
        session_id=session_id,
        student_id=student_id,
        # 消息流
        message_stream=[],
        # 路由控制
        intent=None,
        tutor_mode=None,
        # 教学上下文
        last_message="",
        current_concept=current_concept,
        current_problem=current_problem,
        interaction_history=[],
        attachments=[],
        # 学生上下文
        student_context=student_context,
        consecutive_errors=0,
        # 智能体输出
        agent_outputs={},
        # 追踪数据
        tracking_data={},
        profile_updates={},
        # 数据库会话
        db_session=db_session,
        # 元数据
        session_start_time=time.time(),
        total_interactions=0,
    )


def update_state(
    state: StreamingState,
    **updates: Any,
) -> StreamingState:
    """
    更新状态

    创建状态的浅拷贝并应用更新

    Args:
        state: 当前状态
        **updates: 要更新的字段

    Returns:
        更新后的新状态
    """
    new_state = dict(state)
    new_state.update(updates)
    return StreamingState(**new_state)


def add_message(
    state: StreamingState,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> StreamingState:
    """
    添加消息到状态

    便捷函数，用于向 message_stream 添加新消息

    Args:
        state: 当前状态
        role: 消息角色 (user, assistant, system)
        content: 消息内容
        metadata: 元数据（可选）

    Returns:
        更新后的状态
    """
    message = {
        "role": role,
        "content": content,
        "metadata": metadata or {},
    }

    # 由于 message_stream 使用 operator.add，直接赋值新列表即可
    # LangGraph 会自动追加
    return update_state(state, message_stream=[message])


def get_recent_messages(
    state: StreamingState,
    count: int = 10,
) -> list[dict[str, Any]]:
    """
    获取最近的消息

    Args:
        state: 当前状态
        count: 获取的消息数量

    Returns:
        最近的消息列表
    """
    messages = state.get("message_stream", [])
    return messages[-count:] if len(messages) > count else messages


def get_conversation_context(
    state: StreamingState,
    max_messages: int = 10,
) -> str:
    """
    获取对话上下文字符串

    用于构建 LLM Prompt

    Args:
        state: 当前状态
        max_messages: 最大消息数

    Returns:
        格式化的对话上下文
    """
    messages = get_recent_messages(state, max_messages)
    lines = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)
