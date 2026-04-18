"""
AI 配置管理 API

提供 AI 模型配置的管理接口，仅管理员可访问
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import AdminUserId, DbSession
from app.api.v1.schemas.ai_config import (
    AgentConfigListResponse,
    AgentConfigResponse,
    AgentConfigUpdate,
    AgentTypeInfo,
    AgentTypeListResponse,
    ErrorResponse,
    FetchModelsByCredentialsRequest,
    FetchModelsResponse,
    ModelCreate,
    ModelListResponse,
    ModelResponse,
    ModelsUpdateRequest,
    ModelsUpdateResponse,
    ModelUpdate,
    ProviderCreate,
    ProviderCreateWithModels,
    ProviderListResponse,
    ProviderResponse,
    ProviderTestResponse,
    ProviderUpdate,
    ProviderWithModelsResponse,
    SuccessResponse,
)
from app.domain.models.ai_config import (
    AGENT_TYPE_DISPLAY_NAMES,
    AgentType,
)
from app.services.ai_config_service import AIConfigService

logger = logging.getLogger(__name__)

router = APIRouter()


# ========== 依赖注入 ==========


async def get_ai_config_service(db: DbSession) -> AIConfigService:
    """获取 AI 配置服务"""
    return AIConfigService(db=db)


AIConfigServiceDep = Annotated[AIConfigService, Depends(get_ai_config_service)]


# ========== 提供商管理 ==========


@router.get(
    "/providers",
    response_model=ProviderListResponse,
    summary="获取提供商列表",
    description="获取所有 LLM 提供商列表",
)
async def list_providers(
    _admin_id: AdminUserId,
    service: AIConfigServiceDep,
    include_inactive: bool = Query(False, description="是否包含已禁用的提供商"),
) -> ProviderListResponse:
    """获取提供商列表"""
    providers = await service.list_providers(include_inactive=include_inactive)
    return ProviderListResponse(
        items=[
            ProviderResponse(
                id=p.id,
                name=p.name,
                code=p.code,
                base_url=p.base_url,
                is_active=p.is_active,
                description=p.description,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in providers
        ],
        total=len(providers),
    )


@router.get(
    "/providers/{provider_id}",
    response_model=ProviderResponse,
    summary="获取单个提供商",
    description="根据 ID 获取提供商详情",
    responses={404: {"model": ErrorResponse}},
)
async def get_provider(
    provider_id: str,
    _admin_id: AdminUserId,
    service: AIConfigServiceDep,
) -> ProviderResponse:
    """获取单个提供商"""
    provider = await service.get_provider(provider_id)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="提供商不存在",
        )
    return ProviderResponse(
        id=provider.id,
        name=provider.name,
        code=provider.code,
        base_url=provider.base_url,
        is_active=provider.is_active,
        description=provider.description,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    )


@router.post(
    "/providers",
    response_model=ProviderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建提供商",
    description="创建新的 LLM 提供商",
    responses={400: {"model": ErrorResponse}},
)
async def create_provider(
    data: ProviderCreate,
    _admin_id: AdminUserId,
    service: AIConfigServiceDep,
) -> ProviderResponse:
    """创建提供商"""
    try:
        # 检查代码是否已存在
        existing = await service.get_provider_by_code(data.code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"提供商代码 '{data.code}' 已存在",
            )

        provider = await service.create_provider(
            name=data.name,
            code=data.code,
            base_url=data.base_url,
            api_key=data.api_key,
            description=data.description,
        )

        logger.info(f"管理员创建提供商: id={provider.id}, name={provider.name}")

        return ProviderResponse(
            id=provider.id,
            name=provider.name,
            code=provider.code,
            base_url=provider.base_url,
            is_active=provider.is_active,
            description=provider.description,
            created_at=provider.created_at,
            updated_at=provider.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建提供商失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"创建提供商失败: {str(e)}",
        ) from e


@router.put(
    "/providers/{provider_id}",
    response_model=ProviderResponse,
    summary="更新提供商",
    description="更新提供商信息",
    responses={404: {"model": ErrorResponse}},
)
async def update_provider(
    provider_id: str,
    data: ProviderUpdate,
    _admin_id: AdminUserId,
    service: AIConfigServiceDep,
) -> ProviderResponse:
    """更新提供商"""
    provider = await service.update_provider(
        provider_id=provider_id,
        name=data.name,
        base_url=data.base_url,
        api_key=data.api_key,
        is_active=data.is_active,
        description=data.description,
    )

    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="提供商不存在",
        )

    logger.info(f"管理员更新提供商: id={provider_id}")

    return ProviderResponse(
        id=provider.id,
        name=provider.name,
        code=provider.code,
        base_url=provider.base_url,
        is_active=provider.is_active,
        description=provider.description,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    )


@router.delete(
    "/providers/{provider_id}",
    response_model=SuccessResponse,
    summary="删除提供商",
    description="删除提供商（会同时删除关联的模型）",
    responses={404: {"model": ErrorResponse}},
)
async def delete_provider(
    provider_id: str,
    _admin_id: AdminUserId,
    service: AIConfigServiceDep,
) -> SuccessResponse:
    """删除提供商"""
    result = await service.delete_provider(provider_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="提供商不存在",
        )

    logger.info(f"管理员删除提供商: id={provider_id}")

    return SuccessResponse(success=True, message="提供商已删除")


@router.post(
    "/providers/{provider_id}/test",
    response_model=ProviderTestResponse,
    summary="测试提供商连接",
    description="测试提供商 API 连接是否正常，可指定模型进行真实调用测试",
    responses={404: {"model": ErrorResponse}},
)
async def test_provider(
    provider_id: str,
    _admin_id: AdminUserId,
    service: AIConfigServiceDep,
    model_id: str | None = Query(None, description="指定测试的模型 ID（可选）"),
) -> ProviderTestResponse:
    """测试提供商连接"""
    result = await service.test_provider_connection(provider_id, model_id=model_id)

    if result.get("message") == "提供商不存在":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="提供商不存在",
        )

    return ProviderTestResponse(
        success=result["success"],
        message=result["message"],
        latency_ms=result["latency_ms"],
        model_id=result.get("model_id"),
    )


@router.post(
    "/channels/fetch-models",
    response_model=FetchModelsResponse,
    summary="根据凭据获取可用模型列表",
    description="根据 Base URL 和 API Key 获取可用的模型列表（用于新建渠道时）",
)
async def fetch_models_by_credentials(
    data: FetchModelsByCredentialsRequest,
    _admin_id: AdminUserId,
    service: AIConfigServiceDep,
) -> FetchModelsResponse:
    """根据凭据获取可用模型列表（用于新建渠道时）"""
    result = await service.fetch_models_by_credentials(
        base_url=data.base_url,
        api_key=data.api_key,
    )

    return FetchModelsResponse(
        success=result["success"],
        models=result["models"],
        message=result["message"],
    )


@router.get(
    "/providers/{provider_id}/fetch-models",
    response_model=FetchModelsResponse,
    summary="获取可用模型列表",
    description="从提供商 API 获取可用的模型列表",
    responses={404: {"model": ErrorResponse}},
)
async def fetch_available_models(
    provider_id: str,
    _admin_id: AdminUserId,
    service: AIConfigServiceDep,
) -> FetchModelsResponse:
    """从提供商 API 获取可用模型列表"""
    result = await service.fetch_available_models(provider_id)

    if result.get("message") == "提供商不存在":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="提供商不存在",
        )

    return FetchModelsResponse(
        success=result["success"],
        models=result["models"],
        message=result["message"],
    )


@router.post(
    "/providers/with-models",
    response_model=ProviderWithModelsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建提供商并同时创建模型",
    description="一次性创建提供商和关联的模型（原子操作）",
    responses={400: {"model": ErrorResponse}},
)
async def create_provider_with_models(
    data: ProviderCreateWithModels,
    _admin_id: AdminUserId,
    service: AIConfigServiceDep,
) -> ProviderWithModelsResponse:
    """创建提供商并同时创建模型"""
    try:
        # 检查代码是否已存在
        existing = await service.get_provider_by_code(data.code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"提供商代码 '{data.code}' 已存在",
            )

        # 转换模型数据
        models_data = [
            {"model_id": m.model_id, "name": m.name}
            for m in data.models
        ]

        provider, models = await service.create_provider_with_models(
            name=data.name,
            code=data.code,
            base_url=data.base_url,
            api_key=data.api_key,
            models=models_data,
            description=data.description,
        )

        logger.info(
            f"管理员创建提供商和模型: provider_id={provider.id}, "
            f"provider_name={provider.name}, models_count={len(models)}"
        )

        return ProviderWithModelsResponse(
            provider=ProviderResponse(
                id=provider.id,
                name=provider.name,
                code=provider.code,
                base_url=provider.base_url,
                is_active=provider.is_active,
                description=provider.description,
                created_at=provider.created_at,
                updated_at=provider.updated_at,
            ),
            models=[
                ModelResponse(
                    id=m.id,
                    provider_id=m.provider_id,
                    name=m.name,
                    model_id=m.model_id,
                    default_temperature=m.default_temperature,
                    default_max_tokens=m.default_max_tokens,
                    default_top_p=m.default_top_p,
                    default_timeout=m.default_timeout,
                    default_max_retries=m.default_max_retries,
                    is_active=m.is_active,
                    is_default=m.is_default,
                    capabilities=m.capabilities,
                    description=m.description,
                    created_at=m.created_at,
                    updated_at=m.updated_at,
                    provider_name=m.provider_name,
                    provider_code=m.provider_code,
                )
                for m in models
            ],
            models_count=len(models),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建提供商和模型失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"创建失败: {str(e)}",
        ) from e


@router.put(
    "/providers/{provider_id}/models",
    response_model=ModelsUpdateResponse,
    summary="更新提供商的模型列表",
    description="全量替换提供商的模型列表（自动计算差异，新增/删除模型）",
    responses={404: {"model": ErrorResponse}},
)
async def update_provider_models(
    provider_id: str,
    data: ModelsUpdateRequest,
    _admin_id: AdminUserId,
    service: AIConfigServiceDep,
) -> ModelsUpdateResponse:
    """更新提供商的模型列表（全量替换）"""
    # 检查提供商是否存在
    provider = await service.get_provider(provider_id)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="提供商不存在",
        )

    # 转换模型数据
    models_data = [
        {"model_id": m.model_id, "name": m.name}
        for m in data.models
    ]

    # 同步模型
    result = await service.sync_provider_models(provider_id, models_data)

    logger.info(
        f"管理员更新提供商模型: provider_id={provider_id}, "
        f"added={result['added']}, removed={result['removed']}, unchanged={result['unchanged']}"
    )

    return ModelsUpdateResponse(
        added=result["added"],
        removed=result["removed"],
        unchanged=result["unchanged"],
        models=[
            ModelResponse(
                id=m.id,
                provider_id=m.provider_id,
                name=m.name,
                model_id=m.model_id,
                default_temperature=m.default_temperature,
                default_max_tokens=m.default_max_tokens,
                default_top_p=m.default_top_p,
                default_timeout=m.default_timeout,
                default_max_retries=m.default_max_retries,
                is_active=m.is_active,
                is_default=m.is_default,
                capabilities=m.capabilities,
                description=m.description,
                created_at=m.created_at,
                updated_at=m.updated_at,
                provider_name=m.provider_name,
                provider_code=m.provider_code,
            )
            for m in result["models"]
        ],
    )


# ========== 模型管理 ==========


@router.get(
    "/models",
    response_model=ModelListResponse,
    summary="获取模型列表",
    description="获取所有 LLM 模型列表，可按提供商筛选",
)
async def list_models(
    _admin_id: AdminUserId,
    service: AIConfigServiceDep,
    provider_id: str | None = Query(None, description="提供商 ID（可选，用于筛选）"),
    include_inactive: bool = Query(False, description="是否包含已禁用的模型"),
) -> ModelListResponse:
    """获取模型列表"""
    models = await service.list_models(
        provider_id=provider_id,
        include_inactive=include_inactive,
    )
    return ModelListResponse(
        items=[
            ModelResponse(
                id=m.id,
                provider_id=m.provider_id,
                name=m.name,
                model_id=m.model_id,
                default_temperature=m.default_temperature,
                default_max_tokens=m.default_max_tokens,
                default_top_p=m.default_top_p,
                default_timeout=m.default_timeout,
                default_max_retries=m.default_max_retries,
                is_active=m.is_active,
                is_default=m.is_default,
                capabilities=m.capabilities,
                description=m.description,
                created_at=m.created_at,
                updated_at=m.updated_at,
                provider_name=m.provider_name,
                provider_code=m.provider_code,
            )
            for m in models
        ],
        total=len(models),
    )


@router.get(
    "/models/{model_id}",
    response_model=ModelResponse,
    summary="获取单个模型",
    description="根据 ID 获取模型详情",
    responses={404: {"model": ErrorResponse}},
)
async def get_model(
    model_id: str,
    _admin_id: AdminUserId,
    service: AIConfigServiceDep,
) -> ModelResponse:
    """获取单个模型"""
    model = await service.get_model(model_id)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型不存在",
        )
    return ModelResponse(
        id=model.id,
        provider_id=model.provider_id,
        name=model.name,
        model_id=model.model_id,
        default_temperature=model.default_temperature,
        default_max_tokens=model.default_max_tokens,
        default_top_p=model.default_top_p,
        default_timeout=model.default_timeout,
        default_max_retries=model.default_max_retries,
        is_active=model.is_active,
        is_default=model.is_default,
        capabilities=model.capabilities,
        description=model.description,
        created_at=model.created_at,
        updated_at=model.updated_at,
        provider_name=model.provider_name,
        provider_code=model.provider_code,
    )


@router.post(
    "/models",
    response_model=ModelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建模型",
    description="创建新的 LLM 模型",
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def create_model(
    data: ModelCreate,
    _admin_id: AdminUserId,
    service: AIConfigServiceDep,
) -> ModelResponse:
    """创建模型"""
    try:
        # 检查提供商是否存在
        provider = await service.get_provider(data.provider_id)
        if provider is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="提供商不存在",
            )

        model = await service.create_model(
            provider_id=data.provider_id,
            name=data.name,
            model_id=data.model_id,
            default_temperature=data.default_temperature,
            default_max_tokens=data.default_max_tokens,
            default_top_p=data.default_top_p,
            default_timeout=data.default_timeout,
            default_max_retries=data.default_max_retries,
            capabilities=data.capabilities,
            description=data.description,
        )

        logger.info(f"管理员创建模型: id={model.id}, name={model.name}")

        return ModelResponse(
            id=model.id,
            provider_id=model.provider_id,
            name=model.name,
            model_id=model.model_id,
            default_temperature=model.default_temperature,
            default_max_tokens=model.default_max_tokens,
            default_top_p=model.default_top_p,
            default_timeout=model.default_timeout,
            default_max_retries=model.default_max_retries,
            is_active=model.is_active,
            is_default=model.is_default,
            capabilities=model.capabilities,
            description=model.description,
            created_at=model.created_at,
            updated_at=model.updated_at,
            provider_name=model.provider_name,
            provider_code=model.provider_code,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建模型失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"创建模型失败: {str(e)}",
        ) from e


@router.put(
    "/models/{model_id}",
    response_model=ModelResponse,
    summary="更新模型",
    description="更新模型信息",
    responses={404: {"model": ErrorResponse}},
)
async def update_model(
    model_id: str,
    data: ModelUpdate,
    _admin_id: AdminUserId,
    service: AIConfigServiceDep,
) -> ModelResponse:
    """更新模型"""
    # 构建更新字典，只包含非 None 的字段
    updates = {k: v for k, v in data.model_dump().items() if v is not None}

    model = await service.update_model(model_id, **updates)

    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型不存在",
        )

    logger.info(f"管理员更新模型: id={model_id}")

    return ModelResponse(
        id=model.id,
        provider_id=model.provider_id,
        name=model.name,
        model_id=model.model_id,
        default_temperature=model.default_temperature,
        default_max_tokens=model.default_max_tokens,
        default_top_p=model.default_top_p,
        default_timeout=model.default_timeout,
        default_max_retries=model.default_max_retries,
        is_active=model.is_active,
        is_default=model.is_default,
        capabilities=model.capabilities,
        description=model.description,
        created_at=model.created_at,
        updated_at=model.updated_at,
        provider_name=model.provider_name,
        provider_code=model.provider_code,
    )


@router.delete(
    "/models/{model_id}",
    response_model=SuccessResponse,
    summary="删除模型",
    description="删除模型",
    responses={404: {"model": ErrorResponse}},
)
async def delete_model(
    model_id: str,
    _admin_id: AdminUserId,
    service: AIConfigServiceDep,
) -> SuccessResponse:
    """删除模型"""
    result = await service.delete_model(model_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型不存在",
        )

    logger.info(f"管理员删除模型: id={model_id}")

    return SuccessResponse(success=True, message="模型已删除")


@router.post(
    "/models/{model_id}/set-default",
    response_model=SuccessResponse,
    summary="设置默认模型",
    description="将指定模型设置为全局默认模型",
    responses={404: {"model": ErrorResponse}},
)
async def set_default_model(
    model_id: str,
    _admin_id: AdminUserId,
    service: AIConfigServiceDep,
) -> SuccessResponse:
    """设置默认模型"""
    result = await service.set_default_model(model_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型不存在",
        )

    logger.info(f"管理员设置默认模型: id={model_id}")

    return SuccessResponse(success=True, message="已设置为默认模型")


# ========== 智能体配置管理 ==========


@router.get(
    "/agents",
    response_model=AgentConfigListResponse,
    summary="获取智能体配置列表",
    description="获取所有智能体的模型配置",
)
async def list_agent_configs(
    _admin_id: AdminUserId,
    service: AIConfigServiceDep,
) -> AgentConfigListResponse:
    """获取智能体配置列表"""
    configs = await service.list_agent_configs()
    return AgentConfigListResponse(
        items=[
            AgentConfigResponse(
                id=c.id,
                agent_type=c.agent_type,
                model_id=c.model_id,
                temperature_override=c.temperature_override,
                max_tokens_override=c.max_tokens_override,
                top_p_override=c.top_p_override,
                timeout_override=c.timeout_override,
                max_retries_override=c.max_retries_override,
                extra_config=c.extra_config,
                is_active=c.is_active,
                created_at=c.created_at,
                updated_at=c.updated_at,
                model_name=c.model_name,
                model_model_id=c.model_model_id,
                provider_name=c.provider_name,
            )
            for c in configs
        ],
        total=len(configs),
    )


@router.get(
    "/agents/types",
    response_model=AgentTypeListResponse,
    summary="获取智能体类型列表",
    description="获取所有可配置的智能体类型",
)
async def list_agent_types(
    _admin_id: AdminUserId,
    service: AIConfigServiceDep,
) -> AgentTypeListResponse:
    """获取智能体类型列表"""
    # 获取已配置的智能体
    configs = await service.list_agent_configs()
    configured_types = {c.agent_type for c in configs}

    # 构建类型列表
    items = [
        AgentTypeInfo(
            type=agent_type,
            name=AGENT_TYPE_DISPLAY_NAMES.get(agent_type, agent_type),
            configured=agent_type in configured_types,
        )
        for agent_type in AgentType.all_types()
    ]

    return AgentTypeListResponse(items=items)


@router.get(
    "/agents/{agent_type}",
    response_model=AgentConfigResponse,
    summary="获取单个智能体配置",
    description="根据智能体类型获取配置详情",
    responses={404: {"model": ErrorResponse}},
)
async def get_agent_config(
    agent_type: str,
    _admin_id: AdminUserId,
    service: AIConfigServiceDep,
) -> AgentConfigResponse:
    """获取单个智能体配置"""
    # 验证智能体类型
    if not AgentType.is_valid(agent_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的智能体类型: {agent_type}",
        )

    config = await service.get_agent_config(agent_type)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"智能体 '{agent_type}' 未配置",
        )

    return AgentConfigResponse(
        id=config.id,
        agent_type=config.agent_type,
        model_id=config.model_id,
        temperature_override=config.temperature_override,
        max_tokens_override=config.max_tokens_override,
        top_p_override=config.top_p_override,
        timeout_override=config.timeout_override,
        max_retries_override=config.max_retries_override,
        extra_config=config.extra_config,
        is_active=config.is_active,
        created_at=config.created_at,
        updated_at=config.updated_at,
        model_name=config.model_name,
        model_model_id=config.model_model_id,
        provider_name=config.provider_name,
    )


@router.put(
    "/agents/{agent_type}",
    response_model=AgentConfigResponse,
    summary="更新智能体配置",
    description="创建或更新智能体的模型配置",
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def update_agent_config(
    agent_type: str,
    data: AgentConfigUpdate,
    _admin_id: AdminUserId,
    service: AIConfigServiceDep,
) -> AgentConfigResponse:
    """更新智能体配置"""
    # 验证智能体类型
    if not AgentType.is_valid(agent_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的智能体类型: {agent_type}",
        )

    # 验证模型是否存在
    model = await service.get_model(data.model_id)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型不存在",
        )

    config = await service.upsert_agent_config(
        agent_type=agent_type,
        model_id=data.model_id,
        temperature_override=data.temperature_override,
        max_tokens_override=data.max_tokens_override,
        top_p_override=data.top_p_override,
        timeout_override=data.timeout_override,
        max_retries_override=data.max_retries_override,
        extra_config=data.extra_config,
    )

    logger.info(f"管理员更新智能体配置: agent_type={agent_type}")

    return AgentConfigResponse(
        id=config.id,
        agent_type=config.agent_type,
        model_id=config.model_id,
        temperature_override=config.temperature_override,
        max_tokens_override=config.max_tokens_override,
        top_p_override=config.top_p_override,
        timeout_override=config.timeout_override,
        max_retries_override=config.max_retries_override,
        extra_config=config.extra_config,
        is_active=config.is_active,
        created_at=config.created_at,
        updated_at=config.updated_at,
        model_name=config.model_name,
        model_model_id=config.model_model_id,
        provider_name=config.provider_name,
    )


@router.delete(
    "/agents/{agent_type}",
    response_model=SuccessResponse,
    summary="删除智能体配置",
    description="删除智能体配置（恢复使用默认模型）",
    responses={404: {"model": ErrorResponse}},
)
async def delete_agent_config(
    agent_type: str,
    _admin_id: AdminUserId,
    service: AIConfigServiceDep,
) -> SuccessResponse:
    """删除智能体配置"""
    # 验证智能体类型
    if not AgentType.is_valid(agent_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的智能体类型: {agent_type}",
        )

    result = await service.delete_agent_config(agent_type)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"智能体 '{agent_type}' 未配置",
        )

    logger.info(f"管理员删除智能体配置: agent_type={agent_type}")

    return SuccessResponse(success=True, message="智能体配置已删除，将使用默认模型")
