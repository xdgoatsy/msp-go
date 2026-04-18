"""
西电账号绑定与教务同步 Schema
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class XidianBindStartResponse(BaseModel):
    challenge_id: str = Field(..., description="验证码挑战 ID")
    captcha_big: str = Field(..., description="滑块背景图 Base64")
    captcha_piece: str = Field(..., description="滑块拼图 Base64")
    puzzle_width: int = Field(..., description="背景图宽度")
    puzzle_height: int = Field(..., description="背景图高度")
    piece_width: int = Field(..., description="拼图宽度")
    piece_height: int = Field(..., description="拼图高度")
    piece_y: int = Field(0, description="拼图 Y 坐标")


class XidianBindCompleteRequest(BaseModel):
    challenge_id: str = Field(..., description="验证码挑战 ID")
    slider_position: float = Field(..., ge=0, le=1, description="滑块位置 (0-1)")
    username: str | None = Field(None, description="学号/工号")
    password: str | None = Field(None, description="密码")


class XidianBindCompleteResponse(BaseModel):
    is_bound: bool = Field(..., description="是否已绑定")
    username: str = Field(..., description="学号/工号")
    is_postgraduate: bool | None = Field(None, description="是否研究生")
    last_verified_at: datetime | None = Field(None, description="最近验证时间")


class XidianBindingStatusResponse(BaseModel):
    is_bound: bool = Field(..., description="是否已绑定")
    username: str | None = Field(None, description="学号/工号")
    is_postgraduate: bool | None = Field(None, description="是否研究生")
    last_verified_at: datetime | None = Field(None, description="最近验证时间")
    last_sync_at: datetime | None = Field(None, description="最近同步时间")


class XidianSyncResponse(BaseModel):
    data: dict[str, Any] = Field(..., description="同步数据")
    fetched_at: datetime = Field(..., description="同步时间")
    is_cached: bool = Field(False, description="数据是否来自缓存快照")


class XidianSnapshotResponse(BaseModel):
    data: dict[str, Any] = Field(..., description="快照数据")
    is_cached: bool = Field(True, description="数据来自缓存")
    cached_at: str | None = Field(None, description="快照时间")


class XidianUnbindResponse(BaseModel):
    success: bool = Field(..., description="是否解绑成功")
