"""
全局异常处理器

统一捕获未处理异常，自动记录安全日志，返回标准化错误响应。
生产环境隐藏内部错误细节，防止信息泄露。
"""

import logging
import traceback
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.log_sanitizer import SanitizeLevel, sanitize_dict, sanitize_text

logger = logging.getLogger(__name__)


async def _log_security_event(
    request: Request,
    event_type: str,
    title: str,
    description: str,
    severity: str = "error",
    extra_data: dict[str, Any] | None = None,
) -> None:
    """
    异步记录安全事件到数据库

    使用独立数据库会话，避免影响请求事务。
    失败时静默降级到日志文件，不影响错误响应。
    """
    try:
        from app.domain.models.security_log import SecurityEventType, SecuritySeverity
        from app.infrastructure.database.session import async_session_factory
        from app.services.security_log_service import SecurityLogService

        # 映射字符串到枚举
        event_type_map = {
            "service_error": SecurityEventType.SERVICE_ERROR,
            "request_error": SecurityEventType.REQUEST_ERROR,
            "request_blocked": SecurityEventType.REQUEST_BLOCKED,
        }
        severity_map = {
            "warning": SecuritySeverity.WARNING,
            "error": SecuritySeverity.ERROR,
            "critical": SecuritySeverity.CRITICAL,
        }

        async with async_session_factory() as session:
            service = SecurityLogService(session)
            # 获取客户端 IP
            ip = request.client.host if request.client else None
            await service.log_event(
                event_type=event_type_map.get(event_type, SecurityEventType.SERVICE_ERROR),
                title=title,
                description=sanitize_text(description, SanitizeLevel.STRICT),
                severity=severity_map.get(severity, SecuritySeverity.ERROR),
                ip_address=ip,
                extra_data=sanitize_dict(extra_data or {}, SanitizeLevel.STRICT),
            )
    except Exception as log_err:
        # 安全日志写入失败时降级到文件日志
        logger.error(f"安全事件记录失败: {log_err}")


def _is_production() -> bool:
    """检查是否为生产环境"""
    try:
        from app.config import settings
        return settings.environment == "production"
    except Exception:
        return True  # 安全兜底


async def _handle_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    """处理未捕获的异常"""
    error_id = id(exc)
    tb = traceback.format_exc()

    # 记录完整堆栈到日志文件
    logger.critical(
        f"未处理异常 [error_id={error_id}] "
        f"{request.method} {request.url.path}: {exc}",
        exc_info=True,
    )

    # 异步记录安全事件
    await _log_security_event(
        request=request,
        event_type="service_error",
        title=f"未处理异常: {type(exc).__name__}",
        description=str(exc)[:500],
        severity="critical",
        extra_data={
            "error_id": str(error_id),
            "method": request.method,
            "path": request.url.path,
            "exception_type": type(exc).__name__,
            "traceback": tb[:2000] if not _is_production() else "[已隐藏]",
        },
    )

    # 触发管理员告警
    try:
        from app.services.alert_service import get_alert_service
        alert_svc = get_alert_service()
        await alert_svc.send_alert(
            level="critical",
            title=f"未处理异常: {type(exc).__name__}",
            message=f"{request.method} {request.url.path}\n{str(exc)[:300]}",
            source="exception_handler",
        )
    except Exception:
        pass  # 告警失败不影响响应

    # 生产环境隐藏内部细节
    if _is_production():
        return JSONResponse(
            status_code=500,
            content={
                "detail": "服务器内部错误，请稍后重试",
                "error_id": str(error_id),
            },
        )
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "error_id": str(error_id),
            "type": type(exc).__name__,
        },
    )


async def _handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """处理 HTTP 异常（4xx/5xx）"""
    # 仅记录服务端错误和可疑的客户端错误
    if exc.status_code >= 500:
        await _log_security_event(
            request=request,
            event_type="service_error",
            title=f"HTTP {exc.status_code} 服务端错误",
            description=str(exc.detail)[:500] if exc.detail else "",
            severity="error",
            extra_data={
                "status_code": exc.status_code,
                "method": request.method,
                "path": request.url.path,
            },
        )
    elif exc.status_code in (401, 403):
        await _log_security_event(
            request=request,
            event_type="request_blocked",
            title=f"HTTP {exc.status_code} 访问拒绝",
            description=str(exc.detail)[:500] if exc.detail else "",
            severity="warning",
            extra_data={
                "status_code": exc.status_code,
                "method": request.method,
                "path": request.url.path,
            },
        )

    detail = exc.detail
    if _is_production() and exc.status_code >= 500:
        detail = "服务器内部错误，请稍后重试"

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": detail},
    )


async def _handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """处理请求参数校验错误"""
    # 记录频繁的校验错误（可能是攻击探测）
    errors = exc.errors()
    logger.warning(
        f"请求校验失败 {request.method} {request.url.path}: "
        f"{len(errors)} 个错误"
    )

    if _is_production():
        # 生产环境简化错误信息，不暴露字段细节
        safe_errors = [
            {"field": ".".join(str(loc) for loc in e.get("loc", [])), "msg": e.get("msg", "")}
            for e in errors
        ]
        return JSONResponse(
            status_code=422,
            content={"detail": "请求参数校验失败", "errors": safe_errors},
        )

    return JSONResponse(
        status_code=422,
        content={"detail": errors},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    注册全局异常处理器

    在应用启动时调用，统一处理所有异常类型。
    """
    app.add_exception_handler(Exception, _handle_unhandled_exception)
    app.add_exception_handler(
        StarletteHTTPException, _handle_http_exception  # type: ignore[arg-type]
    )
    app.add_exception_handler(
        RequestValidationError, _handle_validation_error  # type: ignore[arg-type]
    )
    logger.info("全局异常处理器已注册")
