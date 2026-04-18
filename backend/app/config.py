"""
应用配置管理

使用 pydantic-settings 管理环境变量和配置。
生产环境启动时自动校验关键安全配置。
"""

import logging
import sys
from functools import lru_cache
from typing import Literal

from pydantic import computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# 不安全的默认值列表
_INSECURE_JWT_SECRETS = frozenset({
    "your-secret-key-change-in-production",
    "secret", "changeme", "test", "",
})
_INSECURE_ADMIN_PASSWORDS = frozenset({
    "admin123", "admin", "password", "123456", "12345678",
})
_ALLOWED_JWT_ALGORITHMS = frozenset({"HS256", "HS384", "HS512"})


class Settings(BaseSettings):
    """应用配置类"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 应用基础配置
    app_name: str = "高等数学智能学习平台"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # API 配置
    api_v1_prefix: str = "/api/v1"
    # CORS 配置
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    cors_allow_methods: list[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    cors_allow_headers: list[str] = [
        "Authorization", "Content-Type", "Accept",
        "Origin", "X-Requested-With", "X-CSRF-Token",
    ]

    # 数据库配置
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "math_platform"

    # 数据库连接池与语句超时（Phase 1：低风险内存治理）
    db_pool_size: int = 12
    db_max_overflow: int = 8
    db_pool_timeout: int = 30
    db_pool_recycle_seconds: int = 1800
    db_statement_timeout_ms: int = 30000
    db_idle_tx_timeout_ms: int = 60000

    @computed_field
    @property
    def database_url(self) -> str:
        """构建 PostgreSQL 异步连接 URL"""
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @computed_field
    @property
    def database_url_sync(self) -> str:
        """构建 PostgreSQL 同步连接 URL（用于 Alembic）"""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # Redis 配置
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0
    redis_max_connections: int = 20
    redis_retry_on_timeout: bool = True
    redis_socket_timeout_seconds: float = 3.0
    redis_socket_connect_timeout_seconds: float = 3.0
    redis_fallback_cache_max_size: int = 500

    @computed_field
    @property
    def redis_url(self) -> str:
        """构建 Redis 连接 URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # JWT 配置
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    @model_validator(mode="after")
    def validate_jwt_algorithm(self) -> "Settings":
        algorithm = self.jwt_algorithm.upper().strip()
        if algorithm not in _ALLOWED_JWT_ALGORITHMS:
            allowed = ", ".join(sorted(_ALLOWED_JWT_ALGORITHMS))
            raise ValueError(
                f"不支持的 JWT_ALGORITHM={self.jwt_algorithm}，仅允许: {allowed}"
            )
        self.jwt_algorithm = algorithm
        return self

    # 西电教务集成配置
    xidian_ids_base: str = "https://ids.xidian.edu.cn"
    xidian_ehall_base: str = "https://ehall.xidian.edu.cn"
    xidian_yjspt_base: str = "https://yjspt.xidian.edu.cn"
    xidian_user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    )
    xidian_http_connect_timeout: float = 10.0
    xidian_http_read_timeout: float = 30.0
    xidian_challenge_ttl: int = 600  # 10 分钟
    xidian_session_ttl: int = 86400  # 24 小时（兜底，主要靠数据库持久化）
    xidian_sync_retry_count: int = 2  # 同步操作网络重试次数
    xidian_snapshot_fallback_enabled: bool = True  # 启用快照降级
    xidian_captcha_width: int = 280
    xidian_captcha_height: int = 155
    xidian_piece_width: int = 44
    xidian_piece_height: int = 155

    # 加密配置
    # Fernet 密钥用于加密敏感数据（如 API Key）
    # 生成方式：python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    fernet_secret_key: str = ""

    # 初始管理员配置
    admin_username: str = "admin"
    admin_email: str = "admin@example.com"
    admin_password: str = "admin123"

    # 限流配置
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 120  # 每分钟请求限制（SPA 页面切换需要更高配额）
    rate_limit_per_hour: int = 2000  # 每小时请求限制
    rate_limit_per_day: int = 10000  # 每天请求限制
    rate_limit_burst: int = 30  # 突发请求限制（SPA 单页面可能并发 4-6 个请求）

    # AI 接口限流配置（更严格）
    ai_rate_limit_per_minute: int = 20
    ai_rate_limit_per_hour: int = 200
    ai_concurrent_limit: int = 3  # AI 并发请求限制

    # 队列配置
    llm_queue_enabled: bool = False  # 是否启用 LLM 请求队列
    llm_queue_max_size: int = 1000  # 队列最大长度
    llm_queue_workers: int = 5  # 队列工作者数量

    # 监控配置
    metrics_enabled: bool = True  # 是否启用 Prometheus 指标

    # 请求超时配置
    request_timeout_default: float = 30.0  # 默认请求超时（秒）
    request_timeout_ai: float = 300.0  # AI 接口超时（秒）
    request_body_max_size: int = 10 * 1024 * 1024  # 请求体最大 10MB

    # 登录安全配置
    login_max_attempts: int = 5  # 最大登录失败次数
    login_lockout_minutes: int = 15  # 账户锁定时间（分钟）

    # Redis 检查点配置
    redis_checkpoint_enabled: bool = True  # 是否使用 Redis 检查点
    redis_checkpoint_ttl: int = 3600  # 检查点过期时间（秒）

    # 进程内缓存预算（L1）
    profile_cache_maxsize: int = 300
    exercise_cache_maxsize: int = 1200
    bkt_state_cache_maxsize: int = 2000
    api_cache_maxsize: int = 500
    profile_cache_ttl_seconds: int = 60
    exercise_cache_ttl_seconds: int = 600
    bkt_state_cache_ttl_seconds: int = 30
    api_cache_ttl_seconds: int = 5

    # 生命周期开关
    llm_pool_warmup_enabled: bool = False
    log_cleanup_enabled: bool = True
    db_pool_monitor_enabled: bool = True
    db_pool_monitor_interval_seconds: int = 30

    # 安全日志清理配置
    log_archive_after_days: int = 30     # 日志归档天数
    log_delete_after_days: int = 90      # 归档日志删除天数
    log_cleanup_batch_size: int = 500    # 清理批次大小
    log_max_count: int = 100000          # 日志总数告警阈值
    log_cleanup_interval_hours: int = 6  # 自动清理间隔（小时）

    # 告警通知配置
    alert_webhook_url: str = ""          # Webhook 通知地址（飞书/钉钉/企微/Slack）
    alert_smtp_host: str = ""            # SMTP 服务器地址
    alert_smtp_port: int = 587           # SMTP 端口
    alert_smtp_username: str = ""        # SMTP 用户名
    alert_smtp_password: str = ""        # SMTP 密码
    alert_from_email: str = ""           # 发件人邮箱
    alert_to_emails: list[str] = []      # 收件人邮箱列表

    # 存储后端配置
    # "local" = 本地文件系统，"qiniu" = 七牛云对象存储，"s3" = S3 兼容对象存储
    storage_backend: Literal["local", "qiniu", "s3"] = "local"

    # 七牛云对象存储配置
    qiniu_access_key: str = ""           # 七牛云 AccessKey
    qiniu_secret_key: str = ""           # 七牛云 SecretKey
    qiniu_bucket_name: str = ""          # 存储空间名称
    qiniu_domain: str = ""               # 绑定的访问域名（如 https://cdn.example.com）
    qiniu_private_bucket: bool = False   # 是否为私有空间（影响下载 URL 生成方式）
    qiniu_url_expire_seconds: int = 3600 # 私有空间下载链接有效期（秒）

    # S3 兼容对象存储配置（支持 AWS S3、阿里云 OSS、腾讯云 COS、MinIO、中国科技云等）
    s3_endpoint_url: str = ""            # S3 端点 URL（如 https://s3.cstcloud.cn）
    s3_access_key: str = ""              # S3 Access Key ID
    s3_secret_key: str = ""              # S3 Secret Access Key
    s3_bucket_name: str = ""             # 存储桶名称
    s3_region: str = "us-east-1"         # 区域（默认 us-east-1，某些服务可能不需要）
    s3_public_url_base: str = ""         # 公开访问的 CDN 域名（可选，如 https://cdn.example.com）
    s3_private_bucket: bool = False      # 是否为私有桶（影响下载 URL 生成方式）
    s3_url_expire_seconds: int = 3600    # 私有桶预签名 URL 有效期（秒）


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()


