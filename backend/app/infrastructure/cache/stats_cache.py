"""
统计数据缓存服务

为高频统计接口提供 Redis 缓存支持
"""

import hashlib
import json
from collections.abc import Awaitable, Callable
from datetime import timedelta
from functools import wraps
from typing import Any, TypeVar, cast

from app.infrastructure.cache.redis import get_redis

T = TypeVar("T", bound=dict[str, Any])


class StatsCacheService:
    """统计数据缓存服务"""

    # 缓存键前缀
    CACHE_PREFIX = "stats:"

    # 默认缓存时间配置
    CACHE_TTL = {
        "overview": timedelta(minutes=5),
        "user_growth": timedelta(minutes=10),
        "system_status": timedelta(minutes=1),
        "recent_activities": timedelta(minutes=2),
    }

    def __init__(self):
        self._redis = None

    @property
    def redis(self):
        """延迟获取 Redis 客户端"""
        if self._redis is None:
            try:
                self._redis = get_redis()
            except RuntimeError:
                return None
        return self._redis

    def _make_key(self, category: str, *args: Any) -> str:
        """生成缓存键"""
        if args:
            # 对参数进行哈希以生成唯一键
            args_hash = hashlib.md5(
                json.dumps(args, sort_keys=True, default=str).encode()
            ).hexdigest()[:8]
            return f"{self.CACHE_PREFIX}{category}:{args_hash}"
        return f"{self.CACHE_PREFIX}{category}"

    async def get(self, category: str, *args: Any) -> dict[str, Any] | None:
        """获取缓存数据"""
        if self.redis is None:
            return None

        key = self._make_key(category, *args)
        try:
            data = await self.redis.get(key)
            if data:
                return cast(dict[str, Any], json.loads(data))
        except Exception:
            # 缓存读取失败不影响业务
            pass
        return None

    async def set(
        self,
        category: str,
        data: dict[str, Any],
        *args: Any,
        ttl: timedelta | None = None,
    ) -> None:
        """设置缓存数据"""
        if self.redis is None:
            return

        key = self._make_key(category, *args)
        expire = ttl or self.CACHE_TTL.get(category, timedelta(minutes=5))

        try:
            await self.redis.setex(
                key,
                int(expire.total_seconds()),
                json.dumps(data, default=str),
            )
        except Exception:
            # 缓存写入失败不影响业务
            pass

    async def invalidate(self, category: str, *args: Any) -> None:
        """使缓存失效"""
        if self.redis is None:
            return

        key = self._make_key(category, *args)
        try:
            await self.redis.delete(key)
        except Exception:
            pass

    async def invalidate_all(self, category: str) -> None:
        """使某类缓存全部失效"""
        if self.redis is None:
            return

        pattern = f"{self.CACHE_PREFIX}{category}:*"
        try:
            cursor = 0
            while True:
                cursor, keys = await self.redis.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    await self.redis.delete(*keys)
                if cursor == 0:
                    break
        except Exception:
            pass


# 全局缓存服务实例
_stats_cache: StatsCacheService | None = None


def get_stats_cache() -> StatsCacheService:
    """获取统计缓存服务实例"""
    global _stats_cache
    if _stats_cache is None:
        _stats_cache = StatsCacheService()
    return _stats_cache


def cached_stats(
    category: str,
    ttl: timedelta | None = None,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    统计数据缓存装饰器

    @param category: 缓存类别（用于生成缓存键和确定 TTL）
    @param ttl: 自定义缓存时间，不指定则使用默认配置

    @example
    ```python
    @cached_stats("overview")
    async def get_overview_stats(self) -> dict:
        # 实际查询逻辑
        ...
    ```
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            cache = get_stats_cache()

            # 尝试从缓存获取
            cache_args = args[1:] if args else ()  # 排除 self
            cache_kwargs = tuple(sorted(kwargs.items())) if kwargs else ()
            key_args = (*cache_args, cache_kwargs) if cache_kwargs else cache_args
            cached_data = await cache.get(category, *key_args)
            if cached_data is not None:
                return cast(T, cached_data)

            # 执行原函数
            result = await func(*args, **kwargs)

            # 存入缓存
            if result is not None:
                await cache.set(category, result, *key_args, ttl=ttl)

            return result

        return wrapper

    return decorator
