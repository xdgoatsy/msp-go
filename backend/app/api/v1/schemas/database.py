"""
数据库管理 API Schema

定义数据导入导出和数据库监控相关的请求和响应模型
"""

from datetime import datetime

from pydantic import BaseModel, Field

# =============================================================================
# 数据导出
# =============================================================================


class DataExportRequest(BaseModel):
    """数据导出请求"""

    tables: list[str] = Field(
        ...,
        description="要导出的表名列表",
        min_length=1,
    )


class DataExportResponse(BaseModel):
    """数据导出响应"""

    filename: str
    content: str  # Base64 编码的 JSON 文件内容
    exported_at: datetime
    table_counts: dict[str, int]
    total_records: int


# =============================================================================
# 数据导入
# =============================================================================


class TableImportResult(BaseModel):
    """单表导入结果"""

    imported: int = 0
    skipped: int = 0
    failed: int = 0


class DataImportResponse(BaseModel):
    """数据导入响应"""

    success: bool
    imported_at: datetime
    table_results: dict[str, TableImportResult]
    total_imported: int
    total_skipped: int
    total_failed: int
    errors: list[str]


# =============================================================================
# 数据库监控
# =============================================================================


class ExportableTableItem(BaseModel):
    """可导出的表信息"""

    name: str
    display_name: str


class ExportableTablesResponse(BaseModel):
    """可导出表列表响应"""

    tables: list[ExportableTableItem]


class ConnectionPoolStatus(BaseModel):
    """连接池状态"""

    pool_size: int = Field(description="配置的连接池大小")
    max_overflow: int = Field(description="最大溢出连接数")
    checked_out: int = Field(description="当前使用中的连接数")
    checked_in: int = Field(description="当前空闲的连接数")
    overflow: int = Field(description="当前溢出连接数")
    pool_timeout: int = Field(description="连接超时时间(秒)")
    pool_recycle: int = Field(description="连接回收时间(秒)")
    usage_percent: float = Field(description="连接池使用率(%)")


class TableStats(BaseModel):
    """表统计信息"""

    table_name: str
    display_name: str
    row_count: int
    table_size: str
    index_size: str
    total_size: str


class DatabaseOverview(BaseModel):
    """数据库概览"""

    database_name: str
    database_size: str
    postgres_version: str
    uptime: str
    active_connections: int
    max_connections: int


class DatabaseMonitorResponse(BaseModel):
    """数据库监控响应"""

    overview: DatabaseOverview
    connection_pool: ConnectionPoolStatus
    tables: list[TableStats]
    health_status: str
    checked_at: datetime