def validate_production_settings() -> None:
    """
    生产环境启动校验

    检查关键安全配置是否已正确设置。
    校验失败时记录严重警告，不阻止启动（允许运维逐步修复）。
    """
    warnings: list[str] = []

    if settings.jwt_secret_key in _INSECURE_JWT_SECRETS:
        warnings.append(
            "JWT_SECRET_KEY 使用了不安全的默认值！"
            "请设置一个强随机密钥: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
        )

    if settings.admin_password in _INSECURE_ADMIN_PASSWORDS:
        warnings.append(
            "ADMIN_PASSWORD 使用了弱密码！请设置一个强密码。"
        )

    if not settings.fernet_secret_key:
        warnings.append(
            "FERNET_SECRET_KEY 未设置！数据加密功能将不可用。"
            "生成方式: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )

    if settings.environment == "production":
        if settings.debug:
            warnings.append("生产环境不应启用 DEBUG 模式！")

        for w in warnings:
            logger.critical("⚠️ 安全配置警告: %s", w)

        if settings.jwt_secret_key in _INSECURE_JWT_SECRETS:
            logger.critical("生产环境禁止使用默认 JWT 密钥，应用将拒绝启动！")
            sys.exit(1)
    else:
        for w in warnings:
            logger.warning("安全配置提示（开发环境）: %s", w)
