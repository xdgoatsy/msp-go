"""
分页查询工具

提供通用的分页和过滤查询构建器，消除重复的分页逻辑
"""

from enum import Enum
from typing import Any, Generic, Self, TypeVar

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

ModelType = TypeVar("ModelType", bound=DeclarativeBase)


class PaginatedQuery(Generic[ModelType]):
    """
    分页查询构建器

    提供链式 API 构建分页查询，消除重复的分页和过滤逻辑

    Example:
        ```python
        query = PaginatedQuery(db, UserModel)
        query.add_search(search_term, [UserModel.username, UserModel.email])
        query.add_enum_filter(role, UserModel.role, UserRole)
        query.add_filter(UserModel.is_active == True)
        users, total = await query.execute(page=1, page_size=20)
        ```
    """

    def __init__(
        self,
        db: AsyncSession,
        model: type[ModelType],
        base_query: Select[tuple[ModelType]] | None = None,
    ):
        self.db = db
        self.model = model
        self._query = base_query or select(model)
        self._count_query: Select[tuple[int]] | None = None
        self._filters: list[Any] = []

    def add_filter(self, condition: Any) -> Self:
        """添加过滤条件"""
        self._filters.append(condition)
        return self

    def add_search(
        self,
        term: str | None,
        fields: list[Any],
        case_insensitive: bool = True,
    ) -> Self:
        """
        添加搜索条件

        Args:
            term: 搜索词
            fields: 要搜索的字段列表
            case_insensitive: 是否忽略大小写
        """
        if not term or not fields:
            return self

        pattern = f"%{term}%"
        if case_insensitive:
            conditions = [field.ilike(pattern) for field in fields]
        else:
            conditions = [field.like(pattern) for field in fields]

        self._filters.append(or_(*conditions))
        return self

    def add_enum_filter(
        self,
        value: str | None,
        field: Any,
        enum_class: type[Enum],
        skip_value: str = "all",
    ) -> Self:
        """
        添加枚举过滤条件

        Args:
            value: 过滤值
            field: 数据库字段
            enum_class: 枚举类
            skip_value: 跳过过滤的值（如 "all"）
        """
        if not value or value == skip_value:
            return self

        try:
            enum_value = enum_class(value)
            self._filters.append(field == enum_value)
        except ValueError:
            # 无效的枚举值，忽略
            pass

        return self

    def add_string_filter(
        self,
        value: str | None,
        field: Any,
        skip_value: str = "all",
    ) -> Self:
        """
        添加字符串过滤条件

        Args:
            value: 过滤值
            field: 数据库字段
            skip_value: 跳过过滤的值
        """
        if not value or value == skip_value:
            return self

        self._filters.append(field == value)
        return self

    def add_date_range(
        self,
        start_date: Any | None,
        end_date: Any | None,
        field: Any,
    ) -> Self:
        """
        添加日期范围过滤

        Args:
            start_date: 开始日期
            end_date: 结束日期
            field: 日期字段
        """
        if start_date:
            self._filters.append(field >= start_date)
        if end_date:
            self._filters.append(field <= end_date)
        return self

    def order_by(self, *columns: Any) -> Self:
        """添加排序"""
        self._query = self._query.order_by(*columns)
        return self

    async def execute(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ModelType], int]:
        """
        执行分页查询

        Args:
            page: 页码（从 1 开始）
            page_size: 每页数量

        Returns:
            (数据列表, 总数)
        """
        # 应用过滤条件
        if self._filters:
            self._query = self._query.where(*self._filters)

        # 获取总数
        count_query = select(func.count()).select_from(
            self._query.subquery()
        )
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # 分页
        offset = (page - 1) * page_size
        paginated_query = self._query.offset(offset).limit(page_size)

        # 执行查询
        result = await self.db.execute(paginated_query)
        items = list(result.scalars().all())

        return items, total

    async def execute_without_pagination(self) -> list[ModelType]:
        """执行查询（不分页）"""
        if self._filters:
            self._query = self._query.where(*self._filters)

        result = await self.db.execute(self._query)
        return list(result.scalars().all())

    async def count(self) -> int:
        """仅获取总数"""
        if self._filters:
            query = self._query.where(*self._filters)
        else:
            query = self._query

        count_query = select(func.count()).select_from(query.subquery())
        result = await self.db.execute(count_query)
        return result.scalar() or 0


def create_paginated_query(
    db: AsyncSession,
    model: type[ModelType],
    base_query: Select[tuple[ModelType]] | None = None,
) -> PaginatedQuery[ModelType]:
    """
    创建分页查询构建器

    Args:
        db: 数据库会话
        model: ORM 模型类
        base_query: 基础查询（可选）

    Returns:
        PaginatedQuery 实例
    """
    return PaginatedQuery(db, model, base_query)
