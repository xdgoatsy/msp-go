"""
文件上传 API

提供图片和资源文件（视频/文档）上传接口
"""

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.api.deps import TeacherUserId
from app.services.upload_service import (
    UploadServiceError,
    get_upload_service,
)

router = APIRouter()


class UploadResponse(BaseModel):
    """上传响应"""

    file_id: str
    url: str
    filename: str
    content_type: str
    size: int


@router.post("/image", response_model=UploadResponse)
async def upload_image(
    file: Annotated[
        UploadFile,
        File(..., description="图片文件 (JPEG/PNG/GIF/WebP, 最大 10MB)"),
    ],
) -> UploadResponse:
    """
    上传图片

    支持的格式: JPEG, PNG, GIF, WebP
    最大文件大小: 10MB
    """
    service = get_upload_service()

    try:
        result = await service.save_image(file)
        return UploadResponse(
            file_id=result.file_id,
            url=result.url,
            filename=result.filename,
            content_type=result.content_type,
            size=result.size,
        )
    except UploadServiceError as e:
        if e.code == "invalid_content_type":
            raise HTTPException(status_code=415, detail=e.message) from e
        elif e.code == "file_too_large":
            raise HTTPException(status_code=413, detail=e.message) from e
        else:
            raise HTTPException(status_code=500, detail=e.message) from e


@router.post("/resource", response_model=UploadResponse)
async def upload_resource(
    file: Annotated[UploadFile, File(..., description="资源文件（视频/文档，最大 500MB）")],
    current_user_id: TeacherUserId,
) -> UploadResponse:
    """
    上传教学资源文件（仅教师可用）

    支持的格式:
    - 视频: mp4, avi, mov, mkv, webm
    - 文档: pdf, doc, docx, ppt, pptx, txt, md

    最大文件大小: 500MB

    Returns:
        上传结果，包含文件 ID 和可访问 URL（七牛云 CDN 或本地路径）
    """
    service = get_upload_service()

    try:
        result = await service.save_resource_file(file)
        return UploadResponse(
            file_id=result.file_id,
            url=result.url,
            filename=result.filename,
            content_type=result.content_type,
            size=result.size,
        )
    except UploadServiceError as e:
        if e.code == "invalid_content_type":
            raise HTTPException(status_code=415, detail=e.message) from e
        elif e.code == "file_too_large":
            raise HTTPException(status_code=413, detail=e.message) from e
        else:
            raise HTTPException(status_code=500, detail=e.message) from e
