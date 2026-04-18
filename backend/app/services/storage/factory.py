"""
对象存储工厂

根据配置自动创建对应的存储后端实例。
遵循工厂模式和单例模式。
"""

import logging
from pathlib import Path

from app.config import settings
from app.services.storage.base import StorageBackend, StorageError

logger = logging.getLogger(__name__)

# 全局存储后端单例
_storage_backend: StorageBackend | None = None


def get_storage_backend() -> StorageBackend:
    """
    获取存储后端单例

    根据 settings.storage_backend 配置自动创建对应的存储实现：
    - "local": 本地文件系统
    - "qiniu": 七牛云对象存储
    - "s3": S3 兼容对象存储

    Returns:
        StorageBackend 实例

    Raises:
        StorageError: 配置错误或初始化失败时抛出
    """
    global _storage_backend

    if _storage_backend is not None:
        return _storage_backend

    backend_type = settings.storage_backend

    try:
        if backend_type == "local":
            from app.services.storage.local_backend import LocalStorageBackend

            upload_dir = Path(__file__).parent.parent.parent / "uploads"
            _storage_backend = LocalStorageBackend(upload_dir)
            logger.info("已初始化本地文件系统存储后端")

        elif backend_type == "qiniu":
            from app.services.storage.qiniu_backend import QiniuStorageBackend

            _storage_backend = QiniuStorageBackend()
            logger.info("已初始化七牛云存储后端")

        elif backend_type == "s3":
            from app.services.storage.s3_backend import S3StorageBackend

            _storage_backend = S3StorageBackend()
            logger.info("已初始化 S3 兼容存储后端: %s", settings.s3_endpoint_url)

        else:
            raise StorageError(
                f"不支持的存储后端类型: {backend_type}。支持的类型: local, qiniu, s3",
                code="invalid_backend",
            )

        return _storage_backend

    except StorageError:
        raise
    except Exception as e:
        logger.error("初始化存储后端失败: backend=%s, error=%s", backend_type, e)
        raise StorageError(
            f"初始化存储后端失败: {e}",
            code="backend_init_failed",
        ) from e


def reset_storage_backend() -> None:
    """
    重置存储后端单例

    用于测试或配置变更后重新初始化。
    """
    global _storage_backend
    _storage_backend = None
    logger.info("存储后端已重置")
