"""
弹性工程模块 - 断路器 + 重试装饰器

提供生产级的容错机制：
- CircuitBreaker: 防止级联故障，快速失败
- retry_with_backoff: 指数退避重试装饰器
"""

import asyncio
import functools
import logging
import time
from collections.abc import Callable
from enum import Enum
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


# ========== 断路器 ==========


class CircuitState(str, Enum):
    CLOSED = "closed"        # 正常状态，请求通过
    OPEN = "open"            # 熔断状态，快速失败
    HALF_OPEN = "half_open"  # 半开状态，允许探测请求


class CircuitBreakerError(Exception):
    """断路器打开时抛出"""

    def __init__(self, name: str, retry_after: float):
        self.name = name
        self.retry_after = retry_after
        super().__init__(f"断路器 '{name}' 已打开，{retry_after:.0f}s 后重试")


class CircuitBreaker:
    """
    断路器

    状态转换：
    CLOSED → (连续失败 >= threshold) → OPEN
    OPEN → (等待 recovery_timeout) → HALF_OPEN
    HALF_OPEN → (探测成功) → CLOSED
    HALF_OPEN → (探测失败) → OPEN

    用法：
        breaker = CircuitBreaker("llm_api", failure_threshold=5)

        async def call_llm():
            async with breaker:
                return await llm_client.chat(...)
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 1,
        excluded_exceptions: tuple[type[Exception], ...] | None = None,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.excluded_exceptions = excluded_exceptions or ()

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """当前状态（自动检测 OPEN→HALF_OPEN 转换）"""
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                return CircuitState.HALF_OPEN
        return self._state

    async def __aenter__(self) -> "CircuitBreaker":
        async with self._lock:
            current = self.state
            if current == CircuitState.OPEN:
                retry_after = self.recovery_timeout - (time.monotonic() - self._last_failure_time)
                raise CircuitBreakerError(self.name, max(0, retry_after))
            if current == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    raise CircuitBreakerError(self.name, self.recovery_timeout)
                self._half_open_calls += 1
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is None:
            await self._on_success()
        elif exc_type and not issubclass(exc_type, self.excluded_exceptions):
            await self._on_failure()
        return False

    async def _on_success(self) -> None:
        async with self._lock:
            if self._state in (CircuitState.HALF_OPEN, CircuitState.OPEN):
                logger.info("断路器 '%s' 恢复: %s → CLOSED", self.name, self._state.value)
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._half_open_calls = 0

    async def _on_failure(self) -> None:
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._half_open_calls = 0
                logger.warning("断路器 '%s' 探测失败: HALF_OPEN → OPEN", self.name)
            elif self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    "断路器 '%s' 熔断: 连续失败 %d 次, CLOSED → OPEN",
                    self.name, self._failure_count,
                )

    def reset(self) -> None:
        """手动重置断路器"""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_calls = 0


# ========== 重试装饰器 ==========


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """
    指数退避重试装饰器

    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）
        exponential_base: 指数基数
        retryable_exceptions: 可重试的异常类型
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Exception | None = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        break
                    delay = min(base_delay * (exponential_base ** attempt), max_delay)
                    logger.warning(
                        "重试 %s (第 %d/%d 次, %.1fs 后): %s",
                        func.__name__, attempt + 1, max_retries, delay, e,
                    )
                    await asyncio.sleep(delay)
            raise last_exception  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    return decorator


# ========== 全局断路器注册表 ==========

_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
) -> CircuitBreaker:
    """获取或创建命名断路器（单例）"""
    if name not in _breakers:
        _breakers[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )
    return _breakers[name]
