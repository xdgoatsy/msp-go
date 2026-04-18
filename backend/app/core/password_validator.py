"""
密码强度验证器

提供符合 OWASP 标准的密码复杂度校验。
规则：
- 最少 8 个字符
- 至少包含 1 个大写字母
- 至少包含 1 个小写字母
- 至少包含 1 个数字
- 至少包含 1 个特殊字符
- 不在常见弱密码列表中
"""

import re

# 常见弱密码列表（Top 20）
_COMMON_PASSWORDS = frozenset({
    "password", "12345678", "123456789", "1234567890",
    "qwerty123", "admin123", "password1", "iloveyou",
    "sunshine1", "princess1", "football1", "charlie1",
    "access14", "master12", "dragon12", "monkey12",
    "letmein1", "abc12345", "qwerty12", "trustno1",
})

_RE_UPPER = re.compile(r"[A-Z]")
_RE_LOWER = re.compile(r"[a-z]")
_RE_DIGIT = re.compile(r"\d")
_RE_SPECIAL = re.compile(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?`~]")


def validate_password_strength(password: str) -> tuple[bool, list[str]]:
    """
    验证密码强度

    Args:
        password: 待验证的密码

    Returns:
        (是否通过, 错误信息列表)
    """
    errors: list[str] = []

    if len(password) < 8:
        errors.append("密码长度不能少于8位")

    if len(password) > 128:
        errors.append("密码长度不能超过128位")

    if not _RE_UPPER.search(password):
        errors.append("密码必须包含至少1个大写字母")

    if not _RE_LOWER.search(password):
        errors.append("密码必须包含至少1个小写字母")

    if not _RE_DIGIT.search(password):
        errors.append("密码必须包含至少1个数字")

    if not _RE_SPECIAL.search(password):
        errors.append("密码必须包含至少1个特殊字符")

    if password.lower() in _COMMON_PASSWORDS:
        errors.append("密码过于常见，请使用更复杂的密码")

    return len(errors) == 0, errors
