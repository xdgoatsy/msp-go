"""
Redis 缓存管理

提供 Redis 连接和常用操作封装。
包含连接健壮性增强和内存缓存降级策略。
"""

import logging
from collections import OrderedDict

import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)

# Redis 连接池
redis_pool: redis.ConnectionPool | None = None
_redis_client: redis.Redis | None = None


# ========== 内存缓存降级 ==========

class InMemoryFallbackCache:
    """
    内存 LRU 缓存（Redis 不可用时的降级方案）

    简单的 LRU 实现，仅用于短期降级，不支持过期时间精确控制。
    """

    def __init__(self, max_size: int = 1000):
        self._cache: OrderedDict[str, str] = OrderedDict()
        self._max_size = max_size

    def get(self, key: str) -> str | None:
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def set(self, key: str, value: str) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def delete(self, key: str) -> None:
        self._cache.pop(key, None)

    def exists(self, key: str) -> bool:
        return key in self._cache


_fallback_cache = InMemoryFallbackCache(max_size=settings.redis_fallback_cache_max_size)


async def init_redis() -> None:
    """初始化 Redis 连接池"""
    global redis_pool, _redis_client
    redis_pool = redis.ConnectionPool.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        max_connections=settings.redis_max_connections,
        retry_on_timeout=settings.redis_retry_on_timeout,
        socket_timeout=settings.redis_socket_timeout_seconds,
        socket_connect_timeout=settings.redis_socket_connect_timeout_seconds,
    )
    _redis_client = redis.Redis(connection_pool=redis_pool)


async def close_redis() -> None:
    """关闭 Redis 连接池"""
    global redis_pool, _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
    if redis_pool:
        await redis_pool.disconnect()
        redis_pool = None


def get_redis() -> redis.Redis:
    """获取 Redis 客户端"""
    if _redis_client is None:
        raise RuntimeError("Redis 连接池未初始化，请先调用 init_redis()")
    return _redis_client


def get_redis_pool() -> redis.ConnectionPool | None:
    """获取 Redis 连接池（供其他模块复用）"""
    return redis_pool


async def get_redis_client_safe() -> redis.Redis | None:
    """
    安全获取 Redis 客户端

    优先使用全局连接池，回退到创建临时连接。
    适用于各模块统一获取 Redis 连接。

    Returns:
        Redis 客户端，不可用时返回 None
    """
    # 优先使用全局连接池
    if _redis_client is not None:
        try:
            await _redis_client.ping()
            return _redis_client
        except Exception:
            logger.warning("Redis 全局连接不可用，尝试重连")

    # 回退：创建临时连接
    try:
        client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            retry_on_timeout=settings.redis_retry_on_timeout,
            socket_connect_timeout=settings.redis_socket_connect_timeout_seconds,
            socket_timeout=settings.redis_socket_timeout_seconds,
        )
        await client.ping()
        return client
    except Exception:
        logger.warning("Redis 完全不可用，将降级到内存缓存")
        return None


def get_fallback_cache() -> InMemoryFallbackCache:
    """获取内存降级缓存"""
    return _fallback_cache


class RedisCache:
    """Redis 缓存操作封装"""

    def __init__(self, prefix: str = "msp"):
        """
        Args:
            prefix: 键前缀，用于命名空间隔离
        """
        self.prefix = prefix
        self.client = get_redis()

    def _make_key(self, key: str) -> str:
        """生成带前缀的键"""
        return f"{self.prefix}:{key}"

    async def get(self, key: str) -> str | None:
        """获取值"""
        return await self.client.get(self._make_key(key))

    async def set(
        self,
        key: str,
        value: str,
        expire: int | None = None,
    ) -> bool:
        """
        设置值

        Args:
            key: 键
            value: 值
            expire: 过期时间（秒）
        """
        result = await self.client.set(
            self._make_key(key),
            value,
            ex=expire,
        )
        return result is True

    async def delete(self, key: str) -> int:
        """删除键"""
        return await self.client.delete(self._make_key(key))

    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        return await self.client.exists(self._make_key(key)) > 0

    async def hget(self, name: str, key: str) -> str | None:
        """哈希表获取"""
        return await self.client.hget(self._make_key(name), key)

    async def hset(self, name: str, key: str, value: str) -> int:
        """哈希表设置"""
        return await self.client.hset(self._make_key(name), key, value)

    async def hgetall(self, name: str) -> dict[str, str]:
        """获取整个哈希表"""
        return await self.client.hgetall(self._make_key(name))

    async def hdel(self, name: str, *keys: str) -> int:
        """删除哈希表中的键"""
        return await self.client.hdel(self._make_key(name), *keys)


class PIIMaskingCache(RedisCache):
    """
    PII 脱敏映射缓存

    用于存储脱敏标识符与真实 PII 的映射关系

    参考规划文档 6.3 隐私保护与 PII 脱敏
    """

    def __init__(self):
        super().__init__(prefix="msp:pii")
        self.default_expire = 3600  # 1 小时过期

    async def store_mapping(
        self,
        session_id: str,
        mappings: dict[str, str],
    ) -> None:
        """
        存储脱敏映射（pipeline 批量写入）

        Args:
            session_id: 会话 ID
            mappings: {<STUDENT_A>: "张三", <ID_1>: "2023001"}
        """
        if not mappings:
            return
        key = self._make_key(session_id)
        pipe = self.client.pipeline()
        for masked, original in mappings.items():
            pipe.hset(key, masked, original)
        pipe.expire(key, self.default_expire)
        await pipe.execute()

    async def get_original(self, session_id: str, masked: str) -> str | None:
        """获取原始值"""
        return await self.hget(session_id, masked)

    async def restore_all(self, session_id: str, text: str) -> str:
        """
        还原文本中的所有脱敏标识符

        Args:
            session_id: 会话 ID
            text: 包含脱敏标识符的文本

        Returns:
            还原后的文本
        """
        mappings = await self.hgetall(session_id)
        for masked, original in mappings.items():
            text = text.replace(masked, original)
        return text

    async def clear_session(self, session_id: str) -> None:
        """清除会话的映射数据"""
        await self.delete(session_id)
