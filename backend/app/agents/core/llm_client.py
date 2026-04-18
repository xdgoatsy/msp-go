"""
LLM 客户端抽象层

提供统一的 LLM 调用接口，支持多种后端

特性：
- 支持 OpenAI API 兼容的后端（DeepSeek、Qwen 等）
- 支持流式生成
- 支持批量生成
- 内置重试和超时机制
- 连接池支持高并发
- 多 Provider 负载均衡和故障转移

使用 LiteLLM 作为底层调用库，提供更好的兼容性和稳定性
"""

import asyncio
import base64
import logging
import random
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import httpx
import litellm
from litellm import acompletion

# 配置 LiteLLM
litellm.drop_params = True  # 自动忽略不支持的参数
litellm.verbose = False  # type: ignore[attr-defined]  # 关闭详细日志

logger = logging.getLogger(__name__)

# 共享 httpx 客户端（连接池复用，避免每次创建新连接）
_shared_httpx_client: httpx.AsyncClient | None = None


def _get_shared_httpx_client() -> httpx.AsyncClient:
    """获取共享的 httpx 异步客户端（懒初始化）"""
    global _shared_httpx_client
    if _shared_httpx_client is None or _shared_httpx_client.is_closed:
        _shared_httpx_client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=10,
                keepalive_expiry=30.0,
            ),
            follow_redirects=True,
        )
    return _shared_httpx_client


class LLMClientError(Exception):
    """LLM 客户端异常"""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


