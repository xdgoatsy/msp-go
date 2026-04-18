"""
资源服务

提供资源相关的业务逻辑
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.resource import (
    ResourceCreate,
    ResourceFilter,
    ResourceUpdate,
)
from app.infrastructure.repositories.resource_repository import ResourceRepository


class ResourceService:
    """资源服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = ResourceRepository(db)

    async def get_resources(
        self, user_id: str, filter_params: ResourceFilter
    ) -> dict[str, Any]:
        """
        获取资源列表

        Args:
            user_id: 当前用户 ID
            filter_params: 筛选参数

        Returns:
            资源列表响应
        """
        resources, total = await self.repository.get_resources(
            user_id=user_id,
            resource_type=filter_params.type.value if filter_params.type else None,
            chapter=filter_params.chapter,
            topic=filter_params.topic,
            search=filter_params.search,
            favorites_only=filter_params.favorites_only,
            page=filter_params.page,
            page_size=filter_params.page_size,
        )

        has_more = (filter_params.page * filter_params.page_size) < total

        return {
            "items": resources,
            "total": total,
            "page": filter_params.page,
            "page_size": filter_params.page_size,
            "has_more": has_more,
        }

    async def get_resource_by_id(
        self, resource_id: str, user_id: str
    ) -> dict[str, Any] | None:
        """获取单个资源详情"""
        return await self.repository.get_resource_by_id(resource_id, user_id)

    async def create_resource(
        self, owner_id: str, data: ResourceCreate
    ) -> dict[str, Any]:
        """
        创建资源

        Args:
            owner_id: 创建者 ID（教师）
            data: 资源数据

        Returns:
            创建的资源
        """
        resource_data = {
            "title": data.title,
            "type": data.type.value,
            "body": data.body,
            "chapter": data.chapter,
            "topic": data.topic,
            "tags": data.tags,
            "difficulty": data.difficulty,
            "storage_type": data.storage_type.value,
            "url": data.url,
            "duration": data.duration,
            "pages": data.pages,
            "source": data.source,
        }

        return await self.repository.create_resource(owner_id, resource_data)

    async def update_resource(
        self, resource_id: str, owner_id: str, data: ResourceUpdate
    ) -> dict[str, Any] | None:
        """
        更新资源

        Args:
            resource_id: 资源 ID
            owner_id: 所有者 ID（用于权限校验）
            data: 更新数据

        Returns:
            更新后的资源，如果资源不存在或无权限则返回 None
        """
        update_data = {}

        if data.title is not None:
            update_data["title"] = data.title
        if data.type is not None:
            update_data["type"] = data.type.value
        if data.body is not None:
            update_data["body"] = data.body
        if data.chapter is not None:
            update_data["chapter"] = data.chapter
        if data.topic is not None:
            update_data["topic"] = data.topic
        if data.tags is not None:
            update_data["tags"] = data.tags
        if data.difficulty is not None:
            update_data["difficulty"] = data.difficulty
        if data.storage_type is not None:
            update_data["storage_type"] = data.storage_type.value
        if data.url is not None:
            update_data["url"] = data.url
        if data.duration is not None:
            update_data["duration"] = data.duration
        if data.pages is not None:
            update_data["pages"] = data.pages
        if data.source is not None:
            update_data["source"] = data.source

        return await self.repository.update_resource(resource_id, owner_id, update_data)

    async def delete_resource(self, resource_id: str, owner_id: str) -> bool:
        """
        删除资源

        Args:
            resource_id: 资源 ID
            owner_id: 所有者 ID（用于权限校验）

        Returns:
            是否删除成功
        """
        return await self.repository.delete_resource(resource_id, owner_id)

    async def toggle_favorite(self, user_id: str, resource_id: str) -> dict[str, Any]:
        """
        切换收藏状态

        Args:
            user_id: 用户 ID
            resource_id: 资源 ID

        Returns:
            收藏状态响应
        """
        is_favorite = await self.repository.toggle_favorite(user_id, resource_id)

        return {
            "resource_id": resource_id,
            "is_favorite": is_favorite,
            "message": "已收藏" if is_favorite else "已取消收藏",
        }

    async def get_favorites(
        self, user_id: str, page: int = 1, page_size: int = 20
    ) -> dict[str, Any]:
        """获取用户收藏列表"""
        resources, total = await self.repository.get_user_favorites(
            user_id, page, page_size
        )

        has_more = (page * page_size) < total

        return {
            "items": resources,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": has_more,
        }

    async def get_stats(self, user_id: str) -> dict[str, int]:
        """获取资源统计"""
        return await self.repository.get_stats(user_id)


def get_resource_service(db: AsyncSession) -> ResourceService:
    """获取资源服务实例"""
    return ResourceService(db)
