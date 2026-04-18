"""
AI 配置领域模型

使用 dataclass 定义，与 ORM 模型解耦
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class LLMProvider:
    """
    LLM 提供商

    表示一个 AI 服务提供商（如 DeepSeek、OpenAI、Qwen）
    """

    id: str
    name: str
    code: str
    base_url: str
    is_active: bool = True
    description: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # 注意：API Key 不在领域模型中暴露，仅在服务层处理


@dataclass
class LLMModel:
    """
    LLM 模型

    表示一个具体的 AI 模型（如 deepseek-chat、gpt-4）
    """

    id: str
    provider_id: str
    name: str
    model_id: str
    default_temperature: float = 0.7
    default_max_tokens: int | None = None
    default_top_p: float | None = None
    default_timeout: int = 60
    default_max_retries: int = 3
    is_active: bool = True
    is_default: bool = False
    capabilities: dict[str, Any] = field(default_factory=dict)
    description: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # 关联的提供商信息（可选，用于展示）
    provider_name: str | None = None
    provider_code: str | None = None
    provider_base_url: str | None = None


@dataclass
class AgentModelConfig:
    """
    智能体模型配置

    为特定智能体配置使用的模型和参数
    """

    id: str
    agent_type: str
    model_id: str | None = None
    temperature_override: float | None = None
    max_tokens_override: int | None = None
    top_p_override: float | None = None
    timeout_override: int | None = None
    max_retries_override: int | None = None
    extra_config: dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # 关联的模型信息（可选，用于展示）
    model_name: str | None = None
    model_model_id: str | None = None
    provider_name: str | None = None


@dataclass
class ResolvedAgentConfig:
    """
    解析后的智能体配置

    合并了提供商、模型、智能体配置三层的最终配置
    用于 LLMClient 初始化
    """

    agent_type: str
    api_base: str
    api_key: str  # 已解密
    model_name: str
    temperature: float
    timeout: int
    max_retries: int
    max_tokens: int | None = None
    top_p: float | None = None
    extra_config: dict[str, Any] = field(default_factory=dict)

    # 来源信息（用于调试和日志）
    provider_id: str | None = None
    provider_name: str | None = None
    model_id: str | None = None


# 智能体类型常量
class AgentType:
    """智能体类型常量（精简版 - 4 个 LLM 配置类型）"""

    MATH_SOLVER = "math_solver"
    TUTOR = "tutor"
    DIAGNOSTICIAN = "diagnostician"
    PORTRAIT = "portrait"

    @classmethod
    def all_types(cls) -> list[str]:
        """获取所有智能体类型"""
        return [
            cls.MATH_SOLVER,
            cls.TUTOR,
            cls.DIAGNOSTICIAN,
            cls.PORTRAIT,
        ]

    @classmethod
    def is_valid(cls, agent_type: str) -> bool:
        """检查智能体类型是否有效"""
        return agent_type in cls.all_types()


# 智能体类型显示名称映射
AGENT_TYPE_DISPLAY_NAMES = {
    AgentType.MATH_SOLVER: "数学求解智能体",
    AgentType.TUTOR: "导师智能体",
    AgentType.DIAGNOSTICIAN: "诊断智能体",
    AgentType.PORTRAIT: "学生画像",
}
