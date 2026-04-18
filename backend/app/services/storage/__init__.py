"""
对象存储服务模块

提供统一的存储接口抽象和多种存储后端实现。
"""

from app.services.storage.base import (
    StorageBackend,
    StorageError,
    UploadResult,
)
from app.services.storage.factory import get_storage_backend

__all__ = [
    "StorageBackend",
    "StorageError",
    "UploadResult",
    "get_storage_backend",
]
