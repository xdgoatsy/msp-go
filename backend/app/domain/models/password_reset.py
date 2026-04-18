"""密码重置领域模型"""

from enum import Enum


class PasswordResetStatus(str, Enum):
    """密码重置申请状态"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
