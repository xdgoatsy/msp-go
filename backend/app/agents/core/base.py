"""
智能体基类与接口定义

提供所有智能体的公共基类和通用数据结构

设计原则：
- 统一接口：所有智能体继承 BaseAgent
- 类型安全：完整的类型标注
- 可扩展：预留扩展点
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.agents.core.state import StreamingState


class AgentType(str, Enum):
    """智能体类型枚举（精简版 - 4 个核心智能体）"""

    SOLVER = "math_solver"  # 数学求解器（合并 Solver + Verifier + Safety）
    DIAGNOSTICIAN = "diagnostician"  # 诊断器
    TUTOR = "tutor"  # 导师（合并 Tutor + Planner）
    TRACKER = "tracker"  # 学习追踪器


@dataclass
class AgentOutput:
    """
    智能体通用输出结构

    所有智能体的输出都应包含这些基本字段
    """

    success: bool  # 是否成功
    content: str | None = None  # 主要输出内容
    metadata: dict[str, Any] = field(default_factory=dict)  # 元数据
    error: str | None = None  # 错误信息
    agent_type: AgentType | None = None  # 产生此输出的智能体类型
    timestamp: datetime = field(default_factory=datetime.now)  # 时间戳

    def to_message(self) -> dict[str, Any]:
        """转换为消息格式，用于流式推送"""
        return {
            "role": "assistant",
            "content": self.content or "",
            "metadata": {
                "agent_type": self.agent_type.value if self.agent_type else None,
                "success": self.success,
                "timestamp": self.timestamp.isoformat(),
                **self.metadata,
            },
        }


class AgentError(Exception):
    """
    智能体自定义异常

    用于智能体内部错误的统一处理
    """

    def __init__(
        self,
        message: str,
        agent_type: AgentType | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.agent_type = agent_type
        self.details = details or {}

    def __str__(self) -> str:
        agent_info = f"[{self.agent_type.value}] " if self.agent_type else ""
        return f"{agent_info}{self.message}"


class BaseAgent(ABC):
    """
    智能体抽象基类

    所有智能体必须继承此类并实现 process 方法

    使用示例：
    ```python
    class MySolver(BaseAgent):
        @property
        def name(self) -> str:
            return "my_solver"

        @property
        def description(self) -> str:
            return "自定义求解器"

        @property
        def agent_type(self) -> AgentType:
            return AgentType.SOLVER

        async def process(self, state: StreamingState) -> StreamingState:
            # 实现处理逻辑
            return state
    ```
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """智能体名称"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """智能体描述"""
        ...

    @property
    @abstractmethod
    def agent_type(self) -> AgentType:
        """智能体类型"""
        ...

    @abstractmethod
    async def process(self, state: "StreamingState") -> "StreamingState":
        """
        处理状态并返回更新后的状态

        这是智能体的核心方法，所有子类必须实现

        Args:
            state: 当前的流式状态

        Returns:
            更新后的流式状态
        """
        ...

    def create_output(
        self,
        success: bool,
        content: str | None = None,
        error: str | None = None,
        **metadata: Any,
    ) -> AgentOutput:
        """
        创建标准化的输出对象

        Args:
            success: 是否成功
            content: 输出内容
            error: 错误信息
            **metadata: 额外的元数据

        Returns:
            AgentOutput 实例
        """
        return AgentOutput(
            success=success,
            content=content,
            error=error,
            agent_type=self.agent_type,
            metadata=metadata,
        )

    def create_message(
        self,
        content: str,
        msg_type: str = "response",
        **metadata: Any,
    ) -> dict[str, Any]:
        """
        创建消息字典，用于添加到 message_stream

        Args:
            content: 消息内容
            msg_type: 消息类型 (response, thinking, error, etc.)
            **metadata: 额外的元数据

        Returns:
            消息字典
        """
        return {
            "role": "assistant",
            "content": content,
            "metadata": {
                "type": msg_type,
                "agent": self.agent_type.value,
                **metadata,
            },
        }

    async def safe_process(self, state: "StreamingState") -> "StreamingState":
        """
        安全的处理方法，包含错误处理

        自动捕获异常并添加错误消息到状态

        Args:
            state: 当前状态

        Returns:
            更新后的状态（即使出错也会返回有效状态）
        """
        try:
            return await self.process(state)
        except AgentError as e:
            # 智能体内部错误
            error_msg = self.create_message(
                content=f"处理出错：{e.message}",
                msg_type="error",
                error_details=e.details,
            )
            state["message_stream"] = [error_msg]
            return state
        except Exception as e:
            # 未预期的错误
            error_msg = self.create_message(
                content="抱歉，系统遇到了一些问题，请稍后再试。",
                msg_type="error",
                error_class=type(e).__name__,
            )
            state["message_stream"] = [error_msg]
            return state

    async def stream_process(
        self, state: "StreamingState"
    ) -> AsyncIterator[dict[str, Any]]:
        """
        流式处理状态，逐步返回内容

        子类可覆盖此方法实现真正的流式输出。
        默认实现调用 process() 后一次性返回结果。

        Args:
            state: 当前的流式状态

        Yields:
            流式输出的内容块，格式为:
            {"type": "chunk", "content": "...", "agent": "agent_type"}
        """
        # 默认实现：调用 process() 后一次性返回
        result_state = await self.process(state)
        for msg in result_state.get("message_stream", []):
            content = msg.get("content", "")
            if content:
                yield {
                    "type": "chunk",
                    "content": content,
                    "agent": self.agent_type.value,
                    "metadata": msg.get("metadata", {}),
                }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, type={self.agent_type.value})>"