@dataclass
class ProviderHealth:
    """Provider 健康状态"""
    provider_id: str
    is_healthy: bool = True
    failure_count: int = 0
    last_failure_time: float = 0
    last_success_time: float = 0
    avg_latency_ms: float = 0
    total_requests: int = 0

    def record_success(self, latency_ms: float) -> None:
        """记录成功请求"""
        self.is_healthy = True
        self.failure_count = 0
        self.last_success_time = time.time()
        self.total_requests += 1
        # 滑动平均延迟
        if self.avg_latency_ms == 0:
            self.avg_latency_ms = latency_ms
        else:
            self.avg_latency_ms = self.avg_latency_ms * 0.9 + latency_ms * 0.1

    def record_failure(self) -> None:
        """记录失败请求"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.total_requests += 1
        # 连续失败 3 次标记为不健康
        if self.failure_count >= 3:
            self.is_healthy = False

    def should_retry(self, cooldown_seconds: float = 60.0) -> bool:
        """检查是否应该重试不健康的 Provider"""
        if self.is_healthy:
            return True
        # 冷却期后重试
        return time.time() - self.last_failure_time > cooldown_seconds


class LLMClient:
    """
    LLM 客户端

    使用 LiteLLM 提供统一的调用接口，支持多种 OpenAI 兼容 API

    使用示例：
    ```python
    client = LLMClient()

    # 单次生成
    response = await client.generate("你好")

    # 流式生成
    async for chunk in client.stream_generate("讲个故事"):
        print(chunk, end="")

    # 批量生成
    responses = await client.batch_generate(["问题1", "问题2"])
    ```
    """

    def __init__(
        self,
        api_base: str | None = None,
        api_key: str | None = None,
        model_name: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float | None = None,
        timeout: float = 60.0,
        max_retries: int = 3,
        max_connections: int = 100,  # 保留参数兼容性
        provider_id: str | None = None,  # 用于健康追踪
    ):
        """
        初始化 LLM 客户端

        Args:
            api_base: API 基础 URL（默认从配置读取）
            api_key: API 密钥（默认从配置读取）
            model_name: 模型名称（默认从配置读取）
            temperature: 温度参数
            max_tokens: 最大生成 token 数（None 时不传递给 API）
            top_p: Top P 参数（None 时不传递给 API）
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
            max_connections: HTTP 连接池大小（保留兼容性）
            provider_id: Provider 标识（用于健康追踪）
        """
        raw_api_base = api_base or ""
        self.api_base = self._normalize_api_base(raw_api_base)
        self.api_key = api_key or ""
        self.model_name = model_name or "deepseek-chat"
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_connections = max_connections
        self.provider_id = provider_id or f"{self.api_base}:{self.model_name}"

    @staticmethod
    def _normalize_api_base(url: str) -> str:
        """
        规范化 API base URL

        LiteLLM 对于 openai/ 前缀的模型，会在 api_base 后拼接 /chat/completions
        所以需要确保 URL 以 /v1 结尾

        Args:
            url: 原始 URL

        Returns:
            规范化后的 URL（以 /v1 结尾）
        """
        if not url:
            return url

        # 移除尾部斜杠
        url = url.rstrip("/")

        # 如果已经以 /v1 结尾，直接返回
        if url.endswith("/v1"):
            return url

        # 如果包含 /v1/ 路径，截取到 /v1
        if "/v1/" in url:
            return url.split("/v1/")[0] + "/v1"

        # 否则添加 /v1
        return url + "/v1"

    def _get_model_string(self) -> str:
        """获取 LiteLLM 格式的模型字符串"""
        # 对于自定义 OpenAI 兼容 API，使用 openai/ 前缀
        return f"openai/{self.model_name}"

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> str:
        """
        单次生成

        Args:
            prompt: 用户提示
            system_prompt: 系统提示（可选）
            **kwargs: 额外参数（temperature, max_tokens 等）

        Returns:
            生成的文本

        Raises:
            LLMClientError: 生成失败时抛出
        """
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # 合并默认参数和传入参数
            temperature = kwargs.pop("temperature", self.temperature)
            max_tokens = kwargs.pop("max_tokens", self.max_tokens)
            top_p = kwargs.pop("top_p", self.top_p)

            # 构建可选参数
            optional_params: dict[str, Any] = {}
            if max_tokens is not None:
                optional_params["max_tokens"] = max_tokens
            if top_p is not None:
                optional_params["top_p"] = top_p

            response = await acompletion(
                model=self._get_model_string(),
                messages=messages,
                api_base=self.api_base,
                api_key=self.api_key,
                temperature=temperature,
                timeout=self.timeout,
                num_retries=self.max_retries,
                **optional_params,
                **kwargs,
            )

            content = response.choices[0].message.content  # type: ignore[union-attr]
            return content if content else ""

        except TimeoutError as e:
            logger.error(f"LLM 调用超时: prompt={prompt[:50]}...")
            raise LLMClientError("LLM 调用超时", {"timeout": self.timeout}) from e
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise LLMClientError(f"LLM 调用失败: {str(e)}") from e

    async def stream_generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        流式生成

        Args:
            prompt: 用户提示
            system_prompt: 系统提示（可选）
            **kwargs: 额外参数（temperature, max_tokens 等）

        Yields:
            生成的文本片段

        Raises:
            LLMClientError: 生成失败时抛出
        """
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # 合并默认参数和传入参数
            temperature = kwargs.pop("temperature", self.temperature)
            max_tokens = kwargs.pop("max_tokens", self.max_tokens)
            top_p = kwargs.pop("top_p", self.top_p)

            # 构建可选参数
            optional_params: dict[str, Any] = {}
            if max_tokens is not None:
                optional_params["max_tokens"] = max_tokens
            if top_p is not None:
                optional_params["top_p"] = top_p

            response = await acompletion(
                model=self._get_model_string(),
                messages=messages,
                api_base=self.api_base,
                api_key=self.api_key,
                temperature=temperature,
                timeout=self.timeout,
                num_retries=self.max_retries,
                stream=True,
                **optional_params,
                **kwargs,
            )

            async for chunk in response:  # type: ignore[union-attr]
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except TimeoutError as e:
            logger.error(f"LLM 流式调用超时: prompt={prompt[:50]}...")
            raise LLMClientError("LLM 流式调用超时", {"timeout": self.timeout}) from e
        except Exception as e:
            logger.error(f"LLM 流式调用失败: {e}")
            raise LLMClientError(f"LLM 流式调用失败: {str(e)}") from e

    async def batch_generate(
        self,
        prompts: list[str],
        system_prompt: str | None = None,
        max_concurrency: int = 5,
        **kwargs: Any,
    ) -> list[str]:
        """
        批量生成

        并发调用 LLM，提高吞吐量

        Args:
            prompts: 提示列表
            system_prompt: 系统提示（可选，应用于所有请求）
            max_concurrency: 最大并发数
            **kwargs: 额外参数

        Returns:
            生成结果列表（与输入顺序对应）

        Raises:
            LLMClientError: 任一请求失败时抛出
        """
        semaphore = asyncio.Semaphore(max_concurrency)

        async def generate_one(prompt: str) -> str:
            async with semaphore:
                return await self.generate(prompt, system_prompt, **kwargs)

        try:
            tasks = [generate_one(prompt) for prompt in prompts]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 检查是否有异常
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    raise LLMClientError(
                        f"批量生成第 {i} 个请求失败: {str(result)}",
                        {"index": i, "prompt": prompts[i][:50]},
                    )

            return [str(r) for r in results]

        except LLMClientError:
            raise
        except Exception as e:
            logger.error(f"批量生成失败: {e}")
            raise LLMClientError(f"批量生成失败: {str(e)}") from e

    async def generate_with_history(
        self,
        prompt: str,
        history: list[dict[str, str]],
        system_prompt: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        带历史记录的生成（支持工具调用）

        Args:
            prompt: 当前用户提示
            history: 对话历史 [{"role": "user/assistant", "content": "..."}]
            system_prompt: 系统提示（可选）
            tools: 工具定义列表（可选）
            **kwargs: 额外参数（temperature, max_tokens 等）

        Returns:
            包含 content 和 tool_calls 的字典
            {
                "content": str | None,
                "tool_calls": list[dict] | None,
                "finish_reason": str
            }
        """
        try:
            messages = []

            # 添加系统提示
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            # 添加历史记录
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                messages.append({"role": role, "content": content})

            # 添加当前提示
            messages.append({"role": "user", "content": prompt})

            # 合并默认参数和传入参数
            temperature = kwargs.pop("temperature", self.temperature)
            max_tokens = kwargs.pop("max_tokens", self.max_tokens)
            top_p = kwargs.pop("top_p", self.top_p)

            # 构建可选参数
            optional_params: dict[str, Any] = {}
            if max_tokens is not None:
                optional_params["max_tokens"] = max_tokens
            if top_p is not None:
                optional_params["top_p"] = top_p

            # 添加工具调用支持
            if tools:
                optional_params["tools"] = tools
                optional_params["tool_choice"] = "auto"

            response = await acompletion(
                model=self._get_model_string(),
                messages=messages,
                api_base=self.api_base,
                api_key=self.api_key,
                temperature=temperature,
                timeout=self.timeout,
                num_retries=self.max_retries,
                **optional_params,
                **kwargs,
            )

            message = response.choices[0].message  # type: ignore[union-attr]
            content = message.content if hasattr(message, "content") else None
            tool_calls = message.tool_calls if hasattr(message, "tool_calls") else None
            finish_reason = response.choices[0].finish_reason  # type: ignore[union-attr]

            # 转换 tool_calls 为字典格式
            tool_calls_list = None
            if tool_calls:
                tool_calls_list = []
                for tc in tool_calls:
                    tool_calls_list.append({
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    })

            return {
                "content": content,
                "tool_calls": tool_calls_list,
                "finish_reason": finish_reason,
            }

        except Exception as e:
            logger.error(f"带历史生成失败: {e}")
            raise LLMClientError(f"带历史生成失败: {str(e)}") from e

    async def _url_to_base64(self, url: str) -> str:
        """
        将图片 URL 转换为 Base64 数据 URL

        Args:
            url: 图片 URL（可以是本地路径或 HTTP URL）

        Returns:
            Base64 数据 URL (data:image/xxx;base64,...)
        """
        # 如果已经是 base64 格式，直接返回
        if url.startswith("data:"):
            return url

        # 如果是本地文件路径
        if url.startswith("/uploads/") or url.startswith("uploads/"):
            # 构建完整的本地路径
            from pathlib import Path
            base_path = Path(__file__).parent.parent.parent.parent / "uploads"
            filename = url.split("/")[-1]
            file_path = base_path / filename

            if file_path.exists():
                with open(file_path, "rb") as f:
                    content = f.read()

                # 根据扩展名确定 MIME 类型
                ext = file_path.suffix.lower()
                mime_types = {
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".png": "image/png",
                    ".gif": "image/gif",
                    ".webp": "image/webp",
                }
                mime_type = mime_types.get(ext, "image/jpeg")

                base64_data = base64.b64encode(content).decode("utf-8")
                return f"data:{mime_type};base64,{base64_data}"

        # 如果是 HTTP URL，下载并转换
        if url.startswith("http://") or url.startswith("https://"):
            client = _get_shared_httpx_client()
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "image/jpeg")
            # 提取主 MIME 类型
            mime_type = content_type.split(";")[0].strip()

            base64_data = base64.b64encode(response.content).decode("utf-8")
            return f"data:{mime_type};base64,{base64_data}"

        raise LLMClientError(f"无法处理的图片 URL: {url}")

    async def generate_with_images(
        self,
        prompt: str,
        images: list[str],
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> str:
        """
        带图片的单次生成

        Args:
            prompt: 用户提示
            images: 图片 URL 列表（支持本地路径、HTTP URL 或 Base64）
            system_prompt: 系统提示（可选）
            **kwargs: 额外参数（temperature, max_tokens 等）

        Returns:
            生成的文本

        Raises:
            LLMClientError: 生成失败时抛出
        """
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            # 构建多模态内容
            content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]

            for image_url in images:
                base64_url = await self._url_to_base64(image_url)
                content.append({
                    "type": "image_url",
                    "image_url": {"url": base64_url}
                })

            messages.append({"role": "user", "content": content})

            # 合并默认参数和传入参数
            temperature = kwargs.pop("temperature", self.temperature)
            max_tokens = kwargs.pop("max_tokens", self.max_tokens)
            top_p = kwargs.pop("top_p", self.top_p)

            # 构建可选参数
            optional_params: dict[str, Any] = {}
            if max_tokens is not None:
                optional_params["max_tokens"] = max_tokens
            if top_p is not None:
                optional_params["top_p"] = top_p

            response = await acompletion(
                model=self._get_model_string(),
                messages=messages,
                api_base=self.api_base,
                api_key=self.api_key,
                temperature=temperature,
                timeout=self.timeout,
                num_retries=self.max_retries,
                **optional_params,
                **kwargs,
            )

            result = response.choices[0].message.content  # type: ignore[union-attr]
            return result if result else ""

        except TimeoutError as e:
            logger.error(f"LLM 多模态调用超时: prompt={prompt[:50]}...")
            raise LLMClientError("LLM 多模态调用超时", {"timeout": self.timeout}) from e
        except Exception as e:
            logger.error(f"LLM 多模态调用失败: {e}")
            raise LLMClientError(f"LLM 多模态调用失败: {str(e)}") from e

    async def stream_generate_with_images(
        self,
        prompt: str,
        images: list[str],
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        带图片的流式生成

        Args:
            prompt: 用户提示
            images: 图片 URL 列表（支持本地路径、HTTP URL 或 Base64）
            system_prompt: 系统提示（可选）
            **kwargs: 额外参数（temperature, max_tokens 等）

        Yields:
            生成的文本片段

        Raises:
            LLMClientError: 生成失败时抛出
        """
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            # 构建多模态内容
            content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]

            for image_url in images:
                base64_url = await self._url_to_base64(image_url)
                content.append({
                    "type": "image_url",
                    "image_url": {"url": base64_url}
                })

            messages.append({"role": "user", "content": content})

            # 合并默认参数和传入参数
            temperature = kwargs.pop("temperature", self.temperature)
            max_tokens = kwargs.pop("max_tokens", self.max_tokens)
            top_p = kwargs.pop("top_p", self.top_p)

            # 构建可选参数
            optional_params: dict[str, Any] = {}
            if max_tokens is not None:
                optional_params["max_tokens"] = max_tokens
            if top_p is not None:
                optional_params["top_p"] = top_p

            response = await acompletion(
                model=self._get_model_string(),
                messages=messages,
                api_base=self.api_base,
                api_key=self.api_key,
                temperature=temperature,
                timeout=self.timeout,
                num_retries=self.max_retries,
                stream=True,
                **optional_params,
                **kwargs,
            )

            async for chunk in response:  # type: ignore[union-attr]
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except TimeoutError as e:
            logger.error(f"LLM 多模态流式调用超时: prompt={prompt[:50]}...")
            raise LLMClientError("LLM 多模态流式调用超时", {"timeout": self.timeout}) from e
        except Exception as e:
            logger.error(f"LLM 多模态流式调用失败: {e}")
            raise LLMClientError(f"LLM 多模态流式调用失败: {str(e)}") from e


