"""
七牛云对象存储服务

封装七牛云 Kodo SDK，提供文件上传、下载链接生成、删除等功能。
参考文档：https://developer.qiniu.com/kodo/1242/python
"""

import logging
import time
from dataclasses import dataclass

from qiniu import Auth, BucketManager, put_data

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class QiniuUploadResult:
    """七牛云上传结果"""

    key: str        # 对象存储中的文件 key
    url: str        # 可访问的下载 URL
    size: int       # 文件大小（字节）
    content_type: str


class QiniuStorageError(Exception):
    """七牛云存储异常"""

    def __init__(self, message: str, code: str = "qiniu_error"):
        super().__init__(message)
        self.message = message
        self.code = code


class QiniuStorageService:
    """
    七牛云对象存储服务

    支持公开空间和私有空间，提供：
    - 文件上传（字节流）
    - 下载 URL 生成（公开/私有）
    - 文件删除
    - 上传凭证生成
    """

    def __init__(self) -> None:
        self._validate_config()
        self._auth = Auth(settings.qiniu_access_key, settings.qiniu_secret_key)
        self._bucket = settings.qiniu_bucket_name
        self._domain = settings.qiniu_domain.rstrip("/")
        self._private = settings.qiniu_private_bucket
        self._url_expire = settings.qiniu_url_expire_seconds

    def _validate_config(self) -> None:
        """校验七牛云配置完整性"""
        missing = []
        if not settings.qiniu_access_key:
            missing.append("QINIU_ACCESS_KEY")
        if not settings.qiniu_secret_key:
            missing.append("QINIU_SECRET_KEY")
        if not settings.qiniu_bucket_name:
            missing.append("QINIU_BUCKET_NAME")
        if not settings.qiniu_domain:
            missing.append("QINIU_DOMAIN")
        if missing:
            raise QiniuStorageError(
                f"七牛云配置缺失: {', '.join(missing)}，请检查 .env 文件",
                code="config_missing",
            )

    def _make_upload_token(self, key: str | None = None) -> str:
        """
        生成上传凭证

        Args:
            key: 指定上传后的文件 key，None 表示由服务端生成

        Returns:
            上传凭证字符串
        """
        return self._auth.upload_token(self._bucket, key, expires=3600)

    def get_download_url(self, key: str) -> str:
        """
        获取文件下载 URL

        公开空间直接拼接域名；私有空间生成带时效的签名 URL。

        Args:
            key: 文件在存储空间中的 key

        Returns:
            可访问的下载 URL
        """
        base_url = f"{self._domain}/{key}"
        if not self._private:
            return base_url
        # 私有空间：生成带签名的临时 URL
        int(time.time()) + self._url_expire
        return self._auth.private_download_url(base_url, expires=self._url_expire)

    def upload_data(self, data: bytes, key: str, content_type: str) -> QiniuUploadResult:
        """
        上传字节数据到七牛云

        Args:
            data: 文件字节内容
            key: 存储 key（如 images/uuid.jpg）
            content_type: MIME 类型

        Returns:
            QiniuUploadResult

        Raises:
            QiniuStorageError: 上传失败时抛出
        """
        token = self._make_upload_token(key)
        mime_type = content_type

        ret, info = put_data(token, key, data, mime_type=mime_type, check_crc=True)

        if info.status_code != 200:
            logger.error("七牛云上传失败: key=%s, status=%s, error=%s", key, info.status_code, info.error)
            raise QiniuStorageError(
                f"上传失败: {info.error}",
                code="upload_failed",
            )

        logger.info("七牛云上传成功: key=%s, size=%d bytes", key, len(data))
        return QiniuUploadResult(
            key=key,
            url=self.get_download_url(key),
            size=len(data),
            content_type=content_type,
        )

    def delete_file(self, key: str) -> bool:
        """
        删除存储空间中的文件

        Args:
            key: 文件 key

        Returns:
            是否删除成功
        """
        bucket_manager = BucketManager(self._auth)
        result = bucket_manager.delete(self._bucket, key)
        ret, info = result  # type: ignore[misc]
        if info.status_code == 200:
            logger.info("七牛云文件已删除: key=%s", key)
            return True
        logger.warning("七牛云文件删除失败: key=%s, status=%s, error=%s", key, info.status_code, info.error)
        return False


# ---------------------------------------------------------------------------
# 单例工厂
# ---------------------------------------------------------------------------

_qiniu_service: QiniuStorageService | None = None


def get_qiniu_storage_service() -> QiniuStorageService:
    """获取七牛云存储服务单例（懒初始化）"""
    global _qiniu_service
    if _qiniu_service is None:
        _qiniu_service = QiniuStorageService()
    return _qiniu_service
