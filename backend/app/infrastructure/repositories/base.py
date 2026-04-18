"""
基础仓储类

提供通用的 CRUD 操作
"""

from typing import Any, Generic, TypeVar
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """基础仓储类"""

    def __init__(self, model: type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get(self, id: str) -> ModelType | None:
        """根据 ID 获取单条记录"""
        return await self.db.get(self.model, id)

    async def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        """获取多条记录"""
        result = await self.db.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, *, obj_in: dict[str, Any]) -> ModelType:
        """创建记录"""
        if "id" not in obj_in:
            obj_in["id"] = str(uuid4())
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        *,
        db_obj: ModelType,
        obj_in: dict[str, Any],
    ) -> ModelType:
        """更新记录"""
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def delete(self, *, id: str) -> bool:
        """删除记录"""
        obj = await self.get(id)
        if obj:
            await self.db.delete(obj)
            await self.db.flush()
            return True
        return False
