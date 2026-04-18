"""
AI 配置服务

提供 AI 模型配置的业务逻辑，包括：
- 提供商 CRUD
- 模型 CRUD
- 智能体配置 CRUD
- 配置解析（合并三层配置）
- 缓存管理
"""

import logging
from dataclasses import asdict
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.core.cache import CacheManager
from app.domain.models.ai_config import (
    AgentModelConfig,
    LLMModel,
    LLMProvider,
    ResolvedAgentConfig,
)
from app.infrastructure.database.session import async_session_factory
from app.infrastructure.repositories.ai_config_repository import AIConfigRepository
from app.services.encryption_service import EncryptionService, get_encryption_service

logger = logging.getLogger(__name__)

# 缓存 TTL（秒）
PROVIDER_CACHE_TTL = 300  # 5 分钟
MODEL_CACHE_TTL = 300  # 5 分钟
AGENT_CONFIG_CACHE_TTL = 60  # 1 分钟（智能体配置变更更频繁）
RESOLVED_CONFIG_CACHE_TTL = 60  # 1 分钟


class AIConfigServiceError(Exception):
    """AI 配置服务异常"""

    pass


class AIConfigService:
    """
    AI 配置服务

    使用示例：
    ```python
    async with AIConfigService() as service:
        # 获取智能体的解析配置
        config = await service.get_resolved_agent_config("math_solver")

        # 创建提供商
        provider = await service.create_provider(
            name="DeepSeek",
            code="deepseek",
            base_url="https://api.deepseek.com/v1",
            api_key="sk-xxx..."
        )
    ```
    """

    def __init__(
        self,
        db: AsyncSession | None = None,
        encryption_service: EncryptionService | None = None,
        cache: CacheManager | None = None,
    ):
        self._db = db
        self._owns_db = db is None  # 是否需要自己管理数据库会话
        self.encryption = encryption_service or get_encryption_service()
        self.cache = cache or CacheManager(prefix="ai_config", default_ttl=300)

    async def __aenter__(self) -> "AIConfigService":
        """异步上下文管理器入口"""
        if self._owns_db:
            self._db = async_session_factory()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """异步上下文管理器出口"""
        if self._owns_db and self._db is not None:
            if exc_type is not None:
                await self._db.rollback()
            else:
                await self._db.commit()
            await self._db.close()

    @property
    def repository(self) -> AIConfigRepository:
        """获取仓储实例"""
        if self._db is None:
            raise AIConfigServiceError("数据库会话未初始化，请使用 async with 上下文管理器")
        return AIConfigRepository(self._db)

    # ========== 提供商管理 ==========

    async def list_providers(self, include_inactive: bool = False) -> list[LLMProvider]:
        """
        获取提供商列表

        Args:
            include_inactive: 是否包含已禁用的提供商

        Returns:
            提供商列表
        """
        cache_key = f"providers:list:{include_inactive}"

        cached = await self.cache.get(cache_key)
        if cached:
            return [LLMProvider(**p) for p in cached]

        providers = await self.repository.list_providers(include_inactive)

        # 缓存（转换为可序列化的字典）
        await self.cache.set(
            cache_key,
            [self._provider_to_dict(p) for p in providers],
            ttl=PROVIDER_CACHE_TTL,
        )

        return providers

    async def get_provider(self, provider_id: str) -> LLMProvider | None:
        """
        获取单个提供商

        Args:
            provider_id: 提供商 ID

        Returns:
            提供商对象，不存在则返回 None
        """
        return await self.repository.get_provider(provider_id)

    async def get_provider_by_code(self, code: str) -> LLMProvider | None:
        """
        根据代码获取提供商

        Args:
            code: 提供商代码

        Returns:
            提供商对象，不存在则返回 None
        """
        return await self.repository.get_provider_by_code(code)

    async def create_provider(
        self,
        name: str,
        code: str,
        base_url: str,
        api_key: str,
        description: str | None = None,
    ) -> LLMProvider:
        """
        创建提供商

        Args:
            name: 显示名称
            code: 代码标识
            base_url: API Base URL
            api_key: API Key（明文，会被加密存储）
            description: 描述

        Returns:
            创建的提供商对象
        """
        # 加密 API Key
        encrypted_key = self.encryption.encrypt(api_key)

        provider = await self.repository.create_provider(
            name=name,
            code=code,
            base_url=base_url,
            encrypted_api_key=encrypted_key,
            description=description,
        )

        # 清除缓存
        await self._invalidate_provider_cache()

        return provider

    async def update_provider(
        self,
        provider_id: str,
        name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        is_active: bool | None = None,
        description: str | None = None,
    ) -> LLMProvider | None:
        """
        更新提供商

        Args:
            provider_id: 提供商 ID
            name: 显示名称
            base_url: API Base URL
            api_key: API Key（明文，会被加密存储）
            is_active: 是否启用
            description: 描述

        Returns:
            更新后的提供商对象，不存在则返回 None
        """
        updates: dict[str, Any] = {}

        if name is not None:
            updates["name"] = name
        if base_url is not None:
            updates["base_url"] = base_url
        if api_key is not None:
            updates["encrypted_api_key"] = self.encryption.encrypt(api_key)
        if is_active is not None:
            updates["is_active"] = is_active
        if description is not None:
            updates["description"] = description

        if not updates:
            return await self.get_provider(provider_id)

        provider = await self.repository.update_provider(provider_id, **updates)

        if provider:
            # 清除缓存
            await self._invalidate_provider_cache()
            await self._invalidate_resolved_config_cache()

        return provider

    async def delete_provider(self, provider_id: str) -> bool:
        """
        删除提供商

        Args:
            provider_id: 提供商 ID

        Returns:
            是否删除成功
        """
        result = await self.repository.delete_provider(provider_id)

        if result:
            await self._invalidate_provider_cache()
            await self._invalidate_model_cache()
            await self._invalidate_resolved_config_cache()

        return result

    async def create_provider_with_models(
        self,
        name: str,
        code: str,
        base_url: str,
        api_key: str,
        models: list[dict[str, str]],
        description: str | None = None,
    ) -> tuple[LLMProvider, list[LLMModel]]:
        """
        创建提供商并同时创建模型（原子操作）

        Args:
            name: 渠道名称
            code: 代码标识
            base_url: API Base URL
            api_key: API Key
            models: 模型列表 [{"model_id": "xxx", "name": "xxx"}, ...]
            description: 描述

        Returns:
            (提供商对象, 模型列表)
        """
        # 1. 创建提供商
        provider = await self.create_provider(
            name=name,
            code=code,
            base_url=base_url,
            api_key=api_key,
            description=description,
        )

        # 2. 批量创建模型
        created_models: list[LLMModel] = []
        for model_data in models:
            model_id = model_data.get("model_id", "")
            model_name = model_data.get("name") or model_id  # 默认使用 model_id 作为名称

            if not model_id:
                continue

            try:
                model = await self.create_model(
                    provider_id=provider.id,
                    name=model_name,
                    model_id=model_id,
                )
                created_models.append(model)
            except Exception as e:
                logger.warning(f"创建模型 {model_id} 失败: {e}")
                # 继续创建其他模型，不中断

        return provider, created_models

    async def fetch_available_models(self, provider_id: str) -> dict[str, Any]:
        """
        从提供商 API 获取可用模型列表

        Args:
            provider_id: 提供商 ID

        Returns:
            {"success": bool, "models": list[str], "message": str}
        """
        import httpx

        provider = await self.repository.get_provider(provider_id)
        if provider is None:
            return {"success": False, "models": [], "message": "提供商不存在"}

        encrypted_key = await self.repository.get_provider_encrypted_api_key(provider_id)
        if not encrypted_key:
            return {"success": False, "models": [], "message": "API Key 未配置"}

        api_key = self.encryption.decrypt(encrypted_key)
        base_url = provider.base_url.rstrip("/")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{base_url}/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )

                if response.status_code == 200:
                    data = response.json()
                    # OpenAI 格式: {"data": [{"id": "model-id", ...}, ...]}
                    models = []
                    if "data" in data and isinstance(data["data"], list):
                        models = [m.get("id", "") for m in data["data"] if m.get("id")]
                    return {
                        "success": True,
                        "models": sorted(models),
                        "message": f"获取到 {len(models)} 个模型",
                    }
                else:
                    return {
                        "success": False,
                        "models": [],
                        "message": f"HTTP {response.status_code}: {response.text[:200]}",
                    }

        except httpx.TimeoutException:
            return {"success": False, "models": [], "message": "请求超时"}
        except Exception as e:
            return {"success": False, "models": [], "message": f"请求失败: {str(e)}"}

    async def fetch_models_by_credentials(
        self, base_url: str, api_key: str
    ) -> dict[str, Any]:
        """
        根据凭据直接获取模型列表（用于新建渠道时）

        Args:
            base_url: API Base URL
            api_key: API Key

        Returns:
            {"success": bool, "models": list[str], "message": str}
        """
        import httpx

        base_url = base_url.rstrip("/")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{base_url}/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )

                if response.status_code == 200:
                    data = response.json()
                    # OpenAI 格式: {"data": [{"id": "model-id", ...}, ...]}
                    models = []
                    if "data" in data and isinstance(data["data"], list):
                        models = [m.get("id", "") for m in data["data"] if m.get("id")]
                    return {
                        "success": True,
                        "models": sorted(models),
                        "message": f"获取到 {len(models)} 个模型",
                    }
                else:
                    return {
                        "success": False,
                        "models": [],
                        "message": f"HTTP {response.status_code}: {response.text[:200]}",
                    }

        except httpx.TimeoutException:
            return {"success": False, "models": [], "message": "请求超时"}
        except Exception as e:
            return {"success": False, "models": [], "message": f"请求失败: {str(e)}"}

    async def test_provider_connection(
        self, provider_id: str, model_id: str | None = None
    ) -> dict[str, Any]:
        """
        测试提供商连接

        Args:
            provider_id: 提供商 ID
            model_id: 可选，指定测试的模型 ID（进行真实 Chat Completion 测试）

        Returns:
            测试结果 {"success": bool, "message": str, "latency_ms": float, "model_id": str | None}
        """
        import time

        import httpx

        provider = await self.repository.get_provider(provider_id)
        if provider is None:
            return {"success": False, "message": "提供商不存在", "latency_ms": 0, "model_id": None}

        # 获取解密的 API Key
        encrypted_key = await self.repository.get_provider_encrypted_api_key(
            provider_id
        )
        if not encrypted_key:
            return {"success": False, "message": "API Key 未配置", "latency_ms": 0, "model_id": None}

        api_key = self.encryption.decrypt(encrypted_key)
        base_url = provider.base_url.rstrip("/")

        # 判断是否使用 Responses API 端点
        use_responses_api = provider.code == "openai-responses"

        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                if model_id:
                    if use_responses_api:
                        # 使用 OpenAI Responses API 端点
                        response = await client.post(
                            f"{base_url}/v1/responses",
                            headers={
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json",
                            },
                            json={
                                "model": model_id,
                                "input": "Hi",
                                "max_output_tokens": 5,
                            },
                        )
                    else:
                        # 使用标准 Chat Completion 端点
                        response = await client.post(
                            f"{base_url}/v1/chat/completions",
                            headers={
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json",
                            },
                            json={
                                "model": model_id,
                                "messages": [{"role": "user", "content": "Hi"}],
                                "max_tokens": 5,
                            },
                        )
                    latency_ms = (time.time() - start_time) * 1000

                    if response.status_code == 200:
                        return {
                            "success": True,
                            "message": f"模型 {model_id} 连接成功",
                            "latency_ms": round(latency_ms, 2),
                            "model_id": model_id,
                        }
                    else:
                        error_detail = response.text[:200] if response.text else "未知错误"
                        return {
                            "success": False,
                            "message": f"HTTP {response.status_code}: {error_detail}",
                            "latency_ms": round(latency_ms, 2),
                            "model_id": model_id,
                        }
                else:
                    # 测试 /models 端点
                    response = await client.get(
                        f"{base_url}/v1/models",
                        headers={"Authorization": f"Bearer {api_key}"},
                    )
                    latency_ms = (time.time() - start_time) * 1000

                    if response.status_code == 200:
                        return {
                            "success": True,
                            "message": "连接成功",
                            "latency_ms": round(latency_ms, 2),
                            "model_id": None,
                        }
                    else:
                        return {
                            "success": False,
                            "message": f"HTTP {response.status_code}: {response.text[:200]}",
                            "latency_ms": round(latency_ms, 2),
                            "model_id": None,
                        }

        except httpx.TimeoutException:
            return {"success": False, "message": "连接超时", "latency_ms": 15000, "model_id": model_id}
        except Exception as e:
            return {"success": False, "message": f"连接失败: {str(e)}", "latency_ms": 0, "model_id": model_id}

    # ========== 模型管理 ==========

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
        cache_key = f"models:list:{provider_id}:{include_inactive}"

        cached = await self.cache.get(cache_key)
        if cached:
            return [LLMModel(**m) for m in cached]

        models = await self.repository.list_models(provider_id, include_inactive)

        await self.cache.set(
            cache_key,
            [self._model_to_dict(m) for m in models],
            ttl=MODEL_CACHE_TTL,
        )

        return models

    async def get_model(self, model_id: str) -> LLMModel | None:
        """
        获取单个模型

        Args:
            model_id: 模型 ID

        Returns:
            模型对象，不存在则返回 None
        """
        return await self.repository.get_model(model_id)

    async def get_default_model(self) -> LLMModel | None:
        """
        获取默认模型

        Returns:
            默认模型对象，不存在则返回 None
        """
        return await self.repository.get_default_model()

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
        model = await self.repository.create_model(
            provider_id=provider_id,
            name=name,
            model_id=model_id,
            default_temperature=default_temperature,
            default_max_tokens=default_max_tokens,
            default_top_p=default_top_p,
            default_timeout=default_timeout,
            default_max_retries=default_max_retries,
            capabilities=capabilities,
            description=description,
        )

        await self._invalidate_model_cache()

        return model

    async def update_model(
        self,
        model_id: str,
        **updates: Any,
    ) -> LLMModel | None:
        """
        更新模型

        Args:
            model_id: 模型 ID
            **updates: 要更新的字段

        Returns:
            更新后的模型对象，不存在则返回 None
        """
        model = await self.repository.update_model(model_id, **updates)

        if model:
            await self._invalidate_model_cache()
            await self._invalidate_resolved_config_cache()

        return model

    async def delete_model(self, model_id: str) -> bool:
        """
        删除模型

        Args:
            model_id: 模型 ID

        Returns:
            是否删除成功
        """
        result = await self.repository.delete_model(model_id)

        if result:
            await self._invalidate_model_cache()
            await self._invalidate_resolved_config_cache()

        return result

    async def set_default_model(self, model_id: str) -> bool:
        """
        设置默认模型

        Args:
            model_id: 模型 ID

        Returns:
            是否设置成功
        """
        result = await self.repository.set_default_model(model_id)

        if result:
            await self._invalidate_model_cache()
            await self._invalidate_resolved_config_cache()

        return result

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
        result = await self.repository.sync_provider_models(provider_id, models)

        # 清除缓存
        await self._invalidate_model_cache()
        await self._invalidate_resolved_config_cache()

        return result

    # ========== 智能体配置管理 ==========

    async def list_agent_configs(self) -> list[AgentModelConfig]:
        """
        获取所有智能体配置

        Returns:
            智能体配置列表
        """
        cache_key = "agent_configs:list"

        cached = await self.cache.get(cache_key)
        if cached:
            return [AgentModelConfig(**c) for c in cached]

        configs = await self.repository.list_agent_configs()

        await self.cache.set(
            cache_key,
            [self._agent_config_to_dict(c) for c in configs],
            ttl=AGENT_CONFIG_CACHE_TTL,
        )

        return configs

    async def get_agent_config(self, agent_type: str) -> AgentModelConfig | None:
        """
        获取单个智能体配置

        Args:
            agent_type: 智能体类型

        Returns:
            智能体配置对象，不存在则返回 None
        """
        return await self.repository.get_agent_config(agent_type)

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
        config = await self.repository.upsert_agent_config(
            agent_type=agent_type,
            model_id=model_id,
            temperature_override=temperature_override,
            max_tokens_override=max_tokens_override,
            top_p_override=top_p_override,
            timeout_override=timeout_override,
            max_retries_override=max_retries_override,
            extra_config=extra_config,
        )

        await self._invalidate_agent_config_cache()
        await self._invalidate_resolved_config_cache()

        return config

    async def delete_agent_config(self, agent_type: str) -> bool:
        """
        删除智能体配置

        Args:
            agent_type: 智能体类型

        Returns:
            是否删除成功
        """
        result = await self.repository.delete_agent_config(agent_type)

        if result:
            await self._invalidate_agent_config_cache()
            await self._invalidate_resolved_config_cache()

        return result

    # ========== 配置解析（核心方法） ==========

    async def get_resolved_agent_config(
        self,
        agent_type: str,
    ) -> ResolvedAgentConfig | None:
        """
        获取解析后的智能体配置

        合并三层配置：提供商 → 模型 → 智能体覆盖

        这是智能体获取 LLM 配置的主要入口

        Args:
            agent_type: 智能体类型（如 "math_solver", "tutor"）

        Returns:
            解析后的配置，如果未配置则返回 None
        """
        cache_key = f"resolved:{agent_type}"

        cached = await self.cache.get(cache_key)
        if cached:
            return ResolvedAgentConfig(**cached)

        config = await self.repository.get_resolved_config(
            agent_type, self.encryption
        )

        if config:
            # 缓存结果（注意：包含解密后的 API Key，TTL 要短）
            await self.cache.set(
                cache_key,
                asdict(config),
                ttl=RESOLVED_CONFIG_CACHE_TTL,
            )

        return config

    # ========== 缓存管理 ==========

    async def _invalidate_provider_cache(self) -> None:
        """清除提供商相关缓存"""
        await self.cache.delete("providers:list:True")
        await self.cache.delete("providers:list:False")

    async def _invalidate_model_cache(self) -> None:
        """清除模型相关缓存"""
        # 由于模型缓存键包含 provider_id，这里简单地删除所有可能的键
        # 实际生产环境可以使用 Redis SCAN 命令批量删除
        await self.cache.delete("models:list:None:True")
        await self.cache.delete("models:list:None:False")

    async def _invalidate_agent_config_cache(self) -> None:
        """清除智能体配置相关缓存"""
        await self.cache.delete("agent_configs:list")

    async def _invalidate_resolved_config_cache(self) -> None:
        """清除解析配置缓存"""
        # 清除所有智能体的解析配置缓存
        from app.domain.models.ai_config import AgentType

        for agent_type in AgentType.all_types():
            await self.cache.delete(f"resolved:{agent_type}")

    # ========== 序列化辅助方法 ==========

    def _provider_to_dict(self, provider: LLMProvider) -> dict[str, Any]:
        """将提供商转换为可序列化的字典"""
        return {
            "id": provider.id,
            "name": provider.name,
            "code": provider.code,
            "base_url": provider.base_url,
            "is_active": provider.is_active,
            "description": provider.description,
            "created_at": provider.created_at.isoformat(),
            "updated_at": provider.updated_at.isoformat(),
        }

    def _model_to_dict(self, model: LLMModel) -> dict[str, Any]:
        """将模型转换为可序列化的字典"""
        return {
            "id": model.id,
            "provider_id": model.provider_id,
            "name": model.name,
            "model_id": model.model_id,
            "default_temperature": model.default_temperature,
            "default_max_tokens": model.default_max_tokens,
            "default_top_p": model.default_top_p,
            "default_timeout": model.default_timeout,
            "default_max_retries": model.default_max_retries,
            "is_active": model.is_active,
            "is_default": model.is_default,
            "capabilities": model.capabilities,
            "description": model.description,
            "created_at": model.created_at.isoformat(),
            "updated_at": model.updated_at.isoformat(),
            "provider_name": model.provider_name,
            "provider_code": model.provider_code,
            "provider_base_url": model.provider_base_url,
        }

    def _agent_config_to_dict(self, config: AgentModelConfig) -> dict[str, Any]:
        """将智能体配置转换为可序列化的字典"""
        return {
            "id": config.id,
            "agent_type": config.agent_type,
            "model_id": config.model_id,
            "temperature_override": config.temperature_override,
            "max_tokens_override": config.max_tokens_override,
            "top_p_override": config.top_p_override,
            "timeout_override": config.timeout_override,
            "max_retries_override": config.max_retries_override,
            "extra_config": config.extra_config,
            "is_active": config.is_active,
            "created_at": config.created_at.isoformat(),
            "updated_at": config.updated_at.isoformat(),
            "model_name": config.model_name,
            "model_model_id": config.model_model_id,
            "provider_name": config.provider_name,
        }


# 全局服务实例获取函数
async def get_ai_config_service(db: AsyncSession) -> AIConfigService:
    """
    获取 AI 配置服务实例

    用于依赖注入

    Args:
        db: 数据库会话

    Returns:
        AI 配置服务实例
    """
    return AIConfigService(db=db)
