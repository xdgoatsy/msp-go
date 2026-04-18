"""
管理员统计 API 路由

提供管理员控制台所需的统计数据接口
"""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import AdminUserId, DbSession
from app.api.v1.schemas.admin_stats import (
    OverviewStatsResponse,
    RecentActivitiesResponse,
    SystemStatusResponse,
    UserGrowthResponse,
)
from app.services.admin_stats_service import get_admin_stats_service

router = APIRouter()


@router.get("/overview", response_model=OverviewStatsResponse)
async def get_overview_stats(
    db: DbSession,
    _current_user: AdminUserId,
):
    """
    获取概览统计数据

    返回用户总数、各角色数量、活跃度和趋势数据
    """
    service = get_admin_stats_service(db)
    return await service.get_overview_stats()


@router.get("/user-growth", response_model=UserGrowthResponse)
async def get_user_growth(
    db: DbSession,
    _current_user: AdminUserId,
    period: Annotated[
        str,
        Query(pattern="^(7d|30d|90d)$", description="统计周期"),
    ] = "30d",
):
    """
    获取用户增长趋势数据

    Args:
        period: 统计周期 (7d/30d/90d)

    返回指定周期内的用户增长数据点和摘要
    """
    service = get_admin_stats_service(db)
    return await service.get_user_growth(period)


@router.get("/recent-activities", response_model=RecentActivitiesResponse)
async def get_recent_activities(
    db: DbSession,
    _current_user: AdminUserId,
    limit: Annotated[int, Query(ge=1, le=50, description="返回数量")] = 10,
):
    """
    获取最近活动列表

    Args:
        limit: 返回数量限制 (1-50)

    返回最近的用户活动记录
    """
    service = get_admin_stats_service(db)
    return await service.get_recent_activities(limit)


@router.get("/system-status", response_model=SystemStatusResponse)
async def get_system_status(
    db: DbSession,
    _current_user: AdminUserId,
):
    """
    获取系统状态

    返回服务状态、资源使用情况和系统警告
    """
    service = get_admin_stats_service(db)
    return await service.get_system_status()
