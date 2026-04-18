"""
请求限流中间件

基于 Redis 的滑动窗口限流，保护 API 免受滥用

特性：
- 支持多种限流策略（IP、用户、全局）
- 滑动窗口算法
- 可配置的限流规则
- 友好的错误响应
"""

import logging
import time

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """限流异常"""

    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after} seconds.")


class RateLimiter:
    """
    限流器

    使用 Redis Lua 脚本实现滑动窗口限流（单次网络往返）

    使用示例：
    ```python
    limiter = RateLimiter(
        requests_per_minute=60,
        requests_per_hour=1000,
    )

    # 检查是否允许请求
    allowed, retry_after = await limiter.is_allowed("user:123")
    if not allowed:
        raise RateLimitExceeded(retry_after)
    ```
    """

    # Lua 脚本：原子化多窗口滑动窗口限流
    # 将 4 个窗口的清理、计数、写入、过期全部合并为 1 次 Redis 调用
    # 返回: [allowed(0/1), retry_after, remaining_burst, remaining_minute, remaining_hour, remaining_day]
    _LUA_SCRIPT = """
    local base_key = KEYS[1]
    local now = tonumber(ARGV[1])
    local num_windows = tonumber(ARGV[2])

    local allowed = 1
    local retry_after = 0
    local remaining = {}

    for i = 1, num_windows do
        local offset = 2 + (i - 1) * 3
        local window_name = ARGV[offset + 1]
        local limit = tonumber(ARGV[offset + 2])
        local window_size = tonumber(ARGV[offset + 3])

        local redis_key = base_key .. ":" .. window_name
        local window_start = now - window_size

        -- 清理过期记录
        redis.call('ZREMRANGEBYSCORE', redis_key, 0, window_start)
        -- 获取当前计数
        local current_count = redis.call('ZCARD', redis_key)

        if current_count >= limit then
            -- 超限：计算 retry_after
            allowed = 0
            local oldest = redis.call('ZRANGE', redis_key, 0, 0, 'WITHSCORES')
            if #oldest >= 2 then
                local oldest_time = tonumber(oldest[2])
                retry_after = math.max(retry_after, math.ceil(oldest_time + window_size - now) + 1)
            else
                retry_after = math.max(retry_after, 1)
            end
            remaining[i] = 0
        else
            -- 未超限：记录请求并设置过期
            redis.call('ZADD', redis_key, now, tostring(now) .. ':' .. tostring(math.random(100000)))
            redis.call('EXPIRE', redis_key, window_size + 1)
            remaining[i] = limit - (current_count + 1)
        end
    end

    -- 如果被拒绝，回滚本次写入（保持幂等）
    if allowed == 0 then
        for i = 1, num_windows do
            local offset = 2 + (i - 1) * 3
            local window_name = ARGV[offset + 1]
            local redis_key = base_key .. ":" .. window_name
            -- 移除刚写入的记录（score == now 的最新一条）
            redis.call('ZREMRANGEBYSCORE', redis_key, now, now + 0.001)
        end
    end

    local result = {allowed, retry_after}
    for i = 1, num_windows do
        result[i + 2] = remaining[i] or 0
    end
    return result
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        requests_per_day: int = 10000,
        burst_limit: int = 10,
    ):
        self.limits = {
            "burst": (burst_limit, 1),
            "minute": (requests_per_minute, 60),
            "hour": (requests_per_hour, 3600),
            "day": (requests_per_day, 86400),
        }
        # 保持有序列表用于 Lua 脚本参数构建
        self._window_order = list(self.limits.keys())
        self._redis = None
        self._lua_sha: str | None = None

    async def _get_redis(self):
        """获取 Redis 连接"""
        if self._redis is None:
            try:
                from app.infrastructure.cache.redis import get_redis, get_redis_pool

                pool = get_redis_pool()
                if pool is not None:
                    self._redis = get_redis()
                    return self._redis
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
            except Exception as e:
                logger.warning(f"Redis 连接失败，限流功能将被禁用: {e}")
                self._redis = None

        return self._redis

    async def _ensure_lua_script(self, redis) -> str:
        """确保 Lua 脚本已加载到 Redis（EVALSHA 避免重复传输脚本体）"""
        if self._lua_sha is None:
            self._lua_sha = await redis.script_load(self._LUA_SCRIPT)
        assert self._lua_sha is not None
        return self._lua_sha

    async def check_and_get_remaining(self, key: str) -> tuple[bool, int, dict[str, int]]:
        """检查限流并返回各窗口剩余配额（单次 Redis 往返）"""
        redis = await self._get_redis()
        if redis is None:
            return True, 0, {name: limit for name, (limit, _) in self.limits.items()}

        now = time.time()

        try:
            sha = await self._ensure_lua_script(redis)

            # 构建 Lua 参数: now, num_windows, [window_name, limit, window_size] * N
            args: list[str | int | float] = [now, len(self._window_order)]
            for window_name in self._window_order:
                limit, window_size = self.limits[window_name]
                args.extend([window_name, limit, window_size])

            base_key = f"ratelimit:{key}"

            try:
                result = await redis.evalsha(sha, 1, base_key, *args)
            except Exception:
                # NOSCRIPT 回退：脚本被清除，重新加载
                self._lua_sha = None
                sha = await self._ensure_lua_script(redis)
                result = await redis.evalsha(sha, 1, base_key, *args)

            allowed = int(result[0]) == 1
            retry_after = int(result[1])

            remaining: dict[str, int] = {}
            for i, window_name in enumerate(self._window_order):
                remaining[window_name] = max(0, int(result[i + 2]))

            if not allowed:
                blocked_window = "unknown"
                for wn in self._window_order:
                    if remaining[wn] == 0:
                        blocked_window = wn
                        break
                logger.warning(
                    "限流触发: key=%s, window=%s, retry_after=%d",
                    key, blocked_window, retry_after,
                )

            return allowed, retry_after, remaining

        except Exception as e:
            logger.error(f"限流检查失败: {e}")
            return True, 0, {name: limit for name, (limit, _) in self.limits.items()}

    async def is_allowed(self, key: str) -> tuple[bool, int]:
        """
        检查请求是否允许

        Args:
            key: 限流键（如 "ip:192.168.1.1" 或 "user:123"）

        Returns:
            (是否允许, 重试等待秒数)
        """
        allowed, retry_after, _ = await self.check_and_get_remaining(key)
        return allowed, retry_after

    async def get_remaining(self, key: str) -> dict[str, int]:
        """获取剩余配额"""
        _, _, remaining = await self.check_and_get_remaining(key)
        return remaining


class RateLimitMiddleware:
    """
    限流中间件（纯 ASGI 实现）

    从 BaseHTTPMiddleware 迁移到纯 ASGI 以避免每请求创建 TaskGroup 的开销。
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        requests_per_day: int = 10000,
        burst_limit: int = 10,
        exclude_paths: list[str] | None = None,
        key_func=None,
    ):
        self.app = app
        self.limiter = RateLimiter(
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour,
            requests_per_day=requests_per_day,
            burst_limit=burst_limit,
        )
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/api/v1/docs", "/api/v1/redoc"]
        self.key_func = key_func

    def _get_client_ip(self, scope) -> str:
        """从 ASGI scope 中提取客户端 IP"""
        # 检查 X-Forwarded-For 头
        headers = dict(scope.get("headers", []))
        forwarded = headers.get(b"x-forwarded-for", b"").decode("utf-8", errors="ignore")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # 检查 X-Real-IP 头
        real_ip = headers.get(b"x-real-ip", b"").decode("utf-8", errors="ignore")
        if real_ip:
            return real_ip

        # 回退到 scope client
        client = scope.get("client")
        if client:
            return client[0]
        return "unknown"

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # 检查是否排除
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            await self.app(scope, receive, send)
            return

        # 获取限流键
        client_ip = self._get_client_ip(scope)
        key = f"rate_limit:{client_ip}"

        # 检查限流
        try:
            allowed, retry_after = await self.limiter.is_allowed(key)
        except Exception:
            # 限流检查失败时放行
            await self.app(scope, receive, send)
            return

        if not allowed:
            # 返回 429 Too Many Requests
            body = b'{"detail":"Too many requests"}'
            headers = [
                (b"content-type", b"application/json"),
                (b"retry-after", str(int(retry_after)).encode()),
            ]
            await send({
                "type": "http.response.start",
                "status": 429,
                "headers": headers,
            })
            await send({
                "type": "http.response.body",
                "body": body,
            })
            return

        await self.app(scope, receive, send)


