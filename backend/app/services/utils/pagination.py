"""
分页工具

提供通用的分页计算函数和数据类
"""

import math
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class PaginatedResult(Generic[T]):
    """分页结果数据类"""

    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        """计算总页数"""
        return math.ceil(self.total / self.page_size) if self.total > 0 else 1

    @property
    def has_more(self) -> bool:
        """是否有更多数据"""
        return self.page < self.total_pages

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "items": self.items,
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "total_pages": self.total_pages,
        }


def calculate_offset(page: int, page_size: int) -> int:
    """
    计算分页偏移量

    Args:
        page: 页码（从 1 开始）
        page_size: 每页数量

    Returns:
        偏移量
    """
    return (page - 1) * page_size


def calculate_total_pages(total: int, page_size: int) -> int:
    """
    计算总页数

    Args:
        total: 总数量
        page_size: 每页数量

    Returns:
        总页数
    """
    return math.ceil(total / page_size) if total > 0 else 1
