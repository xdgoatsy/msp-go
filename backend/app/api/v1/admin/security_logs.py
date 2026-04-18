"""
安全日志 API 路由

提供安全日志的查询、删除、导出和归档接口
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import AdminUserId, DbSession
from app.api.v1.schemas.security_log import (
    SecurityLogArchiveRequest,
    SecurityLogArchiveResponse,
    SecurityLogDeleteRequest,
    SecurityLogExportRequest,
    SecurityLogExportResponse,
    SecurityLogListResponse,
    SecurityLogStatsResponse,
)
from app.domain.models.security_log import SecurityEventType, SecuritySeverity
from app.services.security_log_service import get_security_log_service

router = APIRouter()


@router.get("", response_model=SecurityLogListResponse)
async def get_security_logs(
    db: DbSession,
    _current_user: AdminUserId,
    event_types: Annotated[
        list[SecurityEventType] | None,
        Query(description="事件类型筛选"),
    ] = None,
    severities: Annotated[
        list[SecuritySeverity] | None,
        Query(description="严重程度筛选"),
    ] = None,
    start_date: Annotated[
        datetime | None,
        Query(description="开始日期"),
    ] = None,
    end_date: Annotated[
        datetime | None,
        Query(description="结束日期"),
    ] = None,
    include_archived: Annotated[
        bool,
        Query(description="是否包含已归档日志"),
    ] = False,
    page: Annotated[
        int,
        Query(ge=1, description="页码"),
    ] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=100, description="每页数量"),
    ] = 50,
):
    """
    获取安全日志列表

    返回按日期分组的安全日志，支持筛选和分页
    """
    service = get_security_log_service(db)
    return await service.get_logs(
        event_types=event_types,
        severities=severities,
        start_date=start_date,
        end_date=end_date,
        include_archived=include_archived,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=SecurityLogStatsResponse)
async def get_security_log_stats(
    db: DbSession,
    _current_user: AdminUserId,
):
    """
    获取安全日志统计

    返回日志总数、各级别数量和最近事件时间
    """
    service = get_security_log_service(db)
    return await service.get_stats()


@router.delete("")
async def delete_security_logs(
    request: SecurityLogDeleteRequest,
    db: DbSession,
    _current_user: AdminUserId,
):
    """
    删除安全日志

    支持按 ID 列表删除、按日期删除或删除全部
    """
    service = get_security_log_service(db)
    deleted_count = await service.delete_logs(
        log_ids=request.log_ids,
        before_date=request.before_date,
        delete_all=request.delete_all,
    )
    return {"deleted_count": deleted_count}


@router.post("/export", response_model=SecurityLogExportResponse)
async def export_security_logs(
    request: SecurityLogExportRequest,
    db: DbSession,
    _current_user: AdminUserId,
):
    """
    导出安全日志

    支持导出为 JSON 或 CSV 格式
    """
    service = get_security_log_service(db)
    return await service.export_logs(
        format=request.format,
        event_types=request.event_types,
        severities=request.severities,
        start_date=request.start_date,
        end_date=request.end_date,
        include_archived=request.include_archived,
    )


@router.post("/archive", response_model=SecurityLogArchiveResponse)
async def archive_security_logs(
    request: SecurityLogArchiveRequest,
    db: DbSession,
    _current_user: AdminUserId,
):
    """
    归档安全日志

    将指定日期之前的日志标记为已归档
    """
    service = get_security_log_service(db)
    archived_count = await service.archive_logs(before_date=request.before_date)
    return {"archived_count": archived_count}


@router.post("/generate-daily-report")
async def generate_daily_report(
    db: DbSession,
    _current_user: AdminUserId,
):
    """
    手动生成每日安全报告

    如果当天没有异常且尚未生成报告，则生成一条"系统安全"报告
    """
    service = get_security_log_service(db)
    report = await service.generate_daily_report()

    if report:
        return {"generated": True, "report_id": report.id}
    else:
        return {"generated": False, "message": "今日已有报告或存在异常事件"}


@router.post("/cleanup")
async def cleanup_security_logs(
    db: DbSession,
    _current_user: AdminUserId,
):
    """
    手动触发日志清理

    执行归档过期日志 + 删除过期归档日志 + 检查日志总量
    """
    from app.services.log_cleanup_service import get_log_cleanup_service

    service = get_log_cleanup_service(db)
    result = await service.run_full_cleanup()
    return result


@router.get("/volume")
async def get_log_volume(
    db: DbSession,
    _current_user: AdminUserId,
):
    """
    获取日志总量信息

    返回活跃日志数、归档日志数、总数和是否超限
    """
    from app.services.log_cleanup_service import get_log_cleanup_service

    service = get_log_cleanup_service(db)
    return await service.check_log_volume()