# AI 接口专用限流器（更严格）
class AIRateLimiter(RateLimiter):
    """
    AI 接口限流器

    针对 AI 相关接口的更严格限流
    """

    def __init__(
        self,
        requests_per_minute: int = 20,  # AI 接口每分钟限制更低
        requests_per_hour: int = 200,
        requests_per_day: int = 2000,
        burst_limit: int = 5,
        concurrent_limit: int = 3,  # 并发请求限制
    ):
        super().__init__(
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour,
            requests_per_day=requests_per_day,
            burst_limit=burst_limit,
        )
        self.concurrent_limit = concurrent_limit

    async def acquire_concurrent(self, key: str) -> bool:
        """
        获取并发槽位

        Args:
            key: 限流键

        Returns:
            是否获取成功
        """
        redis = await self._get_redis()
        if redis is None:
            return True

        try:
            concurrent_key = f"ratelimit:concurrent:{key}"
            current = await redis.incr(concurrent_key)

            if current == 1:
                # 首次设置过期时间（防止泄漏）
                await redis.expire(concurrent_key, 300)

            if current > self.concurrent_limit:
                await redis.decr(concurrent_key)
                logger.warning(f"并发限制触发: key={key}, current={current}")
                return False

            return True

        except Exception as e:
            logger.error(f"并发限制检查失败: {e}")
            return True

    async def release_concurrent(self, key: str) -> None:
        """
        释放并发槽位

        Args:
            key: 限流键
        """
        redis = await self._get_redis()
        if redis is None:
            return

        try:
            concurrent_key = f"ratelimit:concurrent:{key}"
            await redis.decr(concurrent_key)
        except Exception as e:
            logger.error(f"释放并发槽位失败: {e}")


# 全局限流器实例
_global_limiter: RateLimiter | None = None
_ai_limiter: AIRateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """获取全局限流器"""
    global _global_limiter
    if _global_limiter is None:
        from app.config import settings

        _global_limiter = RateLimiter(
            requests_per_minute=getattr(settings, "rate_limit_per_minute", 60),
            requests_per_hour=getattr(settings, "rate_limit_per_hour", 1000),
            requests_per_day=getattr(settings, "rate_limit_per_day", 10000),
        )
    return _global_limiter


def get_ai_rate_limiter() -> AIRateLimiter:
    """获取 AI 接口限流器"""
    global _ai_limiter
    if _ai_limiter is None:
        from app.config import settings

        _ai_limiter = AIRateLimiter(
            requests_per_minute=getattr(settings, "ai_rate_limit_per_minute", 20),
            requests_per_hour=getattr(settings, "ai_rate_limit_per_hour", 200),
            concurrent_limit=getattr(settings, "ai_concurrent_limit", 3),
        )
    return _ai_limiter
