"""
本地文件系统存储实现

将文件保存到本地 backend/uploads/ 目录。
"""

import logging
import os
from pathlib import Path

from app.services.storage.base import StorageBackend, StorageError, UploadResult

logger = logging.getLogger(__name__)


class LocalStorageBackend(StorageBackend):
    """本地文件系统存储实现"""

    def __init__(self, upload_dir: Path):
        """
        初始化本地存储

        Args:
            upload_dir: 上传目录路径
        """
        self.upload_dir = upload_dir
        self._ensure_upload_dir()

    def _ensure_upload_dir(self) -> None:
        """确保上传目录存在"""
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def upload_data(self, data: bytes, key: str, content_type: str) -> UploadResult:
        """
        上传字节数据到本地文件系统

        Args:
            data: 文件字节内容
            key: 存储 key（如 images/uuid.jpg）
            content_type: MIME 类型

        Returns:
            UploadResult

        Raises:
            StorageError: 上传失败时抛出
        """
        file_path = self.upload_dir / key
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(file_path, "wb") as f:
                f.write(data)

            logger.info("文件已保存到本地: %s, 大小: %d bytes", key, len(data))
            return UploadResult(
                key=key,
                url=f"/uploads/{key}",
                size=len(data),
                content_type=content_type,
            )
        except Exception as e:
            file_path.unlink(missing_ok=True)
            logger.error("保存文件到本地失败: %s", e)
            raise StorageError(f"保存文件失败: {e}", code="save_failed") from e

    def get_download_url(self, key: str) -> str:
        """
        获取文件下载 URL

        Args:
            key: 文件在存储空间中的 key

        Returns:
            可访问的下载 URL
        """
        return f"/uploads/{key}"

    def delete_file(self, key: str) -> bool:
        """
        删除本地文件

        Args:
            key: 文件 key

        Returns:
            是否删除成功
        """
        file_path = self.upload_dir / key
        if file_path.exists():
            try:
                os.remove(file_path)
                logger.info("本地文件已删除: %s", key)
                return True
            except Exception as e:
                logger.error("删除本地文件失败: %s", e)
                return False
        return False

    def file_exists(self, key: str) -> bool:
        """
        检查文件是否存在

        Args:
            key: 文件 key

        Returns:
            文件是否存在
        """
        file_path = self.upload_dir / key
        return file_path.exists()
