"""
缓存管理器

提供智能体系统的缓存功能，基于 Redis 实现

特性：
- 支持 JSON 序列化
- 支持 TTL 过期
- 支持 get_or_compute 模式
- 支持缓存键前缀
"""

import hashlib
import json
import logging
from collections.abc import Callable
from typing import Any, TypeVar

from app.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CacheError(Exception):
    """缓存异常"""

    pass


class CacheManager:
    """
    缓存管理器

    封装 Redis 操作，提供统一的缓存接口

    使用示例：
    ```python
    cache = CacheManager(prefix="solver")

    # 设置缓存
    await cache.set("problem:123", {"answer": "x^2"}, ttl=3600)

    # 获取缓存
    result = await cache.get("problem:123")

    # 计算并缓存
    result = await cache.get_or_compute(
        "problem:456",
        compute_fn=lambda: solve_problem("..."),
        ttl=3600
    )
    ```
    """

    def __init__(
        self,
        prefix: str = "agent",
        default_ttl: int = 86400,  # 默认 24 小时
    ):
        """
        初始化缓存管理器

        Args:
            prefix: 缓存键前缀
            default_ttl: 默认过期时间（秒）
        """
        self.prefix = prefix
        self.default_ttl = default_ttl
        self._redis: Any = None
        self._use_global_pool = True  # 优先使用全局连接池

    async def _get_redis(self) -> Any:
        """
        获取 Redis 连接

        优先使用全局连接池，回退到独立连接
        """
        if self._redis is not None:
            return self._redis

        # 优先尝试使用全局连接池
        if self._use_global_pool:
            try:
                from app.infrastructure.cache.redis import get_redis, get_redis_pool

                pool = get_redis_pool()
                if pool is not None:
                    self._redis = get_redis()
                    logger.debug(f"CacheManager 使用全局 Redis 连接池: prefix={self.prefix}")
                    return self._redis
            except (RuntimeError, ImportError):
                pass

        # 回退：创建独立连接（开发/测试环境）
        try:
            from redis import asyncio as aioredis

            redis_url = getattr(settings, "redis_url", "redis://localhost:6379/0")
            self._redis = await aioredis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            logger.warning(f"CacheManager 使用独立 Redis 连接: prefix={self.prefix}")
        except ImportError:
            logger.warning("redis 库未安装，缓存功能将被禁用")
            self._redis = None
        except Exception as e:
            logger.warning(f"Redis 连接失败，缓存功能将被禁用: {e}")
            self._redis = None

        return self._redis

    def _make_key(self, key: str) -> str:
        """
        生成完整的缓存键

        Args:
            key: 原始键

        Returns:
            带前缀的完整键
        """
        return f"{self.prefix}:{key}"

    async def get(self, key: str) -> Any | None:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，不存在则返回 None
        """
        redis = await self._get_redis()
        if redis is None:
            return None

        try:
            full_key = self._make_key(key)
            value = await redis.get(full_key)

            if value is None:
                return None

            return json.loads(value)

        except json.JSONDecodeError as e:
            logger.warning(f"缓存值 JSON 解析失败: key={key}, error={e}")
            return None
        except Exception as e:
            logger.error(f"获取缓存失败: key={key}, error={e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值（必须可 JSON 序列化）
            ttl: 过期时间（秒），None 则使用默认值

        Returns:
            是否设置成功
        """
        redis = await self._get_redis()
        if redis is None:
            return False

        try:
            full_key = self._make_key(key)
            json_value = json.dumps(value, ensure_ascii=False)
            expire_time = ttl if ttl is not None else self.default_ttl

            await redis.setex(full_key, expire_time, json_value)
            return True

        except (TypeError, ValueError) as e:
            logger.warning(f"缓存值 JSON 序列化失败: key={key}, error={e}")
            return False
        except Exception as e:
            logger.error(f"设置缓存失败: key={key}, error={e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        redis = await self._get_redis()
        if redis is None:
            return False

        try:
            full_key = self._make_key(key)
            await redis.delete(full_key)
            return True

        except Exception as e:
            logger.error(f"删除缓存失败: key={key}, error={e}")
            return False

    async def exists(self, key: str) -> bool:
        """
        检查缓存是否存在

        Args:
            key: 缓存键

        Returns:
            是否存在
        """
        redis = await self._get_redis()
        if redis is None:
            return False

        try:
            full_key = self._make_key(key)
            return await redis.exists(full_key) > 0

        except Exception as e:
            logger.error(f"检查缓存存在失败: key={key}, error={e}")
            return False

    async def get_or_compute(
        self,
        key: str,
        compute_fn: Callable[[], T] | Callable[[], Any],
        ttl: int | None = None,
    ) -> T | Any:
        """
        获取缓存，不存在则计算并缓存

        这是最常用的缓存模式

        Args:
            key: 缓存键
            compute_fn: 计算函数（同步或异步）
            ttl: 过期时间（秒）

        Returns:
            缓存值或计算结果
        """
        # 尝试获取缓存
        cached = await self.get(key)
        if cached is not None:
            logger.debug(f"缓存命中: key={key}")
            return cached

        # 计算结果
        logger.debug(f"缓存未命中，开始计算: key={key}")
        import asyncio

        if asyncio.iscoroutinefunction(compute_fn):
            result = await compute_fn()
        else:
            result = compute_fn()

        # 缓存结果
        await self.set(key, result, ttl)

        return result

    async def close(self) -> None:
        """关闭 Redis 连接"""
        if self._redis is not None:
            await self._redis.close()
            self._redis = None


def hash_problem(problem: str) -> str:
    """
    生成问题的哈希指纹

    用于缓存键生成

    Args:
        problem: 问题文本

    Returns:
        MD5 哈希值
    """
    # 标准化：去除首尾空格，转小写
    normalized = problem.strip().lower()
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


def make_cache_key(*parts: str) -> str:
    """
    生成缓存键

    将多个部分用冒号连接

    Args:
        *parts: 键的各个部分

    Returns:
        完整的缓存键
    """
    return ":".join(str(p) for p in parts if p)


# 全局缓存管理器实例
_solver_cache: CacheManager | None = None
_profile_cache: CacheManager | None = None


def get_solver_cache() -> CacheManager:
    """获取求解器缓存管理器"""
    global _solver_cache
    if _solver_cache is None:
        _solver_cache = CacheManager(prefix="solver", default_ttl=86400)  # 24 小时
    return _solver_cache


def get_profile_cache() -> CacheManager:
    """获取学生画像缓存管理器"""
    global _profile_cache
    if _profile_cache is None:
        _profile_cache = CacheManager(prefix="profile", default_ttl=300)  # 5 分钟
    return _profile_cache
