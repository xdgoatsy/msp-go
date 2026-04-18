"""
学习会话领域模型

定义学习会话和消息实体
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """消息角色"""

    USER = "user"  # 学生消息
    ASSISTANT = "assistant"  # AI 回复
    SYSTEM = "system"  # 系统消息


class AgentType(str, Enum):
    """
    智能体类型

    4 核心智能体 + 旧版兼容值
    """

    # 核心智能体
    SOLVER = "math_solver"  # 数学求解智能体（DB 枚举名 SOLVER）
    DIAGNOSTICIAN = "diagnostician"  # 诊断智能体
    TUTOR = "tutor"  # 导师智能体
    TRACKER = "tracker"  # 学习追踪智能体


@dataclass
class SessionMessage:
    """会话消息"""

    id: str
    session_id: str
    role: MessageRole
    content: str

    # 如果是 AI 回复，记录由哪个智能体生成
    agent_type: AgentType | None = None

    # 附件（如上传的解题图片）
    attachments: list[str] = field(default_factory=list)

    # 关联的知识点
    related_concept_ids: list[str] = field(default_factory=list)

    # 关联的练习题
    related_exercise_id: str | None = None

    # 元数据
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class LearningSession:
    """
    学习会话

    一次完整的学习交互过程
    """

    id: str
    student_id: str

    # 会话状态
    is_active: bool = True

    # 当前上下文
    current_topic: str | None = None  # 当前讨论的知识点
    current_exercise_id: str | None = None  # 当前练习的题目

    # 消息历史（按时间顺序）
    messages: list[SessionMessage] = field(default_factory=list)

    # 会话期间的学习记录
    exercises_attempted: list[str] = field(default_factory=list)
    concepts_discussed: list[str] = field(default_factory=list)

    # 时间记录
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: datetime | None = None

    @property
    def duration_minutes(self) -> int:
        """会话时长（分钟）"""
        end = self.ended_at or datetime.now()
        return int((end - self.started_at).total_seconds() / 60)

    def add_message(self, message: SessionMessage) -> None:
        """添加消息"""
        self.messages.append(message)

    def end_session(self) -> None:
        """结束会话"""
        self.is_active = False
        self.ended_at = datetime.now()


@dataclass
class GlobalState:
    """
    全局状态对象

    Orchestrator 维护的状态，用于多智能体协作

    参考规划文档 3.2.1 编排智能体
    """

    session_id: str
    student_id: str

    # 对话历史（用于上下文）
    conversation_history: list[dict] = field(default_factory=list)

    # 学生画像快照
    student_profile_snapshot: dict = field(default_factory=dict)

    # 当前知识点
    current_topic: str | None = None

    # 当前学习路径
    current_path: list[str] = field(default_factory=list)

    # 当前活跃的智能体
    active_agent: AgentType | None = None

    # 状态标记
    awaiting_user_input: bool = True
    last_updated: datetime = field(default_factory=datetime.now)
