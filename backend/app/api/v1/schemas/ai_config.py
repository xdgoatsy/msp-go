"""
AI 配置 API Schema

定义 API 请求和响应的数据结构
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# ========== 提供商 Schema ==========


class ProviderBase(BaseModel):
    """提供商基础字段"""

    name: str = Field(..., min_length=1, max_length=100, description="显示名称")
    code: str = Field(
        ..., min_length=1, max_length=50, pattern=r"^[a-z][a-z0-9_-]*$", description="代码标识（小写字母开头，只能包含小写字母、数字、下划线、连字符）"
    )
    base_url: str = Field(..., min_length=1, max_length=500, description="API Base URL")
    description: str | None = Field(None, max_length=1000, description="描述信息")


class ProviderCreate(ProviderBase):
    """创建提供商请求"""

    api_key: str = Field(..., min_length=1, description="API Key")


class ModelCreateSimple(BaseModel):
    """简化的模型创建（用于批量创建）"""

    model_id: str = Field(..., min_length=1, max_length=100, description="API 模型 ID，如 deepseek-chat")
    name: str | None = Field(None, max_length=100, description="显示名称，默认使用 model_id")


class ProviderCreateWithModels(BaseModel):
    """创建提供商并同时创建模型"""

    name: str = Field(..., min_length=1, max_length=100, description="渠道名称")
    code: str = Field(
        ..., min_length=1, max_length=50, pattern=r"^[a-z][a-z0-9_-]*$", description="代码标识"
    )
    base_url: str = Field(..., min_length=1, max_length=500, description="API Base URL")
    api_key: str = Field(..., min_length=1, description="API Key")
    description: str | None = Field(None, max_length=1000, description="描述信息")
    models: list[ModelCreateSimple] = Field(default_factory=list, description="模型列表")


class ProviderUpdate(BaseModel):
    """更新提供商请求"""

    name: str | None = Field(None, min_length=1, max_length=100, description="显示名称")
    base_url: str | None = Field(None, min_length=1, max_length=500, description="API Base URL")
    api_key: str | None = Field(None, min_length=1, description="API Key（留空则不更新）")
    is_active: bool | None = Field(None, description="是否启用")
    description: str | None = Field(None, max_length=1000, description="描述信息")


class ProviderResponse(BaseModel):
    """提供商响应"""

    id: str = Field(..., description="提供商 ID")
    name: str = Field(..., description="显示名称")
    code: str = Field(..., description="代码标识")
    base_url: str = Field(..., description="API Base URL")
    is_active: bool = Field(..., description="是否启用")
    description: str | None = Field(None, description="描述信息")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = {"from_attributes": True}


class ProviderListResponse(BaseModel):
    """提供商列表响应"""

    items: list[ProviderResponse] = Field(..., description="提供商列表")
    total: int = Field(..., description="总数")


class ProviderTestRequest(BaseModel):
    """提供商连接测试请求"""

    model_id: str | None = Field(None, description="指定测试的模型 ID（可选，不指定则测试 /models 端点）")


class ProviderTestResponse(BaseModel):
    """提供商连接测试响应"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="结果消息")
    latency_ms: float = Field(..., description="延迟（毫秒）")
    model_id: str | None = Field(None, description="测试使用的模型 ID")


class ProviderWithModelsResponse(BaseModel):
    """创建提供商并同时创建模型的响应"""

    provider: ProviderResponse = Field(..., description="创建的提供商")
    models: list["ModelResponse"] = Field(..., description="创建的模型列表")
    models_count: int = Field(..., description="创建的模型数量")


class FetchModelsResponse(BaseModel):
    """从 API 获取可用模型列表的响应"""

    success: bool = Field(..., description="是否成功")
    models: list[str] = Field(default_factory=list, description="可用的模型 ID 列表")
    message: str = Field(..., description="结果消息")


class FetchModelsByCredentialsRequest(BaseModel):
    """根据凭据获取模型列表的请求（用于新建渠道时）"""

    base_url: str = Field(..., min_length=1, max_length=500, description="API Base URL")
    api_key: str = Field(..., min_length=1, description="API Key")


# ========== 模型 Schema ==========


class ModelBase(BaseModel):
    """模型基础字段"""

    provider_id: str = Field(..., description="提供商 ID")
    name: str = Field(..., min_length=1, max_length=100, description="显示名称")
    model_id: str = Field(..., min_length=1, max_length=100, description="API 模型 ID")
    default_temperature: float = Field(0.7, ge=0, le=2, description="默认温度参数")
    default_max_tokens: int | None = Field(None, ge=1, le=128000, description="默认最大 Token 数")
    default_top_p: float | None = Field(None, ge=0, le=1, description="默认 Top P 参数")
    default_timeout: int = Field(60, ge=1, le=600, description="默认超时时间（秒）")
    default_max_retries: int = Field(3, ge=0, le=10, description="默认最大重试次数")
    capabilities: dict[str, Any] = Field(default_factory=dict, description="模型能力标签")
    description: str | None = Field(None, max_length=1000, description="描述信息")


class ModelCreate(ModelBase):
    """创建模型请求"""

    pass


