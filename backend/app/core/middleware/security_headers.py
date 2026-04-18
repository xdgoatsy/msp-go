"""
安全响应头中间件（纯 ASGI 实现）

添加 OWASP 推荐的安全响应头，防止常见 Web 攻击。
使用纯 ASGI 协议而非 BaseHTTPMiddleware，避免性能开销。
"""


from starlette.types import ASGIApp, Receive, Scope, Send


class SecurityHeadersMiddleware:
    """
    安全响应头中间件

    添加以下安全头：
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 0 (现代浏览器推荐禁用，依赖 CSP)
    - Referrer-Policy: strict-origin-when-cross-origin
    - Content-Security-Policy: 基础策略
    - Permissions-Policy: 限制浏览器功能
    - Cache-Control: API 响应不缓存
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        csp_policy: str | None = None,
        exclude_paths: list[str] | None = None,
    ) -> None:
        self.app = app
        self.exclude_paths = exclude_paths or []
        self.csp = csp_policy or (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        )
        # 预编码安全头（避免每次请求重复编码）
        self._security_headers: list[tuple[bytes, bytes]] = [
            (b"x-content-type-options", b"nosniff"),
            (b"x-frame-options", b"DENY"),
            (b"x-xss-protection", b"0"),
            (b"referrer-policy", b"strict-origin-when-cross-origin"),
            (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
            (b"content-security-policy", self.csp.encode()),
        ]
        self._api_cache_header = (b"cache-control", b"no-store, no-cache, must-revalidate")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")

        # 排除路径
        if any(path.startswith(p) for p in self.exclude_paths):
            await self.app(scope, receive, send)
            return

        is_api = path.startswith("/api/")

        async def send_with_headers(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(self._security_headers)
                if is_api:
                    headers.append(self._api_cache_header)
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)
