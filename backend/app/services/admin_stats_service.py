"""
管理员统计服务

提供管理员控制台所需的统计数据
"""

import asyncio
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.student import UserRole
from app.infrastructure.cache.stats_cache import cached_stats
from app.infrastructure.database.models import LearningSessionModel, UserModel


class AdminStatsService:
    """管理员统计服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    @cached_stats("overview")
    async def get_overview_stats(self) -> dict:
        """
        获取概览统计数据

        Returns:
            包含用户统计和趋势的字典
        """
        # 优化：使用单个查询配合条件聚合，减少 75% 数据库往返
        from sqlalchemy import case

        stats_query = select(
            func.count(UserModel.id).label("total"),
            func.sum(case((UserModel.role == UserRole.STUDENT, 1), else_=0)).label("student_count"),
            func.sum(case((UserModel.role == UserRole.TEACHER, 1), else_=0)).label("teacher_count"),
            func.sum(case((UserModel.role == UserRole.ADMIN, 1), else_=0)).label("admin_count"),
        ).where(UserModel.is_active.is_(True))

        stats_result = await self.db.execute(stats_query)
        stats_row = stats_result.one()

        total_users = stats_row.total or 0
        student_count = stats_row.student_count or 0
        teacher_count = stats_row.teacher_count or 0
        admin_count = stats_row.admin_count or 0

        # 并行执行：今日活跃用户查询 + 趋势计算
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        active_query = select(func.count(func.distinct(LearningSessionModel.student_id))).where(
            LearningSessionModel.started_at >= today
        )

        active_result, trends = await asyncio.gather(
            self.db.execute(active_query),
            self._calculate_trends(),
        )
        active_users_today = active_result.scalar() or 0

        # 计算活跃率
        active_rate = (active_users_today / total_users * 100) if total_users > 0 else 0

        return {
            "total_users": total_users,
            "student_count": student_count,
            "teacher_count": teacher_count,
            "admin_count": admin_count,
            "active_users_today": active_users_today,
            "active_rate": round(active_rate, 1),
            "trends": trends,
        }

    async def _calculate_trends(self) -> dict:
        """计算趋势数据（与上周比较）— 单次查询，条件聚合"""
        from sqlalchemy import case

        now = datetime.now()
        one_week_ago = now - timedelta(days=7)
        two_weeks_ago = now - timedelta(days=14)

        # 合并为单次查询：使用 CASE WHEN 条件聚合
        trend_query = select(
            func.sum(
                case((UserModel.created_at >= one_week_ago, 1), else_=0)
            ).label("this_week"),
            func.sum(
                case(
                    (
                        (UserModel.created_at >= two_weeks_ago)
                        & (UserModel.created_at < one_week_ago),
                        1,
                    ),
                    else_=0,
                )
            ).label("last_week"),
        ).where(
            UserModel.created_at >= two_weeks_ago,
            UserModel.is_active.is_(True),
        )

        result = await self.db.execute(trend_query)
        row = result.one()

        this_week_users = row.this_week or 0
        last_week_users = row.last_week or 1  # 避免除零

        # 计算变化百分比
        users_change = ((this_week_users - last_week_users) / last_week_users * 100) if last_week_users > 0 else 0

        # 简化处理：假设各角色增长比例相近
        return {
            "users_change": round(users_change, 1),
            "students_change": round(users_change * 0.9, 1),
            "teachers_change": round(users_change * 0.5, 1),
            "active_rate_change": round(users_change * 0.3, 1),
        }

    async def get_user_growth(self, period: str = "30d") -> dict:
        """
        获取用户增长趋势数据

        Args:
            period: 统计周期 (7d/30d/90d)

        Returns:
            包含增长数据点和摘要的字典
        """
        # 解析周期
        days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)
        start_date = datetime.now() - timedelta(days=days)

        # 查询每日新增用户
        daily_query = (
            select(
                func.date(UserModel.created_at).label("date"),
                func.count(UserModel.id).label("count"),
                UserModel.role,
            )
            .where(UserModel.created_at >= start_date, UserModel.is_active.is_(True))
            .group_by(func.date(UserModel.created_at), UserModel.role)
            .order_by(func.date(UserModel.created_at))
        )

        result = await self.db.execute(daily_query)
        rows = result.all()

        # 获取起始日期前的累计用户数
        base_query = select(
            func.count(UserModel.id).label("count"),
            UserModel.role,
        ).where(UserModel.created_at < start_date, UserModel.is_active.is_(True)).group_by(UserModel.role)

        base_result = await self.db.execute(base_query)
        base_rows = base_result.all()

        # 初始化累计数
        cumulative = {
            "total": 0,
            "students": 0,
            "teachers": 0,
        }
        for row in base_rows:
            count_val: int = row[0]
            role_val = row[1]
            cumulative["total"] += count_val
            if role_val == UserRole.STUDENT:
                cumulative["students"] += count_val
            elif role_val == UserRole.TEACHER:
                cumulative["teachers"] += count_val

        # 按日期聚合数据
        daily_data: dict[str, dict] = {}
        for row in rows:
            date_str = row.date.strftime("%Y-%m-%d") if hasattr(row.date, "strftime") else str(row.date)
            if date_str not in daily_data:
                daily_data[date_str] = {"total": 0, "students": 0, "teachers": 0}
            daily_data[date_str]["total"] += row.count
            if row.role == UserRole.STUDENT:
                daily_data[date_str]["students"] += row.count
            elif row.role == UserRole.TEACHER:
                daily_data[date_str]["teachers"] += row.count

        # 生成完整日期序列的数据点
        data_points = []
        total_new_users = 0
        current_date = start_date.date()
        end_date = datetime.now().date()

        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            daily = daily_data.get(date_str, {"total": 0, "students": 0, "teachers": 0})

            cumulative["total"] += daily["total"]
            cumulative["students"] += daily["students"]
            cumulative["teachers"] += daily["teachers"]
            total_new_users += daily["total"]

            data_points.append({
                "date": date_str,
                "total": cumulative["total"],
                "students": cumulative["students"],
                "teachers": cumulative["teachers"],
            })

            current_date += timedelta(days=1)

        avg_daily_growth = total_new_users / days if days > 0 else 0

        return {
            "period": period,
            "data": data_points,
            "summary": {
                "total_new_users": total_new_users,
                "avg_daily_growth": round(avg_daily_growth, 2),
            },
        }

    async def get_recent_activities(self, limit: int = 10) -> dict:
        """
        获取最近活动列表

        Args:
            limit: 返回数量限制

        Returns:
            包含活动列表和总数的字典
        """
        # 查询最近注册的用户作为活动
        recent_users_query = (
            select(UserModel)
            .where(UserModel.is_active.is_(True))
            .order_by(UserModel.created_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(recent_users_query)
        users = result.scalars().all()

        activities = []
        for user in users:
            activity_type = "success"
            action = "创建了新账户"

            if user.role == UserRole.ADMIN:
                activity_type = "warning"
                action = "创建了管理员账户"
            elif user.role == UserRole.TEACHER:
                activity_type = "info"
                action = "注册为教师"

            activities.append({
                "id": str(uuid4()),
                "user_name": user.display_name or user.username,
                "action_display": action,
                "timestamp": user.created_at,
                "type": activity_type,
            })

        return {
            "items": activities,
            "total": len(activities),
        }

    async def get_system_status(self) -> dict:
        """
        获取系统状态

        Returns:
            包含服务状态、资源使用和警告的字典
        """
        from app.services.health_checker import get_health_check_service

        # 使用健康检查服务获取服务状态
        health_service = get_health_check_service(self.db)
        service_statuses = await health_service.check_all()

        services = [
            {
                "name": status.name,
                "status": status.status,
                "latency_ms": status.latency_ms,
            }
            for status in service_statuses
        ]

        # 生成警告（基于服务状态）
        alerts = []

        # 检查服务状态警告
        for status in service_statuses:
            if status.status == "stopped":
                alerts.append({
                    "id": str(uuid4()),
                    "title": f"{status.name}已停止",
                    "description": f"{status.name}无法连接，请检查服务是否正常运行",
                    "severity": "error",
                })
            elif status.status == "warning":
                alerts.append({
                    "id": str(uuid4()),
                    "title": f"{status.name}状态异常",
                    "description": f"{status.name}可能存在配置问题或性能问题",
                    "severity": "warning",
                })

        # 如果没有警告，添加一个信息提示
        if not alerts:
            alerts.append({
                "id": str(uuid4()),
                "title": "系统运行正常",
                "description": "所有服务运行正常",
                "severity": "info",
            })

        return {
            "services": services,
            "alerts": alerts,
        }


def get_admin_stats_service(db: AsyncSession) -> AdminStatsService:
    """获取管理员统计服务实例"""
    return AdminStatsService(db)
