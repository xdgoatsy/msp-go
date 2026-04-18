"""
数据库会话管理

提供异步数据库连接和会话管理。
包含连接池监控和语句超时配置。
"""

import logging
import time
from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import Pool

from app.config import settings
from app.core.middleware.metrics import record_db_session_hold

logger = logging.getLogger(__name__)

# 创建异步引擎（含生产级优化）
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_recycle=settings.db_pool_recycle_seconds,
    connect_args={
        # asyncpg 连接参数
        "server_settings": {
            "statement_timeout": str(settings.db_statement_timeout_ms),
            "idle_in_transaction_session_timeout": str(settings.db_idle_tx_timeout_ms),
        },
    },
)

# ========== 慢查询监控 + 连接泄漏检测 ==========


@event.listens_for(engine.sync_engine, "before_cursor_execute")
def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """记录查询开始时间"""
    conn.info["_query_start_time"] = time.monotonic()


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """检测慢查询并记录"""
    start = conn.info.pop("_query_start_time", None)
    if start is None:
        return
    elapsed = time.monotonic() - start
    if elapsed > 0.1:  # 100ms 阈值
        stmt_preview = statement[:200] if statement else "<empty>"
        logger.warning("慢查询 (%.3fs): %s", elapsed, stmt_preview)


@event.listens_for(Pool, "checkout")
def _on_checkout(dbapi_conn, connection_record, connection_proxy):
    """连接检出时记录时间（用于泄漏检测）"""
    connection_record.info["_checkout_time"] = time.monotonic()


@event.listens_for(Pool, "checkin")
def _on_checkin(dbapi_conn, connection_record):
    """连接归还时检测长时间持有"""
    checkout_time = connection_record.info.pop("_checkout_time", None)
    if checkout_time is not None:
        hold_duration = time.monotonic() - checkout_time
        if hold_duration > 10.0:  # 10 秒阈值
            logger.warning(
                "连接持有时间过长: %.1fs（可能存在连接泄漏）", hold_duration
            )


# 创建异步会话工厂
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 声明式基类
Base = declarative_base()


async def init_db() -> None:
    """
    初始化数据库

    在应用启动时调用，创建所有表
    注意：生产环境应使用 Alembic 迁移
    """
    async with engine.begin():
        # 开发环境可以自动创建表
        # await conn.run_sync(Base.metadata.create_all)
        pass


async def close_db() -> None:
    """
    关闭数据库连接

    在应用关闭时调用
    """
    await engine.dispose()


def get_pool_status() -> dict[str, int]:
    """
    获取连接池状态（用于监控和 Prometheus 指标）

    Returns:
        {"pool_size": N, "checked_in": N, "checked_out": N, "overflow": N}
    """
    pool = engine.pool
    size = getattr(pool, "size", lambda: 0)
    checkedin = getattr(pool, "checkedin", lambda: 0)
    checkedout = getattr(pool, "checkedout", lambda: 0)
    overflow = getattr(pool, "overflow", lambda: 0)
    return {
        "pool_size": int(size()),
        "checked_in": int(checkedin()),
        "checked_out": int(checkedout()),
        "overflow": int(overflow()),
    }


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话

    用于依赖注入
    """
    _hold_start = time.monotonic()
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()
        finally:
            record_db_session_hold(time.monotonic() - _hold_start)
            await session.close()
