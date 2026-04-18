"""
数据库管理服务

提供数据导入导出和数据库监控功能
"""

import base64
import json
import logging
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.pool import QueuePool

from app.infrastructure.database.session import engine

logger = logging.getLogger(__name__)

# 可导出的表及其显示名称
EXPORTABLE_TABLES: dict[str, str] = {
    "users": "用户",
    "student_profiles": "学生画像",
    "knowledge_nodes": "知识节点",
    "knowledge_relations": "知识关系",
    "learning_sessions": "学习会话",
    "session_messages": "会话消息",
    "contents": "内容",
    "system_settings": "系统设置",
    "classes": "班级",
    "class_enrollments": "班级学生",
    "security_logs": "安全日志",
}

# 导出时排除的敏感字段
SENSITIVE_FIELDS = {"hashed_password", "encrypted_password", "session_cookies"}

# 导入顺序（按外键依赖排列）
IMPORT_ORDER = [
    "users",
    "student_profiles",
    "knowledge_nodes",
    "knowledge_relations",
    "system_settings",
    "classes",
    "class_enrollments",
    "contents",
    "learning_sessions",
    "session_messages",
    "security_logs",
]


class DatabaseManagementService:
    """数据库管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ======================== 导出 ========================

    async def export_data(self, tables: list[str], admin_id: str) -> dict:
        """
        导出指定表的数据为 JSON

        逐表 SELECT *，排除敏感字段，JSON 序列化后 Base64 编码
        """
        invalid = [t for t in tables if t not in EXPORTABLE_TABLES]
        if invalid:
            raise ValueError(f"不支持导出的表: {', '.join(invalid)}")

        export_data = {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "exported_by": admin_id,
            "tables": {},
        }
        table_counts: dict[str, int] = {}

        for table_name in tables:
            rows = await self._export_table(table_name)
            export_data["tables"][table_name] = rows
            table_counts[table_name] = len(rows)

        json_str = json.dumps(export_data, ensure_ascii=False, default=str)
        content_b64 = base64.b64encode(json_str.encode("utf-8")).decode("ascii")

        total = sum(table_counts.values())
        filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        return {
            "filename": filename,
            "content": content_b64,
            "exported_at": datetime.now(),
            "table_counts": table_counts,
            "total_records": total,
        }

    async def _export_table(self, table_name: str) -> list[dict]:
        """导出单张表数据，排除敏感字段"""
        result = await self.db.execute(text(f"SELECT * FROM {table_name}"))  # noqa: S608
        columns = list(result.keys())
        rows = []
        for row in result.fetchall():
            row_dict = {}
            for col, val in zip(columns, row, strict=False):
                if col in SENSITIVE_FIELDS:
                    continue
                row_dict[col] = val
            rows.append(row_dict)
        return rows

    # ======================== 导入 ========================

    async def import_data(self, file_content: bytes, admin_id: str) -> dict:
        """
        从 JSON 备份文件导入数据

        按外键依赖顺序导入，使用 ON CONFLICT DO NOTHING 跳过已存在记录
        """
        try:
            data = json.loads(file_content.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise ValueError(f"JSON 文件解析失败: {e}") from e

        if "tables" not in data or not isinstance(data["tables"], dict):
            raise ValueError("无效的备份文件格式")

        tables_data: dict = data["tables"]
        results: dict[str, dict] = {}
        errors: list[str] = []
        total_imported = 0
        total_skipped = 0
        total_failed = 0

        # 按依赖顺序排列
        ordered = [t for t in IMPORT_ORDER if t in tables_data]
        ordered += [t for t in tables_data if t not in IMPORT_ORDER]

        for table_name in ordered:
            if table_name not in EXPORTABLE_TABLES:
                errors.append(f"跳过未知表: {table_name}")
                continue

            rows = tables_data[table_name]
            result = await self._import_table(table_name, rows)
            results[table_name] = result
            total_imported += result["imported"]
            total_skipped += result["skipped"]
            total_failed += result["failed"]
            if result.get("error"):
                errors.append(f"{table_name}: {result['error']}")

        return {
            "success": total_failed == 0,
            "imported_at": datetime.now(),
            "table_results": results,
            "total_imported": total_imported,
            "total_skipped": total_skipped,
            "total_failed": total_failed,
            "errors": errors,
        }

    async def _import_table(self, table_name: str, rows: list[dict]) -> dict:
        """导入单张表数据，ON CONFLICT DO NOTHING"""
        imported = 0
        skipped = 0
        failed = 0

        for row in rows:
            filtered = {k: v for k, v in row.items() if k not in SENSITIVE_FIELDS}
            if not filtered:
                skipped += 1
                continue

            columns = ", ".join(filtered.keys())
            placeholders = ", ".join(f":{k}" for k in filtered.keys())

            try:
                result = await self.db.execute(
                    text(
                        f"INSERT INTO {table_name} ({columns}) "  # noqa: S608
                        f"VALUES ({placeholders}) "
                        f"ON CONFLICT DO NOTHING"
                    ),
                    filtered,
                )
                if result.rowcount and result.rowcount > 0:  # type: ignore[union-attr]
                    imported += 1
                else:
                    skipped += 1
            except Exception as e:
                failed += 1
                logger.warning("导入 %s 行失败: %s", table_name, e)

        return {"imported": imported, "skipped": skipped, "failed": failed}

    # ======================== 监控 ========================

    async def get_database_monitor(self) -> dict:
        """获取数据库监控数据（概览 + 连接池 + 表统计）"""
        overview = await self._get_database_overview()
        pool_status = self._get_connection_pool_status()
        tables = await self._get_table_stats()

        health = "healthy"
        if pool_status["usage_percent"] > 90:
            health = "degraded"
        if pool_status["usage_percent"] > 95:
            health = "unhealthy"

        return {
            "overview": overview,
            "connection_pool": pool_status,
            "tables": tables,
            "health_status": health,
            "checked_at": datetime.now(),
        }

    async def _get_database_overview(self) -> dict:
        """获取数据库概览信息"""
        size_result = await self.db.execute(
            text("SELECT pg_size_pretty(pg_database_size(current_database()))")
        )
        db_size = size_result.scalar() or "未知"

        name_result = await self.db.execute(text("SELECT current_database()"))
        db_name = name_result.scalar() or "未知"

        ver_result = await self.db.execute(text("SELECT version()"))
        pg_version_raw = ver_result.scalar() or ""
        pg_version = pg_version_raw.split(",")[0] if pg_version_raw else "未知"

        uptime_result = await self.db.execute(
            text("SELECT now() - pg_postmaster_start_time()")
        )
        uptime = str(uptime_result.scalar() or "未知")

        conn_result = await self.db.execute(
            text("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
        )
        active_conns = conn_result.scalar() or 0

        max_conn_result = await self.db.execute(text("SHOW max_connections"))
        max_conns = int(max_conn_result.scalar() or 100)

        return {
            "database_name": db_name,
            "database_size": db_size,
            "postgres_version": pg_version,
            "uptime": uptime,
            "active_connections": active_conns,
            "max_connections": max_conns,
        }

    def _get_connection_pool_status(self) -> dict:
        """获取 SQLAlchemy 连接池状态"""
        pool = engine.pool
        assert isinstance(pool, QueuePool), "仅支持 QueuePool 类型的连接池"
        pool_size = pool.size()
        checked_out = pool.checkedout()
        overflow = pool.overflow()
        checked_in = pool.checkedin()
        max_overflow = pool._max_overflow  # noqa: SLF001

        total_capacity = pool_size + max_overflow
        usage = (checked_out / total_capacity * 100) if total_capacity > 0 else 0

        return {
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "checked_out": checked_out,
            "checked_in": checked_in,
            "overflow": overflow,
            "pool_timeout": 30,
            "pool_recycle": 3600,
            "usage_percent": round(usage, 1),
        }

    async def _get_table_stats(self) -> list[dict]:
        """获取各表的行数和大小统计"""
        result = await self.db.execute(
            text(
                "SELECT "
                "  relname AS table_name, "
                "  n_live_tup AS row_count, "
                "  pg_size_pretty(pg_table_size(relid)) AS table_size, "
                "  pg_size_pretty(pg_indexes_size(relid)) AS index_size, "
                "  pg_size_pretty(pg_total_relation_size(relid)) AS total_size "
                "FROM pg_stat_user_tables "
                "ORDER BY pg_total_relation_size(relid) DESC"
            )
        )

        tables = []
        for row in result.fetchall():
            display_name = EXPORTABLE_TABLES.get(row[0], row[0])
            tables.append(
                {
                    "table_name": row[0],
                    "display_name": display_name,
                    "row_count": row[1] or 0,
                    "table_size": row[2],
                    "index_size": row[3],
                    "total_size": row[4],
                }
            )

        return tables
