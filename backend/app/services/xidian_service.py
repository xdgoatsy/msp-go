"""
西电教务集成服务
"""

from __future__ import annotations

import asyncio
import base64
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.base import CipherContext
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.core.cache import CacheManager
from app.config import settings
from app.infrastructure.database.models import XidianAccountModel, XidianSnapshotModel
from app.integrations.xidian.client import CaptchaData, XidianClient, parse_login_page
from app.services.encryption_service import EncryptionService, get_encryption_service

logger = logging.getLogger(__name__)

EHALL_APP_ID_CLASSTABLE = "4770397878132218"
EHALL_APP_ID_SCORE = "4768574631264620"
EHALL_APP_ID_EXAM = "4768687067472349"


@dataclass
class XidianChallenge:
    challenge_id: str
    captcha: CaptchaData


class XidianServiceError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


_xidian_cache: CacheManager | None = None
_fallback_cache: dict[str, tuple[datetime, Any]] = {}
_user_locks: dict[str, asyncio.Lock] = {}


def get_xidian_cache() -> CacheManager:
    global _xidian_cache
    if _xidian_cache is None:
        _xidian_cache = CacheManager(
            prefix="xidian",
            default_ttl=settings.xidian_session_ttl,
        )
    return _xidian_cache


def _fallback_set(key: str, value: Any, ttl: int | None) -> None:
    expires_at = datetime.now() + timedelta(seconds=ttl or settings.xidian_session_ttl)
    _fallback_cache[key] = (expires_at, value)


def _fallback_get(key: str) -> Any | None:
    cached = _fallback_cache.get(key)
    if not cached:
        return None
    expires_at, value = cached
    if expires_at < datetime.now():
        _fallback_cache.pop(key, None)
        return None
    return value


def _fallback_delete(key: str) -> None:
    _fallback_cache.pop(key, None)


def _aes_encrypt(password: str, salt: str) -> str:
    prefix = (
        "xidianscriptsxduxidianscriptsxduxidianscriptsxduxidianscriptsxdu"
    )
    data = (prefix + password).encode("utf-8")
    pad_len = 16 - len(data) % 16
    data += bytes([pad_len]) * pad_len
    key = salt.encode("utf-8")
    iv = b"xidianscriptsxdu"
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor: CipherContext = cipher.encryptor()
    encrypted = encryptor.update(data) + encryptor.finalize()
    return base64.b64encode(encrypted).decode()


def _build_week_list(week_str: str) -> list[bool]:
    return [ch == "1" for ch in str(week_str)]


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def json_dumps(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False)


def _get_user_lock(user_id: str) -> asyncio.Lock:
    if user_id not in _user_locks:
        _user_locks[user_id] = asyncio.Lock()
    return _user_locks[user_id]