def create_llm_client(**kwargs: Any) -> LLMClient:
    """
    创建新的 LLM 客户端

    用于需要自定义配置的场景

    Args:
        **kwargs: 传递给 LLMClient 构造函数的参数

    Returns:
        新的 LLMClient 实例
    """
    return LLMClient(**kwargs)


async def create_llm_client_from_config(agent_type: str) -> LLMClient:
    """
    从智能体配置创建 LLM 客户端

    从数据库获取智能体的模型配置，创建对应的 LLMClient

    Args:
        agent_type: 智能体类型（如 "math_solver", "tutor"）

    Returns:
        配置好的 LLMClient 实例

    Raises:
        LLMClientError: 配置获取失败时抛出

    使用示例：
    ```python
    # 在智能体中使用
    client = await create_llm_client_from_config("math_solver")
    response = await client.generate("你好")
    ```
    """
    try:
        from app.services.ai_config_service import AIConfigService

        async with AIConfigService() as service:
            config = await service.get_resolved_agent_config(agent_type)

            if config is None:
                raise LLMClientError(
                    f"智能体 '{agent_type}' 未配置模型，请在管理后台配置 AI 模型",
                    {"agent_type": agent_type},
                )

            logger.info(
                f"从配置创建 LLMClient: agent_type={agent_type}, "
                f"model={config.model_name}, provider={config.provider_name}"
            )

            return LLMClient(
                api_base=config.api_base,
                api_key=config.api_key,
                model_name=config.model_name,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                top_p=config.top_p,
                timeout=float(config.timeout),
                max_retries=config.max_retries,
            )

    except Exception as e:
        logger.error(f"从配置创建 LLMClient 失败: {e}")
        raise LLMClientError(
            f"从配置创建 LLMClient 失败: {str(e)}",
            {"agent_type": agent_type},
        ) from e


