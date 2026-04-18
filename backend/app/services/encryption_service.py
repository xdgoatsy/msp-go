"""
加密服务

使用 Fernet 对称加密保护敏感数据（如 API Key）

Fernet 特性：
- 基于 AES-128-CBC
- 包含 HMAC 完整性校验
- 自动处理 IV 和时间戳
"""

import logging

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """加密服务异常"""

    pass


class EncryptionService:
    """
    Fernet 加密服务

    使用示例：
    ```python
    service = get_encryption_service()

    # 加密
    encrypted = service.encrypt("sk-xxx...")

    # 解密
    decrypted = service.decrypt(encrypted)
    ```
    """

    def __init__(self, secret_key: str):
        """
        初始化加密服务

        Args:
            secret_key: Fernet 密钥（32 字节 base64 编码）
        """
        try:
            self._fernet = Fernet(secret_key.encode())
        except Exception as e:
            logger.error(f"Fernet 密钥初始化失败: {e}")
            raise EncryptionError(f"无效的加密密钥: {e}") from e

    def encrypt(self, plaintext: str) -> str:
        """
        加密字符串

        Args:
            plaintext: 明文

        Returns:
            Base64 编码的密文
        """
        if not plaintext:
            return ""

        try:
            encrypted = self._fernet.encrypt(plaintext.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"加密失败: {e}")
            raise EncryptionError(f"加密失败: {e}") from e

    def decrypt(self, ciphertext: str) -> str:
        """
        解密字符串

        Args:
            ciphertext: Base64 编码的密文

        Returns:
            明文
        """
        if not ciphertext:
            return ""

        try:
            decrypted = self._fernet.decrypt(ciphertext.encode())
            return decrypted.decode()
        except InvalidToken as e:
            logger.error("解密失败: 无效的密文或密钥")
            raise EncryptionError("解密失败: 无效的密文或密钥不匹配") from e
        except Exception as e:
            logger.error(f"解密失败: {e}")
            raise EncryptionError(f"解密失败: {e}") from e

    @staticmethod
    def generate_key() -> str:
        """
        生成新的 Fernet 密钥

        用于初始化配置

        Returns:
            Base64 编码的密钥
        """
        return Fernet.generate_key().decode()


# 全局加密服务实例缓存
_encryption_service: EncryptionService | None = None


def get_encryption_service() -> EncryptionService:
    """
    获取加密服务单例

    从配置中读取密钥，如果未配置则生成临时密钥（仅限开发环境）
    """
    global _encryption_service

    if _encryption_service is not None:
        return _encryption_service

    secret_key = getattr(settings, "fernet_secret_key", None)

    if not secret_key:
        # 开发环境：生成临时密钥并警告
        logger.warning(
            "未配置 FERNET_SECRET_KEY，使用临时密钥（仅限开发环境）。"
            "生产环境请配置环境变量 FERNET_SECRET_KEY"
        )
        secret_key = Fernet.generate_key().decode()

    _encryption_service = EncryptionService(secret_key)
    return _encryption_service


def reset_encryption_service() -> None:
    """
    重置加密服务单例

    用于测试或配置变更后重新初始化
    """
    global _encryption_service
    _encryption_service = None
