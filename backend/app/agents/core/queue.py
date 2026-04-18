"""
LLM 请求队列

基于 Redis 的异步请求队列，实现削峰填谷

特性：
- 异步请求处理
- 优先级队列
- 请求去重
- 超时处理
- 结果缓存
"""

import asyncio
import hashlib
import json
import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class RequestPriority(int, Enum):
    """请求优先级"""
    HIGH = 1
    NORMAL = 5
    LOW = 10


class RequestStatus(str, Enum):
    """请求状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class QueuedRequest:
    """队列请求"""
    id: str
    prompt: str
    system_prompt: str | None = None
    priority: int = RequestPriority.NORMAL
    created_at: float = field(default_factory=time.time)
    timeout: float = 60.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "system_prompt": self.system_prompt,
            "priority": self.priority,
            "created_at": self.created_at,
            "timeout": self.timeout,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QueuedRequest":
        return cls(**data)


@dataclass
class QueuedResponse:
    """队列响应"""
    request_id: str
    status: RequestStatus
    result: str | None = None
    error: str | None = None
    processing_time_ms: float = 0
    completed_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "processing_time_ms": self.processing_time_ms,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QueuedResponse":
        data["status"] = RequestStatus(data["status"])
        return cls(**data)


class LLMRequestQueue:
    """
    LLM 请求队列

    使用 Redis 实现异步请求队列

    使用示例：
    ```python
    queue = LLMRequestQueue()
    await queue.init()

    # 提交请求
    request_id = await queue.submit(
        prompt="你好",
        priority=RequestPriority.HIGH,
    )

    # 等待结果
    response = await queue.wait_for_result(request_id, timeout=30)
    print(response.result)
    ```
    """

    def __init__(
        self,
        queue_name: str = "llm_queue",
        result_ttl: int = 300,  # 结果缓存 5 分钟
        max_queue_size: int = 1000,
        dedup_enabled: bool = True,
        dedup_ttl: int = 60,  # 去重窗口 1 分钟
    ):
        """
        初始化请求队列

        Args:
            queue_name: 队列名称
            result_ttl: 结果缓存时间（秒）
            max_queue_size: 最大队列长度
            dedup_enabled: 是否启用请求去重
            dedup_ttl: 去重窗口时间（秒）
        """
        self.queue_name = queue_name
        self.result_ttl = result_ttl
        self.max_queue_size = max_queue_size
        self.dedup_enabled = dedup_enabled
        self.dedup_ttl = dedup_ttl
        self._redis: Redis[str] | None = None
        self._initialized = False

    async def init(self) -> None:
        """初始化 Redis 连接"""
        if self._initialized:
            return

        try:
            from app.infrastructure.cache.redis import get_redis, get_redis_pool

            pool = get_redis_pool()
            if pool is not None:
                self._redis = get_redis()
                self._initialized = True
                logger.info("LLMRequestQueue 使用全局 Redis 连接池")
                return
        except (RuntimeError, ImportError):
            pass

        try:
            from redis import asyncio as aioredis

            from app.config import settings

            redis_url = getattr(settings, "redis_url", "redis://localhost:6379/0")
            self._redis = await aioredis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            self._initialized = True
            logger.info("LLMRequestQueue 使用独立 Redis 连接")
        except Exception as e:
            logger.error(f"LLMRequestQueue 初始化失败: {e}")
            raise

    def _get_redis(self) -> "Redis[str]":
        """获取 Redis 客户端，确保已初始化"""
        if self._redis is None:
            raise RuntimeError("LLMRequestQueue 未初始化，请先调用 init()")
        return self._redis

    def _make_queue_key(self) -> str:
        """生成队列键"""
        return f"queue:{self.queue_name}"

    def _make_result_key(self, request_id: str) -> str:
        """生成结果键"""
        return f"queue:{self.queue_name}:result:{request_id}"

    def _make_status_key(self, request_id: str) -> str:
        """生成状态键"""
        return f"queue:{self.queue_name}:status:{request_id}"

    def _make_dedup_key(self, prompt_hash: str) -> str:
        """生成去重键"""
        return f"queue:{self.queue_name}:dedup:{prompt_hash}"

    def _hash_prompt(self, prompt: str, system_prompt: str | None = None) -> str:
        """生成提示词哈希"""
        content = f"{system_prompt or ''}:{prompt}"
        return hashlib.md5(content.encode()).hexdigest()

    async def submit(
        self,
        prompt: str,
        system_prompt: str | None = None,
        priority: RequestPriority = RequestPriority.NORMAL,
        timeout: float = 60.0,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        提交请求到队列

        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            priority: 优先级
            timeout: 超时时间
            metadata: 元数据

        Returns:
            请求 ID

        Raises:
            Exception: 队列已满或提交失败
        """
        if not self._initialized:
            await self.init()

        # 检查队列长度
        queue_key = self._make_queue_key()
        queue_size = await self._get_redis().zcard(queue_key)
        if queue_size >= self.max_queue_size:
            raise Exception(f"队列已满: {queue_size}/{self.max_queue_size}")

        # 去重检查
        if self.dedup_enabled:
            prompt_hash = self._hash_prompt(prompt, system_prompt)
            dedup_key = self._make_dedup_key(prompt_hash)
            existing_id = await self._get_redis().get(dedup_key)
            if existing_id:
                logger.debug(f"请求去重命中: {existing_id}")
                return existing_id

        # 创建请求
        request_id = str(uuid.uuid4())
        request = QueuedRequest(
            id=request_id,
            prompt=prompt,
            system_prompt=system_prompt,
            priority=priority,
            timeout=timeout,
            metadata=metadata or {},
        )

        # 添加到队列（使用优先级作为分数）
        score = priority * 1000000000 + time.time()  # 优先级 + 时间戳
        await self._get_redis().zadd(queue_key, {json.dumps(request.to_dict()): score})

        # 设置状态
        status_key = self._make_status_key(request_id)
        await self._get_redis().setex(status_key, int(timeout) + 60, RequestStatus.PENDING.value)

        # 设置去重键
        if self.dedup_enabled:
            prompt_hash = self._hash_prompt(prompt, system_prompt)
            dedup_key = self._make_dedup_key(prompt_hash)
            await self._get_redis().setex(dedup_key, self.dedup_ttl, request_id)

        logger.debug(f"请求已提交: id={request_id}, priority={priority}")
        return request_id

    async def pop(self) -> QueuedRequest | None:
        """
        从队列中取出一个请求

        Returns:
            请求对象，队列为空返回 None
        """
        if not self._initialized:
            await self.init()

        queue_key = self._make_queue_key()

        # 取出优先级最高的请求
        items = await self._get_redis().zpopmin(queue_key, 1)
        if not items:
            return None

        request_data, _ = items[0]
        request = QueuedRequest.from_dict(json.loads(request_data))

        # 更新状态
        status_key = self._make_status_key(request.id)
        await self._get_redis().set(status_key, RequestStatus.PROCESSING.value)

        logger.debug(f"请求已取出: id={request.id}")
        return request

    async def complete(
        self,
        request_id: str,
        result: str | None = None,
        error: str | None = None,
        processing_time_ms: float = 0,
    ) -> None:
        """
        完成请求

        Args:
            request_id: 请求 ID
            result: 结果
            error: 错误信息
            processing_time_ms: 处理时间
        """
        if not self._initialized:
            await self.init()

        status = RequestStatus.COMPLETED if result else RequestStatus.FAILED
        response = QueuedResponse(
            request_id=request_id,
            status=status,
            result=result,
            error=error,
            processing_time_ms=processing_time_ms,
        )

        # 保存结果
        result_key = self._make_result_key(request_id)
        await self._get_redis().setex(result_key, self.result_ttl, json.dumps(response.to_dict()))

        # 更新状态
        status_key = self._make_status_key(request_id)
        await self._get_redis().set(status_key, status.value)

        # 发布完成通知
        channel = f"queue:{self.queue_name}:done:{request_id}"
        await self._get_redis().publish(channel, "done")

        logger.debug(f"请求已完成: id={request_id}, status={status.value}")

    async def get_status(self, request_id: str) -> RequestStatus | None:
        """
        获取请求状态

        Args:
            request_id: 请求 ID

        Returns:
            请求状态
        """
        if not self._initialized:
            await self.init()

        status_key = self._make_status_key(request_id)
        status = await self._get_redis().get(status_key)
        if status:
            return RequestStatus(status)
        return None

    async def get_result(self, request_id: str) -> QueuedResponse | None:
        """
        获取请求结果

        Args:
            request_id: 请求 ID

        Returns:
            响应对象
        """
        if not self._initialized:
            await self.init()

        result_key = self._make_result_key(request_id)
        data = await self._get_redis().get(result_key)
        if data:
            return QueuedResponse.from_dict(json.loads(data))
        return None

    async def wait_for_result(
        self,
        request_id: str,
        timeout: float = 60.0,
        poll_interval: float = 0.1,
    ) -> QueuedResponse:
        """
        等待请求结果

        Args:
            request_id: 请求 ID
            timeout: 超时时间
            poll_interval: 轮询间隔

        Returns:
            响应对象

        Raises:
            TimeoutError: 超时
        """
        if not self._initialized:
            await self.init()

        start_time = time.time()

        while time.time() - start_time < timeout:
            # 检查结果
            response = await self.get_result(request_id)
            if response:
                return response

            # 检查状态
            status = await self.get_status(request_id)
            if status in (RequestStatus.COMPLETED, RequestStatus.FAILED, RequestStatus.TIMEOUT):
                response = await self.get_result(request_id)
                if response:
                    return response

            await asyncio.sleep(poll_interval)

        # 超时
        await self.complete(request_id, error="Request timeout")
        raise TimeoutError(f"Request {request_id} timeout after {timeout}s")

    async def get_queue_stats(self) -> dict[str, Any]:
        """
        获取队列统计信息

        Returns:
            统计信息
        """
        if not self._initialized:
            await self.init()

        queue_key = self._make_queue_key()
        queue_size = await self._get_redis().zcard(queue_key)

        return {
            "queue_name": self.queue_name,
            "queue_size": queue_size,
            "max_queue_size": self.max_queue_size,
            "utilization": queue_size / self.max_queue_size if self.max_queue_size > 0 else 0,
        }


