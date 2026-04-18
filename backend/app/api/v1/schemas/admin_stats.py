"""
管理员统计 API Schema 定义
"""

from datetime import datetime

from pydantic import BaseModel, Field

# =============================================================================
# 趋势数据
# =============================================================================


class TrendData(BaseModel):
    """趋势数据"""

    users_change: float = Field(description="用户数变化百分比")
    students_change: float = Field(description="学生数变化百分比")
    teachers_change: float = Field(description="教师数变化百分比")
    active_rate_change: float = Field(description="活跃率变化百分比")


# =============================================================================
# 概览统计
# =============================================================================


class OverviewStatsResponse(BaseModel):
    """概览统计响应"""

    total_users: int = Field(description="总用户数")
    student_count: int = Field(description="学生数量")
    teacher_count: int = Field(description="教师数量")
    admin_count: int = Field(description="管理员数量")
    active_users_today: int = Field(description="今日活跃用户数")
    active_rate: float = Field(description="活跃率（百分比）")
    trends: TrendData = Field(description="趋势数据")


# =============================================================================
# 用户增长
# =============================================================================


class UserGrowthDataPoint(BaseModel):
    """用户增长数据点"""

    date: str = Field(description="日期 (YYYY-MM-DD)")
    total: int = Field(description="累计总用户数")
    students: int = Field(description="累计学生数")
    teachers: int = Field(description="累计教师数")


class UserGrowthSummary(BaseModel):
    """用户增长摘要"""

    total_new_users: int = Field(description="期间新增用户总数")
    avg_daily_growth: float = Field(description="日均增长数")


class UserGrowthResponse(BaseModel):
    """用户增长响应"""

    period: str = Field(description="统计周期 (7d/30d/90d)")
    data: list[UserGrowthDataPoint] = Field(description="增长数据点列表")
    summary: UserGrowthSummary = Field(description="增长摘要")


# =============================================================================
# 最近活动
# =============================================================================


class ActivityItem(BaseModel):
    """活动项"""

    id: str = Field(description="活动 ID")
    user_name: str = Field(description="用户名")
    action_display: str = Field(description="操作描述")
    timestamp: datetime = Field(description="时间戳")
    type: str = Field(description="活动类型 (success/info/warning)")


class RecentActivitiesResponse(BaseModel):
    """最近活动响应"""

    items: list[ActivityItem] = Field(description="活动列表")
    total: int = Field(description="总数")


# =============================================================================
# 系统状态
# =============================================================================


class ServiceStatus(BaseModel):
    """服务状态"""

    name: str = Field(description="服务名称")
    status: str = Field(description="状态 (running/stopped/warning)")
    latency_ms: float | None = Field(default=None, description="延迟（毫秒）")


class SystemAlert(BaseModel):
    """系统警告"""

    id: str = Field(description="警告 ID")
    title: str = Field(description="标题")
    description: str = Field(description="描述")
    severity: str = Field(description="严重程度 (error/warning/info)")


class SystemStatusResponse(BaseModel):
    """系统状态响应"""

    services: list[ServiceStatus] = Field(description="服务状态列表")
    alerts: list[SystemAlert] = Field(description="系统警告列表")
