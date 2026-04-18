"""
用户仓储

提供用户数据访问操作
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import UserModel
from app.infrastructure.repositories.base import BaseRepository


class UserRepository(BaseRepository[UserModel]):
    """用户仓储类"""

    def __init__(self, db: AsyncSession):
        super().__init__(UserModel, db)

    async def get_by_username(self, username: str) -> UserModel | None:
        """根据用户名获取用户"""
        result = await self.db.execute(
            select(UserModel).where(UserModel.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> UserModel | None:
        """根据邮箱获取用户"""
        result = await self.db.execute(
            select(UserModel).where(UserModel.email == email)
        )
        return result.scalar_one_or_none()

    async def update_password(self, user_id: str, hashed_password: str) -> bool:
        """更新用户密码"""
        user = await self.get(user_id)
        if user:
            user.hashed_password = hashed_password
            self.db.add(user)
            await self.db.flush()
            return True
        return False
