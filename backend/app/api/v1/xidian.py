"""
西电账号绑定与教务同步接口
"""

from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.deps import CurrentUserId, DbSession
from app.api.v1.schemas.xidian import (
    XidianBindCompleteRequest,
    XidianBindCompleteResponse,
    XidianBindingStatusResponse,
    XidianBindStartResponse,
    XidianSnapshotResponse,
    XidianSyncResponse,
    XidianUnbindResponse,
)
from app.config import settings
from app.services.xidian_service import XidianService, XidianServiceError

router = APIRouter()


def _error_response(error: XidianServiceError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"code": error.code, "message": error.message},
    )


@router.get("/binding", response_model=XidianBindingStatusResponse)
async def get_binding_status(
    db: DbSession,
    user_id: CurrentUserId,
) -> XidianBindingStatusResponse:
    service = XidianService(db)
    status = await service.get_binding_status(user_id)
    return XidianBindingStatusResponse(**status)


@router.post("/binding/start", response_model=XidianBindStartResponse)
async def start_binding(
    db: DbSession,
    user_id: CurrentUserId,
) -> XidianBindStartResponse | JSONResponse:
    service = XidianService(db)
    try:
        challenge = await service.start_binding()
        return XidianBindStartResponse(
            challenge_id=challenge.challenge_id,
            captcha_big=challenge.captcha.big_image,
            captcha_piece=challenge.captcha.piece_image,
            puzzle_width=settings.xidian_captcha_width,
            puzzle_height=settings.xidian_captcha_height,
            piece_width=settings.xidian_piece_width,
            piece_height=settings.xidian_piece_height,
            piece_y=challenge.captcha.piece_y,
        )
    except XidianServiceError as e:
        return _error_response(e)


@router.post("/binding/complete", response_model=XidianBindCompleteResponse)
async def complete_binding(
    db: DbSession,
    user_id: CurrentUserId,
    request: XidianBindCompleteRequest,
) -> XidianBindCompleteResponse | JSONResponse:
    service = XidianService(db)
    try:
        account = await service.complete_binding(
            user_id=user_id,
            challenge_id=request.challenge_id,
            username=request.username,
            password=request.password,
            slider_position=request.slider_position,
        )
        return XidianBindCompleteResponse(
            is_bound=True,
            username=account.username,
            is_postgraduate=account.is_postgraduate,
            last_verified_at=account.last_verified_at,
        )
    except XidianServiceError as e:
        return _error_response(e)


@router.post("/binding/unbind", response_model=XidianUnbindResponse)
async def unbind(
    db: DbSession,
    user_id: CurrentUserId,
) -> XidianUnbindResponse:
    service = XidianService(db)
    await service.unbind(user_id)
    return XidianUnbindResponse(success=True)


@router.post("/sync/classtable", response_model=XidianSyncResponse)
async def sync_classtable(
    db: DbSession,
    user_id: CurrentUserId,
) -> XidianSyncResponse | JSONResponse:
    service = XidianService(db)
    try:
        data = await service.sync_classtable(user_id)
        is_cached = data.pop("is_cached", False)
        return XidianSyncResponse(data=data, fetched_at=datetime.now(), is_cached=is_cached)
    except XidianServiceError as e:
        return _error_response(e)


@router.post("/sync/exams", response_model=XidianSyncResponse)
async def sync_exams(
    db: DbSession,
    user_id: CurrentUserId,
) -> XidianSyncResponse | JSONResponse:
    service = XidianService(db)
    try:
        data = await service.sync_exams(user_id)
        is_cached = data.pop("is_cached", False)
        return XidianSyncResponse(data=data, fetched_at=datetime.now(), is_cached=is_cached)
    except XidianServiceError as e:
        return _error_response(e)


@router.post("/sync/scores", response_model=XidianSyncResponse)
async def sync_scores(
    db: DbSession,
    user_id: CurrentUserId,
) -> XidianSyncResponse | JSONResponse:
    service = XidianService(db)
    try:
        data = await service.sync_scores(user_id)
        is_cached = data.pop("is_cached", False)
        return XidianSyncResponse(data=data, fetched_at=datetime.now(), is_cached=is_cached)
    except XidianServiceError as e:
        return _error_response(e)


@router.get("/snapshot/{data_type}", response_model=XidianSnapshotResponse)
async def get_snapshot(
    data_type: str,
    db: DbSession,
    user_id: CurrentUserId,
) -> XidianSnapshotResponse | JSONResponse:
    service = XidianService(db)
    try:
        data = await service.get_snapshot(user_id, data_type)
        cached_at = data.pop("cached_at", None)
        data.pop("is_cached", None)
        return XidianSnapshotResponse(data=data, cached_at=cached_at)
    except XidianServiceError as e:
        return _error_response(e)
