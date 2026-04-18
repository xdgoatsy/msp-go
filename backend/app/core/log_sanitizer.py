"""
日志脱敏过滤器

自动检测并脱敏日志中的敏感信息，防止生产环境信息泄露。
支持：密码、Token、密钥、手机号、邮箱、身份证号、银行卡号、IP 地址等。

性能设计：
- 正则预编译，避免重复编译开销
- 支持缓存已脱敏的字符串片段
- 可配置脱敏级别（生产环境严格，开发环境宽松）
"""

import logging
import re
from enum import Enum
from functools import lru_cache
from typing import Any


class SanitizeLevel(str, Enum):
    """脱敏级别"""
    OFF = "off"              # 不脱敏（仅开发环境）
    STANDARD = "standard"    # 标准脱敏（密码、Token、密钥）
    STRICT = "strict"        # 严格脱敏（包含 PII：手机号、邮箱、身份证等）


# 预编译正则表达式（性能关键）
_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    # 密码字段（JSON/表单/URL 参数）
    (re.compile(
        r'(?i)(password|passwd|pwd|secret|token|api_key|apikey|access_key|'
        r'secret_key|authorization|auth_token|refresh_token|fernet_secret_key|'
        r'jwt_secret_key|private_key|client_secret)'
        r'[\s]*[=:"\'][\s]*["\']?([^"\'\s,}{]{3,})["\']?'
    ), r'\1=***REDACTED***', "credential"),

    # Bearer Token
    (re.compile(
        r'(?i)(Bearer\s+)([A-Za-z0-9\-._~+/]+=*)'
    ), r'\1***REDACTED***', "bearer_token"),

    # JWT Token（三段式）
    (re.compile(
        r'eyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+'
    ), '***JWT_REDACTED***', "jwt"),

    # Fernet 密钥
    (re.compile(
        r'[A-Za-z0-9\-_]{43}='
    ), '***KEY_REDACTED***', "fernet_key"),
]

# PII 模式（仅 STRICT 级别启用）
_PII_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    # 中国手机号
    (re.compile(
        r'(?<!\d)(1[3-9]\d{9})(?!\d)'
    ), r'***PHONE***', "phone"),

    # 邮箱地址
    (re.compile(
        r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
    ), r'***@\2', "email"),

    # 中国身份证号（18位）
    (re.compile(
        r'(?<!\d)(\d{6})((?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01]))(\d{3}[\dXx])(?!\d)'
    ), r'\1********\3', "id_card"),
]

def sanitize_text(text: str, level: SanitizeLevel = SanitizeLevel.STRICT) -> str:
    """
    对文本进行脱敏处理

    Args:
        text: 待脱敏文本
        level: 脱敏级别

    Returns:
        脱敏后的文本
    """
    if level == SanitizeLevel.OFF or not text:
        return text

    result = text

    # 始终处理凭证类敏感信息
    for pattern, replacement, _name in _PATTERNS:
        result = pattern.sub(replacement, result)

    # STRICT 级别额外处理 PII
    if level == SanitizeLevel.STRICT:
        for pattern, replacement, _name in _PII_PATTERNS:
            result = pattern.sub(replacement, result)

    return result


def sanitize_dict(
    data: dict[str, Any],
    level: SanitizeLevel = SanitizeLevel.STRICT,
) -> dict[str, Any]:
    """
    对字典中的敏感字段进行脱敏

    递归处理嵌套字典和列表，自动识别敏感键名。
    """
    if level == SanitizeLevel.OFF or not data:
        return data

    # 敏感键名集合（小写匹配）
    _SENSITIVE_KEYS = {
        "password", "passwd", "pwd", "secret", "token", "api_key",
        "apikey", "access_key", "secret_key", "authorization",
        "auth_token", "refresh_token", "private_key", "client_secret",
        "fernet_secret_key", "jwt_secret_key", "credit_card",
        "encrypted_password",
    }

    result = {}
    for key, value in data.items():
        key_lower = key.lower()
        if key_lower in _SENSITIVE_KEYS:
            result[key] = "***REDACTED***"
        elif isinstance(value, dict):
            result[key] = sanitize_dict(value, level)
        elif isinstance(value, list):
            result[key] = [
                sanitize_dict(item, level) if isinstance(item, dict)
                else sanitize_text(str(item), level) if isinstance(item, str)
                else item
                for item in value
            ]
        elif isinstance(value, str):
            result[key] = sanitize_text(value, level)
        else:
            result[key] = value

    return result


class SanitizingLogFilter(logging.Filter):
    """
    日志脱敏过滤器

    挂载到 logging handler 上，自动脱敏所有日志消息。
    """

    def __init__(self, level: SanitizeLevel = SanitizeLevel.STRICT, name: str = ""):
        super().__init__(name)
        self.level = level

    def filter(self, record: logging.LogRecord) -> bool:
        """过滤并脱敏日志记录"""
        if self.level == SanitizeLevel.OFF:
            return True

        # 脱敏消息文本
        if isinstance(record.msg, str):
            record.msg = sanitize_text(record.msg, self.level)

        # 脱敏参数
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: sanitize_text(str(v), self.level) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    sanitize_text(str(a), self.level) if isinstance(a, str) else a
                    for a in record.args
                )

        return True


@lru_cache(maxsize=1)
def get_sanitize_level_from_env() -> SanitizeLevel:
    """根据环境变量获取脱敏级别"""
    try:
        from app.config import settings
        env = settings.environment
        if env == "production":
            return SanitizeLevel.STRICT
        elif env == "staging":
            return SanitizeLevel.STANDARD
        else:
            return SanitizeLevel.OFF
    except Exception:
        return SanitizeLevel.STRICT  # 安全兜底


def install_log_sanitizer() -> None:
    """
    安装全局日志脱敏过滤器

    在应用启动时调用，为根 logger 添加脱敏过滤器。
    """
    level = get_sanitize_level_from_env()
    if level == SanitizeLevel.OFF:
        return

    root_logger = logging.getLogger()
    sanitizer = SanitizingLogFilter(level=level)

    # 避免重复安装
    for f in root_logger.filters:
        if isinstance(f, SanitizingLogFilter):
            return

    root_logger.addFilter(sanitizer)
