"""
Prometheus 指标中间件

收集应用性能指标，支持 Prometheus 监控

特性：
- 请求计数和延迟
- 活跃连接数
- 自定义业务指标
- /metrics 端点
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# 尝试导入 prometheus_client，不可用时使用模拟实现
try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        Info,
        generate_latest,
        multiprocess,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # 定义占位符以满足类型检查
    Counter: Any = None
    Gauge: Any = None
    Histogram: Any = None
    Info: Any = None
    generate_latest: Any = None
    CONTENT_TYPE_LATEST: Any = None
    CollectorRegistry: Any = None
    multiprocess: Any = None
    logger.warning("prometheus_client 未安装，指标功能将被禁用")


# ========== 指标定义 ==========

if PROMETHEUS_AVAILABLE:
    # 请求计数器
    REQUEST_COUNT = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status_code"],
    )

    # 请求延迟直方图
    REQUEST_LATENCY = Histogram(
        "http_request_duration_seconds",
        "HTTP request latency in seconds",
        ["method", "endpoint"],
        buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
    )

    # 活跃请求数
    ACTIVE_REQUESTS = Gauge(
        "http_requests_active",
        "Number of active HTTP requests",
        ["method", "endpoint"],
    )

    # LLM 请求指标
    LLM_REQUEST_COUNT = Counter(
        "llm_requests_total",
        "Total LLM API requests",
        ["provider", "model", "status"],
    )

    LLM_REQUEST_LATENCY = Histogram(
        "llm_request_duration_seconds",
        "LLM API request latency in seconds",
        ["provider", "model"],
        buckets=(0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 15.0, 30.0, 60.0),
    )

    LLM_TOKENS_TOTAL = Counter(
        "llm_tokens_total",
        "Total LLM tokens used",
        ["provider", "model", "type"],  # type: input/output
    )

    # 智能体指标
    AGENT_INVOCATIONS = Counter(
        "agent_invocations_total",
        "Total agent invocations",
        ["agent_type", "status"],
    )

    AGENT_LATENCY = Histogram(
        "agent_duration_seconds",
        "Agent processing latency in seconds",
        ["agent_type"],
        buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
    )

    # 队列指标
    QUEUE_SIZE = Gauge(
        "llm_queue_size",
        "Current LLM request queue size",
        ["queue_name"],
    )

    QUEUE_WAIT_TIME = Histogram(
        "llm_queue_wait_seconds",
        "Time spent waiting in queue",
        ["queue_name"],
        buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
    )

    # 数据库连接池指标
    DB_POOL_SIZE = Gauge(
        "db_pool_connections",
        "Database connection pool size",
        ["state"],  # active, idle, overflow
    )

    # Redis 连接指标
    REDIS_CONNECTIONS = Gauge(
        "redis_connections",
        "Redis connection count",
        ["state"],
    )

    # ========== Phase 0: 性能基线指标 ==========

    # SymPy 等价性检查指标
    SYMPY_CHECK_DURATION = Histogram(
        "sympy_check_duration_seconds",
        "SymPy equivalence check latency in seconds",
        ["layer"],  # symbolic, numeric, parse
        buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0),
    )

    SYMPY_CHECK_LAYER = Counter(
        "sympy_check_layer_total",
        "Equivalence check layer hit count",
        ["layer", "result"],  # layer: exact/normalized/symbolic/numeric/llm, result: hit/miss
    )

    # BKT 更新指标
    BKT_UPDATE_DURATION = Histogram(
        "bkt_update_duration_seconds",
        "BKT state update latency in seconds",
        ["operation"],  # get_mastery/update_after_attempt
        buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
    )

    # 缓存命中率指标
    CACHE_OPERATIONS = Counter(
        "cache_operations_total",
        "Cache hit/miss count",
        ["cache_name", "operation"],  # cache_name: profile/exercise/bkt_state/api, operation: hit/miss
    )

    # DB 连接持有时间指标
    DB_SESSION_HOLD_DURATION = Histogram(
        "db_session_hold_duration_seconds",
        "Database session hold duration in seconds",
        buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
    )

    # 应用信息
    APP_INFO = Info(
        "app",
        "Application information",
    )


class MetricsMiddleware:
    """
    指标收集中间件（纯 ASGI 实现）

    自动收集 HTTP 请求指标。
    从 BaseHTTPMiddleware 迁移到纯 ASGI 以避免每请求创建 TaskGroup 的开销。
    """

    def __init__(
        self,
        app,
        exclude_paths: list[str] | None = None,
    ):
        self.app = app
        self.exclude_paths = exclude_paths or ["/metrics", "/health"]

    def _normalize_path(self, path: str) -> str:
        """标准化路径（移除动态参数）"""
        parts = path.split("/")
        normalized = []
        for part in parts:
            if part and (part.isdigit() or len(part) == 36 and "-" in part):
                normalized.append("{id}")
            else:
                normalized.append(part)
        return "/".join(normalized)

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or not PROMETHEUS_AVAILABLE:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # 检查是否排除
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET")
        endpoint = self._normalize_path(path)

        # 记录活跃请求
        ACTIVE_REQUESTS.labels(method=method, endpoint=endpoint).inc()

        start_time = time.time()
        status_code = 500

        async def send_with_metrics(message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 500)
            await send(message)

        try:
            await self.app(scope, receive, send_with_metrics)
        finally:
            latency = time.time() - start_time
            REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(latency)
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
            ).inc()
            ACTIVE_REQUESTS.labels(method=method, endpoint=endpoint).dec()


def get_metrics() -> bytes:
    """
    获取 Prometheus 指标

    Returns:
        指标数据（Prometheus 格式）
    """
    if not PROMETHEUS_AVAILABLE:
        return b"# prometheus_client not installed\n"

    return generate_latest()


def get_metrics_content_type() -> str:
    """获取指标内容类型"""
    if not PROMETHEUS_AVAILABLE:
        return "text/plain"
    return CONTENT_TYPE_LATEST


# ========== 业务指标记录函数 ==========


def record_llm_request(
    provider: str,
    model: str,
    status: str,
    latency_seconds: float,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> None:
    """
    记录 LLM 请求指标

    Args:
        provider: 提供商
        model: 模型名称
        status: 状态 (success/error/timeout)
        latency_seconds: 延迟（秒）
        input_tokens: 输入 token 数
        output_tokens: 输出 token 数
    """
    if not PROMETHEUS_AVAILABLE:
        return

    LLM_REQUEST_COUNT.labels(provider=provider, model=model, status=status).inc()
    LLM_REQUEST_LATENCY.labels(provider=provider, model=model).observe(latency_seconds)

    if input_tokens > 0:
        LLM_TOKENS_TOTAL.labels(provider=provider, model=model, type="input").inc(input_tokens)
    if output_tokens > 0:
        LLM_TOKENS_TOTAL.labels(provider=provider, model=model, type="output").inc(output_tokens)


def record_agent_invocation(
    agent_type: str,
    status: str,
    latency_seconds: float,
) -> None:
    """
    记录智能体调用指标

    Args:
        agent_type: 智能体类型
        status: 状态 (success/error)
        latency_seconds: 延迟（秒）
    """
    if not PROMETHEUS_AVAILABLE:
        return

    AGENT_INVOCATIONS.labels(agent_type=agent_type, status=status).inc()
    AGENT_LATENCY.labels(agent_type=agent_type).observe(latency_seconds)


def record_queue_metrics(
    queue_name: str,
    queue_size: int,
    wait_time_seconds: float | None = None,
) -> None:
    """
    记录队列指标

    Args:
        queue_name: 队列名称
        queue_size: 队列大小
        wait_time_seconds: 等待时间（秒）
    """
    if not PROMETHEUS_AVAILABLE:
        return

    QUEUE_SIZE.labels(queue_name=queue_name).set(queue_size)
    if wait_time_seconds is not None:
        QUEUE_WAIT_TIME.labels(queue_name=queue_name).observe(wait_time_seconds)


def record_db_pool_metrics(
    active: int,
    idle: int,
    overflow: int,
) -> None:
    """
    记录数据库连接池指标

    Args:
        active: 活跃连接数
        idle: 空闲连接数
        overflow: 溢出连接数
    """
    if not PROMETHEUS_AVAILABLE:
        return

    DB_POOL_SIZE.labels(state="active").set(active)
    DB_POOL_SIZE.labels(state="idle").set(idle)
    DB_POOL_SIZE.labels(state="overflow").set(overflow)


def record_redis_metrics(
    active: int,
    idle: int,
) -> None:
    """
    记录 Redis 连接指标

    Args:
        active: 活跃连接数
        idle: 空闲连接数
    """
    if not PROMETHEUS_AVAILABLE:
        return

    REDIS_CONNECTIONS.labels(state="active").set(active)
    REDIS_CONNECTIONS.labels(state="idle").set(idle)


def record_sympy_check(
    layer: str,
    duration_seconds: float,
    result: str = "hit",
) -> None:
    """
    记录 SymPy 等价性检查指标

    Args:
        layer: 验证层 (exact/normalized/symbolic/numeric/llm)
        duration_seconds: 延迟（秒）
        result: 结果 (hit/miss)
    """
    if not PROMETHEUS_AVAILABLE:
        return

    SYMPY_CHECK_DURATION.labels(layer=layer).observe(duration_seconds)
    SYMPY_CHECK_LAYER.labels(layer=layer, result=result).inc()


def record_bkt_update(
    operation: str,
    duration_seconds: float,
) -> None:
    """
    记录 BKT 更新指标

    Args:
        operation: 操作类型 (get_mastery/update_after_attempt)
        duration_seconds: 延迟（秒）
    """
    if not PROMETHEUS_AVAILABLE:
        return

    BKT_UPDATE_DURATION.labels(operation=operation).observe(duration_seconds)


def record_cache_operation(
    cache_name: str,
    operation: str,
) -> None:
    """
    记录缓存操作指标

    Args:
        cache_name: 缓存名称 (profile/exercise/bkt_state/api)
        operation: 操作 (hit/miss)
    """
    if not PROMETHEUS_AVAILABLE:
        return

    CACHE_OPERATIONS.labels(cache_name=cache_name, operation=operation).inc()


def record_db_session_hold(duration_seconds: float) -> None:
    """
    记录 DB 连接持有时间

    Args:
        duration_seconds: 持有时间（秒）
    """
    if not PROMETHEUS_AVAILABLE:
        return

    DB_SESSION_HOLD_DURATION.observe(duration_seconds)


def set_app_info(
    version: str,
    environment: str,
    **extra: str,
) -> None:
    """
    设置应用信息

    Args:
        version: 版本号
        environment: 环境
        **extra: 额外信息
    """
    if not PROMETHEUS_AVAILABLE:
        return

    APP_INFO.info({
        "version": version,
        "environment": environment,
        **extra,
    })