class QueueWorker:
    """
    队列工作者

    从队列中取出请求并处理

    使用示例：
    ```python
    async def process_request(request: QueuedRequest) -> str:
        # 调用 LLM
        return await llm_client.generate(request.prompt)

    worker = QueueWorker(queue, process_request)
    await worker.start()
    ```
    """

    def __init__(
        self,
        queue: LLMRequestQueue,
        processor: Callable[[QueuedRequest], Any],
        concurrency: int = 5,
        poll_interval: float = 0.1,
    ):
        """
        初始化工作者

        Args:
            queue: 请求队列
            processor: 请求处理函数
            concurrency: 并发数
            poll_interval: 轮询间隔
        """
        self.queue = queue
        self.processor = processor
        self.concurrency = concurrency
        self.poll_interval = poll_interval
        self._running = False
        self._tasks: list[asyncio.Task] = []

    async def _worker(self, worker_id: int) -> None:
        """工作者协程"""
        logger.info(f"Worker {worker_id} 启动")

        while self._running:
            try:
                # 从队列取出请求
                request = await self.queue.pop()
                if request is None:
                    await asyncio.sleep(self.poll_interval)
                    continue

                # 检查超时
                if time.time() - request.created_at > request.timeout:
                    await self.queue.complete(request.id, error="Request expired")
                    continue

                # 处理请求
                start_time = time.time()
                try:
                    result = await self.processor(request)
                    processing_time = (time.time() - start_time) * 1000
                    await self.queue.complete(
                        request.id,
                        result=result,
                        processing_time_ms=processing_time,
                    )
                except Exception as e:
                    processing_time = (time.time() - start_time) * 1000
                    await self.queue.complete(
                        request.id,
                        error=str(e),
                        processing_time_ms=processing_time,
                    )
                    logger.error(f"Worker {worker_id} 处理请求失败: {e}")

            except Exception as e:
                logger.error(f"Worker {worker_id} 异常: {e}")
                await asyncio.sleep(1)

        logger.info(f"Worker {worker_id} 停止")

    async def start(self) -> None:
        """启动工作者"""
        if self._running:
            return

        self._running = True
        for i in range(self.concurrency):
            task = asyncio.create_task(self._worker(i))
            self._tasks.append(task)

        logger.info(f"QueueWorker 启动: concurrency={self.concurrency}")

    async def stop(self) -> None:
        """停止工作者"""
        self._running = False
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()
        logger.info("QueueWorker 停止")


# 全局队列实例
_global_queue: LLMRequestQueue | None = None


async def get_llm_request_queue() -> LLMRequestQueue:
    """获取全局 LLM 请求队列"""
    global _global_queue
    if _global_queue is None:
        _global_queue = LLMRequestQueue()
        await _global_queue.init()
    return _global_queue
