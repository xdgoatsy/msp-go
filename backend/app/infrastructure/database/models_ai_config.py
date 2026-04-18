"""
AI 配置相关 ORM 模型

三层配置架构：
1. LLMProviderModel - 提供商（DeepSeek、OpenAI、Qwen 等）
2. LLMModelModel - 模型（deepseek-chat、gpt-4 等）
3. AgentModelConfigModel - 智能体配置（每个智能体独立配置）
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.session import Base


def generate_uuid() -> str:
    """生成 UUID 字符串"""
    return str(uuid4())


class LLMProviderModel(Base):
    """
    LLM 提供商表

    存储 AI 服务提供商的基本信息和认证凭据
    """

    __tablename__ = "llm_providers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, comment="显示名称，如 DeepSeek"
    )
    code: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, comment="代码标识，如 deepseek"
    )
    base_url: Mapped[str] = mapped_column(String(500), comment="API Base URL")
    encrypted_api_key: Mapped[str] = mapped_column(
        Text, comment="Fernet 加密的 API Key"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    description: Mapped[str | None] = mapped_column(Text, comment="描述信息")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    # 关系：一个提供商有多个模型
    models: Mapped[list["LLMModelModel"]] = relationship(
        back_populates="provider", cascade="all, delete-orphan"
    )


class LLMModelModel(Base):
    """
    LLM 模型表

    存储具体的 AI 模型信息和默认参数
    """

    __tablename__ = "llm_models"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    provider_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("llm_providers.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(
        String(100), comment="显示名称，如 DeepSeek Chat"
    )
    model_id: Mapped[str] = mapped_column(
        String(100), comment="API 模型 ID，如 deepseek-chat"
    )

    # 默认参数
    default_temperature: Mapped[float] = mapped_column(
        Float, default=0.7, comment="默认温度参数"
    )
    default_max_tokens: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="默认最大 Token 数"
    )
    default_top_p: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="默认 Top P 参数"
    )
    default_timeout: Mapped[int] = mapped_column(
        Integer, default=60, comment="默认超时时间（秒）"
    )
    default_max_retries: Mapped[int] = mapped_column(
        Integer, default=3, comment="默认最大重试次数"
    )

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    is_default: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否为全局默认模型"
    )

    # 元数据
    capabilities: Mapped[dict] = mapped_column(
        JSON, default=dict, comment="模型能力标签，如 {chat: true, vision: false}"
    )
    description: Mapped[str | None] = mapped_column(Text, comment="描述信息")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    # 关系
    provider: Mapped["LLMProviderModel"] = relationship(back_populates="models")
    agent_configs: Mapped[list["AgentModelConfigModel"]] = relationship(
        back_populates="model"
    )

    # 约束：同一提供商下模型 ID 唯一
    __table_args__ = (
        UniqueConstraint("provider_id", "model_id", name="uq_provider_model"),
    )


class AgentModelConfigModel(Base):
    """
    智能体模型配置表

    为每个智能体配置使用的模型和参数覆盖
    """

    __tablename__ = "agent_model_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    agent_type: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        comment="智能体类型，如 orchestrator, solver",
    )
    model_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("llm_models.id", ondelete="SET NULL"),
        index=True,
        comment="关联的模型 ID",
    )

    # 参数覆盖（为 null 时使用模型默认值）
    temperature_override: Mapped[float | None] = mapped_column(
        Float, comment="温度参数覆盖"
    )
    max_tokens_override: Mapped[int | None] = mapped_column(
        Integer, comment="最大 Token 数覆盖"
    )
    top_p_override: Mapped[float | None] = mapped_column(Float, comment="Top P 覆盖")
    timeout_override: Mapped[int | None] = mapped_column(
        Integer, comment="超时时间覆盖（秒）"
    )
    max_retries_override: Mapped[int | None] = mapped_column(
        Integer, comment="最大重试次数覆盖"
    )

    # 额外配置
    extra_config: Mapped[dict] = mapped_column(
        JSON, default=dict, comment="智能体特定的额外配置"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    # 关系
    model: Mapped["LLMModelModel | None"] = relationship(back_populates="agent_configs")


# 智能体类型常量
AGENT_TYPES = [
    "math_solver",  # 数学求解智能体
    "tutor",  # 导师智能体
    "diagnostician",  # 诊断智能体
    "portrait",  # 学生画像
]
