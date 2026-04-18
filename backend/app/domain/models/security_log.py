"""
安全日志领域模型

定义安全事件类型、严重程度和日志实体
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID


class SecurityEventType(str, Enum):
    """安全事件类型"""

    # 登录相关
    LOGIN_FAILED = "login_failed"           # 登录失败
    LOGIN_ANOMALY = "login_anomaly"         # 异常登录（异地、频繁尝试等）

    # 请求相关
    REQUEST_ERROR = "request_error"         # 请求异常（参数错误、越权等）
    REQUEST_BLOCKED = "request_blocked"     # 请求被拦截

    # 服务相关
    SERVICE_ERROR = "service_error"         # 服务异常
    SERVICE_RECOVERED = "service_recovered" # 服务恢复

    # 系统报告
    DAILY_REPORT = "daily_report"           # 每日安全报告

    # 配置变更
    CONFIG_CHANGED = "config_changed"       # 系统配置变更


class SecuritySeverity(str, Enum):
    """安全事件严重程度"""

    INFO = "info"           # 信息（如每日报告）
    WARNING = "warning"     # 警告
    ERROR = "error"         # 错误
    CRITICAL = "critical"   # 严重


# 事件类型到严重程度的默认映射
EVENT_SEVERITY_MAP: dict[SecurityEventType, SecuritySeverity] = {
    SecurityEventType.LOGIN_FAILED: SecuritySeverity.WARNING,
    SecurityEventType.LOGIN_ANOMALY: SecuritySeverity.ERROR,
    SecurityEventType.REQUEST_ERROR: SecuritySeverity.WARNING,
    SecurityEventType.REQUEST_BLOCKED: SecuritySeverity.WARNING,
    SecurityEventType.SERVICE_ERROR: SecuritySeverity.ERROR,
    SecurityEventType.SERVICE_RECOVERED: SecuritySeverity.INFO,
    SecurityEventType.DAILY_REPORT: SecuritySeverity.INFO,
    SecurityEventType.CONFIG_CHANGED: SecuritySeverity.INFO,
}

# 事件类型的中文显示名称
EVENT_TYPE_DISPLAY: dict[SecurityEventType, str] = {
    SecurityEventType.LOGIN_FAILED: "登录失败",
    SecurityEventType.LOGIN_ANOMALY: "异常登录",
    SecurityEventType.REQUEST_ERROR: "请求异常",
    SecurityEventType.REQUEST_BLOCKED: "请求拦截",
    SecurityEventType.SERVICE_ERROR: "服务异常",
    SecurityEventType.SERVICE_RECOVERED: "服务恢复",
    SecurityEventType.DAILY_REPORT: "每日报告",
    SecurityEventType.CONFIG_CHANGED: "配置变更",
}


@dataclass
class SecurityLog:
    """安全日志实体"""

    id: UUID
    event_type: SecurityEventType
    severity: SecuritySeverity
    title: str
    description: str
    created_at: datetime
    ip_address: str | None = None
    user_id: UUID | None = None
    username: str | None = None
    extra_data: dict[str, Any] = field(default_factory=dict)
    archived: bool = False
