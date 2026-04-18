"""
对象存储抽象接口

定义统一的存储接口，所有存储后端必须实现此接口。
遵循 SOLID 原则中的接口隔离和依赖倒置原则。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class UploadResult:
    """上传结果"""

    key: str          # 对象存储中的文件 key
    url: str          # 可访问的下载 URL
    size: int         # 文件大小（字节）
    content_type: str # MIME 类型


class StorageError(Exception):
    """存储服务异常"""

    def __init__(self, message: str, code: str = "storage_error"):
        super().__init__(message)
        self.message = message
        self.code = code


class StorageBackend(ABC):
    """
    对象存储抽象接口

    所有存储后端（本地、七牛云、S3 等）必须实现此接口。
    """

    @abstractmethod
    def upload_data(self, data: bytes, key: str, content_type: str) -> UploadResult:
        """
        上传字节数据

        Args:
            data: 文件字节内容
            key: 存储 key（如 images/uuid.jpg）
            content_type: MIME 类型

        Returns:
            UploadResult

        Raises:
            StorageError: 上传失败时抛出
        """
        pass

    @abstractmethod
    def get_download_url(self, key: str) -> str:
        """
        获取文件下载 URL

        Args:
            key: 文件在存储空间中的 key

        Returns:
            可访问的下载 URL
        """
        pass

    @abstractmethod
    def delete_file(self, key: str) -> bool:
        """
        删除存储空间中的文件

        Args:
            key: 文件 key

        Returns:
            是否删除成功
        """
        pass

    @abstractmethod
    def file_exists(self, key: str) -> bool:
        """
        检查文件是否存在

        Args:
            key: 文件 key

        Returns:
            文件是否存在
        """
        pass