class ModelUpdate(BaseModel):
    """更新模型请求"""

    name: str | None = Field(None, min_length=1, max_length=100, description="显示名称")
    model_id: str | None = Field(None, min_length=1, max_length=100, description="API 模型 ID")
    default_temperature: float | None = Field(None, ge=0, le=2, description="默认温度参数")
    default_max_tokens: int | None = Field(None, ge=1, le=128000, description="默认最大 Token 数")
    default_top_p: float | None = Field(None, ge=0, le=1, description="默认 Top P 参数")
    default_timeout: int | None = Field(None, ge=1, le=600, description="默认超时时间（秒）")
    default_max_retries: int | None = Field(None, ge=0, le=10, description="默认最大重试次数")
    is_active: bool | None = Field(None, description="是否启用")
    capabilities: dict[str, Any] | None = Field(None, description="模型能力标签")
    description: str | None = Field(None, max_length=1000, description="描述信息")


class ModelResponse(BaseModel):
    """模型响应"""

    id: str = Field(..., description="模型 ID")
    provider_id: str = Field(..., description="提供商 ID")
    name: str = Field(..., description="显示名称")
    model_id: str = Field(..., description="API 模型 ID")
    default_temperature: float = Field(..., description="默认温度参数")
    default_max_tokens: int | None = Field(None, description="默认最大 Token 数")
    default_top_p: float | None = Field(None, description="默认 Top P 参数")
    default_timeout: int = Field(..., description="默认超时时间（秒）")
    default_max_retries: int = Field(..., description="默认最大重试次数")
    is_active: bool = Field(..., description="是否启用")
    is_default: bool = Field(..., description="是否为默认模型")
    capabilities: dict[str, Any] = Field(..., description="模型能力标签")
    description: str | None = Field(None, description="描述信息")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    # 关联的提供商信息
    provider_name: str | None = Field(None, description="提供商名称")
    provider_code: str | None = Field(None, description="提供商代码")

    model_config = {"from_attributes": True}


class ModelListResponse(BaseModel):
    """模型列表响应"""

    items: list[ModelResponse] = Field(..., description="模型列表")
    total: int = Field(..., description="总数")


# ========== 智能体配置 Schema ==========


class AgentConfigBase(BaseModel):
    """智能体配置基础字段"""

    model_id: str = Field(..., description="模型 ID")
    temperature_override: float | None = Field(None, ge=0, le=2, description="温度参数覆盖")
    max_tokens_override: int | None = Field(None, ge=1, le=128000, description="最大 Token 数覆盖")
    top_p_override: float | None = Field(None, ge=0, le=1, description="Top P 参数覆盖")
    timeout_override: int | None = Field(None, ge=1, le=600, description="超时时间覆盖（秒）")
    max_retries_override: int | None = Field(None, ge=0, le=10, description="最大重试次数覆盖")
    extra_config: dict[str, Any] = Field(default_factory=dict, description="额外配置")


class AgentConfigUpdate(AgentConfigBase):
    """更新智能体配置请求"""

    pass


class AgentConfigResponse(BaseModel):
    """智能体配置响应"""

    id: str = Field(..., description="配置 ID")
    agent_type: str = Field(..., description="智能体类型")
    model_id: str | None = Field(None, description="模型 ID")
    temperature_override: float | None = Field(None, description="温度参数覆盖")
    max_tokens_override: int | None = Field(None, description="最大 Token 数覆盖")
    top_p_override: float | None = Field(None, description="Top P 参数覆盖")
    timeout_override: int | None = Field(None, description="超时时间覆盖（秒）")
    max_retries_override: int | None = Field(None, description="最大重试次数覆盖")
    extra_config: dict[str, Any] = Field(..., description="额外配置")
    is_active: bool = Field(..., description="是否启用")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    # 关联的模型信息
    model_name: str | None = Field(None, description="模型名称")
    model_model_id: str | None = Field(None, description="API 模型 ID")
    provider_name: str | None = Field(None, description="提供商名称")

    model_config = {"from_attributes": True}


class AgentConfigListResponse(BaseModel):
    """智能体配置列表响应"""

    items: list[AgentConfigResponse] = Field(..., description="智能体配置列表")
    total: int = Field(..., description="总数")


# ========== 智能体类型 Schema ==========


class AgentTypeInfo(BaseModel):
    """智能体类型信息"""

    type: str = Field(..., description="智能体类型代码")
    name: str = Field(..., description="智能体显示名称")
    configured: bool = Field(..., description="是否已配置")


class AgentTypeListResponse(BaseModel):
    """智能体类型列表响应"""

    items: list[AgentTypeInfo] = Field(..., description="智能体类型列表")


# ========== 通用响应 ==========


class SuccessResponse(BaseModel):
    """通用成功响应"""

    success: bool = Field(True, description="是否成功")
    message: str = Field(..., description="消息")


class ErrorResponse(BaseModel):
    """通用错误响应"""

    success: bool = Field(False, description="是否成功")
    error: str = Field(..., description="错误信息")
    detail: str | None = Field(None, description="详细信息")


# ========== 模型批量更新 Schema ==========


class ModelsUpdateRequest(BaseModel):
    """模型批量更新请求（全量替换）"""

    models: list[ModelCreateSimple] = Field(..., description="完整的模型列表")


class ModelsUpdateResponse(BaseModel):
    """模型批量更新响应"""

    added: int = Field(..., description="新增数量")
    removed: int = Field(..., description="删除数量")
    unchanged: int = Field(..., description="未变数量")
    models: list[ModelResponse] = Field(..., description="更新后的模型列表")
