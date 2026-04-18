"""
进程内 LRU 缓存层 (L1 Cache)

在 Redis (L2) 之前提供零网络开销的内存缓存，适用于：
- 高频读取、低频变更的热数据（学生画像、题目详情等）
- 短 TTL 容忍最终一致性的场景

特性：
- 基于 Python 标准库 functools.lru_cache 思路，使用 OrderedDict 实现
- 支持 TTL 自动过期
- 支持最大容量限制（LRU 淘汰）
- 线程安全（asyncio 单线程模型下天然安全）
- 支持手动失效和批量清除
"""

import time
from collections import OrderedDict
from typing import Any

from app.config import settings
from app.core.middleware.metrics import record_cache_operation


class TTLCache:
    """
    带 TTL 的 LRU 缓存

    使用示例：
    ```python
    cache = TTLCache(maxsize=1000, ttl=300)  # 最多 1000 条，5 分钟过期

    cache.set("user:123", {"name": "张三"})
    result = cache.get("user:123")  # 命中返回值，未命中返回 None

    cache.delete("user:123")  # 手动失效
    cache.clear()  # 清空
    ```
    """

    __slots__ = ("_maxsize", "_ttl", "_cache", "_timestamps", "_hits", "_misses", "_name")

    def __init__(self, maxsize: int = 1024, ttl: float = 300.0, name: str = "default"):
        """
        Args:
            maxsize: 最大缓存条目数
            ttl: 默认过期时间（秒）
            name: 缓存实例名称（用于 Prometheus 标签）
        """
        self._maxsize = maxsize
        self._ttl = ttl
        self._name = name
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._timestamps: dict[str, float] = {}
        # 统计
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Any | None:
        """获取缓存值，未命中或过期返回 None"""
        if key not in self._cache:
            self._misses += 1
            record_cache_operation(self._name, "miss")
            return None

        # 检查过期
        ts = self._timestamps.get(key, 0)
        if time.monotonic() - ts > self._ttl:
            # 过期，删除
            self._cache.pop(key, None)
            self._timestamps.pop(key, None)
            self._misses += 1
            record_cache_operation(self._name, "miss")
            return None

        # 命中，移到末尾（最近使用）
        self._cache.move_to_end(key)
        self._hits += 1
        record_cache_operation(self._name, "hit")
        return self._cache[key]

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """设置缓存值"""
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            # 容量检查，淘汰最久未使用的
            while len(self._cache) >= self._maxsize:
                oldest_key, _ = self._cache.popitem(last=False)
                self._timestamps.pop(oldest_key, None)

        self._cache[key] = value
        self._timestamps[key] = time.monotonic()

    def delete(self, key: str) -> bool:
        """删除缓存条目"""
        if key in self._cache:
            del self._cache[key]
            self._timestamps.pop(key, None)
            return True
        return False

    def clear(self) -> None:
        """清空所有缓存"""
        self._cache.clear()
        self._timestamps.clear()

    def invalidate_prefix(self, prefix: str) -> int:
        """按前缀批量失效"""
        keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
        for k in keys_to_delete:
            del self._cache[k]
            self._timestamps.pop(k, None)
        return len(keys_to_delete)

    @property
    def stats(self) -> dict[str, Any]:
        """缓存统计信息"""
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "maxsize": self._maxsize,
            "ttl": self._ttl,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total, 4) if total > 0 else 0,
        }

    def __len__(self) -> int:
        return len(self._cache)

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None


# ========== 全局缓存实例 ==========

# 学生画像缓存：短 TTL，高频读取
profile_cache = TTLCache(
    maxsize=settings.profile_cache_maxsize,
    ttl=float(settings.profile_cache_ttl_seconds),
    name="profile",
)

# 题目详情缓存：较长 TTL，题目不常变
exercise_cache = TTLCache(
    maxsize=settings.exercise_cache_maxsize,
    ttl=float(settings.exercise_cache_ttl_seconds),
    name="exercise",
)

# BKT 状态缓存：短 TTL，降低高频掌握度查询开销
bkt_state_cache = TTLCache(
    maxsize=settings.bkt_state_cache_maxsize,
    ttl=float(settings.bkt_state_cache_ttl_seconds),
    name="bkt_state",
)

# 通用 API 响应缓存：极短 TTL，防止瞬时重复请求
api_cache = TTLCache(
    maxsize=settings.api_cache_maxsize,
    ttl=float(settings.api_cache_ttl_seconds),
    name="api",
)
