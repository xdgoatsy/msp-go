"""
西电教务系统 HTTP 客户端

封装 IDS 登录、滑块验证码校验、Ehall/Yjspt 请求等底层能力。
"""

from __future__ import annotations

import asyncio
import base64
import logging
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class LoginPageData:
    hidden_inputs: dict[str, str]
    continue_inputs: dict[str, str]
    pwd_encrypt_salt: str | None
    error_message: str | None


@dataclass
class CaptchaData:
    big_image: str
    piece_image: str
    piece_y: int = 0  # 滑块 Y 坐标


class _IDSLoginParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hidden_inputs: dict[str, str] = {}
        self.continue_inputs: dict[str, str] = {}
        self.pwd_encrypt_salt: str | None = None
        self._in_continue_form = False
        self._capture_error = False
        self._error_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = {k: v for k, v in attrs if v is not None}
        tag_id = attrs_map.get("id")
        tag_type = attrs_map.get("type")
        tag_name = attrs_map.get("name") or tag_id

        if tag == "form" and tag_id == "continue":
            self._in_continue_form = True

        if tag_id == "showErrorTip":
            self._capture_error = True

        if tag == "input" and tag_name:
            value = attrs_map.get("value", "")
            if tag_id == "pwdEncryptSalt":
                self.pwd_encrypt_salt = value
            if tag_type == "hidden":
                self.hidden_inputs[tag_name] = value
            if self._in_continue_form:
                self.continue_inputs[tag_name] = value

    def handle_data(self, data: str) -> None:
        if self._capture_error:
            text = data.strip()
            if text:
                self._error_parts.append(text)

    def handle_endtag(self, tag: str) -> None:
        if tag == "form" and self._in_continue_form:
            self._in_continue_form = False
        if tag in {"div", "span", "p"} and self._capture_error:
            self._capture_error = False

    @property
    def error_message(self) -> str | None:
        if not self._error_parts:
            return None
        return " ".join(self._error_parts).strip()


def parse_login_page(html: str) -> LoginPageData:
    parser = _IDSLoginParser()
    parser.feed(html)
    return LoginPageData(
        hidden_inputs=parser.hidden_inputs,
        continue_inputs=parser.continue_inputs,
        pwd_encrypt_salt=parser.pwd_encrypt_salt,
        error_message=parser.error_message,
    )


class XidianClient:
    def __init__(
        self,
        *,
        cookies: list[dict[str, Any]] | None = None,
        connect_timeout: float | None = None,
        read_timeout: float | None = None,
    ) -> None:
        headers = {
            "User-Agent": settings.xidian_user_agent,
            "Accept": "*/*",
        }
        timeout = httpx.Timeout(
            connect=connect_timeout or settings.xidian_http_connect_timeout,
            read=read_timeout or settings.xidian_http_read_timeout,
            write=10.0,
            pool=10.0,
        )
        self._client = httpx.AsyncClient(
            headers=headers,
            follow_redirects=False,
            timeout=timeout,
        )
        self._retry_count = settings.xidian_sync_retry_count
        if cookies:
            self._apply_cookies(cookies)

    async def close(self) -> None:
        await self._client.aclose()

    def _apply_cookies(self, cookies: list[dict[str, Any]]) -> None:
        for item in cookies:
            cookie_kwargs: dict[str, str] = {}
            domain = item.get("domain")
            path = item.get("path")
            if isinstance(domain, str) and domain:
                cookie_kwargs["domain"] = domain
            if isinstance(path, str) and path:
                cookie_kwargs["path"] = path
            self._client.cookies.set(
                item.get("name", ""),
                item.get("value", ""),
                **cookie_kwargs,
            )

    def export_cookies(self) -> list[dict[str, Any]]:
        exported: list[dict[str, Any]] = []
        for cookie in self._client.cookies.jar:
            exported.append(
                {
                    "name": cookie.name,
                    "value": cookie.value,
                    "domain": cookie.domain,
                    "path": cookie.path,
                    "expires": cookie.expires,
                    "secure": cookie.secure,
                }
            )
        return exported

    async def get_login_page(self, service: str | None) -> LoginPageData:
        url = f"{settings.xidian_ids_base}/authserver/login"
        response = await self._client.get(url, params={"service": service} if service else None)
        response.raise_for_status()
        return parse_login_page(response.text)

    async def open_slider_captcha(self) -> CaptchaData:
        url = f"{settings.xidian_ids_base}/authserver/common/openSliderCaptcha.htl"
        response = await self._client.get(
            url,
            params={"_": str(int(datetime.now().timestamp() * 1000))},
        )
        response.raise_for_status()
        data = response.json()
        # 打印 API 返回的所有字段用于调试
        logger.info(f"Captcha API response keys: {list(data.keys())}")
        logger.info(f"Captcha API response (excluding images): { {k: v for k, v in data.items() if k not in ('bigImage', 'smallImage')} }")
        # 尝试获取 Y 坐标，可能的字段名：y, offsetY, top, tagWidth 等
        piece_y = int(data.get("y", 0) or data.get("offsetY", 0) or data.get("top", 0))
        return CaptchaData(
            big_image=data.get("bigImage", ""),
            piece_image=data.get("smallImage", ""),
            piece_y=piece_y,
        )

    async def verify_slider_captcha(self, canvas_length: int, move_length: int) -> bool:
        url = f"{settings.xidian_ids_base}/authserver/common/verifySliderCaptcha.htl"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
            "Origin": settings.xidian_ids_base,
        }
        response = await self._client.post(
            url,
            data={"canvasLength": canvas_length, "moveLength": move_length},
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("errorCode") == 1

    async def submit_login(
        self,
        form_data: dict[str, Any],
    ) -> httpx.Response:
        url = f"{settings.xidian_ids_base}/authserver/login"
        return await self._client.post(url, data=form_data)

    async def follow_redirects(self, start_url: str, headers: dict[str, str] | None = None) -> httpx.Response:
        url = start_url
        response = await self._request_with_retry("GET", url, headers=headers)
        for _ in range(10):
            if response.status_code not in (301, 302):
                return response
            location = response.headers.get("location")
            if not location:
                return response
            url = urljoin(url, location)
            response = await self._request_with_retry("GET", url, headers=headers)
        return response

    async def get_json(self, url: str, *, params: dict[str, Any] | None = None, data: Any = None, headers: dict[str, str] | None = None) -> httpx.Response:
        if data is None:
            return await self._request_with_retry("GET", url, params=params, headers=headers)
        return await self._request_with_retry("POST", url, params=params, data=data, headers=headers)

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(self._retry_count + 1):
            try:
                return await self._client.request(method, url, **kwargs)
            except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as exc:
                last_exc = exc
                if attempt < self._retry_count:
                    delay = 1.0 * (2 ** attempt)
                    logger.warning(
                        "请求 %s %s 失败 (第%d次): %s, %.1fs 后重试",
                        method, url, attempt + 1, exc, delay,
                    )
                    await asyncio.sleep(delay)
        raise last_exc  # type: ignore[misc]

    @staticmethod
    def encode_base64(raw: bytes) -> str:
        return base64.b64encode(raw).decode()
