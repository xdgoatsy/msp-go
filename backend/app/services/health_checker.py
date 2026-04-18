"""
健康检查服务

提供各服务的健康状态检查，支持延迟测量

特性：
- 多服务健康检查
- 延迟测量
- 连接池状态
- LLM 连接验证
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = logging.getLogger(__name__)

ServiceStatusType = Literal["running", "stopped", "warning"]


@dataclass
class ServiceStatus:
    """服务状态"""

    name: str
    status: ServiceStatusType
    latency_ms: float | None = None
    details: dict[str, Any] = field(default_factory=dict)


class BaseHealthChecker(ABC):
    """健康检查器基类"""

    def __init__(self, name: str):
        self.name = name

    async def check(self) -> ServiceStatus:
        """
        执行健康检查

        Returns:
            ServiceStatus 包含状态和延迟
        """
        try:
            start = time.perf_counter()
            status = await self._do_check()
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return ServiceStatus(
                name=self.name,
                status=status,
                latency_ms=latency_ms,
            )
        except Exception as e:
            logger.warning(f"健康检查失败 [{self.name}]: {e}")
            return ServiceStatus(
                name=self.name,
                status="stopped",
                latency_ms=None,
            )

    @abstractmethod
    async def _do_check(self) -> ServiceStatusType:
        """
        执行具体的健康检查逻辑

        Returns:
            状态字符串: "running", "stopped", "warning"

        Raises:
            Exception: 检查失败时抛出
        """
        pass


class WebServerHealthChecker(BaseHealthChecker):
    """Web 服务器健康检查（始终运行）"""

    def __init__(self):
        super().__init__("Web 服务器")

    async def _do_check(self) -> ServiceStatusType:
        # Web 服务器是自身，能执行到这里说明正在运行
        return "running"


class DatabaseHealthChecker(BaseHealthChecker):
    """数据库健康检查"""

    def __init__(self, db: AsyncSession):
        super().__init__("数据库")
        self.db = db

    async def _do_check(self) -> ServiceStatusType:
        await self.db.execute(select(1))
        return "running"


class RedisHealthChecker(BaseHealthChecker):
    """Redis 缓存健康检查"""

    def __init__(self):
        super().__init__("Redis 缓存")

    async def _do_check(self) -> ServiceStatusType:
        # 优先使用全局连接池
        try:
            from app.infrastructure.cache.redis import get_redis, get_redis_pool

            pool = get_redis_pool()
            if pool is not None:
                client = get_redis()
                await client.ping()
                return "running"
        except (RuntimeError, ImportError):
            pass

        # 回退：创建临时连接
        import redis.asyncio as redis

        client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
        )
        try:
            await client.ping()
            return "running"
        finally:
            await client.close()


class AIServiceHealthChecker(BaseHealthChecker):
    """AI 推理服务健康检查"""

    def __init__(self, db: AsyncSession):
        super().__init__("AI 推理服务")
        self.db = db

    async def _do_check(self) -> ServiceStatusType:
        # 检查是否有可用的 AI 渠道配置
        from app.infrastructure.database.models_ai_config import LLMProviderModel

        result = await self.db.execute(
            select(LLMProviderModel).where(LLMProviderModel.is_active.is_(True)).limit(1)
        )
        channel = result.scalar_one_or_none()

        if channel is None:
            return "warning"

        return "running"


class LLMPoolHealthChecker(BaseHealthChecker):
    """LLM 客户端池健康检查"""

    def __init__(self):
        super().__init__("LLM 客户端池")

    async def _do_check(self) -> ServiceStatusType:
        try:
            from app.agents.core.llm_client import get_llm_client_pool

            pool = get_llm_client_pool()
            health_status = pool.get_health_status()

            if not health_status:
                return "warning"

            healthy_count = sum(1 for s in health_status if s["is_healthy"])
            total_count = len(health_status)

            if healthy_count == 0:
                return "stopped"
            elif healthy_count < total_count:
                return "warning"
            else:
                return "running"
        except Exception:
            return "warning"


class HealthCheckService:
    """健康检查服务聚合"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._checkers: list[BaseHealthChecker] | None = None

    @property
    def checkers(self) -> list[BaseHealthChecker]:
        """懒加载检查器列表"""
        if self._checkers is None:
            self._checkers = [
                WebServerHealthChecker(),
                DatabaseHealthChecker(self.db),
                RedisHealthChecker(),
                AIServiceHealthChecker(self.db),
                LLMPoolHealthChecker(),
            ]
        return self._checkers

    async def check_all(self) -> list[ServiceStatus]:
        """
        检查所有服务状态

        Returns:
            服务状态列表
        """
        results = []
        for checker in self.checkers:
            status = await checker.check()
            results.append(status)
        return results

    async def check_one(self, name: str) -> ServiceStatus | None:
        """
        检查单个服务状态

        Args:
            name: 服务名称

        Returns:
            服务状态，未找到返回 None
        """
        for checker in self.checkers:
            if checker.name == name:
                return await checker.check()
        return None

    async def get_detailed_status(self) -> dict[str, Any]:
        """
        获取详细的健康状态

        Returns:
            包含所有服务状态和汇总信息的字典
        """
        statuses = await self.check_all()

        running_count = sum(1 for s in statuses if s.status == "running")
        warning_count = sum(1 for s in statuses if s.status == "warning")
        stopped_count = sum(1 for s in statuses if s.status == "stopped")

        # 计算总体状态
        if stopped_count > 0:
            overall_status = "unhealthy"
        elif warning_count > 0:
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        return {
            "status": overall_status,
            "summary": {
                "running": running_count,
                "warning": warning_count,
                "stopped": stopped_count,
                "total": len(statuses),
            },
            "services": [
                {
                    "name": s.name,
                    "status": s.status,
                    "latency_ms": s.latency_ms,
                    "details": s.details,
                }
                for s in statuses
            ],
            "version": settings.app_version,
        }


def get_health_check_service(db: AsyncSession) -> HealthCheckService:
    """获取健康检查服务实例"""
    return HealthCheckService(db)
