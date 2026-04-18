"""
Redis 检查点存储

为 LangGraph 工作流提供 Redis 持久化检查点

特性：
- 支持多实例部署的会话状态共享
- 自动过期清理
- 序列化/反序列化状态

注意：此实现基于 langgraph-checkpoint 的 API
"""

import json
import logging
from collections.abc import AsyncIterator, Sequence
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    get_checkpoint_id,
)

logger = logging.getLogger(__name__)


class RedisCheckpointer(BaseCheckpointSaver):
    """
    Redis 检查点存储器

    将 LangGraph 工作流状态持久化到 Redis

    使用示例：
    ```python
    from app.agents.workflow.checkpointer import RedisCheckpointer

    checkpointer = RedisCheckpointer(ttl=3600)
    await checkpointer.init()

    # 在工作流编译时使用
    app = workflow.compile(checkpointer=checkpointer)
    ```
    """

    def __init__(
        self,
        prefix: str = "langgraph:checkpoint",
        ttl: int = 3600,  # 默认 1 小时过期
    ):
        """
        初始化 Redis 检查点存储器

        Args:
            prefix: Redis 键前缀
            ttl: 检查点过期时间（秒）
        """
        super().__init__()
        self.prefix = prefix
        self.ttl = ttl
        self._redis: Any = None
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
                logger.info("RedisCheckpointer 使用全局 Redis 连接池")
                return
        except (RuntimeError, ImportError):
            pass

        # 回退：创建独立连接
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
            logger.warning("RedisCheckpointer 使用独立 Redis 连接")
        except Exception as e:
            logger.error(f"RedisCheckpointer 初始化失败: {e}")
            raise

    def _make_key(self, thread_id: str, checkpoint_id: str | None = None) -> str:
        """生成 Redis 键"""
        if checkpoint_id:
            return f"{self.prefix}:{thread_id}:{checkpoint_id}"
        return f"{self.prefix}:{thread_id}"

    def _make_list_key(self, thread_id: str) -> str:
        """生成检查点列表键"""
        return f"{self.prefix}:list:{thread_id}"

    def _serialize(self, data: Any) -> str:
        """序列化数据"""
        return json.dumps(data, ensure_ascii=False, default=str)

    def _deserialize(self, data: str) -> Any:
        """反序列化数据"""
        return json.loads(data)

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        """
        异步获取检查点元组

        Args:
            config: 运行配置

        Returns:
            CheckpointTuple 或 None
        """
        if not self._initialized:
            await self.init()

        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            return None

        checkpoint_id = get_checkpoint_id(config)

        try:
            if checkpoint_id:
                # 获取指定的检查点
                key = self._make_key(thread_id, checkpoint_id)
                data = await self._redis.get(key)
            else:
                # 获取最新的检查点
                list_key = self._make_list_key(thread_id)
                checkpoint_ids = await self._redis.lrange(list_key, 0, 0)

                if not checkpoint_ids:
                    return None

                checkpoint_id = checkpoint_ids[0]
                key = self._make_key(thread_id, checkpoint_id)
                data = await self._redis.get(key)

            if not data:
                return None

            parsed = self._deserialize(data)

            # 构建 Checkpoint TypedDict
            checkpoint: Checkpoint = {
                "v": parsed.get("v", 1),
                "id": parsed.get("id", checkpoint_id),
                "ts": parsed.get("ts", ""),
                "channel_values": parsed.get("channel_values", {}),
                "channel_versions": parsed.get("channel_versions", {}),
                "versions_seen": parsed.get("versions_seen", {}),
                "updated_channels": parsed.get("updated_channels", set()),
            }

            # 构建 CheckpointMetadata TypedDict
            metadata: CheckpointMetadata = parsed.get("metadata", {})

            return CheckpointTuple(
                config={
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": config.get("configurable", {}).get("checkpoint_ns", ""),
                        "checkpoint_id": checkpoint_id,
                    }
                },
                checkpoint=checkpoint,
                metadata=metadata,
                parent_config=parsed.get("parent_config"),
            )

        except Exception as e:
            logger.error(f"获取检查点失败: thread_id={thread_id}, error={e}")
            return None

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        """
        异步保存检查点

        Args:
            config: 运行配置
            checkpoint: 检查点数据
            metadata: 元数据
            new_versions: 新版本信息

        Returns:
            更新后的配置
        """
        if not self._initialized:
            await self.init()

        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            raise ValueError("thread_id is required")

        checkpoint_ns = config.get("configurable", {}).get("checkpoint_ns", "")
        checkpoint_id = checkpoint["id"]

        try:
            # 序列化检查点数据
            data = {
                "v": checkpoint.get("v", 1),
                "id": checkpoint_id,
                "ts": checkpoint.get("ts", ""),
                "channel_values": checkpoint.get("channel_values", {}),
                "channel_versions": checkpoint.get("channel_versions", {}),
                "versions_seen": checkpoint.get("versions_seen", {}),
                "pending_sends": checkpoint.get("pending_sends", []),
                "metadata": metadata,
                "parent_config": {
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": config.get("configurable", {}).get("checkpoint_id"),
                    }
                } if config.get("configurable", {}).get("checkpoint_id") else None,
            }

            key = self._make_key(thread_id, checkpoint_id)
            await self._redis.setex(key, self.ttl, self._serialize(data))

            # 更新检查点列表（保留最近 10 个）
            list_key = self._make_list_key(thread_id)
            await self._redis.lpush(list_key, checkpoint_id)
            await self._redis.ltrim(list_key, 0, 9)
            await self._redis.expire(list_key, self.ttl)

            logger.debug(f"保存检查点: thread_id={thread_id}, checkpoint_id={checkpoint_id}")

            return {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": checkpoint_id,
                }
            }

        except Exception as e:
            logger.error(f"保存检查点失败: thread_id={thread_id}, error={e}")
            raise

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        """
        异步保存写入操作

        Args:
            config: 运行配置
            writes: 写入操作列表
            task_id: 任务 ID
            task_path: 任务路径
        """
        # 当前实现中，写入操作已包含在 checkpoint 中
        pass

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]:
        """
        异步列出检查点

        Args:
            config: 运行配置
            filter: 过滤条件
            before: 在此之前的检查点
            limit: 限制数量

        Yields:
            CheckpointTuple
        """
        if not self._initialized:
            await self.init()

        if config is None:
            return

        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            return

        try:
            list_key = self._make_list_key(thread_id)
            checkpoint_ids = await self._redis.lrange(list_key, 0, (limit or 10) - 1)

            for checkpoint_id in checkpoint_ids:
                key = self._make_key(thread_id, checkpoint_id)
                data = await self._redis.get(key)

                if not data:
                    continue

                parsed = self._deserialize(data)

                checkpoint: Checkpoint = {
                    "v": parsed.get("v", 1),
                    "id": parsed.get("id", checkpoint_id),
                    "ts": parsed.get("ts", ""),
                    "channel_values": parsed.get("channel_values", {}),
                    "channel_versions": parsed.get("channel_versions", {}),
                    "versions_seen": parsed.get("versions_seen", {}),
                    "updated_channels": parsed.get("updated_channels", set()),
                }

                metadata: CheckpointMetadata = parsed.get("metadata", {})

                yield CheckpointTuple(
                    config={
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_ns": config.get("configurable", {}).get("checkpoint_ns", ""),
                            "checkpoint_id": checkpoint_id,
                        }
                    },
                    checkpoint=checkpoint,
                    metadata=metadata,
                    parent_config=parsed.get("parent_config"),
                )

        except Exception as e:
            logger.error(f"列出检查点失败: thread_id={thread_id}, error={e}")

    async def adelete(self, thread_id: str) -> None:
        """
        删除线程的所有检查点

        Args:
            thread_id: 线程 ID
        """
        if not self._initialized:
            await self.init()

        try:
            list_key = self._make_list_key(thread_id)
            checkpoint_ids = await self._redis.lrange(list_key, 0, -1)

            # 删除所有检查点
            for checkpoint_id in checkpoint_ids:
                key = self._make_key(thread_id, checkpoint_id)
                await self._redis.delete(key)

            # 删除列表
            await self._redis.delete(list_key)

            logger.info(f"删除检查点: thread_id={thread_id}, count={len(checkpoint_ids)}")

        except Exception as e:
            logger.error(f"删除检查点失败: thread_id={thread_id}, error={e}")

    # 同步方法实现（基类要求）
    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        """同步获取检查点元组"""
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.aget_tuple(config))

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        """同步保存检查点"""
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.aput(config, checkpoint, metadata, new_versions)
        )

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        """同步保存写入"""
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        loop.run_until_complete(
            self.aput_writes(config, writes, task_id, task_path)
        )

    def list(  # type: ignore[override]
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]:
        """列出检查点（返回异步迭代器）

        注意：此方法返回 AsyncIterator 而非 Iterator，
        因为 LangGraph 在异步上下文中使用此检查点器。
        """
        return self.alist(config, filter=filter, before=before, limit=limit)


# 全局检查点实例
_redis_checkpointer: RedisCheckpointer | None = None


async def get_redis_checkpointer(ttl: int = 3600) -> RedisCheckpointer:
    """
    获取 Redis 检查点存储器实例

    Args:
        ttl: 检查点过期时间（秒）

    Returns:
        RedisCheckpointer 实例
    """
    global _redis_checkpointer
    if _redis_checkpointer is None:
        _redis_checkpointer = RedisCheckpointer(ttl=ttl)
        await _redis_checkpointer.init()
    return _redis_checkpointer