class ConfigurableLLMClient:
    """
    可配置的 LLM 客户端包装器

    自动从数据库配置获取参数，支持配置热更新

    使用示例：
    ```python
    # 创建可配置客户端
    client = ConfigurableLLMClient("math_solver")

    # 使用时自动获取最新配置
    response = await client.generate("你好")

    # 强制刷新配置
    await client.refresh()
    ```
    """

    def __init__(self, agent_type: str):
        """
        初始化可配置客户端

        Args:
            agent_type: 智能体类型
        """
        self.agent_type = agent_type
        self._client: LLMClient | None = None
        self._initialized = False

    async def _ensure_client(self) -> LLMClient:
        """确保客户端已初始化"""
        if self._client is None or not self._initialized:
            self._client = await create_llm_client_from_config(self.agent_type)
            self._initialized = True
        return self._client

    async def refresh(self) -> None:
        """刷新配置，重新创建客户端"""
        self._client = await create_llm_client_from_config(self.agent_type)
        self._initialized = True
        logger.info(f"刷新 LLMClient 配置: agent_type={self.agent_type}")

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> str:
        """单次生成"""
        client = await self._ensure_client()
        return await client.generate(prompt, system_prompt, **kwargs)

    async def stream_generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """流式生成"""
        client = await self._ensure_client()
        async for chunk in client.stream_generate(prompt, system_prompt, **kwargs):
            yield chunk

    async def batch_generate(
        self,
        prompts: list[str],
        system_prompt: str | None = None,
        max_concurrency: int = 5,
        **kwargs: Any,
    ) -> list[str]:
        """批量生成"""
        client = await self._ensure_client()
        return await client.batch_generate(
            prompts, system_prompt, max_concurrency, **kwargs
        )

    async def generate_with_history(
        self,
        prompt: str,
        history: list[dict[str, str]],
        system_prompt: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """带历史记录的生成（支持工具调用）"""
        client = await self._ensure_client()
        return await client.generate_with_history(
            prompt, history, system_prompt, tools, **kwargs
        )

    async def generate_with_images(
        self,
        prompt: str,
        images: list[str],
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> str:
        """带图片的单次生成"""
        client = await self._ensure_client()
        return await client.generate_with_images(prompt, images, system_prompt, **kwargs)

    async def stream_generate_with_images(
        self,
        prompt: str,
        images: list[str],
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """带图片的流式生成"""
        client = await self._ensure_client()
        async for chunk in client.stream_generate_with_images(prompt, images, system_prompt, **kwargs):
            yield chunk


# 智能体类型到客户端的缓存
_agent_clients: dict[str, ConfigurableLLMClient] = {}


def get_agent_llm_client(agent_type: str) -> ConfigurableLLMClient:
    """
    获取智能体的 LLM 客户端

    使用缓存避免重复创建

    Args:
        agent_type: 智能体类型

    Returns:
        ConfigurableLLMClient 实例
    """
    if agent_type not in _agent_clients:
        _agent_clients[agent_type] = ConfigurableLLMClient(agent_type)
    return _agent_clients[agent_type]


async def refresh_agent_llm_client(agent_type: str) -> None:
    """
    刷新智能体的 LLM 客户端配置

    当配置变更时调用

    Args:
        agent_type: 智能体类型
    """
    if agent_type in _agent_clients:
        await _agent_clients[agent_type].refresh()


async def refresh_all_agent_llm_clients() -> None:
    """
    刷新所有智能体的 LLM 客户端配置

    当全局配置变更时调用
    """
    for client in _agent_clients.values():
        await client.refresh()


# ========== LLM 客户端池（负载均衡 + 故障转移） ==========


class LoadBalanceStrategy:
    """负载均衡策略"""
    ROUND_ROBIN = "round_robin"  # 轮询
    RANDOM = "random"  # 随机
    LEAST_LATENCY = "least_latency"  # 最低延迟
    WEIGHTED = "weighted"  # 加权


@dataclass
class PooledClient:
    """池化的客户端"""
    client: LLMClient
    weight: int = 1
    health: ProviderHealth = field(default_factory=lambda: ProviderHealth(provider_id=""))

    def __post_init__(self):
        if self.health.provider_id == "":
            self.health.provider_id = self.client.provider_id


class LLMClientPool:
    """
    LLM 客户端池

    支持多 Provider 负载均衡和故障转移

    使用示例：
    ```python
    pool = LLMClientPool()

    # 添加多个 Provider
    pool.add_client(LLMClient(api_base="https://api.deepseek.com", ...))
    pool.add_client(LLMClient(api_base="https://api.openai.com", ...))

    # 自动选择健康的 Provider
    response = await pool.generate("你好")

    # 流式生成（自动故障转移）
    async for chunk in pool.stream_generate("讲个故事"):
        print(chunk, end="")
    ```
    """

    def __init__(
        self,
        strategy: str = LoadBalanceStrategy.ROUND_ROBIN,
        failover_enabled: bool = True,
        health_check_interval: float = 60.0,
    ):
        """
        初始化客户端池

        Args:
            strategy: 负载均衡策略
            failover_enabled: 是否启用故障转移
            health_check_interval: 健康检查间隔（秒）
        """
        self.strategy = strategy
        self.failover_enabled = failover_enabled
        self.health_check_interval = health_check_interval
        self._clients: list[PooledClient] = []
        self._round_robin_index = 0
        self._lock = asyncio.Lock()

    def add_client(self, client: LLMClient, weight: int = 1) -> None:
        """
        添加客户端到池

        Args:
            client: LLM 客户端
            weight: 权重（用于加权负载均衡）
        """
        pooled = PooledClient(
            client=client,
            weight=weight,
            health=ProviderHealth(provider_id=client.provider_id),
        )
        self._clients.append(pooled)
        logger.info(f"添加 LLM 客户端到池: {client.provider_id}, weight={weight}")

    def _get_healthy_clients(self) -> list[PooledClient]:
        """获取健康的客户端列表"""
        healthy = []
        for pc in self._clients:
            if pc.health.is_healthy or pc.health.should_retry(self.health_check_interval):
                healthy.append(pc)
        return healthy

    async def _select_client(self) -> PooledClient | None:
        """根据策略选择客户端"""
        healthy = self._get_healthy_clients()
        if not healthy:
            # 所有客户端都不健康，尝试返回最近失败的
            if self._clients:
                return min(self._clients, key=lambda x: x.health.failure_count)
            return None

        if self.strategy == LoadBalanceStrategy.RANDOM:
            return random.choice(healthy)

        elif self.strategy == LoadBalanceStrategy.LEAST_LATENCY:
            return min(healthy, key=lambda x: x.health.avg_latency_ms or float('inf'))

        elif self.strategy == LoadBalanceStrategy.WEIGHTED:
            weights = [pc.weight for pc in healthy]
            return random.choices(healthy, weights=weights, k=1)[0]

        else:  # ROUND_ROBIN
            async with self._lock:
                index = self._round_robin_index % len(healthy)
                self._round_robin_index += 1
                return healthy[index]

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> str:
        """
        生成（带故障转移）

        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            **kwargs: 额外参数

        Returns:
            生成的文本

        Raises:
            LLMClientError: 所有 Provider 都失败时抛出
        """
        tried_providers: set[str] = set()
        last_error: Exception | None = None

        while True:
            pooled = await self._select_client()
            if pooled is None or pooled.client.provider_id in tried_providers:
                break

            tried_providers.add(pooled.client.provider_id)
            start_time = time.time()

            try:
                result = await pooled.client.generate(prompt, system_prompt, **kwargs)
                latency_ms = (time.time() - start_time) * 1000
                pooled.health.record_success(latency_ms)
                return result

            except Exception as e:
                pooled.health.record_failure()
                last_error = e
                logger.warning(
                    f"LLM 请求失败，尝试故障转移: provider={pooled.client.provider_id}, error={e}"
                )

                if not self.failover_enabled:
                    break

        raise LLMClientError(
            f"所有 LLM Provider 都失败: {last_error}",
            {"tried_providers": list(tried_providers)},
        )

    async def stream_generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        流式生成（带故障转移）

        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            **kwargs: 额外参数

        Yields:
            生成的文本片段
        """
        tried_providers: set[str] = set()
        last_error: Exception | None = None

        while True:
            pooled = await self._select_client()
            if pooled is None or pooled.client.provider_id in tried_providers:
                break

            tried_providers.add(pooled.client.provider_id)
            start_time = time.time()

            try:
                async for chunk in pooled.client.stream_generate(prompt, system_prompt, **kwargs):
                    yield chunk
                latency_ms = (time.time() - start_time) * 1000
                pooled.health.record_success(latency_ms)
                return

            except Exception as e:
                pooled.health.record_failure()
                last_error = e
                logger.warning(
                    f"LLM 流式请求失败，尝试故障转移: provider={pooled.client.provider_id}, error={e}"
                )

                if not self.failover_enabled:
                    break

        raise LLMClientError(
            f"所有 LLM Provider 流式请求都失败: {last_error}",
            {"tried_providers": list(tried_providers)},
        )

    def get_health_status(self) -> list[dict[str, Any]]:
        """获取所有客户端的健康状态"""
        return [
            {
                "provider_id": pc.client.provider_id,
                "is_healthy": pc.health.is_healthy,
                "failure_count": pc.health.failure_count,
                "avg_latency_ms": round(pc.health.avg_latency_ms, 2),
                "total_requests": pc.health.total_requests,
            }
            for pc in self._clients
        ]


# 全局客户端池实例
_global_pool: LLMClientPool | None = None


def get_llm_client_pool() -> LLMClientPool:
    """
    获取全局 LLM 客户端池

    Returns:
        LLMClientPool 实例
    """
    global _global_pool
    if _global_pool is None:
        _global_pool = LLMClientPool(
            strategy=LoadBalanceStrategy.ROUND_ROBIN,
            failover_enabled=True,
        )
    return _global_pool


async def init_llm_client_pool_from_config() -> LLMClientPool:
    """
    从数据库配置初始化 LLM 客户端池

    读取所有活跃的 Provider 和模型配置，创建客户端池

    Returns:
        配置好的 LLMClientPool 实例
    """
    global _global_pool

    try:
        from app.services.ai_config_service import AIConfigService

        async with AIConfigService() as service:
            providers = await service.list_providers(include_inactive=False)
            models = await service.list_models(include_inactive=False)

            pool = LLMClientPool(
                strategy=LoadBalanceStrategy.LEAST_LATENCY,
                failover_enabled=True,
            )

            # 为每个活跃的 Provider + Model 组合创建客户端
            for model in models:
                provider = next(
                    (p for p in providers if p.id == model.provider_id),
                    None
                )
                if provider is None:
                    continue

                # 获取解密的 API Key
                encrypted_key = await service.repository.get_provider_encrypted_api_key(
                    provider.id
                )
                if not encrypted_key:
                    continue

                api_key = service.encryption.decrypt(encrypted_key)

                client = LLMClient(
                    api_base=provider.base_url,
                    api_key=api_key,
                    model_name=model.model_id,
                    temperature=model.default_temperature,
                    max_tokens=model.default_max_tokens,
                    top_p=model.default_top_p,
                    timeout=float(model.default_timeout),
                    max_retries=model.default_max_retries,
                    provider_id=f"{provider.code}:{model.model_id}",
                )
                pool.add_client(client)

            if pool._clients:
                _global_pool = pool
                logger.info(f"从配置初始化 LLM 客户端池: {len(pool._clients)} 个客户端")
            else:
                logger.warning("未找到活跃的 LLM 配置，请在管理后台配置 AI 模型")
                _global_pool = pool  # 空池

            return _global_pool

    except Exception as e:
        logger.error(f"从配置初始化 LLM 客户端池失败: {e}")
        return get_llm_client_pool()