class XidianService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.encryption: EncryptionService = get_encryption_service()
        self.cache = get_xidian_cache()

    async def start_binding(self) -> XidianChallenge:
        service_url = (
            f"{settings.xidian_ehall_base}/login"
            f"?service={settings.xidian_ehall_base}/new/index.html"
        )
        client = XidianClient()
        try:
            login_page = await client.get_login_page(service_url)
            if not login_page.pwd_encrypt_salt:
                raise XidianServiceError("LOGIN_PAGE_INVALID", "无法解析登录页面")
            captcha = await client.open_slider_captcha()
            challenge_id = str(uuid4())
            await self._cache_set(
                f"challenge:{challenge_id}",
                {
                    "service_url": service_url,
                    "hidden_inputs": login_page.hidden_inputs,
                    "pwd_encrypt_salt": login_page.pwd_encrypt_salt,
                    "cookies": client.export_cookies(),
                    "created_at": datetime.now().isoformat(),
                },
                ttl=settings.xidian_challenge_ttl,
            )
            return XidianChallenge(challenge_id=challenge_id, captcha=captcha)
        finally:
            await client.close()

    async def complete_binding(
        self,
        *,
        user_id: str,
        challenge_id: str,
        username: str | None,
        password: str | None,
        slider_position: float,
    ) -> XidianAccountModel:
        challenge = await self._cache_get(f"challenge:{challenge_id}")
        if not challenge:
            raise XidianServiceError(
                "CHALLENGE_EXPIRED",
                "验证码已过期，请重新获取",
                status_code=400,
            )

        account = await self._get_account(user_id)
        if not username:
            if not account:
                raise XidianServiceError("ACCOUNT_REQUIRED", "缺少账号信息")
            username = account.username

        if not password:
            if not account or not account.encrypted_password:
                raise XidianServiceError("PASSWORD_REQUIRED", "请输入密码完成绑定")
            password = self.encryption.decrypt(account.encrypted_password)

        client = XidianClient(cookies=challenge.get("cookies"))
        try:
            verified = await client.verify_slider_captcha(
                canvas_length=settings.xidian_captcha_width,
                move_length=int(slider_position * settings.xidian_captcha_width),
            )
            if not verified:
                raise XidianServiceError("CAPTCHA_FAILED", "验证码校验失败")

            form_data = dict(challenge.get("hidden_inputs") or {})
            form_data.pop("pwdEncryptSalt", None)
            salt = challenge.get("pwd_encrypt_salt")
            if not salt:
                raise XidianServiceError("LOGIN_PAGE_INVALID", "登录参数缺失")
            form_data.update(
                {
                    "username": username,
                    "password": _aes_encrypt(password, salt),
                    "rememberMe": "true",
                    "cllt": "userNameLogin",
                    "dllt": "generalLogin",
                    "_eventId": "submit",
                }
            )

            response = await client.submit_login(form_data)
            if response.status_code in (301, 302):
                location = response.headers.get("location")
                if location:
                    await client.follow_redirects(location)
            elif response.status_code == 200:
                page = parse_login_page(response.text)
                if page.error_message:
                    raise XidianServiceError("PASSWORD_WRONG", page.error_message, 401)
                if page.continue_inputs:
                    follow_resp = await client.submit_login(page.continue_inputs)
                    if follow_resp.status_code in (301, 302):
                        location = follow_resp.headers.get("location")
                        if location:
                            await client.follow_redirects(location)
                    else:
                        raise XidianServiceError("LOGIN_FAILED", "登录失败，请重试")
                else:
                    raise XidianServiceError("LOGIN_FAILED", "登录失败，请重试")
            elif response.status_code == 401:
                page = parse_login_page(response.text)
                msg = page.error_message or "用户名或密码有误"
                raise XidianServiceError("PASSWORD_WRONG", msg, 401)
            else:
                raise XidianServiceError("LOGIN_FAILED", "登录失败，请稍后重试")

            await self._cache_set(
                f"session:{user_id}",
                {"cookies": client.export_cookies()},
                ttl=settings.xidian_session_ttl,
            )
            await self._cache_delete(f"challenge:{challenge_id}")

            is_postgraduate = await self._detect_postgraduate(client)
            encrypted_password = self.encryption.encrypt(password)

            if account:
                account.username = username
                account.encrypted_password = encrypted_password
                account.is_postgraduate = is_postgraduate
                account.status = "active"
                account.last_verified_at = datetime.now()
                account.session_cookies = client.export_cookies()
                account.cookies_updated_at = datetime.now()
                self.db.add(account)
            else:
                account = XidianAccountModel(
                    user_id=user_id,
                    username=username,
                    encrypted_password=encrypted_password,
                    is_postgraduate=is_postgraduate,
                    status="active",
                    last_verified_at=datetime.now(),
                    session_cookies=client.export_cookies(),
                    cookies_updated_at=datetime.now(),
                )
                self.db.add(account)
            await self.db.commit()
            await self.db.refresh(account)
            return account
        finally:
            await client.close()

    async def get_binding_status(self, user_id: str) -> dict[str, Any]:
        account = await self._get_account(user_id)
        if not account:
            return {"is_bound": False}

        last_sync_stmt = select(func.max(XidianSnapshotModel.fetched_at)).where(
            XidianSnapshotModel.user_id == user_id
        )
        result = await self.db.execute(last_sync_stmt)
        last_sync_at = result.scalar_one_or_none()

        return {
            "is_bound": True,
            "username": account.username,
            "is_postgraduate": account.is_postgraduate,
            "last_verified_at": account.last_verified_at,
            "last_sync_at": last_sync_at,
        }

    async def unbind(self, user_id: str) -> None:
        account = await self._get_account(user_id)
        if not account:
            return

        await self.db.execute(
            delete(XidianSnapshotModel).where(XidianSnapshotModel.user_id == user_id)
        )
        await self.db.delete(account)
        await self.db.commit()
        await self._cache_delete(f"session:{user_id}")

    async def get_snapshot(self, user_id: str, data_type: str) -> dict[str, Any]:
        """直接返回数据库中最近的快照数据，不触发同步"""
        snapshot = await self._get_latest_snapshot(user_id, data_type)
        if not snapshot:
            raise XidianServiceError("NO_SNAPSHOT", "暂无缓存数据", 404)
        result = dict(snapshot.payload)
        result["is_cached"] = True
        result["cached_at"] = snapshot.fetched_at.isoformat() if snapshot.fetched_at else None
        return result

    async def sync_classtable(self, user_id: str) -> dict[str, Any]:
        async with _get_user_lock(user_id):
            return await self._sync_with_retry(user_id, "classtable")

    async def sync_exams(self, user_id: str) -> dict[str, Any]:
        async with _get_user_lock(user_id):
            return await self._sync_with_retry(user_id, "exam")

    async def sync_scores(self, user_id: str) -> dict[str, Any]:
        async with _get_user_lock(user_id):
            return await self._sync_with_retry(user_id, "score")

    async def _sync_with_retry(self, user_id: str, data_type: str) -> dict[str, Any]:
        account = await self._require_account(user_id)
        last_error: Exception | None = None

        # 尝试两轮：第一轮用 Redis Cookie，第二轮用数据库持久化 Cookie
        for attempt in range(2):
            try:
                cookies = await self._load_session_cookies(user_id, from_db=(attempt == 1))
                client = XidianClient(cookies=cookies)
                try:
                    data = await self._do_sync(client, account, data_type)
                    # 成功后保活：将最新 Cookie 写回 Redis + DB
                    await self._persist_cookies(user_id, client)
                    await self._save_snapshot(user_id, data_type, data, data.get("semester_code"))
                    return data
                finally:
                    await client.close()
            except XidianServiceError as e:
                last_error = e
                if e.code == "CAPTCHA_REQUIRED" and attempt == 0:
                    logger.info("用户 %s 同步 %s: Redis Cookie 过期，尝试从数据库加载", user_id, data_type)
                    continue
                break
            except Exception as e:
                last_error = e
                break

        # 同步失败，尝试快照降级
        if settings.xidian_snapshot_fallback_enabled:
            snapshot = await self._get_latest_snapshot(user_id, data_type)
            if snapshot:
                logger.info("用户 %s 同步 %s 失败，返回快照数据", user_id, data_type)
                result = dict(snapshot.payload)
                result["is_cached"] = True
                result["cached_at"] = snapshot.fetched_at.isoformat() if snapshot.fetched_at else None
                return result

        if last_error:
            raise last_error
        raise XidianServiceError("SYNC_FAILED", "同步失败，请稍后重试")

    async def _do_sync(
        self, client: XidianClient, account: XidianAccountModel, data_type: str
    ) -> dict[str, Any]:
        if data_type == "classtable":
            if account.is_postgraduate:
                return await self._fetch_classtable_yjspt(client, account.username)
            return await self._fetch_classtable_ehall(client, account.username)
        elif data_type == "exam":
            if account.is_postgraduate:
                return await self._fetch_exams_yjspt(client, account.username)
            return await self._fetch_exams_ehall(client, account.username)
        elif data_type == "score":
            if account.is_postgraduate:
                return await self._fetch_scores_yjspt(client, account.username)
            return await self._fetch_scores_ehall(client, account.username)
        raise XidianServiceError("INVALID_DATA_TYPE", f"不支持的数据类型: {data_type}")

    async def _get_account(self, user_id: str) -> XidianAccountModel | None:
        stmt = select(XidianAccountModel).where(XidianAccountModel.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _require_account(self, user_id: str) -> XidianAccountModel:
        account = await self._get_account(user_id)
        if not account:
            raise XidianServiceError("NOT_BOUND", "请先绑定西电账号", 400)
        return account

    async def _load_session_cookies(self, user_id: str, *, from_db: bool = False) -> list[dict[str, Any]]:
        if not from_db:
            # 快速路径：先查 Redis 缓存
            cached = await self._cache_get(f"session:{user_id}")
            if cached and cached.get("cookies"):
                return cached.get("cookies")

        # Redis 无数据或强制从 DB 加载 → 从数据库加载持久化 Cookie
        account = await self._get_account(user_id)
        if account and account.session_cookies:
            logger.info("用户 %s: 从数据库加载持久化 Cookie", user_id)
            # 回填 Redis 缓存
            await self._cache_set(
                f"session:{user_id}",
                {"cookies": account.session_cookies},
                ttl=settings.xidian_session_ttl,
            )
            return account.session_cookies

        # 数据库也无数据
        raise XidianServiceError(
            "CAPTCHA_REQUIRED",
            "会话已过期，请重新验证",
            409,
        )

    async def _save_snapshot(
        self,
        user_id: str,
        data_type: str,
        payload: dict[str, Any],
        semester_code: str | None,
    ) -> None:
        snapshot = XidianSnapshotModel(
            user_id=user_id,
            data_type=data_type,
            semester_code=semester_code,
            payload=payload,
            fetched_at=datetime.now(),
        )
        self.db.add(snapshot)
        await self.db.commit()

    async def _persist_cookies(self, user_id: str, client: XidianClient) -> None:
        """将 client 当前的 Cookie 同时写入 Redis 缓存和数据库（双写保活）"""
        cookies = client.export_cookies()
        # 写入 Redis
        await self._cache_set(
            f"session:{user_id}",
            {"cookies": cookies},
            ttl=settings.xidian_session_ttl,
        )
        # 写入数据库
        account = await self._get_account(user_id)
        if account:
            account.session_cookies = cookies
            account.cookies_updated_at = datetime.now()
            self.db.add(account)
            await self.db.commit()

    async def _get_latest_snapshot(
        self, user_id: str, data_type: str
    ) -> XidianSnapshotModel | None:
        """查询数据库中最近一次快照"""
        stmt = (
            select(XidianSnapshotModel)
            .where(
                XidianSnapshotModel.user_id == user_id,
                XidianSnapshotModel.data_type == data_type,
            )
            .order_by(XidianSnapshotModel.fetched_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _cache_get(self, key: str) -> Any | None:
        cached = await self.cache.get(key)
        if cached is not None:
            return cached
        return _fallback_get(key)

    async def _cache_set(self, key: str, value: Any, ttl: int | None = None) -> None:
        ok = await self.cache.set(key, value, ttl)
        if not ok:
            _fallback_set(key, value, ttl)

    async def _cache_delete(self, key: str) -> None:
        await self.cache.delete(key)
        _fallback_delete(key)

    async def _detect_postgraduate(self, client: XidianClient) -> bool | None:
        try:
            portal_url = (
                f"{settings.xidian_yjspt_base}/gsapp/"
                "sys/yjsemaphome/portal/index.do"
            )
            response = await client.follow_redirects(portal_url)
            if response.status_code in (301, 302):
                return None
            data_rsp = await client.get_json(
                f"{settings.xidian_yjspt_base}/gsapp/"
                "sys/yjsemaphome/modules/pubWork/getCanVisitAppList.do"
            )
            if data_rsp.status_code in (301, 302):
                return None
            data = data_rsp.json()
            return data.get("res") is not None
        except Exception as e:
            logger.warning(f"检测研究生身份失败: {e}")
            return None

    async def _fetch_classtable_ehall(
        self, client: XidianClient, username: str
    ) -> dict[str, Any]:
        await self._ensure_ehall_login(client)

        referer_headers = self._ehall_headers()
        app_location = await self._use_ehall_app(client, EHALL_APP_ID_CLASSTABLE)
        await client.get_json(app_location, headers=referer_headers)

        semester_code = await self._get_current_semester_ehall(client)
        term_start_day = await self._get_term_start_day_ehall(client, semester_code)

        response = await client.get_json(
            f"{settings.xidian_ehall_base}/jwapp/sys/wdkb/modules/xskcb/xskcb.do",
            data={"XNXQDM": semester_code, "XH": username},
            headers=referer_headers,
        )
        self._ensure_not_redirected(response)
        data = response.json().get("datas", {}).get("xskcb", {})
        if data.get("extParams", {}).get("code") != 1:
            msg = data.get("extParams", {}).get("msg", "课表查询失败")
            if "课程未发布" in str(msg):
                return {
                    "semester_code": semester_code,
                    "term_start_day": term_start_day,
                    "semester_length": 1,
                    "class_detail": [],
                    "not_arranged": [],
                    "time_arrangement": [],
                    "class_changes": [],
                }
            raise XidianServiceError("DATA_FETCH_FAILED", msg)

        rows = data.get("rows", [])
        class_detail: list[dict[str, Any]] = []
        time_arrangement: list[dict[str, Any]] = []
        detail_index: dict[tuple[str, str | None, str | None], int] = {}
        semester_length = 1

        for row in rows:
            name = row.get("KCM") or row.get("KCMC") or ""
            code = row.get("KCH")
            number = row.get("KXH")
            key = (name, code, number)
            if key not in detail_index:
                detail_index[key] = len(class_detail)
                class_detail.append({"name": name, "code": code, "number": number})

            week_str = str(row.get("SKZC", ""))
            week_list = _build_week_list(week_str)
            semester_length = max(semester_length, len(week_list))
            time_arrangement.append(
                {
                    "source": "school",
                    "index": detail_index[key],
                    "start": _safe_int(row.get("KSJC")),
                    "stop": _safe_int(row.get("JSJC")),
                    "day": _safe_int(row.get("SKXQ")),
                    "week_list": week_list,
                    "teacher": row.get("SKJS"),
                    "classroom": row.get("JASMC"),
                }
            )

        not_arranged_rsp = await client.get_json(
            f"{settings.xidian_ehall_base}/jwapp/sys/wdkb/modules/xskcb/cxxsllsywpk.do",
            data={"XNXQDM": semester_code, "XH": username},
            headers=referer_headers,
        )
        self._ensure_not_redirected(not_arranged_rsp)
        not_arranged_rows = (
            not_arranged_rsp.json().get("datas", {}).get("cxxsllsywpk", {}).get("rows", [])
        )
        not_arranged = [
            {
                "name": row.get("KCM"),
                "code": row.get("KCH"),
                "number": row.get("KXH"),
                "teacher": row.get("SKJS"),
            }
            for row in not_arranged_rows
        ]

        class_changes = await self._fetch_class_changes(client, semester_code)

        return {
            "semester_code": semester_code,
            "term_start_day": term_start_day,
            "semester_length": semester_length,
            "class_detail": class_detail,
            "not_arranged": not_arranged,
            "time_arrangement": time_arrangement,
            "class_changes": class_changes,
        }

    async def _fetch_classtable_yjspt(
        self, client: XidianClient, username: str
    ) -> dict[str, Any]:
        semester_rsp = await client.get_json(
            f"{settings.xidian_yjspt_base}/gsapp/sys/wdkbapp/modules/xskcb/kfdxnxqcx.do",
            data={},
        )
        self._ensure_not_redirected(semester_rsp)
        semester_code = (
            semester_rsp.json()
            .get("datas", {})
            .get("kfdxnxqcx", {})
            .get("rows", [{}])[0]
            .get("WID")
        )

        now = datetime.now()
        week_rsp = await client.get_json(
            f"{settings.xidian_yjspt_base}/gsapp/sys/yjsemaphome/portal/queryRcap.do",
            data={"day": now.strftime("%Y%m%d")},
        )
        self._ensure_not_redirected(week_rsp)
        week_data = week_rsp.json()
        term_start_day = now.strftime("%Y-%m-%d")
        match = re.search(r"[0-9]+", str(week_data.get("xnxq")))
        if match:
            current_week = int(match.group(0))
            week_day = now.weekday()
            term_start = now + timedelta(days=(1 - current_week) * 7 - week_day)
            term_start_day = term_start.strftime("%Y-%m-%d")

        class_rsp = await client.get_json(
            f"{settings.xidian_yjspt_base}/gsapp/sys/wdkbapp/modules/xskcb/xspkjgcx.do",
            data={"XNXQDM": semester_code},
        )
        self._ensure_not_redirected(class_rsp)
        class_data = class_rsp.json()
        if class_data.get("code") != "0":
            msg = class_data.get("msg", "课表查询失败")
            if "课程未发布" in str(msg):
                return {
                    "semester_code": semester_code,
                    "term_start_day": term_start_day,
                    "semester_length": 1,
                    "class_detail": [],
                    "not_arranged": [],
                    "time_arrangement": [],
                    "class_changes": [],
                }
            raise XidianServiceError("DATA_FETCH_FAILED", msg)

        rows = class_data.get("datas", {}).get("xspkjgcx", {}).get("rows", [])
        class_detail: list[dict[str, Any]] = []
        time_arrangement: list[dict[str, Any]] = []
        detail_index: dict[tuple[str, str | None], int] = {}
        semester_length = 1

        for row in rows:
            name = row.get("KCMC", "")
            code = row.get("KCDM")
            key = (name, code)
            if key not in detail_index:
                detail_index[key] = len(class_detail)
                class_detail.append({"name": name, "code": code, "number": None})

            week_str = str(row.get("ZCBH", ""))
            week_list = _build_week_list(week_str)
            semester_length = max(semester_length, len(week_list))
            time_arrangement.append(
                {
                    "source": "school",
                    "index": detail_index[key],
                    "start": _safe_int(row.get("KSJCDM")),
                    "stop": _safe_int(row.get("JSJCDM")),
                    "day": _safe_int(row.get("XQ")),
                    "week_list": week_list,
                    "teacher": row.get("JSXM"),
                    "classroom": row.get("JASMC"),
                }
            )

        not_arranged_rsp = await client.get_json(
            f"{settings.xidian_yjspt_base}/gsapp/sys/wdkbapp/modules/xskcb/xswsckbkc.do",
            data={"XNXQDM": semester_code, "XH": username},
        )
        self._ensure_not_redirected(not_arranged_rsp)
        not_arranged_rows = (
            not_arranged_rsp.json()
            .get("datas", {})
            .get("xswsckbkc", {})
            .get("rows", [])
        )
        not_arranged = [
            {
                "name": row.get("KCMC"),
                "code": row.get("KCDM"),
                "number": None,
                "teacher": row.get("SKJS"),
            }
            for row in not_arranged_rows
        ]

        return {
            "semester_code": semester_code,
            "term_start_day": term_start_day,
            "semester_length": semester_length,
            "class_detail": class_detail,
            "not_arranged": not_arranged,
            "time_arrangement": time_arrangement,
            "class_changes": [],
        }

    async def _fetch_scores_ehall(self, client: XidianClient, username: str) -> dict[str, Any]:
        await self._ensure_ehall_login(client)
        referer_headers = self._ehall_headers()
        app_location = await self._use_ehall_app(client, EHALL_APP_ID_SCORE)
        await client.get_json(app_location, headers=referer_headers)

        query_setting = {
            "name": "SFYX",
            "value": "1",
            "linkOpt": "and",
            "builder": "m_value_equal",
        }
        response = await client.get_json(
            f"{settings.xidian_ehall_base}/jwapp/sys/cjcx/modules/cjcx/xscjcx.do",
            data={
                "*json": 1,
                "querySetting": json_dumps(query_setting),
                "*order": "+XNXQDM,KCH,KXH",
                "pageSize": 1000,
                "pageNumber": 1,
            },
            headers=referer_headers,
        )
        self._ensure_not_redirected(response)
        data = response.json()
        rows = data.get("datas", {}).get("xscjcx", {}).get("rows", [])
        scores = [
            {
                "name": row.get("XSKCM"),
                "score": row.get("ZCJ"),
                "semester_code": row.get("XNXQDM"),
                "credit": row.get("XF"),
                "class_status": row.get("XGXKLBDM_DISPLAY")
                or row.get("KCXZDM_DISPLAY"),
                "class_type": row.get("KCLBDM_DISPLAY"),
                "score_status": row.get("CXCKDM_DISPLAY"),
                "score_type_code": _safe_int(row.get("DJCJLXDM")),
                "level": row.get("DJCJMC"),
                "is_passed": row.get("SFJG"),
                "class_id": row.get("JXBID"),
            }
            for row in rows
        ]
        semester_code = rows[0].get("XNXQDM") if rows else None
        return {"semester_code": semester_code, "scores": scores}

    async def _fetch_scores_yjspt(self, client: XidianClient, username: str) -> dict[str, Any]:
        response = await client.get_json(
            f"{settings.xidian_yjspt_base}/gsapp/sys/wdcjapp/modules/wdcj/xscjcx.do",
            data={"querySetting": [], "pageSize": 1000, "pageNumber": 1},
        )
        self._ensure_not_redirected(response)
        data = response.json()
        ext = data.get("datas", {}).get("xscjcx", {}).get("extParams", {})
        if ext.get("code") != 1:
            raise XidianServiceError("DATA_FETCH_FAILED", ext.get("msg", "成绩查询失败"))
        rows = data.get("datas", {}).get("xscjcx", {}).get("rows", [])
        scores = [
            {
                "name": row.get("KCMC"),
                "score": row.get("DYBFZCJ"),
                "semester_code": row.get("XNXQDM_DISPLAY"),
                "credit": row.get("XF"),
                "class_status": row.get("KCLBMC"),
                "class_type": row.get("KCLBMC"),
                "score_status": row.get("KSXZDM_DISPLAY"),
                "score_type_code": _safe_int(row.get("CJFZDM")),
                "level": row.get("CJXSZ"),
                "is_passed": row.get("SFJG"),
                "class_id": row.get("KCDM"),
            }
            for row in rows
        ]
        semester_code = rows[0].get("XNXQDM_DISPLAY") if rows else None
        return {"semester_code": semester_code, "scores": scores}

    async def _fetch_exams_ehall(self, client: XidianClient, username: str) -> dict[str, Any]:
        await self._ensure_ehall_login(client)
        referer_headers = self._ehall_headers()
        app_location = await self._use_ehall_app(client, EHALL_APP_ID_EXAM)
        await client.get_json(app_location, headers=referer_headers)

        semester_code = await self._get_current_semester_ehall(client)
        arranged_rsp = await client.get_json(
            f"{settings.xidian_ehall_base}/jwapp/sys/studentWdksapApp/modules/wdksap/wdksap.do",
            params={"XNXQDM": semester_code, "*order": "-KSRQ,-KSSJMS"},
            data={},
            headers=referer_headers,
        )
        self._ensure_not_redirected(arranged_rsp)
        arranged_data = arranged_rsp.json()
        if arranged_data.get("code") != "0":
            msg = (
                arranged_data.get("datas", {})
                .get("wdksap", {})
                .get("extParams", {})
                .get("msg", "考试信息获取失败")
            )
            raise XidianServiceError("DATA_FETCH_FAILED", msg)
        arranged_rows = arranged_data.get("datas", {}).get("wdksap", {}).get("rows", [])
        arranged = [
            {
                "subject": row.get("KCM"),
                "type": row.get("KSMC"),
                "time": row.get("KSSJMS"),
                "place": row.get("JASMC"),
                "seat": row.get("ZWH"),
            }
            for row in arranged_rows
        ]

        to_be_rsp = await client.get_json(
            f"{settings.xidian_ehall_base}/jwapp/sys/studentWdksapApp/modules/wdksap/cxyxkwapkwdkc.do",
            params={"XNXQDM": semester_code},
            data={},
            headers=referer_headers,
        )
        self._ensure_not_redirected(to_be_rsp)
        to_be_data = to_be_rsp.json()
        if to_be_data.get("code") != "0":
            msg = (
                to_be_data.get("datas", {})
                .get("cxyxkwapkwdkc", {})
                .get("extParams", {})
                .get("msg", "考试信息获取失败")
            )
            raise XidianServiceError("DATA_FETCH_FAILED", msg)
        to_be_rows = (
            to_be_data.get("datas", {}).get("cxyxkwapkwdkc", {}).get("rows", [])
        )
        to_be_arranged = [
            {"subject": row.get("KCM"), "id": row.get("KCH")} for row in to_be_rows
        ]

        return {
            "semester_code": semester_code,
            "arranged": arranged,
            "to_be_arranged": to_be_arranged,
        }

    async def _fetch_exams_yjspt(self, client: XidianClient, username: str) -> dict[str, Any]:
        semester_code = await self._get_current_semester_yjspt(client)
        query_setting = [
            {
                "name": "XNXQDM",
                "caption": "学年学期代码",
                "builder": "equal",
                "linkOpt": "AND",
                "value": semester_code,
            },
            {
                "name": "SFFBKSAP",
                "caption": "是否发布考试安排",
                "builder": "equal",
                "linkOpt": "AND",
                "value": "1",
            },
            {
                "name": "XH",
                "caption": "学号",
                "builder": "equal",
                "linkOpt": "AND",
                "value": username,
            },
            {
                "name": "KSAPWID",
                "caption": "考试安排WID",
                "builder": "notEqual",
                "linkOpt": "AND",
                "value": None,
            },
        ]
        response = await client.get_json(
            f"{settings.xidian_yjspt_base}/gsapp/sys/wdksapp/modules/ksxxck/wdksxxcx.do",
            params={
                "querySetting": json_dumps(query_setting),
                "pageSize": 1000,
                "pageNumber": 1,
            },
            data={},
        )
        self._ensure_not_redirected(response)
        rows = response.json().get("datas", {}).get("wdksxxcx", {}).get("rows", [])
        arranged = [
            {
                "subject": row.get("KCMC"),
                "type": row.get("KSLXDM_DISPLAY"),
                "time": row.get("KSSJMS"),
                "place": row.get("JASMC"),
                "seat": None,
            }
            for row in rows
        ]
        return {"semester_code": semester_code, "arranged": arranged, "to_be_arranged": []}

    async def _fetch_class_changes(self, client: XidianClient, semester_code: str) -> list[dict[str, Any]]:
        referer_headers = self._ehall_headers()
        response = await client.get_json(
            f"{settings.xidian_ehall_base}/jwapp/sys/wdkb/modules/xskcb/xsdkkc.do",
            data={"XNXQDM": semester_code, "*order": "-SQSJ"},
            headers=referer_headers,
        )
        self._ensure_not_redirected(response)
        data = response.json().get("datas", {}).get("xsdkkc", {})
        rows = data.get("rows", [])
        changes = []
        for row in rows:
            changes.append(
                {
                    "type": row.get("TKLXDM"),
                    "class_code": row.get("KCH"),
                    "class_number": row.get("KXH"),
                    "class_name": row.get("KCM"),
                    "original_weeks": row.get("SKZC"),
                    "new_weeks": row.get("XSKZC"),
                    "original_teacher": row.get("YSKJS"),
                    "new_teacher": row.get("XSKJS"),
                    "original_range": [
                        _safe_int(row.get("KSJC"), -1),
                        _safe_int(row.get("JSJC"), -1),
                    ],
                    "new_range": [
                        _safe_int(row.get("XKSJC"), -1),
                        _safe_int(row.get("XJSJC"), -1),
                    ],
                    "original_week": row.get("SKXQ"),
                    "new_week": row.get("XSKXQ"),
                    "original_classroom": row.get("JASMC"),
                    "new_classroom": row.get("XJASMC"),
                }
            )
        return changes

    async def _ensure_ehall_login(self, client: XidianClient) -> None:
        response = await client.get_json(
            f"{settings.xidian_ehall_base}/jsonp/getAppUsageMonitor.json?type=uv",
            headers=self._ehall_headers(),
        )
        if response.status_code in (301, 302):
            raise XidianServiceError("CAPTCHA_REQUIRED", "会话已过期，请重新验证", 409)
        data = response.json()
        if not data.get("hasLogin"):
            raise XidianServiceError("CAPTCHA_REQUIRED", "会话已过期，请重新验证", 409)

    async def _use_ehall_app(self, client: XidianClient, app_id: str) -> str:
        referer_headers = self._ehall_headers()
        response = await client.get_json(
            f"{settings.xidian_ehall_base}/appShow",
            params={"appId": app_id},
            headers=referer_headers,
        )
        self._ensure_not_redirected(response)
        location = response.headers.get("location")
        if not location:
            raise XidianServiceError("DATA_FETCH_FAILED", "无法打开教务应用")
        return re.sub(r";jsessionid=.*?\?", "?", location)

    async def _get_current_semester_ehall(self, client: XidianClient) -> str:
        referer_headers = self._ehall_headers()
        response = await client.get_json(
            f"{settings.xidian_ehall_base}/jwapp/sys/wdkb/modules/jshkcb/dqxnxq.do",
            data={},
            headers=referer_headers,
        )
        self._ensure_not_redirected(response)
        return (
            response.json()
            .get("datas", {})
            .get("dqxnxq", {})
            .get("rows", [{}])[0]
            .get("DM")
        )

    async def _get_term_start_day_ehall(self, client: XidianClient, semester_code: str) -> str:
        referer_headers = self._ehall_headers()
        parts = str(semester_code).split("-")
        year_part = "-".join(parts[:2]) if len(parts) >= 2 else semester_code
        term_part = parts[2] if len(parts) >= 3 else ""
        response = await client.get_json(
            f"{settings.xidian_ehall_base}/jwapp/sys/wdkb/modules/jshkcb/cxjcs.do",
            data={"XN": year_part, "XQ": term_part},
            headers=referer_headers,
        )
        self._ensure_not_redirected(response)
        return (
            response.json()
            .get("datas", {})
            .get("cxjcs", {})
            .get("rows", [{}])[0]
            .get("XQKSRQ")
        )

    async def _get_current_semester_yjspt(self, client: XidianClient) -> str:
        response = await client.get_json(
            f"{settings.xidian_yjspt_base}/gsapp/sys/yjsemaphome/modules/pubWork/getUserInfo.do",
            data={},
        )
        self._ensure_not_redirected(response)
        data = response.json()
        if data.get("code") != "0":
            raise XidianServiceError("DATA_FETCH_FAILED", data.get("msg", "获取学期失败"))
        return data.get("data", {}).get("xnxqdm", "")

    def _ensure_not_redirected(self, response: Any) -> None:
        if response.status_code in (301, 302):
            location = response.headers.get("location", "")
            if "authserver/login" in location:
                raise XidianServiceError("CAPTCHA_REQUIRED", "会话已过期，请重新验证", 409)

    @staticmethod
    def _ehall_headers() -> dict[str, str]:
        return {
            "Referer": "http://ehall.xidian.edu.cn/new/index_xd.html",
            "Host": "ehall.xidian.edu.cn",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "identity",
            "Connection": "Keep-Alive",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
