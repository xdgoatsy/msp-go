"""
自动日志清理服务

提供定时归档和删除旧安全日志的功能。
支持通过 API 手动触发或在应用启动时注册后台任务。

清理策略：
- 归档：超过 archive_after_days 天的活跃日志 → 标记为 archived
- 删除：超过 delete_after_days 天的归档日志 → 物理删除
- 大小监控：当日志总数超过阈值时触发告警

性能设计：
- 分批处理，避免长事务锁表
- 使用数据库索引优化查询
- 后台异步执行，不阻塞主线程
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import SecurityLogModel

logger = logging.getLogger(__name__)


class LogCleanupService:
    """安全日志自动清理服务"""

    # 默认清理策略
    DEFAULT_ARCHIVE_AFTER_DAYS = 30    # 30 天后归档
    DEFAULT_DELETE_AFTER_DAYS = 90     # 90 天后删除
    DEFAULT_BATCH_SIZE = 500           # 每批处理数量
    DEFAULT_MAX_LOG_COUNT = 100000     # 日志总数告警阈值

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._load_config()

    def _load_config(self) -> None:
        """从配置加载清理策略"""
        try:
            from app.config import settings
            self.archive_after_days = getattr(
                settings, "log_archive_after_days", self.DEFAULT_ARCHIVE_AFTER_DAYS
            )
            self.delete_after_days = getattr(
                settings, "log_delete_after_days", self.DEFAULT_DELETE_AFTER_DAYS
            )
            self.batch_size = getattr(
                settings, "log_cleanup_batch_size", self.DEFAULT_BATCH_SIZE
            )
            self.max_log_count = getattr(
                settings, "log_max_count", self.DEFAULT_MAX_LOG_COUNT
            )
        except Exception:
            self.archive_after_days = self.DEFAULT_ARCHIVE_AFTER_DAYS
            self.delete_after_days = self.DEFAULT_DELETE_AFTER_DAYS
            self.batch_size = self.DEFAULT_BATCH_SIZE
            self.max_log_count = self.DEFAULT_MAX_LOG_COUNT

    async def auto_archive(self) -> int:
        """
        自动归档过期日志

        将超过 archive_after_days 天的活跃日志标记为 archived。
        分批处理避免长事务。

        Returns:
            归档的记录总数
        """
        cutoff = datetime.now() - timedelta(days=self.archive_after_days)
        total_archived = 0

        while True:
            # 分批查询待归档的日志 ID
            query = (
                select(SecurityLogModel.id)
                .where(
                    and_(
                        SecurityLogModel.created_at < cutoff,
                        SecurityLogModel.archived.is_(False),
                    )
                )
                .limit(self.batch_size)
            )
            result = await self.db.execute(query)
            ids = [row[0] for row in result.all()]

            if not ids:
                break

            stmt = (
                update(SecurityLogModel)
                .where(SecurityLogModel.id.in_(ids))
                .values(archived=True)
            )
            await self.db.execute(stmt)
            await self.db.commit()
            total_archived += len(ids)

            logger.info(f"日志归档: 本批 {len(ids)} 条，累计 {total_archived} 条")

        return total_archived

    async def auto_delete(self) -> int:
        """
        自动删除过期归档日志

        物理删除超过 delete_after_days 天的归档日志。
        分批处理避免长事务。

        Returns:
            删除的记录总数
        """
        cutoff = datetime.now() - timedelta(days=self.delete_after_days)
        total_deleted = 0

        while True:
            query = (
                select(SecurityLogModel.id)
                .where(
                    and_(
                        SecurityLogModel.created_at < cutoff,
                        SecurityLogModel.archived.is_(True),
                    )
                )
                .limit(self.batch_size)
            )
            result = await self.db.execute(query)
            ids = [row[0] for row in result.all()]

            if not ids:
                break

            stmt = delete(SecurityLogModel).where(SecurityLogModel.id.in_(ids))
            await self.db.execute(stmt)
            await self.db.commit()
            total_deleted += len(ids)

            logger.info(f"日志删除: 本批 {len(ids)} 条，累计 {total_deleted} 条")

        return total_deleted

    async def check_log_volume(self) -> dict:
        """
        检查日志总量，超过阈值时触发告警

        Returns:
            包含总数、归档数和是否超限的字典
        """
        # 活跃日志数
        active_query = select(func.count(SecurityLogModel.id)).where(
            SecurityLogModel.archived.is_(False)
        )
        active_result = await self.db.execute(active_query)
        active_count = active_result.scalar() or 0

        # 归档日志数
        archived_query = select(func.count(SecurityLogModel.id)).where(
            SecurityLogModel.archived.is_(True)
        )
        archived_result = await self.db.execute(archived_query)
        archived_count = archived_result.scalar() or 0

        total = active_count + archived_count
        exceeded = total > self.max_log_count

        if exceeded:
            logger.warning(
                f"日志总量超过阈值: {total}/{self.max_log_count}"
            )
            # 触发告警
            try:
                from app.services.alert_service import get_alert_service
                alert_svc = get_alert_service()
                await alert_svc.send_alert(
                    level="warning",
                    title="安全日志总量超过阈值",
                    message=f"当前日志总数: {total}（阈值: {self.max_log_count}）\n"
                            f"活跃: {active_count}，归档: {archived_count}",
                    source="log_cleanup",
                )
            except Exception:
                pass

        return {
            "active_count": active_count,
            "archived_count": archived_count,
            "total": total,
            "max_allowed": self.max_log_count,
            "exceeded": exceeded,
        }

    async def run_full_cleanup(self) -> dict:
        """
        执行完整清理流程：归档 → 删除 → 检查总量

        Returns:
            清理结果摘要
        """
        logger.info("开始执行日志自动清理...")

        archived = await self.auto_archive()
        deleted = await self.auto_delete()
        volume = await self.check_log_volume()

        result = {
            "archived_count": archived,
            "deleted_count": deleted,
            "volume": volume,
            "cleanup_at": datetime.now().isoformat(),
        }

        logger.info(
            f"日志清理完成: 归档 {archived} 条, 删除 {deleted} 条, "
            f"当前总量 {volume['total']}"
        )
        return result


async def run_scheduled_cleanup() -> dict:
    """
    定时清理入口（供后台任务调用）

    创建独立数据库会话执行清理。
    """
    from app.infrastructure.database.session import async_session_factory

    async with async_session_factory() as session:
        service = LogCleanupService(session)
        return await service.run_full_cleanup()


def get_log_cleanup_service(db: AsyncSession) -> LogCleanupService:
    """获取日志清理服务实例"""
    return LogCleanupService(db)
