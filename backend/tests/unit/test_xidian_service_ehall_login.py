"""
XidianService Ehall 登录探测单元测试
"""

import pytest

from app.services.xidian_service import XidianService, XidianServiceError


class _FakeResponse:
    def __init__(
        self,
        *,
        status_code: int,
        payload: dict[str, object] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}

    def json(self) -> dict[str, object]:
        return self._payload


class _FakeClient:
    def __init__(self, response: _FakeResponse) -> None:
        self._response = response
        self.last_url: str | None = None
        self.last_headers: dict[str, str] | None = None

    async def get_json(self, url: str, **kwargs: object) -> _FakeResponse:
        self.last_url = url
        headers = kwargs.get("headers")
        self.last_headers = headers if isinstance(headers, dict) else None
        return self._response


def _make_service() -> XidianService:
    return object.__new__(XidianService)


@pytest.mark.asyncio
class TestEnsureEhallLogin:
    async def test_monitor_request_contains_ehall_headers(self) -> None:
        service = _make_service()
        client = _FakeClient(
            _FakeResponse(status_code=200, payload={"hasLogin": True})
        )

        await service._ensure_ehall_login(client)

        assert client.last_headers is not None
        assert client.last_url is not None
        assert client.last_url.endswith("/jsonp/getAppUsageMonitor.json?type=uv")
        assert (
            client.last_headers.get("Referer")
            == "http://ehall.xidian.edu.cn/new/index_xd.html"
        )
        assert client.last_headers.get("Host") == "ehall.xidian.edu.cn"

    async def test_has_login_true_passes(self) -> None:
        service = _make_service()
        client = _FakeClient(
            _FakeResponse(status_code=200, payload={"hasLogin": True})
        )

        await service._ensure_ehall_login(client)

    async def test_has_login_false_raises_captcha_required(self) -> None:
        service = _make_service()
        client = _FakeClient(
            _FakeResponse(status_code=200, payload={"hasLogin": False})
        )

        with pytest.raises(XidianServiceError) as exc:
            await service._ensure_ehall_login(client)

        assert exc.value.code == "CAPTCHA_REQUIRED"

    async def test_redirect_raises_captcha_required(self) -> None:
        service = _make_service()
        client = _FakeClient(_FakeResponse(status_code=302))

        with pytest.raises(XidianServiceError) as exc:
            await service._ensure_ehall_login(client)

        assert exc.value.code == "CAPTCHA_REQUIRED"
