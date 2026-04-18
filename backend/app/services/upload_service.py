"""
文件上传服务

提供文件验证、存储和 URL 生成功能。
支持多种存储后端（本地、七牛云、S3 兼容），
通过环境变量 STORAGE_BACKEND 切换（"local"、"qiniu" 或 "s3"）。

使用统一的存储抽象层，遵循 SOLID 原则。
"""

import logging
import uuid
from dataclasses import dataclass

from fastapi import UploadFile

from app.services.storage import StorageBackend, StorageError, get_storage_backend

logger = logging.getLogger(__name__)

# 支持的图片类型
ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}

# 支持的资源文件类型（视频 + 文档）
ALLOWED_RESOURCE_CONTENT_TYPES = {
    # 视频
    "video/mp4": ".mp4",
    "video/avi": ".avi",
    "video/quicktime": ".mov",
    "video/x-matroska": ".mkv",
    "video/webm": ".webm",
    # 文档
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "text/plain": ".txt",
    "text/markdown": ".md",
}

# 最大文件大小 (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# 最大资源文件大小 (500MB)
MAX_RESOURCE_FILE_SIZE = 500 * 1024 * 1024

# 分块读写大小 (1MB)
CHUNK_SIZE = 1024 * 1024


@dataclass
class UploadResult:
    """上传结果"""

    file_id: str
    url: str
    filename: str
    content_type: str
    size: int


class UploadServiceError(Exception):
    """上传服务异常"""

    def __init__(self, message: str, code: str = "upload_error"):
        super().__init__(message)
        self.message = message
        self.code = code


class UploadService:
    """
    文件上传服务

    使用统一的存储抽象层，支持多种存储后端。
    根据 settings.storage_backend 自动选择存储后端：
    - "local"：保存到本地 backend/uploads/ 目录
    - "qiniu"：上传到七牛云对象存储
    - "s3"：上传到 S3 兼容对象存储
    """

    def __init__(self, storage_backend: StorageBackend | None = None):
        """
        初始化上传服务

        Args:
            storage_backend: 存储后端实例（可选，默认使用工厂创建）
        """
        self._storage = storage_backend or get_storage_backend()

    def validate_image(self, file: UploadFile) -> None:
        """
        验证图片文件类型和大小

        Raises:
            UploadServiceError: 验证失败时抛出
        """
        content_type = file.content_type or ""
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise UploadServiceError(
                f"不支持的文件类型: {content_type}。支持的类型: JPEG, PNG, GIF, WebP",
                code="invalid_content_type",
            )
        if file.size is not None and file.size > MAX_FILE_SIZE:
            raise UploadServiceError(
                f"文件大小超过限制: {file.size / 1024 / 1024:.2f}MB > 10MB",
                code="file_too_large",
            )

    async def save_image(self, file: UploadFile) -> UploadResult:
        """
        保存图片文件

        使用统一的存储抽象层上传文件。

        Returns:
            UploadResult 包含文件信息和可访问 URL
        """
        self.validate_image(file)

        file_id = str(uuid.uuid4())
        content_type = file.content_type or "image/jpeg"
        extension = ALLOWED_CONTENT_TYPES.get(content_type, ".jpg")
        key = f"images/{file_id}{extension}"

        # 读取文件内容
        data = await self._read_file_data(file, MAX_FILE_SIZE)

        try:
            result = self._storage.upload_data(data, key, content_type)
            return UploadResult(
                file_id=file_id,
                url=result.url,
                filename=f"{file_id}{extension}",
                content_type=content_type,
                size=result.size,
            )
        except StorageError as e:
            raise UploadServiceError(e.message, code=e.code) from e

    def validate_resource_file(self, file: UploadFile) -> None:
        """
        验证资源文件类型和大小

        Raises:
            UploadServiceError: 验证失败时抛出
        """
        content_type = file.content_type or ""
        if content_type not in ALLOWED_RESOURCE_CONTENT_TYPES:
            raise UploadServiceError(
                f"不支持的文件类型: {content_type}。支持视频(mp4/avi/mov/mkv/webm)和文档(pdf/doc/ppt/txt)",
                code="invalid_content_type",
            )
        if file.size is not None and file.size > MAX_RESOURCE_FILE_SIZE:
            raise UploadServiceError(
                f"文件大小超过限制: {file.size / 1024 / 1024:.2f}MB > 500MB",
                code="file_too_large",
            )

    async def save_resource_file(self, file: UploadFile) -> UploadResult:
        """
        保存资源文件（视频/文档）

        使用统一的存储抽象层上传文件。

        Returns:
            UploadResult 包含文件信息和可访问 URL
        """
        self.validate_resource_file(file)

        file_id = str(uuid.uuid4())
        content_type = file.content_type or "application/octet-stream"
        extension = ALLOWED_RESOURCE_CONTENT_TYPES.get(content_type, "")

        # 按类型分目录存储
        if content_type.startswith("video/"):
            prefix = "videos"
        else:
            prefix = "documents"
        key = f"{prefix}/{file_id}{extension}"

        # 读取文件内容
        data = await self._read_file_data(file, MAX_RESOURCE_FILE_SIZE)

        try:
            result = self._storage.upload_data(data, key, content_type)
            return UploadResult(
                file_id=file_id,
                url=result.url,
                filename=f"{file_id}{extension}",
                content_type=content_type,
                size=result.size,
            )
        except StorageError as e:
            raise UploadServiceError(e.message, code=e.code) from e

    async def _read_file_data(self, file: UploadFile, max_size: int) -> bytes:
        """
        读取文件数据并检查大小

        Args:
            file: 上传文件
            max_size: 最大文件大小（字节）

        Returns:
            文件字节数据

        Raises:
            UploadServiceError: 文件过大时抛出
        """
        data = b""
        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break
            data += chunk
            if len(data) > max_size:
                raise UploadServiceError(
                    f"文件大小超过限制: {len(data) / 1024 / 1024:.2f}MB > {max_size / 1024 / 1024:.0f}MB",
                    code="file_too_large",
                )
        return data

    def delete_image(self, file_id: str) -> bool:
        """
        删除图片

        使用统一的存储抽象层删除文件。
        """
        for ext in ALLOWED_CONTENT_TYPES.values():
            key = f"images/{file_id}{ext}"
            if self._storage.delete_file(key):
                logger.info("图片已删除: file_id=%s", file_id)
                return True
        logger.warning("图片删除失败或不存在: file_id=%s", file_id)
        return False

    def delete_resource_file(self, file_id: str, content_type: str) -> bool:
        """
        删除资源文件

        Args:
            file_id: 文件 ID
            content_type: 文件 MIME 类型

        Returns:
            是否删除成功
        """
        extension = ALLOWED_RESOURCE_CONTENT_TYPES.get(content_type, "")
        prefix = "videos" if content_type.startswith("video/") else "documents"
        key = f"{prefix}/{file_id}{extension}"

        if self._storage.delete_file(key):
            logger.info("资源文件已删除: file_id=%s", file_id)
            return True
        logger.warning("资源文件删除失败或不存在: file_id=%s", file_id)
        return False


# 全局服务实例
_upload_service: UploadService | None = None


def get_upload_service() -> UploadService:
    """获取上传服务实例"""
    global _upload_service
    if _upload_service is None:
        _upload_service = UploadService()
    return _upload_service
