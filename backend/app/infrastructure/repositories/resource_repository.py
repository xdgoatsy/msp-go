"""
资源仓储

提供资源数据的持久化操作
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.models.content import AssetKind, ContentStatus, ContentType
from app.infrastructure.database.models import (
    ContentAssetModel,
    ContentModel,
    UserFavoriteModel,
)

# 资源类型映射
RESOURCE_TYPE_MAP = {
    "video": ContentType.VIDEO,
    "document": ContentType.ARTICLE,  # 文档映射到 article
}

CONTENT_TYPE_TO_RESOURCE = {
    ContentType.VIDEO: "video",
    ContentType.ARTICLE: "document",
}

RECOMMENDATION_DIFFICULTY_RANGES = {
    "beginner": (0.0, 0.33),
    "intermediate": (0.34, 0.66),
    "advanced": (0.67, 1.0),
}


class ResourceRepository:
    """资源仓储"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_resources(
        self,
        user_id: str,
        resource_type: str | None = None,
        chapter: str | None = None,
        topic: str | None = None,
        search: str | None = None,
        favorites_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        获取资源列表

        Args:
            user_id: 当前用户 ID
            resource_type: 资源类型筛选
            chapter: 章节筛选
            topic: 主题筛选
            search: 搜索关键词
            favorites_only: 仅显示收藏
            page: 页码
            page_size: 每页数量

        Returns:
            (资源列表, 总数)
        """
        # 基础查询：已发布且未删除的资源内容
        base_conditions = [
            ContentModel.status == ContentStatus.PUBLISHED,
            ContentModel.deleted_at.is_(None),
            ContentModel.type.in_(
                [ContentType.VIDEO, ContentType.ARTICLE]
            ),
        ]

        # 类型筛选
        if resource_type and resource_type in RESOURCE_TYPE_MAP:
            base_conditions.append(
                ContentModel.type == RESOURCE_TYPE_MAP[resource_type]
            )

        # 章节筛选 (存储在 meta.chapter)
        if chapter:
            base_conditions.append(
                ContentModel.meta["chapter"].as_string() == chapter
            )

        # 主题筛选 (存储在 meta.topic)
        if topic:
            base_conditions.append(
                ContentModel.meta["topic"].as_string() == topic
            )

        # 搜索
        if search:
            search_pattern = f"%{search}%"
            base_conditions.append(
                or_(
                    ContentModel.title.ilike(search_pattern),
                    ContentModel.meta["topic"].as_string().ilike(search_pattern),
                )
            )

        # 收藏筛选
        if favorites_only:
            favorite_subquery = (
                select(UserFavoriteModel.content_id)
                .where(UserFavoriteModel.user_id == user_id)
                .scalar_subquery()
            )
            base_conditions.append(ContentModel.id.in_(favorite_subquery))

        # 构建查询
        query = (
            select(ContentModel)
            .options(
                selectinload(ContentModel.assets),
                selectinload(ContentModel.owner),
            )
            .where(and_(*base_conditions))
            .order_by(ContentModel.created_at.desc())
        )

        # 获取总数
        count_query = select(func.count()).select_from(
            select(ContentModel.id).where(and_(*base_conditions)).subquery()
        )
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # 分页
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # 执行查询
        result = await self.db.execute(query)
        contents = result.scalars().all()

        # 获取用户收藏状态
        content_ids = [c.id for c in contents]
        favorites = await self._get_user_favorites(user_id, content_ids)

        # 转换为响应格式（列表查询不包含 body 字段以减少响应体积）
        resources = []
        for content in contents:
            resource = self._content_to_resource(content, content.id in favorites, include_body=False)
            resources.append(resource)

        return resources, total

    async def get_resource_by_id(
        self, resource_id: str, user_id: str
    ) -> dict[str, Any] | None:
        """获取单个资源详情"""
        query = (
            select(ContentModel)
            .options(
                selectinload(ContentModel.assets),
                selectinload(ContentModel.owner),
            )
            .where(
                and_(
                    ContentModel.id == resource_id,
                    ContentModel.status == ContentStatus.PUBLISHED,
                    ContentModel.deleted_at.is_(None),
                )
            )
        )

        result = await self.db.execute(query)
        content = result.scalar_one_or_none()

        if not content:
            return None

        # 检查收藏状态
        favorites = await self._get_user_favorites(user_id, [resource_id])
        is_favorite = resource_id in favorites

        # 增加浏览次数
        await self._increment_views(resource_id)

        return self._content_to_resource(content, is_favorite)

    async def search_recommendations(
        self,
        *,
        query: str | None = None,
        chapter: str | None = None,
        topic: str | None = None,
        resource_type: str | None = None,
        difficulty: str | None = None,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        """
        检索 AI 推荐用资源。

        与 get_resources 的精确筛选不同，这里面向对话推荐场景：
        - 只返回已发布、未删除的视频/文档资源
        - 对标题、正文、章节、主题、来源、标签做关键词模糊匹配
        - 将 beginner/intermediate/advanced 映射到现有 0-1 难度系数
        """
        limit = max(1, min(limit, 3))

        conditions = [
            ContentModel.status == ContentStatus.PUBLISHED,
            ContentModel.deleted_at.is_(None),
            ContentModel.type.in_([ContentType.VIDEO, ContentType.ARTICLE]),
        ]

        if resource_type and resource_type in RESOURCE_TYPE_MAP:
            conditions.append(ContentModel.type == RESOURCE_TYPE_MAP[resource_type])

        if difficulty and difficulty in RECOMMENDATION_DIFFICULTY_RANGES:
            min_difficulty, max_difficulty = RECOMMENDATION_DIFFICULTY_RANGES[
                difficulty
            ]
            conditions.extend(
                [
                    ContentModel.difficulty >= min_difficulty,
                    ContentModel.difficulty <= max_difficulty,
                ]
            )

        text_terms = [
            term.strip()
            for term in (query, chapter, topic)
            if isinstance(term, str) and term.strip()
        ]
        unique_terms = list(dict.fromkeys(text_terms))
        if unique_terms:
            text_conditions = []
            for term in unique_terms:
                pattern = f"%{term}%"
                text_conditions.extend(
                    [
                        ContentModel.title.ilike(pattern),
                        ContentModel.body.ilike(pattern),
                        ContentModel.meta["chapter"].as_string().ilike(pattern),
                        ContentModel.meta["topic"].as_string().ilike(pattern),
                        ContentModel.meta["source"].as_string().ilike(pattern),
                        cast(ContentModel.tags, String).ilike(pattern),
                    ]
                )
            conditions.append(or_(*text_conditions))

        stmt = (
            select(ContentModel)
            .options(
                selectinload(ContentModel.assets),
                selectinload(ContentModel.owner),
            )
            .where(and_(*conditions))
            .order_by(ContentModel.created_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        contents = result.scalars().all()

        return [
            self._content_to_resource(content, False, include_body=False)
            for content in contents
        ]

    async def create_resource(
        self, owner_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """创建资源"""
        content_type = RESOURCE_TYPE_MAP.get(data["type"], ContentType.ARTICLE)

        # 构建 meta 数据
        meta = {
            "chapter": data.get("chapter"),
            "topic": data.get("topic"),
            "source": data.get("source"),
            "duration": data.get("duration"),
            "pages": data.get("pages"),
            "storage_type": data.get("storage_type", "external"),
            "views": 0,
            "likes": 0,
        }

        content = ContentModel(
            id=str(uuid4()),
            type=content_type,
            owner_teacher_id=owner_id,
            status=ContentStatus.PUBLISHED,
            title=data["title"],
            body=data.get("body", ""),
            difficulty=data.get("difficulty", 0.5),
            tags=data.get("tags", []),
            meta=meta,
            published_at=datetime.now(),
        )

        self.db.add(content)

        # 如果有 URL，创建附件
        if data.get("url"):
            asset_kind = self._get_asset_kind(data["type"])
            asset = ContentAssetModel(
                id=str(uuid4()),
                content_id=content.id,
                kind=asset_kind,
                url=data["url"],
                meta={
                    "storage_type": data.get("storage_type", "external"),
                    "duration": data.get("duration"),
                    "pages": data.get("pages"),
                },
            )
            self.db.add(asset)

        await self.db.commit()

        content = await self._get_content_for_response(content.id)
        return self._content_to_resource(content, False)

    async def update_resource(
        self, resource_id: str, owner_id: str, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """更新资源"""
        query = select(ContentModel).where(
            and_(
                ContentModel.id == resource_id,
                ContentModel.owner_teacher_id == owner_id,
                ContentModel.deleted_at.is_(None),
            )
        )

        result = await self.db.execute(query)
        content = result.scalar_one_or_none()

        if not content:
            return None

        # 更新字段
        if data.get("title") is not None:
            content.title = data["title"]
        if data.get("body") is not None:
            content.body = data["body"]
        if data.get("type") is not None:
            content.type = RESOURCE_TYPE_MAP.get(data["type"], content.type)
        if data.get("difficulty") is not None:
            content.difficulty = data["difficulty"]
        if data.get("tags") is not None:
            content.tags = data["tags"]

        # 更新 meta
        meta = content.meta.copy()
        for key in ["chapter", "topic", "source", "duration", "pages", "storage_type"]:
            if data.get(key) is not None:
                meta[key] = data[key]
        content.meta = meta

        content.updated_at = datetime.now()

        await self.db.commit()

        content = await self._get_content_for_response(content.id)
        return self._content_to_resource(content, False)

    async def delete_resource(self, resource_id: str, owner_id: str) -> bool:
        """软删除资源"""
        query = select(ContentModel).where(
            and_(
                ContentModel.id == resource_id,
                ContentModel.owner_teacher_id == owner_id,
                ContentModel.deleted_at.is_(None),
            )
        )

        result = await self.db.execute(query)
        content = result.scalar_one_or_none()

        if not content:
            return False

        content.deleted_at = datetime.now()
        content.status = ContentStatus.ARCHIVED
        await self.db.commit()

        return True

    async def toggle_favorite(self, user_id: str, resource_id: str) -> bool:
        """切换收藏状态，返回新的收藏状态"""
        # 检查资源是否存在
        resource_exists = await self.db.execute(
            select(ContentModel.id).where(
                and_(
                    ContentModel.id == resource_id,
                    ContentModel.status == ContentStatus.PUBLISHED,
                    ContentModel.deleted_at.is_(None),
                )
            )
        )
        if not resource_exists.scalar_one_or_none():
            raise ValueError("资源不存在")

        # 检查是否已收藏
        existing = await self.db.execute(
            select(UserFavoriteModel).where(
                and_(
                    UserFavoriteModel.user_id == user_id,
                    UserFavoriteModel.content_id == resource_id,
                )
            )
        )
        favorite = existing.scalar_one_or_none()

        if favorite:
            # 取消收藏
            await self.db.delete(favorite)
            await self.db.commit()
            return False
        else:
            # 添加收藏
            new_favorite = UserFavoriteModel(
                id=str(uuid4()),
                user_id=user_id,
                content_id=resource_id,
            )
            self.db.add(new_favorite)
            await self.db.commit()
            return True

    async def get_user_favorites(
        self, user_id: str, page: int = 1, page_size: int = 20
    ) -> tuple[list[dict[str, Any]], int]:
        """获取用户收藏列表"""
        return await self.get_resources(
            user_id=user_id,
            favorites_only=True,
            page=page,
            page_size=page_size,
        )

    async def get_stats(self, user_id: str) -> dict[str, int]:
        """获取资源统计"""
        base_conditions = [
            ContentModel.status == ContentStatus.PUBLISHED,
            ContentModel.deleted_at.is_(None),
        ]

        # 总数
        total_query = select(func.count()).where(
            and_(
                *base_conditions,
                ContentModel.type.in_(
                    [ContentType.VIDEO, ContentType.ARTICLE, ContentType.NOTE]
                ),
            )
        )
        total_result = await self.db.execute(total_query)
        total = total_result.scalar() or 0

        # 视频数
        video_query = select(func.count()).where(
            and_(*base_conditions, ContentModel.type == ContentType.VIDEO)
        )
        video_result = await self.db.execute(video_query)
        videos = video_result.scalar() or 0

        # 文档数
        doc_query = select(func.count()).where(
            and_(*base_conditions, ContentModel.type == ContentType.ARTICLE)
        )
        doc_result = await self.db.execute(doc_query)
        documents = doc_result.scalar() or 0

        # 用户收藏数
        favorite_query = select(func.count()).where(
            UserFavoriteModel.user_id == user_id
        )
        favorite_result = await self.db.execute(favorite_query)
        favorites = favorite_result.scalar() or 0

        return {
            "total": total,
            "videos": videos,
            "documents": documents,
            "favorites": favorites,
        }

    # =========================================================================
    # 私有方法
    # =========================================================================

    async def _get_user_favorites(
        self, user_id: str, content_ids: list[str]
    ) -> set[str]:
        """获取用户对指定内容的收藏状态"""
        if not content_ids:
            return set()

        query = select(UserFavoriteModel.content_id).where(
            and_(
                UserFavoriteModel.user_id == user_id,
                UserFavoriteModel.content_id.in_(content_ids),
            )
        )
        result = await self.db.execute(query)
        return set(result.scalars().all())

    async def _increment_views(self, resource_id: str) -> None:
        """增加浏览次数"""
        query = select(ContentModel).where(ContentModel.id == resource_id)
        result = await self.db.execute(query)
        content = result.scalar_one_or_none()

        if content:
            meta = content.meta.copy()
            meta["views"] = meta.get("views", 0) + 1
            content.meta = meta
            await self.db.commit()

    async def _get_content_for_response(self, content_id: str) -> ContentModel:
        """重新查询内容并预加载响应转换需要的关系。"""
        query = (
            select(ContentModel)
            .options(
                selectinload(ContentModel.assets),
                selectinload(ContentModel.owner),
            )
            .where(ContentModel.id == content_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one()

    def _content_to_resource(
        self, content: ContentModel, is_favorite: bool, include_body: bool = True
    ) -> dict[str, Any]:
        """
        将 ContentModel 转换为资源响应格式

        Args:
            content: 内容模型
            is_favorite: 是否已收藏
            include_body: 是否包含 body 字段（列表查询时可排除以减少响应体积）
        """
        meta = content.meta or {}

        # 获取主附件
        main_asset = None
        if content.assets:
            main_asset = content.assets[0]

        # 确定资源类型
        resource_type = CONTENT_TYPE_TO_RESOURCE.get(content.type, "document")

        result: dict[str, Any] = {
            "id": content.id,
            "title": content.title,
            "type": resource_type,
            "chapter": meta.get("chapter"),
            "topic": meta.get("topic"),
            "tags": content.tags or [],
            "difficulty": content.difficulty,
            "source": meta.get("source"),
            "url": main_asset.url if main_asset else None,
            "storage_type": meta.get("storage_type"),
            "duration": meta.get("duration"),
            "pages": meta.get("pages"),
            "views": meta.get("views", 0),
            "likes": meta.get("likes", 0),
            "is_favorite": is_favorite,
            "owner_id": content.owner_teacher_id,
            "owner_name": content.owner.display_name if content.owner else None,
            "created_at": content.created_at,
            "updated_at": content.updated_at,
        }

        # 仅在需要时包含 body 字段（详情页需要，列表页不需要）
        if include_body:
            result["body"] = content.body

        return result

    def _get_asset_kind(self, resource_type: str) -> AssetKind:
        """根据资源类型获取附件类型"""
        if resource_type == "video":
            return AssetKind.VIDEO
        elif resource_type == "document":
            return AssetKind.PDF
        else:
            return AssetKind.ATTACHMENT
