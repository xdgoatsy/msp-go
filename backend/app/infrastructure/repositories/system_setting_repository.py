"""
系统配置仓储

提供系统配置的数据访问操作
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import SystemSettingModel


class SystemSettingRepository:
    """系统配置仓储"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, key: str) -> SystemSettingModel | None:
        """获取配置项"""
        stmt = select(SystemSettingModel).where(SystemSettingModel.key == key)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def set(
        self, key: str, value: str, description: str = ""
    ) -> SystemSettingModel:
        """设置配置项（存在则更新，不存在则创建）"""
        existing = await self.get(key)

        if existing:
            existing.value = value
            if description:
                existing.description = description
            existing.updated_at = datetime.now()
            await self.db.flush()
            return existing
        else:
            setting = SystemSettingModel(
                key=key,
                value=value,
                description=description,
                updated_at=datetime.now(),
            )
            self.db.add(setting)
            await self.db.flush()
            return setting

    async def get_all(self) -> list[SystemSettingModel]:
        """获取所有配置项"""
        stmt = select(SystemSettingModel)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_keys(self, keys: list[str]) -> list[SystemSettingModel]:
        """批量获取配置项"""
        stmt = select(SystemSettingModel).where(SystemSettingModel.key.in_(keys))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
