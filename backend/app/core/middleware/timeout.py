"""
请求超时中间件（纯 ASGI 实现）

为 HTTP 请求设置超时限制，防止长时间占用连接。
支持按路径前缀配置不同超时时间。
"""

import asyncio
import logging

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)


class TimeoutMiddleware:
    """
    请求超时中间件

    默认超时 30 秒，AI 接口 300 秒。
    超时后返回 504 Gateway Timeout。
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        default_timeout: float = 30.0,
        path_timeouts: dict[str, float] | None = None,
        exclude_paths: list[str] | None = None,
    ) -> None:
        self.app = app
        self.default_timeout = default_timeout
        self.path_timeouts = path_timeouts or {
            "/api/v1/session": 300.0,  # AI 会话接口
            "/api/v1/exercise/ai": 120.0,  # AI 出题
        }
        self.exclude_paths = exclude_paths or [
            "/health",
            "/metrics",
        ]

    def _get_timeout(self, path: str) -> float | None:
        """获取路径对应的超时时间"""
        for prefix in self.exclude_paths:
            if path.startswith(prefix):
                return None  # 不限制

        for prefix, timeout in self.path_timeouts.items():
            if path.startswith(prefix):
                return timeout

        return self.default_timeout

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        timeout = self._get_timeout(path)

        if timeout is None:
            await self.app(scope, receive, send)
            return

        # 追踪响应是否已开始（防止双重 http.response.start）
        response_started = False

        async def send_with_tracking(message: dict) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await asyncio.wait_for(
                self.app(scope, receive, send_with_tracking),
                timeout=timeout,
            )
        except TimeoutError:
            logger.warning(
                "请求超时: %s %s (timeout=%.1fs)",
                scope.get("method", "?"),
                path,
                timeout,
            )
            # 仅在响应尚未开始时发送 504
            if not response_started:
                response = JSONResponse(
                    status_code=504,
                    content={
                        "detail": "请求处理超时，请稍后重试",
                        "timeout": timeout,
                    },
                )
                await response(scope, receive, send)
            # 响应已开始则无法发送 504，仅记录日志
