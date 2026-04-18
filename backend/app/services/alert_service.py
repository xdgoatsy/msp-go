"""
管理员告警通知服务

当发生关键安全事件时，通过 Webhook / 邮件通知管理员。
支持告警聚合、去重和频率限制，避免告警风暴。

性能设计：
- 异步非阻塞发送，不影响主请求
- Redis 告警去重和频率限制
- 批量聚合短时间内的同类告警
"""

import hashlib
import logging
from datetime import datetime
from enum import Enum
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class AlertChannel(str, Enum):
    """告警通道"""
    WEBHOOK = "webhook"
    EMAIL = "email"


class AlertLevel(str, Enum):
    """告警级别（决定通知策略）"""
    WARNING = "warning"    # 仅记录，不主动通知
    ERROR = "error"        # Webhook 通知
    CRITICAL = "critical"  # Webhook + 邮件通知


class AlertService:
    """管理员告警通知服务"""

    # 告警频率限制（秒）
    RATE_LIMIT_WINDOW = 300  # 5 分钟内同类告警只发一次
    # 告警聚合窗口（秒）
    AGGREGATE_WINDOW = 60    # 1 分钟内同类告警聚合

    def __init__(self) -> None:
        self._webhook_url: str | None = None
        self._email_config: dict[str, Any] | None = None
        self._enabled: bool = False
        self._load_config()

    def _load_config(self) -> None:
        """从配置加载告警设置"""
        try:
            from app.config import settings
            self._webhook_url = getattr(settings, "alert_webhook_url", None) or None
            smtp_host = getattr(settings, "alert_smtp_host", None)
            if smtp_host:
                self._email_config = {
                    "host": smtp_host,
                    "port": getattr(settings, "alert_smtp_port", 587),
                    "username": getattr(settings, "alert_smtp_username", ""),
                    "password": getattr(settings, "alert_smtp_password", ""),
                    "from_addr": getattr(settings, "alert_from_email", ""),
                    "to_addrs": getattr(settings, "alert_to_emails", []),
                }
            self._enabled = bool(self._webhook_url or self._email_config)
            if self._enabled:
                logger.info("告警服务已启用")
            else:
                logger.info("告警服务未配置，已禁用")
        except Exception as e:
            logger.warning(f"告警服务配置加载失败: {e}")
            self._enabled = False

    async def send_alert(
        self,
        level: str,
        title: str,
        message: str,
        source: str = "system",
        extra: dict[str, Any] | None = None,
    ) -> bool:
        """
        发送告警通知

        Args:
            level: 告警级别 (warning/error/critical)
            title: 告警标题
            message: 告警详情
            source: 告警来源
            extra: 附加数据

        Returns:
            是否成功发送
        """
        if not self._enabled:
            return False

        # 频率限制检查
        alert_key = self._make_dedup_key(title, source)
        if await self._is_rate_limited(alert_key):
            logger.debug(f"告警被频率限制: {title}")
            return False

        alert_data = {
            "level": level,
            "title": title,
            "message": message,
            "source": source,
            "timestamp": datetime.now().isoformat(),
            "extra": extra or {},
        }

        sent = False

        # Webhook 通知（ERROR 及以上）
        if level in ("error", "critical") and self._webhook_url:
            sent = await self._send_webhook(alert_data)

        # 邮件通知（仅 CRITICAL）
        if level == "critical" and self._email_config:
            await self._send_email(alert_data)
            sent = True

        # 标记已发送（频率限制）
        if sent:
            await self._mark_sent(alert_key)

        return sent

    def _make_dedup_key(self, title: str, source: str) -> str:
        """生成告警去重键"""
        raw = f"{source}:{title}"
        return hashlib.md5(raw.encode()).hexdigest()

    async def _is_rate_limited(self, alert_key: str) -> bool:
        """检查告警是否被频率限制（使用 SET NX 原子操作）"""
        try:
            from app.infrastructure.cache.redis import get_redis_client_safe
            client = await get_redis_client_safe()
            if client is None:
                return False
            key = f"msp:alert:rate:{alert_key}"
            # SET NX EX 原子操作：如果 key 不存在则设置并返回 True
            result = await client.set(key, "1", ex=self.RATE_LIMIT_WINDOW, nx=True)
            # result 为 True 表示设置成功（key 不存在），即未被限制
            # result 为 None 表示 key 已存在，即被限制
            return result is None
        except Exception:
            return False

    async def _mark_sent(self, alert_key: str) -> None:
        """标记告警已发送（已在 _is_rate_limited 中通过 SET NX 原子完成）"""
        pass

    async def _send_webhook(self, data: dict[str, Any]) -> bool:
        """发送 Webhook 通知"""
        if not self._webhook_url:
            return False

        # 构建通用 Webhook 消息体（兼容飞书/钉钉/企业微信/Slack）
        level_emoji = {"warning": "⚠️", "error": "🔴", "critical": "🚨"}
        emoji = level_emoji.get(data["level"], "ℹ️")

        payload = {
            "msg_type": "text",
            "content": {
                "text": (
                    f"{emoji} [{data['level'].upper()}] {data['title']}\n"
                    f"来源: {data['source']}\n"
                    f"时间: {data['timestamp']}\n"
                    f"详情: {data['message'][:500]}"
                ),
            },
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(self._webhook_url, json=payload)
                if resp.status_code < 300:
                    logger.info(f"Webhook 告警发送成功: {data['title']}")
                    return True
                logger.warning(f"Webhook 告警发送失败: HTTP {resp.status_code}")
                return False
        except Exception as e:
            logger.error(f"Webhook 告警发送异常: {e}")
            return False

    async def _send_email(self, data: dict[str, Any]) -> bool:
        """发送邮件通知（异步非阻塞）"""
        if not self._email_config:
            return False

        try:
            from email.mime.text import MIMEText

            import aiosmtplib

            body = (
                f"告警级别: {data['level'].upper()}\n"
                f"告警标题: {data['title']}\n"
                f"告警来源: {data['source']}\n"
                f"告警时间: {data['timestamp']}\n"
                f"详细信息:\n{data['message']}\n"
            )

            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = f"[安全告警] {data['title']}"
            msg["From"] = self._email_config["from_addr"]
            msg["To"] = ", ".join(self._email_config["to_addrs"])

            await aiosmtplib.send(
                msg,
                hostname=self._email_config["host"],
                port=self._email_config["port"],
                username=self._email_config["username"],
                password=self._email_config["password"],
                use_tls=True,
            )
            logger.info(f"邮件告警发送成功: {data['title']}")
            return True
        except ImportError:
            logger.warning("aiosmtplib 未安装，跳过邮件告警")
            return False
        except Exception as e:
            logger.error(f"邮件告警发送异常: {e}")
            return False


# 单例
_alert_service: AlertService | None = None


def get_alert_service() -> AlertService:
    """获取告警服务单例"""
    global _alert_service
    if _alert_service is None:
        _alert_service = AlertService()
    return _alert_service
