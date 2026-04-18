"""
AI 配置数据仓储

提供 AI 配置相关的数据库操作
"""

import logging
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.models.ai_config import (
    AgentModelConfig,
    LLMModel,
    LLMProvider,
    ResolvedAgentConfig,
)
from app.infrastructure.database.models_ai_config import (
    AgentModelConfigModel,
    LLMModelModel,
    LLMProviderModel,
)

logger = logging.getLogger(__name__)


class AIConfigRepository:
    """
    AI 配置仓储

    提供提供商、模型、智能体配置的 CRUD 操作
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========== 提供商操作 ==========

    async def list_providers(
        self, include_inactive: bool = False
    ) -> list[LLMProvider]:
        """
        获取提供商列表

        Args:
            include_inactive: 是否包含已禁用的提供商

        Returns:
            提供商列表
        """
        query = select(LLMProviderModel)

        if not include_inactive:
            query = query.where(LLMProviderModel.is_active.is_(True))

        query = query.order_by(LLMProviderModel.created_at.desc())

        result = await self.db.execute(query)
        models = result.scalars().all()

        return [self._provider_model_to_domain(m) for m in models]

    async def get_provider(self, provider_id: str) -> LLMProvider | None:
        """
        根据 ID 获取提供商

        Args:
            provider_id: 提供商 ID

        Returns:
            提供商对象，不存在则返回 None
        """
        model = await self.db.get(LLMProviderModel, provider_id)
        if model is None:
            return None
        return self._provider_model_to_domain(model)

    async def get_provider_by_code(self, code: str) -> LLMProvider | None:
        """
        根据代码获取提供商

        Args:
            code: 提供商代码（如 deepseek）

        Returns:
            提供商对象，不存在则返回 None
        """
        query = select(LLMProviderModel).where(LLMProviderModel.code == code)
        result = await self.db.execute(query)
        model = result.scalar_one_or_none()

        if model is None:
            return None
        return self._provider_model_to_domain(model)

    async def get_provider_encrypted_api_key(self, provider_id: str) -> str | None:
        """
        获取提供商的加密 API Key

        Args:
            provider_id: 提供商 ID

        Returns:
            加密的 API Key，不存在则返回 None
        """
        model = await self.db.get(LLMProviderModel, provider_id)
        if model is None:
            return None
        return model.encrypted_api_key

    async def create_provider(
        self,
        name: str,
        code: str,
        base_url: str,
        encrypted_api_key: str,
        description: str | None = None,
    ) -> LLMProvider:
        """
        创建提供商

        Args:
            name: 显示名称
            code: 代码标识
            base_url: API Base URL
            encrypted_api_key: 加密的 API Key
            description: 描述

        Returns:
            创建的提供商对象
        """
        model = LLMProviderModel(
            name=name,
            code=code,
            base_url=base_url,
            encrypted_api_key=encrypted_api_key,
            description=description,
        )

        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)

        logger.info(f"创建提供商: id={model.id}, name={name}, code={code}")
        return self._provider_model_to_domain(model)

    async def update_provider(
        self, provider_id: str, **updates: Any
    ) -> LLMProvider | None:
        """
        更新提供商

        Args:
            provider_id: 提供商 ID
            **updates: 要更新的字段

        Returns:
            更新后的提供商对象，不存在则返回 None
        """
        model = await self.db.get(LLMProviderModel, provider_id)
        if model is None:
            return None

        for field, value in updates.items():
            if hasattr(model, field) and value is not None:
                setattr(model, field, value)

        await self.db.flush()
        await self.db.refresh(model)

        logger.info(f"更新提供商: id={provider_id}, updates={list(updates.keys())}")
        return self._provider_model_to_domain(model)

    async def delete_provider(self, provider_id: str) -> bool:
        """
        删除提供商

        Args:
            provider_id: 提供商 ID

        Returns:
            是否删除成功
        """
        model = await self.db.get(LLMProviderModel, provider_id)
        if model is None:
            return False

        await self.db.delete(model)
        await self.db.flush()

        logger.info(f"删除提供商: id={provider_id}")
        return True

    # ========== 模型操作 ==========

    async def list_models(
        self,
        provider_id: str | None = None,
        include_inactive: bool = False,
    ) -> list[LLMModel]:
        """
        获取模型列表

        Args:
            provider_id: 提供商 ID（可选，用于筛选）
            include_inactive: 是否包含已禁用的模型

        Returns:
            模型列表
        """
        query = select(LLMModelModel).options(selectinload(LLMModelModel.provider))

        if provider_id:
            query = query.where(LLMModelModel.provider_id == provider_id)

        if not include_inactive:
            query = query.where(LLMModelModel.is_active.is_(True))

        query = query.order_by(LLMModelModel.created_at.desc())

        result = await self.db.execute(query)
        models = result.scalars().all()

        return [self._model_model_to_domain(m) for m in models]

    async def get_model(self, model_id: str) -> LLMModel | None:
        """
        根据 ID 获取模型

        Args:
            model_id: 模型 ID

        Returns:
            模型对象，不存在则返回 None
        """
        query = (
            select(LLMModelModel)
            .options(selectinload(LLMModelModel.provider))
            .where(LLMModelModel.id == model_id)
        )
        result = await self.db.execute(query)
        model = result.scalar_one_or_none()

        if model is None:
            return None
        return self._model_model_to_domain(model)

    async def get_default_model(self) -> LLMModel | None:
        """
        获取默认模型

        Returns:
            默认模型对象，不存在则返回 None
        """
        query = (
            select(LLMModelModel)
            .options(selectinload(LLMModelModel.provider))
            .where(LLMModelModel.is_default.is_(True))
            .where(LLMModelModel.is_active.is_(True))
        )
        result = await self.db.execute(query)
        model = result.scalar_one_or_none()

        if model is None:
            return None
        return self._model_model_to_domain(model)

    async def create_model(
        self,
        provider_id: str,
        name: str,
        model_id: str,
        default_temperature: float = 0.7,
        default_max_tokens: int = 2048,
        default_top_p: float = 0.9,
        default_timeout: int = 60,
        default_max_retries: int = 3,
        capabilities: dict | None = None,
        description: str | None = None,
    ) -> LLMModel:
        """
        创建模型

        Args:
            provider_id: 提供商 ID
            name: 显示名称
            model_id: API 模型 ID
            default_temperature: 默认温度
            default_max_tokens: 默认最大 Token 数
            default_top_p: 默认 Top P
            default_timeout: 默认超时时间
            default_max_retries: 默认最大重试次数
            capabilities: 模型能力标签
            description: 描述

        Returns:
            创建的模型对象
        """
        model = LLMModelModel(
            provider_id=provider_id,
            name=name,
            model_id=model_id,
            default_temperature=default_temperature,
            default_max_tokens=default_max_tokens,
            default_top_p=default_top_p,
            default_timeout=default_timeout,
            default_max_retries=default_max_retries,
            capabilities=capabilities or {},
            description=description,
        )

        self.db.add(model)
        await self.db.flush()

        # 重新查询以加载关系
        query = (
            select(LLMModelModel)
            .options(selectinload(LLMModelModel.provider))
            .where(LLMModelModel.id == model.id)
        )
        result = await self.db.execute(query)
        model = result.scalar_one()

        logger.info(f"创建模型: id={model.id}, name={name}, model_id={model_id}")
        return self._model_model_to_domain(model)

    async def update_model(self, model_id: str, **updates: Any) -> LLMModel | None:
        """
        更新模型

        Args:
            model_id: 模型 ID
            **updates: 要更新的字段

        Returns:
            更新后的模型对象，不存在则返回 None
        """
        query = (
            select(LLMModelModel)
            .options(selectinload(LLMModelModel.provider))
            .where(LLMModelModel.id == model_id)
        )
        result = await self.db.execute(query)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        for field, value in updates.items():
            if hasattr(model, field) and value is not None:
                setattr(model, field, value)

        await self.db.flush()
        await self.db.refresh(model)

        logger.info(f"更新模型: id={model_id}, updates={list(updates.keys())}")
        return self._model_model_to_domain(model)

    async def delete_model(self, model_id: str) -> bool:
        """
        删除模型

        Args:
            model_id: 模型 ID

        Returns:
            是否删除成功
        """
        model = await self.db.get(LLMModelModel, model_id)
        if model is None:
            return False

        await self.db.delete(model)
        await self.db.flush()

        logger.info(f"删除模型: id={model_id}")
        return True

    async def sync_provider_models(
        self,
        provider_id: str,
        models: list[dict[str, str]],
    ) -> dict[str, Any]:
        """
        同步提供商的模型列表（全量替换）

        Args:
            provider_id: 提供商 ID
            models: 新的模型列表 [{"model_id": "xxx", "name": "xxx"}, ...]

        Returns:
            {"added": int, "removed": int, "unchanged": int, "models": list[LLMModel]}
        """
        # 获取现有模型
        existing_models = await self.list_models(provider_id, include_inactive=True)
        existing_model_ids = {m.model_id for m in existing_models}
        existing_model_map = {m.model_id: m for m in existing_models}

        # 新模型 ID 集合
        new_model_ids = {m.get("model_id", "") for m in models if m.get("model_id")}

        # 计算差异
        to_add = new_model_ids - existing_model_ids
        to_remove = existing_model_ids - new_model_ids
        unchanged = existing_model_ids & new_model_ids

        # 删除不再需要的模型
        for model_id_str in to_remove:
            existing = existing_model_map.get(model_id_str)
            if existing:
                await self.delete_model(existing.id)

        # 添加新模型
        for model_data in models:
            model_id_str = model_data.get("model_id", "")
            if model_id_str in to_add:
                model_name = model_data.get("name") or model_id_str
                await self.create_model(
                    provider_id=provider_id,
                    name=model_name,
                    model_id=model_id_str,
                )

        # 获取更新后的模型列表
        updated_models = await self.list_models(provider_id, include_inactive=True)

        logger.info(
            f"同步提供商模型: provider_id={provider_id}, "
            f"added={len(to_add)}, removed={len(to_remove)}, unchanged={len(unchanged)}"
        )

        return {
            "added": len(to_add),
            "removed": len(to_remove),
            "unchanged": len(unchanged),
            "models": updated_models,
        }

    async def set_default_model(self, model_id: str) -> bool:
        """
        设置默认模型

        Args:
            model_id: 模型 ID

        Returns:
            是否设置成功
        """
        # 先取消所有默认模型
        await self.db.execute(
            update(LLMModelModel).values(is_default=False)
        )

        # 设置新的默认模型
        model = await self.db.get(LLMModelModel, model_id)
        if model is None:
            return False

        model.is_default = True
        await self.db.flush()

        logger.info(f"设置默认模型: id={model_id}")
        return True

    # ========== 智能体配置操作 ==========

    async def list_agent_configs(self) -> list[AgentModelConfig]:
        """
        获取所有智能体配置

        Returns:
            智能体配置列表
        """
        query = (
            select(AgentModelConfigModel)
            .options(
                selectinload(AgentModelConfigModel.model).selectinload(
                    LLMModelModel.provider
                )
            )
            .order_by(AgentModelConfigModel.agent_type)
        )

        result = await self.db.execute(query)
        models = result.scalars().all()

        return [self._agent_config_model_to_domain(m) for m in models]

    async def get_agent_config(self, agent_type: str) -> AgentModelConfig | None:
        """
        获取单个智能体配置

        Args:
            agent_type: 智能体类型

        Returns:
            智能体配置对象，不存在则返回 None
        """
        query = (
            select(AgentModelConfigModel)
            .options(
                selectinload(AgentModelConfigModel.model).selectinload(
                    LLMModelModel.provider
                )
            )
            .where(AgentModelConfigModel.agent_type == agent_type)
        )

        result = await self.db.execute(query)
        model = result.scalar_one_or_none()

        if model is None:
            return None
        return self._agent_config_model_to_domain(model)

    async def upsert_agent_config(
        self,
        agent_type: str,
        model_id: str,
        temperature_override: float | None = None,
        max_tokens_override: int | None = None,
        top_p_override: float | None = None,
        timeout_override: int | None = None,
        max_retries_override: int | None = None,
        extra_config: dict | None = None,
    ) -> AgentModelConfig:
        """
        创建或更新智能体配置

        Args:
            agent_type: 智能体类型
            model_id: 模型 ID
            temperature_override: 温度覆盖
            max_tokens_override: 最大 Token 数覆盖
            top_p_override: Top P 覆盖
            timeout_override: 超时时间覆盖
            max_retries_override: 最大重试次数覆盖
            extra_config: 额外配置

        Returns:
            智能体配置对象
        """
        # 查找现有配置
        query = select(AgentModelConfigModel).where(
            AgentModelConfigModel.agent_type == agent_type
        )
        result = await self.db.execute(query)
        model = result.scalar_one_or_none()

        if model is None:
            # 创建新配置
            model = AgentModelConfigModel(
                agent_type=agent_type,
                model_id=model_id,
                temperature_override=temperature_override,
                max_tokens_override=max_tokens_override,
                top_p_override=top_p_override,
                timeout_override=timeout_override,
                max_retries_override=max_retries_override,
                extra_config=extra_config or {},
            )
            self.db.add(model)
            logger.info(f"创建智能体配置: agent_type={agent_type}")
        else:
            # 更新现有配置
            model.model_id = model_id
            model.temperature_override = temperature_override
            model.max_tokens_override = max_tokens_override
            model.top_p_override = top_p_override
            model.timeout_override = timeout_override
            model.max_retries_override = max_retries_override
            model.extra_config = extra_config or {}
            logger.info(f"更新智能体配置: agent_type={agent_type}")

        await self.db.flush()

        # 重新查询以加载关系
        query = (
            select(AgentModelConfigModel)
            .options(
                selectinload(AgentModelConfigModel.model).selectinload(
                    LLMModelModel.provider
                )
            )
            .where(AgentModelConfigModel.id == model.id)
        )
        result = await self.db.execute(query)
        model = result.scalar_one()

        return self._agent_config_model_to_domain(model)

    async def delete_agent_config(self, agent_type: str) -> bool:
        """
        删除智能体配置

        Args:
            agent_type: 智能体类型

        Returns:
            是否删除成功
        """
        query = select(AgentModelConfigModel).where(
            AgentModelConfigModel.agent_type == agent_type
        )
        result = await self.db.execute(query)
        model = result.scalar_one_or_none()

        if model is None:
            return False

        await self.db.delete(model)
        await self.db.flush()

        logger.info(f"删除智能体配置: agent_type={agent_type}")
        return True

    # ========== 配置解析 ==========

    async def get_resolved_config(
        self, agent_type: str, encryption_service: Any
    ) -> ResolvedAgentConfig | None:
        """
        获取解析后的智能体配置

        合并提供商、模型、智能体配置三层的最终配置

        Args:
            agent_type: 智能体类型
            encryption_service: 加密服务（用于解密 API Key）

        Returns:
            解析后的配置，如果未配置则返回 None
        """
        # 获取智能体配置
        agent_config = await self.get_agent_config(agent_type)

        if agent_config is None or agent_config.model_id is None:
            # 未配置，尝试使用默认模型
            model = await self.get_default_model()
            if model is None:
                return None
        else:
            model = await self.get_model(agent_config.model_id)
            if model is None:
                return None

        # 获取提供商
        provider_model = await self.db.get(LLMProviderModel, model.provider_id)
        if provider_model is None:
            return None

        # 解密 API Key
        api_key = encryption_service.decrypt(provider_model.encrypted_api_key)

        # 合并配置（智能体覆盖 > 模型默认值）
        if agent_config:
            temperature = (
                agent_config.temperature_override
                if agent_config.temperature_override is not None
                else model.default_temperature
            )
            max_tokens = (
                agent_config.max_tokens_override
                if agent_config.max_tokens_override is not None
                else model.default_max_tokens
            )
            top_p = (
                agent_config.top_p_override
                if agent_config.top_p_override is not None
                else model.default_top_p
            )
            timeout = (
                agent_config.timeout_override
                if agent_config.timeout_override is not None
                else model.default_timeout
            )
            max_retries = (
                agent_config.max_retries_override
                if agent_config.max_retries_override is not None
                else model.default_max_retries
            )
            extra_config = agent_config.extra_config
        else:
            temperature = model.default_temperature
            max_tokens = model.default_max_tokens
            top_p = model.default_top_p
            timeout = model.default_timeout
            max_retries = model.default_max_retries
            extra_config = {}

        return ResolvedAgentConfig(
            agent_type=agent_type,
            api_base=provider_model.base_url,
            api_key=api_key,
            model_name=model.model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            timeout=timeout,
            max_retries=max_retries,
            extra_config=extra_config,
            provider_id=provider_model.id,
            provider_name=provider_model.name,
            model_id=model.id,
        )

    # ========== 模型转换 ==========

    def _provider_model_to_domain(self, model: LLMProviderModel) -> LLMProvider:
        """将 ORM 模型转换为领域模型"""
        return LLMProvider(
            id=model.id,
            name=model.name,
            code=model.code,
            base_url=model.base_url,
            is_active=model.is_active,
            description=model.description,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _model_model_to_domain(self, model: LLMModelModel) -> LLMModel:
        """将 ORM 模型转换为领域模型"""
        return LLMModel(
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
            provider_name=model.provider.name if model.provider else None,
            provider_code=model.provider.code if model.provider else None,
            provider_base_url=model.provider.base_url if model.provider else None,
        )

    def _agent_config_model_to_domain(
        self, model: AgentModelConfigModel
    ) -> AgentModelConfig:
        """将 ORM 模型转换为领域模型"""
        return AgentModelConfig(
            id=model.id,
            agent_type=model.agent_type,
            model_id=model.model_id,
            temperature_override=model.temperature_override,
            max_tokens_override=model.max_tokens_override,
            top_p_override=model.top_p_override,
            timeout_override=model.timeout_override,
            max_retries_override=model.max_retries_override,
            extra_config=model.extra_config,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
            model_name=model.model.name if model.model else None,
            model_model_id=model.model.model_id if model.model else None,
            provider_name=(
                model.model.provider.name if model.model and model.model.provider else None
            ),
        )
