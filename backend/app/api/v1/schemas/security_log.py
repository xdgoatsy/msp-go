"""
安全日志 API Schema

定义安全日志相关的请求和响应模型
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.models.security_log import SecurityEventType, SecuritySeverity

# =============================================================================
# 响应模型
# =============================================================================


class SecurityLogItem(BaseModel):
    """单条安全日志"""

    id: str
    event_type: SecurityEventType
    severity: SecuritySeverity
    title: str
    description: str
    ip_address: str | None = None
    user_id: str | None = None
    username: str | None = None
    extra_data: dict = Field(default_factory=dict)
    archived: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class SecurityLogGroup(BaseModel):
    """按日期分组的安全日志"""

    date: str  # YYYY-MM-DD
    date_display: str  # 显示名称，如"今天"、"昨天"、"2026-01-25"
    logs: list[SecurityLogItem]
    count: int


class SecurityLogListResponse(BaseModel):
    """安全日志列表响应"""

    groups: list[SecurityLogGroup]
    total: int
    has_more: bool


class SecurityLogStatsResponse(BaseModel):
    """安全日志统计响应"""

    total_count: int
    error_count: int
    warning_count: int
    info_count: int
    last_error_at: datetime | None = None
    last_daily_report_at: datetime | None = None


# =============================================================================
# 请求模型
# =============================================================================


class SecurityLogQueryParams(BaseModel):
    """安全日志查询参数"""

    event_types: list[SecurityEventType] | None = None
    severities: list[SecuritySeverity] | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    include_archived: bool = False
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


class SecurityLogDeleteRequest(BaseModel):
    """安全日志删除请求"""

    log_ids: list[str] | None = None  # 指定 ID 删除
    before_date: datetime | None = None  # 删除指定日期之前的日志
    delete_all: bool = False  # 删除所有（需要确认）


class SecurityLogExportRequest(BaseModel):
    """安全日志导出请求"""

    format: str = Field(default="json", pattern="^(json|csv)$")
    event_types: list[SecurityEventType] | None = None
    severities: list[SecuritySeverity] | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    include_archived: bool = False


class SecurityLogExportResponse(BaseModel):
    """安全日志导出响应"""

    filename: str
    content: str  # Base64 编码的文件内容
    content_type: str
    record_count: int


class SecurityLogArchiveRequest(BaseModel):
    """安全日志归档请求"""

    before_date: datetime  # 归档指定日期之前的日志


class SecurityLogArchiveResponse(BaseModel):
    """安全日志归档响应"""

    archived_count: int
