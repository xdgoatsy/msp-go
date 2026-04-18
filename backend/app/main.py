"""
FastAPI 应用入口

创建和配置 FastAPI 应用实例。
集成安全头、超时、限流、监控等中间件。
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from app.api.deps import DbSession
from app.api.v1.router import api_router
from app.config import settings, validate_production_settings

# 尽早安装日志脱敏过滤器（在任何日志输出之前）
from app.core.log_sanitizer import install_log_sanitizer
from app.infrastructure.cache.redis import close_redis, init_redis
from app.infrastructure.database.session import async_session_factory, close_db, init_db
from app.services.auth_service import AuthService

install_log_sanitizer()

# 生产环境安全配置校验
validate_production_settings()

logger = logging.getLogger(__name__)


async def _log_cleanup_loop() -> None:
    """日志自动清理后台循环（带指数退避）"""
    interval = settings.log_cleanup_interval_hours * 3600
    fail_count = 0
    max_backoff = 3600  # 最大退避 1 小时
    while True:
        try:
            wait_time = interval if fail_count == 0 else min(interval * (2 ** fail_count), max_backoff)
            await asyncio.sleep(wait_time)
            from app.services.log_cleanup_service import run_scheduled_cleanup
            result = await run_scheduled_cleanup()
            logger.info(f"定时日志清理完成: {result}")
            fail_count = 0
        except asyncio.CancelledError:
            break
        except Exception as e:
            fail_count += 1
            logger.error(f"定时日志清理失败 (连续第 {fail_count} 次): {e}")


async def _pool_monitor_loop() -> None:
    """连接池监控后台循环（按配置间隔采集）"""
    while True:
        try:
            await asyncio.sleep(settings.db_pool_monitor_interval_seconds)
            from app.core.middleware.metrics import record_db_pool_metrics
            from app.infrastructure.database.session import get_pool_status
            status = get_pool_status()
            record_db_pool_metrics(
                active=status["checked_out"],
                idle=status["checked_in"],
                overflow=status["overflow"],
            )
        except asyncio.CancelledError:
            break
        except Exception:
            pass  # 监控失败不影响业务


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理"""
    # 启动时初始化
    await init_db()
    await init_redis()

    # 初始化管理员账户
    async with async_session_factory() as session:
        auth_service = AuthService(session)
        await auth_service.init_admin()
        await session.commit()

    # 设置应用信息（Prometheus 指标）
    if settings.metrics_enabled:
        try:
            from app.core.middleware.metrics import set_app_info
            set_app_info(
                version=settings.app_version,
                environment=settings.environment,
            )
        except Exception as e:
            logger.warning(f"设置应用指标信息失败: {e}")

    # 预热 LLM 客户端池
    if settings.llm_pool_warmup_enabled:
        try:
            from app.agents.core.llm_client import init_llm_client_pool_from_config
            await init_llm_client_pool_from_config()
            logger.info("LLM 客户端池预热完成")
        except Exception as e:
            logger.warning(f"LLM 客户端池预热失败: {e}")
    else:
        logger.info("LLM 客户端池预热已关闭")

    # 启动日志自动清理后台任务
    cleanup_task = None
    if settings.log_cleanup_enabled and settings.log_cleanup_interval_hours > 0:
        cleanup_task = asyncio.create_task(_log_cleanup_loop())
        logger.info(
            f"日志自动清理已启用，间隔 {settings.log_cleanup_interval_hours} 小时"
        )

    logger.info(f"应用启动完成: {settings.app_name} v{settings.app_version}")

    # 启动连接池监控后台任务
    pool_monitor_task = None
    if settings.metrics_enabled and settings.db_pool_monitor_enabled:
        pool_monitor_task = asyncio.create_task(_pool_monitor_loop())

    yield

    # 关闭时清理
    if pool_monitor_task and not pool_monitor_task.done():
        pool_monitor_task.cancel()
        try:
            await pool_monitor_task
        except asyncio.CancelledError:
            pass
    if cleanup_task and not cleanup_task.done():
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass

    await close_redis()
    await close_db()
    logger.info("应用关闭完成")


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""
    # 生产环境禁用 OpenAPI 文档
    is_prod = settings.environment == "production"

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="基于多智能体协作与深度知识追踪的高等数学教育平台",
        openapi_url=None if is_prod else f"{settings.api_v1_prefix}/openapi.json",
        docs_url=None if is_prod else f"{settings.api_v1_prefix}/docs",
        redoc_url=None if is_prod else f"{settings.api_v1_prefix}/redoc",
        lifespan=lifespan,
    )

    # === 纯 ASGI 中间件（高性能，无 BaseHTTPMiddleware 开销） ===

    # 请求 ID 中间件（最外层，确保所有日志都能关联请求 ID）
    from app.core.middleware.request_id import RequestIDMiddleware
    app.add_middleware(RequestIDMiddleware)

    # 请求超时中间件
    try:
        from app.core.middleware.timeout import TimeoutMiddleware
        app.add_middleware(
            TimeoutMiddleware,
            default_timeout=settings.request_timeout_default,
            path_timeouts={
                "/api/v1/session": settings.request_timeout_ai,
                "/api/v1/exercise/ai": 120.0,
            },
        )
        logger.info("请求超时中间件已启用")
    except Exception as e:
        logger.warning(f"请求超时中间件启用失败: {e}")

    # 安全响应头中间件
    try:
        from app.core.middleware.security_headers import SecurityHeadersMiddleware
        app.add_middleware(
            SecurityHeadersMiddleware,
            exclude_paths=["/health", "/metrics"],
        )
        logger.info("安全响应头中间件已启用")
    except Exception as e:
        logger.warning(f"安全响应头中间件启用失败: {e}")

    # GZip 压缩
    app.add_middleware(GZipMiddleware, minimum_size=500)

    # CORS（使用精确的方法和头白名单）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # 限流中间件
    if settings.rate_limit_enabled:
        try:
            from app.core.middleware.rate_limit import RateLimitMiddleware
            app.add_middleware(
                RateLimitMiddleware,
                requests_per_minute=settings.rate_limit_per_minute,
                requests_per_hour=settings.rate_limit_per_hour,
                requests_per_day=settings.rate_limit_per_day,
                burst_limit=settings.rate_limit_burst,
                exclude_paths=["/health", "/metrics", f"{settings.api_v1_prefix}/docs", f"{settings.api_v1_prefix}/redoc"],
            )
            logger.info("限流中间件已启用")
        except Exception as e:
            logger.warning(f"限流中间件启用失败: {e}")

    # 指标中间件
    if settings.metrics_enabled:
        try:
            from app.core.middleware.metrics import MetricsMiddleware
            app.add_middleware(
                MetricsMiddleware,
                exclude_paths=["/metrics", "/health"],
            )
            logger.info("指标中间件已启用")
        except Exception as e:
            logger.warning(f"指标中间件启用失败: {e}")

    # 注册全局异常处理器
    from app.core.exception_handlers import register_exception_handlers
    register_exception_handlers(app)

    # 注册路由
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    # 挂载静态文件目录 (用于图片上传)
    uploads_dir = Path(__file__).parent.parent / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

    return app


app = create_app()


@app.get("/health", tags=["健康检查"])
async def health_check() -> dict[str, str]:
    """简单健康检查端点"""
    return {"status": "healthy", "version": settings.app_version}


@app.get("/health/detailed", tags=["健康检查"])
async def health_check_detailed(db: DbSession) -> dict:
    """详细健康检查端点"""
    from app.services.health_checker import get_health_check_service

    service = get_health_check_service(db)
    return await service.get_detailed_status()


@app.get("/metrics", tags=["监控"])
async def metrics() -> Response:
    """Prometheus 指标端点"""
    from app.core.middleware.metrics import get_metrics, get_metrics_content_type

    return Response(
        content=get_metrics(),
        media_type=get_metrics_content_type(),
    )
