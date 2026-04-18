"""
安全日志服务

提供安全事件记录、查询、删除、导出和归档功能
"""

import base64
import csv
import io
import json
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.security_log import (
    EVENT_SEVERITY_MAP,
    EVENT_TYPE_DISPLAY,
    SecurityEventType,
    SecuritySeverity,
)
from app.infrastructure.database.models import SecurityLogModel


def _sanitize_extra_data(data: dict[str, Any] | None) -> dict[str, Any]:
    """对 extra_data 进行脱敏，防止敏感信息持久化到数据库"""
    if not data:
        return {}
    try:
        from app.core.log_sanitizer import SanitizeLevel, sanitize_dict
        return sanitize_dict(data, SanitizeLevel.STRICT)
    except Exception:
        return data


class SecurityLogService:
    """安全日志服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # 事件记录
    # =========================================================================

    async def log_event(
        self,
        event_type: SecurityEventType,
        title: str,
        description: str = "",
        severity: SecuritySeverity | None = None,
        ip_address: str | None = None,
        user_id: str | None = None,
        username: str | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> SecurityLogModel:
        """
        记录安全事件

        Args:
            event_type: 事件类型
            title: 事件标题
            description: 详细描述
            severity: 严重程度（不指定则使用默认映射）
            ip_address: 来源 IP
            user_id: 关联用户 ID
            username: 用户名
            extra_data: 扩展元数据

        Returns:
            创建的日志记录
        """
        if severity is None:
            severity = EVENT_SEVERITY_MAP.get(event_type, SecuritySeverity.INFO)

        log = SecurityLogModel(
            id=str(uuid4()),
            event_type=event_type,
            severity=severity,
            title=title,
            description=description,
            ip_address=ip_address,
            user_id=user_id,
            username=username,
            extra_data=_sanitize_extra_data(extra_data),
            archived=False,
            created_at=datetime.now(),
        )

        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)

        # CRITICAL/ERROR 事件自动触发管理员告警
        if severity in (SecuritySeverity.CRITICAL, SecuritySeverity.ERROR):
            try:
                from app.services.alert_service import get_alert_service
                alert_svc = get_alert_service()
                alert_level = "critical" if severity == SecuritySeverity.CRITICAL else "error"
                await alert_svc.send_alert(
                    level=alert_level,
                    title=title,
                    message=description[:500] if description else "",
                    source=f"security_log:{event_type.value}",
                    extra={"log_id": log.id, "ip": ip_address or ""},
                )
            except Exception:
                pass  # 告警失败不影响日志记录

        return log

    async def generate_daily_report(self) -> SecurityLogModel | None:
        """
        生成每日安全报告

        如果当天没有异常事件，则生成一条"系统安全"的报告
        如果当天已有报告或有异常事件，则不生成

        Returns:
            生成的报告记录，如果不需要生成则返回 None
        """
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        # 检查今天是否已有每日报告
        existing_report_query = select(SecurityLogModel).where(
            and_(
                SecurityLogModel.event_type == SecurityEventType.DAILY_REPORT,
                SecurityLogModel.created_at >= today_start,
                SecurityLogModel.created_at < today_end,
            )
        )
        result = await self.db.execute(existing_report_query)
        if result.scalar_one_or_none():
            return None  # 今天已有报告

        # 检查今天是否有异常事件（非 INFO 级别）
        error_query = select(func.count(SecurityLogModel.id)).where(
            and_(
                SecurityLogModel.created_at >= today_start,
                SecurityLogModel.created_at < today_end,
                SecurityLogModel.severity != SecuritySeverity.INFO,
            )
        )
        error_result = await self.db.execute(error_query)
        error_count = error_result.scalar() or 0

        if error_count > 0:
            return None  # 今天有异常，不生成"安全"报告

        # 生成每日安全报告
        return await self.log_event(
            event_type=SecurityEventType.DAILY_REPORT,
            title="每日安全报告",
            description="系统运行正常，未检测到安全异常",
            severity=SecuritySeverity.INFO,
            extra_data={"date": today_start.strftime("%Y-%m-%d")},
        )

    # =========================================================================
    # 查询
    # =========================================================================

    async def get_logs(
        self,
        event_types: list[SecurityEventType] | None = None,
        severities: list[SecuritySeverity] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        include_archived: bool = False,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """
        查询安全日志（按日期分组）

        Returns:
            包含分组日志、总数和是否有更多的字典
        """
        # 构建查询条件
        conditions = []

        if not include_archived:
            conditions.append(SecurityLogModel.archived.is_(False))

        if event_types:
            conditions.append(SecurityLogModel.event_type.in_(event_types))

        if severities:
            conditions.append(SecurityLogModel.severity.in_(severities))

        if start_date:
            conditions.append(SecurityLogModel.created_at >= start_date)

        if end_date:
            conditions.append(SecurityLogModel.created_at <= end_date)

        # 查询总数
        count_query = select(func.count(SecurityLogModel.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # 查询日志列表
        offset = (page - 1) * page_size
        query = (
            select(SecurityLogModel)
            .order_by(SecurityLogModel.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        logs = result.scalars().all()

        # 按日期分组
        groups = self._group_logs_by_date(logs)

        return {
            "groups": groups,
            "total": total,
            "has_more": offset + len(logs) < total,
        }

    async def get_stats(self) -> dict:
        """获取安全日志统计"""
        # 总数
        total_query = select(func.count(SecurityLogModel.id)).where(
            SecurityLogModel.archived.is_(False)
        )
        total_result = await self.db.execute(total_query)
        total_count = total_result.scalar() or 0

        # 按严重程度统计
        severity_query = (
            select(SecurityLogModel.severity, func.count(SecurityLogModel.id))
            .where(SecurityLogModel.archived.is_(False))
            .group_by(SecurityLogModel.severity)
        )
        severity_result = await self.db.execute(severity_query)
        severity_counts = {row[0]: row[1] for row in severity_result.all()}

        # 最近一次错误
        last_error_query = (
            select(SecurityLogModel.created_at)
            .where(
                and_(
                    SecurityLogModel.archived.is_(False),
                    SecurityLogModel.severity.in_(
                        [SecuritySeverity.ERROR, SecuritySeverity.CRITICAL]
                    ),
                )
            )
            .order_by(SecurityLogModel.created_at.desc())
            .limit(1)
        )
        last_error_result = await self.db.execute(last_error_query)
        last_error_at = last_error_result.scalar_one_or_none()

        # 最近一次每日报告
        last_report_query = (
            select(SecurityLogModel.created_at)
            .where(SecurityLogModel.event_type == SecurityEventType.DAILY_REPORT)
            .order_by(SecurityLogModel.created_at.desc())
            .limit(1)
        )
        last_report_result = await self.db.execute(last_report_query)
        last_daily_report_at = last_report_result.scalar_one_or_none()

        return {
            "total_count": total_count,
            "error_count": severity_counts.get(SecuritySeverity.ERROR, 0)
            + severity_counts.get(SecuritySeverity.CRITICAL, 0),
            "warning_count": severity_counts.get(SecuritySeverity.WARNING, 0),
            "info_count": severity_counts.get(SecuritySeverity.INFO, 0),
            "last_error_at": last_error_at,
            "last_daily_report_at": last_daily_report_at,
        }

    def _group_logs_by_date(self, logs: list[SecurityLogModel]) -> list[dict]:
        """将日志按日期分组"""
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        groups_dict: dict[str, list[SecurityLogModel]] = {}

        for log in logs:
            date_key = log.created_at.strftime("%Y-%m-%d")
            if date_key not in groups_dict:
                groups_dict[date_key] = []
            groups_dict[date_key].append(log)

        groups = []
        for date_str, date_logs in groups_dict.items():
            log_date = datetime.strptime(date_str, "%Y-%m-%d").date()

            if log_date == today:
                date_display = "今天"
            elif log_date == yesterday:
                date_display = "昨天"
            else:
                date_display = date_str

            groups.append(
                {
                    "date": date_str,
                    "date_display": date_display,
                    "logs": [self._log_to_dict(log) for log in date_logs],
                    "count": len(date_logs),
                }
            )

        return groups

    def _log_to_dict(self, log: SecurityLogModel) -> dict:
        """将日志模型转换为字典"""
        return {
            "id": log.id,
            "event_type": log.event_type,
            "severity": log.severity,
            "title": log.title,
            "description": log.description,
            "ip_address": log.ip_address,
            "user_id": log.user_id,
            "username": log.username,
            "extra_data": log.extra_data,
            "archived": log.archived,
            "created_at": log.created_at,
        }

    # =========================================================================
    # 删除
    # =========================================================================

    async def delete_logs(
        self,
        log_ids: list[str] | None = None,
        before_date: datetime | None = None,
        delete_all: bool = False,
    ) -> int:
        """
        删除安全日志

        Args:
            log_ids: 指定要删除的日志 ID 列表
            before_date: 删除指定日期之前的日志
            delete_all: 删除所有日志

        Returns:
            删除的记录数
        """
        if delete_all:
            stmt = delete(SecurityLogModel)
        elif log_ids:
            stmt = delete(SecurityLogModel).where(SecurityLogModel.id.in_(log_ids))
        elif before_date:
            stmt = delete(SecurityLogModel).where(
                SecurityLogModel.created_at < before_date
            )
        else:
            return 0

        result = await self.db.execute(stmt)
        await self.db.commit()

        return result.rowcount

    # =========================================================================
    # 导出
    # =========================================================================

    async def export_logs(
        self,
        format: str = "json",
        event_types: list[SecurityEventType] | None = None,
        severities: list[SecuritySeverity] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        include_archived: bool = False,
    ) -> dict:
        """
        导出安全日志

        Args:
            format: 导出格式 (json/csv)
            其他参数: 筛选条件

        Returns:
            包含文件名、内容（Base64）、类型和记录数的字典
        """
        # 构建查询条件
        conditions = []

        if not include_archived:
            conditions.append(SecurityLogModel.archived.is_(False))

        if event_types:
            conditions.append(SecurityLogModel.event_type.in_(event_types))

        if severities:
            conditions.append(SecurityLogModel.severity.in_(severities))

        if start_date:
            conditions.append(SecurityLogModel.created_at >= start_date)

        if end_date:
            conditions.append(SecurityLogModel.created_at <= end_date)

        # 查询所有符合条件的日志
        query = select(SecurityLogModel).order_by(SecurityLogModel.created_at.desc())
        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        logs = result.scalars().all()

        # 生成文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format == "csv":
            content, content_type = self._export_to_csv(logs)
            filename = f"security_logs_{timestamp}.csv"
        else:
            content, content_type = self._export_to_json(logs)
            filename = f"security_logs_{timestamp}.json"

        return {
            "filename": filename,
            "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
            "content_type": content_type,
            "record_count": len(logs),
        }

    def _export_to_json(self, logs: list[SecurityLogModel]) -> tuple[str, str]:
        """导出为 JSON 格式"""
        data = []
        for log in logs:
            data.append(
                {
                    "id": log.id,
                    "event_type": log.event_type.value,
                    "event_type_display": EVENT_TYPE_DISPLAY.get(
                        log.event_type, log.event_type.value
                    ),
                    "severity": log.severity.value,
                    "title": log.title,
                    "description": log.description,
                    "ip_address": log.ip_address,
                    "user_id": log.user_id,
                    "username": log.username,
                    "extra_data": log.extra_data,
                    "archived": log.archived,
                    "created_at": log.created_at.isoformat(),
                }
            )

        return json.dumps(data, ensure_ascii=False, indent=2), "application/json"

    def _export_to_csv(self, logs: list[SecurityLogModel]) -> tuple[str, str]:
        """导出为 CSV 格式"""
        output = io.StringIO()
        writer = csv.writer(output)

        # 写入表头
        writer.writerow(
            [
                "ID",
                "事件类型",
                "严重程度",
                "标题",
                "描述",
                "IP 地址",
                "用户 ID",
                "用户名",
                "创建时间",
                "已归档",
            ]
        )

        # 写入数据
        for log in logs:
            writer.writerow(
                [
                    log.id,
                    EVENT_TYPE_DISPLAY.get(log.event_type, log.event_type.value),
                    log.severity.value,
                    log.title,
                    log.description,
                    log.ip_address or "",
                    log.user_id or "",
                    log.username or "",
                    log.created_at.isoformat(),
                    "是" if log.archived else "否",
                ]
            )

        return output.getvalue(), "text/csv"

    # =========================================================================
    # 归档
    # =========================================================================

    async def archive_logs(self, before_date: datetime) -> int:
        """
        归档指定日期之前的日志

        Args:
            before_date: 归档此日期之前的日志

        Returns:
            归档的记录数
        """
        stmt = (
            update(SecurityLogModel)
            .where(
                and_(
                    SecurityLogModel.created_at < before_date,
                    SecurityLogModel.archived.is_(False),
                )
            )
            .values(archived=True)
        )

        result = await self.db.execute(stmt)
        await self.db.commit()

        return result.rowcount


def get_security_log_service(db: AsyncSession) -> SecurityLogService:
    """获取安全日志服务实例"""
    return SecurityLogService(db)
