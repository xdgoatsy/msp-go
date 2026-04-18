"""
查询构建工具

提供通用的查询条件构建函数
"""

from enum import Enum
from typing import TypeVar

from sqlalchemy import ColumnElement

E = TypeVar("E", bound=Enum)


def build_user_search_condition(
    model: type,
    search: str | None,
) -> ColumnElement[bool] | None:
    """
    构建用户搜索条件

    Args:
        model: 用户模型类（需要有 username, email, display_name 字段）
        search: 搜索关键词

    Returns:
        SQLAlchemy 条件表达式，如果 search 为空则返回 None
    """
    if not search:
        return None

    pattern = f"%{search}%"
    return (
        model.username.ilike(pattern)
        | model.email.ilike(pattern)
        | model.display_name.ilike(pattern)
    )


def validate_enum(
    value: str | None,
    enum_class: type[E],
    exclude: str = "all",
) -> E | None:
    """
    验证并转换枚举值

    Args:
        value: 要验证的字符串值
        enum_class: 枚举类
        exclude: 要排除的特殊值（默认 "all"）

    Returns:
        枚举值，如果无效或被排除则返回 None
    """
    if not value or value == exclude:
        return None

    try:
        return enum_class(value)
    except ValueError:
        return None
