"""
API v1 Schemas

定义 API 请求和响应的数据结构
"""

from app.api.v1.schemas.ai_config import (
    AgentConfigListResponse,
    AgentConfigResponse,
    AgentConfigUpdate,
    AgentTypeInfo,
    AgentTypeListResponse,
    ErrorResponse,
    ModelCreate,
    ModelListResponse,
    ModelResponse,
    ModelUpdate,
    ProviderCreate,
    ProviderListResponse,
    ProviderResponse,
    ProviderTestResponse,
    ProviderUpdate,
    SuccessResponse,
)

__all__ = [
    # Provider
    "ProviderCreate",
    "ProviderUpdate",
    "ProviderResponse",
    "ProviderListResponse",
    "ProviderTestResponse",
    # Model
    "ModelCreate",
    "ModelUpdate",
    "ModelResponse",
    "ModelListResponse",
    # Agent Config
    "AgentConfigUpdate",
    "AgentConfigResponse",
    "AgentConfigListResponse",
    # Agent Type
    "AgentTypeInfo",
    "AgentTypeListResponse",
    # Common
    "SuccessResponse",
    "ErrorResponse",
]
