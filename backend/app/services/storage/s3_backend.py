"""
S3 兼容对象存储实现

支持所有兼容 AWS S3 API 的对象存储服务，包括：
- AWS S3
- 阿里云 OSS (S3 兼容模式)
- 腾讯云 COS (S3 兼容模式)
- MinIO
- 中国科技云 (cstcloud.cn)
- 其他 S3 兼容服务

使用 boto3 SDK 实现，支持 v4 签名。
"""

import logging

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.config import settings
from app.services.storage.base import StorageBackend, StorageError, UploadResult

logger = logging.getLogger(__name__)


class S3StorageBackend(StorageBackend):
    """S3 兼容对象存储实现"""

    def __init__(self) -> None:
        self._validate_config()
        self._bucket = settings.s3_bucket_name
        # 如果 region 为空字符串，使用默认值 us-east-1
        self._region = settings.s3_region or "us-east-1"
        self._public_url_base = settings.s3_public_url_base
        self._private = settings.s3_private_bucket
        self._url_expire = settings.s3_url_expire_seconds

        # 初始化 S3 客户端
        # 对于某些 S3 兼容服务（如中国科技云），使用 path 风格地址并禁用 SSL 验证
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=self._region,
            verify=False,  # 禁用 SSL 证书验证（某些 S3 兼容服务需要）
            config=Config(
                signature_version="s3v4",  # 使用 v4 签名
                s3={"addressing_style": "path"},  # 使用 path 风格（兼容性更好）
                connect_timeout=30,  # 连接超时 30 秒
                read_timeout=300,  # 读取超时 300 秒（5 分钟）
                retries={"max_attempts": 3, "mode": "standard"},  # 重试 3 次
            ),
        )

    def _validate_config(self) -> None:
        """校验 S3 配置完整性"""
        missing = []
        if not settings.s3_endpoint_url:
            missing.append("S3_ENDPOINT_URL")
        if not settings.s3_access_key:
            missing.append("S3_ACCESS_KEY")
        if not settings.s3_secret_key:
            missing.append("S3_SECRET_KEY")
        if not settings.s3_bucket_name:
            missing.append("S3_BUCKET_NAME")
        if missing:
            raise StorageError(
                f"S3 配置缺失: {', '.join(missing)}，请检查 .env 文件",
                code="config_missing",
            )

    def upload_data(self, data: bytes, key: str, content_type: str) -> UploadResult:
        """
        上传字节数据到 S3

        Args:
            data: 文件字节内容
            key: 存储 key（如 images/uuid.jpg）
            content_type: MIME 类型

        Returns:
            UploadResult

        Raises:
            StorageError: 上传失败时抛出
        """
        try:
            # 上传对象
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
                # 如果是公开桶，设置 ACL 为 public-read
                ACL="public-read" if not self._private else "private",
            )

            logger.info("S3 上传成功: key=%s, size=%d bytes", key, len(data))
            return UploadResult(
                key=key,
                url=self.get_download_url(key),
                size=len(data),
                content_type=content_type,
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            logger.error("S3 上传失败: key=%s, code=%s, error=%s", key, error_code, error_msg)
            raise StorageError(
                f"上传失败: {error_msg}",
                code="upload_failed",
            ) from e
        except Exception as e:
            logger.error("S3 上传失败: key=%s, error=%s", key, e)
            raise StorageError(f"上传失败: {e}", code="upload_failed") from e

    def get_download_url(self, key: str) -> str:
        """
        获取文件下载 URL

        公开空间直接拼接域名；私有空间生成带时效的预签名 URL。

        Args:
            key: 文件在存储空间中的 key

        Returns:
            可访问的下载 URL
        """
        if not self._private:
            # 公开空间：使用自定义域名或默认 S3 URL
            if self._public_url_base:
                return f"{self._public_url_base.rstrip('/')}/{key}"
            # 默认 S3 URL 格式
            endpoint = settings.s3_endpoint_url.rstrip("/")
            return f"{endpoint}/{self._bucket}/{key}"

        # 私有空间：生成预签名 URL
        try:
            url = self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=self._url_expire,
            )
            return url
        except ClientError as e:
            logger.error("生成预签名 URL 失败: key=%s, error=%s", key, e)
            raise StorageError(f"生成下载链接失败: {e}", code="url_generation_failed") from e

    def delete_file(self, key: str) -> bool:
        """
        删除存储空间中的文件

        Args:
            key: 文件 key

        Returns:
            是否删除成功
        """
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
            logger.info("S3 文件已删除: key=%s", key)
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.warning("S3 文件删除失败: key=%s, code=%s", key, error_code)
            return False
        except Exception as e:
            logger.error("S3 文件删除失败: key=%s, error=%s", key, e)
            return False

    def file_exists(self, key: str) -> bool:
        """
        检查文件是否存在

        Args:
            key: 文件 key

        Returns:
            文件是否存在
        """
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "404":
                return False
            logger.warning("检查文件是否存在失败: key=%s, code=%s", key, error_code)
            return False
        except Exception as e:
            logger.error("检查文件是否存在失败: key=%s, error=%s", key, e)
            return False
