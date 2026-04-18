"""
请求 ID 中间件

为每个请求生成或透传唯一 ID，贯穿日志链路。
纯 ASGI 实现，无 BaseHTTPMiddleware 开销。

特性：
- 透传客户端 X-Request-ID 头（如果存在）
- 自动生成 UUID4 请求 ID（如果不存在）
- 注入到 contextvars 供日志使用
- 响应头中返回 X-Request-ID
"""

import logging
import uuid
from contextvars import ContextVar
from typing import Any

logger = logging.getLogger(__name__)

# 请求 ID 上下文变量（供日志和其他模块使用）
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    """获取当前请求 ID"""
    return request_id_var.get()


class RequestIDMiddleware:
    """
    请求 ID 中间件（纯 ASGI 实现）

    使用示例：
    ```python
    from app.core.middleware.request_id import RequestIDMiddleware

    app.add_middleware(RequestIDMiddleware)
    ```
    """

    def __init__(self, app: Any):
        self.app = app

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        # 从请求头中提取或生成 request_id
        headers = dict(scope.get("headers", []))
        request_id = (
            headers.get(b"x-request-id", b"").decode("utf-8", errors="ignore")
            or str(uuid.uuid4())
        )

        # 注入到 contextvars
        token = request_id_var.set(request_id)

        async def send_with_request_id(message: dict) -> None:
            """在响应头中注入 X-Request-ID"""
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            request_id_var.reset(token)
