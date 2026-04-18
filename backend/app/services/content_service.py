"""
内容服务

提供内容管理的业务逻辑，包括 CRUD、发布、向量检索等
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.content import ContentStatus, ContentType
from app.domain.models.student import UserRole
from app.infrastructure.database.models import ContentModel, UserModel
from app.infrastructure.repositories.content_repository import ContentRepository


class ContentService:
    """
    内容服务

    封装内容管理的业务逻辑
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ContentRepository(db)

    # =========================================================================
    # 创建与更新
    # =========================================================================

    async def create_content(
        self,
        *,
        type: ContentType,
        title: str,
        body: str,
        actor: UserModel,
        difficulty: float = 0.5,
        concept_ids: list[str] | None = None,
        tags: list[str] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> ContentModel:
        """
        创建内容

        Args:
            type: 内容类型
            title: 标题
            body: 内容体
            actor: 操作者（必须是教师或管理员）
            difficulty: 难度系数
            concept_ids: 关联知识点
            tags: 标签
            meta: 扩展元数据

        Returns:
            创建的内容

        Raises:
            PermissionError: 非教师/管理员无权创建
        """
        if actor.role not in (UserRole.TEACHER, UserRole.ADMIN):
            raise PermissionError("只有教师或管理员可以创建内容")

        content = await self.repo.create(
            type=type,
            owner_teacher_id=actor.id,
            title=title,
            body=body,
            difficulty=difficulty,
            concept_ids=concept_ids,
            tags=tags,
            meta=meta,
        )

        await self.db.commit()
        return content

    async def update_content(
        self,
        content_id: str,
        actor: UserModel,
        updates: dict[str, Any],
    ) -> ContentModel | None:
        """
        更新内容

        Args:
            content_id: 内容 ID
            actor: 操作者
            updates: 更新字段

        Returns:
            更新后的内容，无权限返回 None
        """
        # 过滤不允许更新的字段
        forbidden_fields = {"id", "owner_teacher_id", "created_at", "deleted_at"}
        updates = {k: v for k, v in updates.items() if k not in forbidden_fields}

        if not updates:
            return await self.repo.get_by_owner(content_id, actor.id)

        content = await self.repo.update_by_owner(content_id, actor.id, updates)

        if content:
            await self.db.commit()

        return content

    async def delete_content(
        self,
        content_id: str,
        actor: UserModel,
    ) -> bool:
        """
        删除内容（软删除）

        Args:
            content_id: 内容 ID
            actor: 操作者

        Returns:
            是否删除成功
        """
        success = await self.repo.soft_delete_by_owner(content_id, actor.id)

        if success:
            await self.db.commit()

        return success

    # =========================================================================
    # 发布与归档
    # =========================================================================

    async def publish_content(
        self,
        content_id: str,
        actor: UserModel,
    ) -> ContentModel | None:
        """
        发布内容

        Args:
            content_id: 内容 ID
            actor: 操作者

        Returns:
            发布后的内容
        """
        content = await self.repo.publish_by_owner(content_id, actor.id)

        if content:
            await self.db.commit()

        return content

    async def archive_content(
        self,
        content_id: str,
        actor: UserModel,
    ) -> ContentModel | None:
        """
        归档内容

        Args:
            content_id: 内容 ID
            actor: 操作者

        Returns:
            归档后的内容
        """
        content = await self.repo.archive_by_owner(content_id, actor.id)

        if content:
            await self.db.commit()

        return content

    # =========================================================================
    # 查询
    # =========================================================================

    async def get_content(
        self,
        content_id: str,
        actor: UserModel | None = None,
    ) -> ContentModel | None:
        """
        获取内容

        Args:
            content_id: 内容 ID
            actor: 操作者（None 表示公开访问）

        Returns:
            内容对象
        """
        if actor:
            # 有登录用户，尝试获取其有权限的内容
            content = await self.repo.get_by_owner(content_id, actor.id)
            if content:
                return content

        # 公开访问，只能获取已发布内容
        return await self.repo.get_published(content_id)

    async def list_contents(
        self,
        *,
        actor: UserModel | None = None,
        type: ContentType | None = None,
        status: ContentStatus | None = None,
        owner_only: bool = False,
        skip: int = 0,
        limit: int = 20,
    ) -> list[ContentModel]:
        """
        列出内容

        Args:
            actor: 操作者
            type: 内容类型过滤
            status: 状态过滤（仅 owner 视角有效）
            owner_only: 是否只看自己的内容
            skip: 跳过数量
            limit: 返回数量

        Returns:
            内容列表
        """
        if actor and owner_only:
            # 教师查看自己的内容
            return await self.repo.list_by_owner(
                actor.id,
                status=status,
                skip=skip,
                limit=limit,
            )

        # 公开列表
        return await self.repo.list_published(
            type=type,
            skip=skip,
            limit=limit,
        )

    # =========================================================================
    # 向量检索
    # =========================================================================

    async def semantic_search(
        self,
        embedding: list[float],
        *,
        limit: int = 20,
        type: ContentType | None = None,
    ) -> list[tuple[ContentModel, float]]:
        """
        语义检索

        Args:
            embedding: 查询向量
            limit: 返回数量
            type: 内容类型过滤

        Returns:
            (内容, 距离) 列表
        """
        return await self.repo.search_by_embedding(
            embedding,
            limit=limit,
            type=type,
        )

    async def update_embedding(
        self,
        content_id: str,
        model_name: str,
        embedding: list[float],
    ) -> None:
        """
        更新内容向量

        Args:
            content_id: 内容 ID
            model_name: 模型名称
            embedding: 向量数据
        """
        await self.repo.upsert_embedding(content_id, model_name, embedding)
        await self.db.commit()
