"""
内容仓储

提供内容的 CRUD 操作，包含权限控制和向量检索
"""

from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from sqlalchemy import and_, case, exists, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.content import (
    AuditAction,
    ContentStatus,
    ContentType,
    OutboxEventType,
)
from app.infrastructure.database.models import (
    ContentAclModel,
    ContentAttemptModel,
    ContentAuditModel,
    ContentEmbeddingModel,
    ContentModel,
    OutboxEventModel,
)


class ContentRepository:
    """
    内容仓储

    实现方案文档 4.1 的写权限控制：
    - 写操作必须"单条 SQL 带权限条件"
    - 读操作强制状态过滤
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # 写操作（带权限条件）
    # =========================================================================

    async def create(
        self,
        *,
        type: ContentType,
        owner_teacher_id: str,
        title: str,
        body: str,
        difficulty: float = 0.5,
        concept_ids: list[str] | None = None,
        tags: list[str] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> ContentModel:
        """
        创建内容

        Args:
            type: 内容类型
            owner_teacher_id: 所有者教师 ID
            title: 标题
            body: 内容体
            difficulty: 难度系数
            concept_ids: 关联知识点
            tags: 标签
            meta: 扩展元数据

        Returns:
            创建的内容对象
        """
        content_id = str(uuid4())
        content = ContentModel(
            id=content_id,
            type=type,
            owner_teacher_id=owner_teacher_id,
            status=ContentStatus.DRAFT,
            title=title,
            body=body,
            difficulty=difficulty,
            concept_ids=concept_ids or [],
            tags=tags or [],
            meta=meta or {},
        )
        self.db.add(content)

        # 写审计日志
        await self._audit(
            content_id=content_id,
            actor_id=owner_teacher_id,
            action=AuditAction.CREATE,
            diff={"title": title, "type": type.value},
        )

        # 写 outbox 事件
        await self._push_event(
            OutboxEventType.EMBEDDING_REQUIRED,
            {"content_id": content_id, "action": "create"},
        )

        await self.db.flush()
        await self.db.refresh(content)
        return content

    async def update_by_owner(
        self,
        content_id: str,
        actor_id: str,
        updates: dict[str, Any],
    ) -> ContentModel | None:
        """
        更新内容（仅 owner 或有权限的协作者可操作）

        单条 SQL 带权限条件，避免 TOCTOU 问题

        Args:
            content_id: 内容 ID
            actor_id: 操作者 ID
            updates: 更新字段

        Returns:
            更新后的内容，无权限或不存在返回 None
        """
        permission_condition = self._build_permission_condition(content_id, actor_id)

        # 单条 SQL 更新
        audit_updates = {k: v for k, v in updates.items() if k != "updated_at"}
        update_values = {**audit_updates, "updated_at": datetime.now()}
        stmt = (
            update(ContentModel)
            .where(
                and_(
                    ContentModel.id == content_id,
                    ContentModel.deleted_at.is_(None),
                    permission_condition,
                )
            )
            .values(**update_values)
            .returning(ContentModel)
        )

        result = await self.db.execute(stmt)
        content = result.scalar_one_or_none()

        if content:
            # 刷新对象以确保所有属性都被加载
            await self.db.refresh(content)

            # 写审计日志
            await self._audit(
                content_id=content_id,
                actor_id=actor_id,
                action=AuditAction.UPDATE,
                diff=audit_updates,
            )
            # 写 outbox 事件
            await self._push_event(
                OutboxEventType.CONTENT_CHANGED,
                {"content_id": content_id, "updates": list(audit_updates.keys())},
            )

        return content

    async def soft_delete_by_owner(
        self,
        content_id: str,
        actor_id: str,
    ) -> bool:
        """
        软删除内容（仅 owner 或有权限的协作者可操作）

        Args:
            content_id: 内容 ID
            actor_id: 操作者 ID

        Returns:
            是否删除成功
        """
        permission_condition = self._build_permission_condition(
            content_id, actor_id, require_admin=True
        )

        stmt = (
            update(ContentModel)
            .where(
                and_(
                    ContentModel.id == content_id,
                    ContentModel.deleted_at.is_(None),
                    permission_condition,
                )
            )
            .values(deleted_at=datetime.now(), updated_at=datetime.now())
            .returning(ContentModel.id)
        )

        result = await self.db.execute(stmt)
        deleted = result.scalar_one_or_none()

        if deleted:
            await self._audit(
                content_id=content_id,
                actor_id=actor_id,
                action=AuditAction.DELETE,
            )
            await self._push_event(
                OutboxEventType.CONTENT_DELETED,
                {"content_id": content_id},
            )
            return True
        return False

    async def publish_by_owner(
        self,
        content_id: str,
        actor_id: str,
    ) -> ContentModel | None:
        """
        发布内容

        Args:
            content_id: 内容 ID
            actor_id: 操作者 ID

        Returns:
            发布后的内容
        """
        permission_condition = self._build_permission_condition(content_id, actor_id)

        now = datetime.now()
        stmt = (
            update(ContentModel)
            .where(
                and_(
                    ContentModel.id == content_id,
                    ContentModel.deleted_at.is_(None),
                    ContentModel.status != ContentStatus.PUBLISHED,
                    permission_condition,
                )
            )
            .values(
                status=ContentStatus.PUBLISHED,
                published_at=now,
                updated_at=now,
            )
            .returning(ContentModel)
        )

        result = await self.db.execute(stmt)
        content = result.scalar_one_or_none()

        if content:
            await self._audit(
                content_id=content_id,
                actor_id=actor_id,
                action=AuditAction.PUBLISH,
            )
            await self._push_event(
                OutboxEventType.CONTENT_PUBLISHED,
                {"content_id": content_id},
            )

        return content

    async def archive_by_owner(
        self,
        content_id: str,
        actor_id: str,
    ) -> ContentModel | None:
        """
        归档内容

        Args:
            content_id: 内容 ID
            actor_id: 操作者 ID

        Returns:
            归档后的内容
        """
        permission_condition = self._build_permission_condition(content_id, actor_id)

        stmt = (
            update(ContentModel)
            .where(
                and_(
                    ContentModel.id == content_id,
                    ContentModel.deleted_at.is_(None),
                    permission_condition,
                )
            )
            .values(
                status=ContentStatus.ARCHIVED,
                updated_at=datetime.now(),
            )
            .returning(ContentModel)
        )

        result = await self.db.execute(stmt)
        content = result.scalar_one_or_none()

        if content:
            await self._audit(
                content_id=content_id,
                actor_id=actor_id,
                action=AuditAction.ARCHIVE,
            )
            await self._push_event(
                OutboxEventType.CONTENT_ARCHIVED,
                {"content_id": content_id},
            )

        return content

    # =========================================================================
    # 读操作（强制状态过滤）
    # =========================================================================

    async def get_published(self, content_id: str) -> ContentModel | None:
        """
        获取已发布的内容（公开访问）

        强制过滤：status='published' AND deleted_at IS NULL
        """
        stmt = select(ContentModel).where(
            and_(
                ContentModel.id == content_id,
                ContentModel.status == ContentStatus.PUBLISHED,
                ContentModel.deleted_at.is_(None),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_owner(
        self,
        content_id: str,
        owner_id: str,
    ) -> ContentModel | None:
        """
        获取内容（owner 视角，可看草稿）
        """
        permission_condition = self._build_permission_condition(content_id, owner_id)

        stmt = select(ContentModel).where(
            and_(
                ContentModel.id == content_id,
                ContentModel.deleted_at.is_(None),
                permission_condition,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_published(
        self,
        *,
        type: ContentType | None = None,
        concept_ids: list[str] | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[ContentModel]:
        """
        列出已发布内容（公开访问）

        强制过滤：status='published' AND deleted_at IS NULL
        """
        stmt = select(ContentModel).where(
            and_(
                ContentModel.status == ContentStatus.PUBLISHED,
                ContentModel.deleted_at.is_(None),
            )
        )

        if type:
            stmt = stmt.where(ContentModel.type == type)

        # concept_ids 过滤需要 JSON 包含查询，这里简化处理
        # 实际可用 PostgreSQL 的 @> 操作符

        stmt = stmt.order_by(ContentModel.published_at.desc())
        stmt = stmt.offset(skip).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_by_owner(
        self,
        owner_id: str,
        *,
        status: ContentStatus | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[ContentModel]:
        """
        列出教师名下的内容
        """
        stmt = select(ContentModel).where(
            and_(
                ContentModel.owner_teacher_id == owner_id,
                ContentModel.deleted_at.is_(None),
            )
        )

        if status:
            stmt = stmt.where(ContentModel.status == status)

        stmt = stmt.order_by(ContentModel.updated_at.desc())
        stmt = stmt.offset(skip).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_by_owner_with_stats(
        self,
        owner_id: str,
        *,
        type: ContentType | None = None,
        meta_type: str | None = None,
        status: ContentStatus | None = None,
        difficulty_min: float | None = None,
        difficulty_max: float | None = None,
        search: str | None = None,
        concept_ids: list[str] | None = None,
        tags: list[str] | None = None,
        group: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[tuple[ContentModel, int, float]], int]:
        """
        列出教师名下的内容（带统计信息）

        Args:
            owner_id: 教师 ID
            type: 内容类型过滤
            meta_type: meta.type 题型过滤
            status: 状态过滤
            difficulty_min: 最小难度
            difficulty_max: 最大难度
            search: 搜索关键词（分组名/内容）
            concept_ids: 知识点过滤
            tags: 标签过滤
            group: 分组精确筛选（匹配 title 字段）
            sort_by: 排序字段
            sort_order: 排序方向
            skip: 跳过数量
            limit: 返回数量

        Returns:
            ((内容, 使用次数, 正确率) 列表, 总数)
        """
        # 构建基础查询
        base_conditions = [
            ContentModel.owner_teacher_id == owner_id,
            ContentModel.deleted_at.is_(None),
        ]

        if type:
            base_conditions.append(ContentModel.type == type)
        if meta_type:
            base_conditions.append(ContentModel.meta["type"].astext == meta_type)
        if status:
            base_conditions.append(ContentModel.status == status)
        if difficulty_min is not None:
            base_conditions.append(ContentModel.difficulty >= difficulty_min)
        if difficulty_max is not None:
            base_conditions.append(ContentModel.difficulty <= difficulty_max)
        if search:
            search_pattern = f"%{search}%"
            base_conditions.append(
                or_(
                    ContentModel.title.ilike(search_pattern),
                    ContentModel.body.ilike(search_pattern),
                )
            )
        if concept_ids:
            # PostgreSQL 数组包含查询
            base_conditions.append(ContentModel.concept_ids.contains(concept_ids))
        if tags:
            base_conditions.append(ContentModel.tags.overlap(tags))
        if group:
            base_conditions.append(ContentModel.title == group)

        # 统计查询
        usage_count = func.count(ContentAttemptModel.id).label("usage_count")
        correct_rate = (
            func.coalesce(
                func.sum(case((ContentAttemptModel.is_correct.is_(True), 1), else_=0))
                / func.nullif(func.count(ContentAttemptModel.id), 0),
                0.0,
            )
        ).label("correct_rate")

        # 主查询
        stmt = (
            select(ContentModel, usage_count, correct_rate)
            .outerjoin(
                ContentAttemptModel,
                ContentModel.id == ContentAttemptModel.content_id,
            )
            .where(and_(*base_conditions))
            .group_by(ContentModel.id)
        )

        # 排序
        sort_column = {
            "created_at": ContentModel.created_at,
            "updated_at": ContentModel.updated_at,
            "difficulty": ContentModel.difficulty,
            "usage_count": usage_count,
        }.get(sort_by, ContentModel.created_at)

        if sort_order == "asc":
            stmt = stmt.order_by(sort_column.asc())
        else:
            stmt = stmt.order_by(sort_column.desc())

        # 计算总数
        count_stmt = (
            select(func.count(func.distinct(ContentModel.id)))
            .select_from(ContentModel)
            .where(and_(*base_conditions))
        )
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        # 分页
        stmt = stmt.offset(skip).limit(limit)

        result = await self.db.execute(stmt)
        items = [
            (row.ContentModel, row.usage_count, row.correct_rate) for row in result.all()
        ]

        return items, total

    async def batch_update_status(
        self,
        content_ids: list[str],
        owner_id: str,
        status: ContentStatus,
        type: ContentType | None = None,
    ) -> int:
        """
        批量更新内容状态

        Args:
            content_ids: 内容 ID 列表
            owner_id: 操作者 ID
            status: 目标状态
            type: 内容类型过滤

        Returns:
            成功更新的数量
        """
        now = datetime.now()
        updates = {"status": status, "updated_at": now}
        if status == ContentStatus.PUBLISHED:
            updates["published_at"] = now

        stmt = (
            update(ContentModel)
            .where(
                and_(
                    ContentModel.id.in_(content_ids),
                    ContentModel.deleted_at.is_(None),
                    *([ContentModel.type == type] if type else []),
                    or_(
                        ContentModel.owner_teacher_id == owner_id,
                        exists(
                            select(ContentAclModel.content_id).where(
                                and_(
                                    ContentAclModel.content_id == ContentModel.id,
                                    ContentAclModel.teacher_id == owner_id,
                                )
                            )
                        ),
                    ),
                )
            )
            .values(**updates)
        )

        result = await self.db.execute(stmt)
        count = result.rowcount if result.rowcount is not None else 0  # type: ignore[attr-defined]

        # 写审计日志
        for content_id in content_ids[:count]:
            await self._audit(
                content_id=content_id,
                actor_id=owner_id,
                action=AuditAction.UPDATE,
                diff={"status": status.value},
            )

        return count

    async def batch_soft_delete(
        self,
        content_ids: list[str],
        owner_id: str,
        type: ContentType | None = None,
    ) -> int:
        """
        批量软删除内容

        Args:
            content_ids: 内容 ID 列表
            owner_id: 操作者 ID
            type: 内容类型过滤

        Returns:
            成功删除的数量
        """
        now = datetime.now()
        stmt = (
            update(ContentModel)
            .where(
                and_(
                    ContentModel.id.in_(content_ids),
                    ContentModel.deleted_at.is_(None),
                    *([ContentModel.type == type] if type else []),
                    or_(
                        ContentModel.owner_teacher_id == owner_id,
                        exists(
                            select(ContentAclModel.content_id).where(
                                and_(
                                    ContentAclModel.content_id == ContentModel.id,
                                    ContentAclModel.teacher_id == owner_id,
                                    ContentAclModel.permission == "admin",
                                )
                            )
                        ),
                    ),
                )
            )
            .values(deleted_at=now, updated_at=now)
        )

        result = await self.db.execute(stmt)
        count = result.rowcount if result.rowcount is not None else 0  # type: ignore[attr-defined]

        # 写审计日志
        for content_id in content_ids[:count]:
            await self._audit(
                content_id=content_id,
                actor_id=owner_id,
                action=AuditAction.DELETE,
            )

        return count

    async def duplicate_content(
        self,
        content_id: str,
        owner_id: str,
        type: ContentType | None = None,
    ) -> ContentModel | None:
        """
        复制内容

        Args:
            content_id: 源内容 ID
            owner_id: 操作者 ID
            type: 内容类型过滤

        Returns:
            复制后的新内容
        """
        # 获取源内容
        source = await self.get_by_owner(content_id, owner_id)
        if not source:
            return None
        if type and source.type != type:
            return None

        # 创建副本
        new_id = str(uuid4())
        new_content = ContentModel(
            id=new_id,
            type=source.type,
            owner_teacher_id=owner_id,
            status=ContentStatus.DRAFT,
            title=f"[副本] {source.title}",
            body=source.body,
            difficulty=source.difficulty,
            concept_ids=source.concept_ids,
            tags=source.tags,
            meta=source.meta.copy() if source.meta else {},
        )
        self.db.add(new_content)

        # 写审计日志
        await self._audit(
            content_id=new_id,
            actor_id=owner_id,
            action=AuditAction.CREATE,
            diff={"source_id": content_id, "title": new_content.title},
        )

        await self.db.flush()
        await self.db.refresh(new_content)
        return new_content

    async def get_stats_by_owner(
        self,
        owner_id: str,
        *,
        type: ContentType | None = None,
    ) -> dict[str, Any]:
        """
        获取教师的题目统计数据

        Args:
            owner_id: 教师 ID
            type: 内容类型过滤

        Returns:
            统计数据字典
        """
        base_conditions = [
            ContentModel.owner_teacher_id == owner_id,
            ContentModel.deleted_at.is_(None),
        ]
        if type:
            base_conditions.append(ContentModel.type == type)

        # 基础统计
        base_stmt = select(
            func.count(ContentModel.id).label("total"),
            func.count(
                case((ContentModel.status == ContentStatus.PUBLISHED, 1))
            ).label("published"),
            func.count(case((ContentModel.status == ContentStatus.DRAFT, 1))).label(
                "draft"
            ),
            func.count(case((ContentModel.status == ContentStatus.ARCHIVED, 1))).label(
                "archived"
            ),
            func.avg(ContentModel.difficulty).label("avg_difficulty"),
        ).where(and_(*base_conditions))

        result = await self.db.execute(base_stmt)
        row = result.one()

        # 使用统计
        usage_stmt = (
            select(
                func.count(ContentAttemptModel.id).label("total_usage"),
                func.avg(
                    case((ContentAttemptModel.is_correct.is_(True), 1.0), else_=0.0)
                ).label("avg_correct_rate"),
            )
            .select_from(ContentAttemptModel)
            .join(ContentModel, ContentAttemptModel.content_id == ContentModel.id)
            .where(
                and_(
                    *base_conditions,
                )
            )
        )

        usage_result = await self.db.execute(usage_stmt)
        usage_row = usage_result.one()

        return {
            "total_count": row.total or 0,
            "published_count": row.published or 0,
            "draft_count": row.draft or 0,
            "archived_count": row.archived or 0,
            "avg_difficulty": float(row.avg_difficulty or 0.0),
            "total_usage": usage_row.total_usage or 0,
            "avg_correct_rate": float(usage_row.avg_correct_rate or 0.0),
        }

    # =========================================================================
    # 向量检索
    # =========================================================================

    async def search_by_embedding(
        self,
        embedding: list[float],
        *,
        limit: int = 20,
        type: ContentType | None = None,
    ) -> list[tuple[ContentModel, float]]:
        """
        向量检索

        实现方案文档 5.3 的检索 SQL 模板：
        - 向量召回只负责"相关性候选"
        - 最终可见性由 status/deleted_at 二次过滤

        Args:
            embedding: 查询向量
            limit: 返回数量
            type: 内容类型过滤

        Returns:
            (内容, 距离) 列表，按距离升序
        """
        # 构建查询：JOIN contents 并过滤可见性
        distance_expr = ContentEmbeddingModel.embedding.cosine_distance(embedding)

        stmt = (
            select(ContentModel, distance_expr.label("distance"))
            .join(
                ContentEmbeddingModel,
                ContentModel.id == ContentEmbeddingModel.content_id,
            )
            .where(
                and_(
                    ContentModel.status == ContentStatus.PUBLISHED,
                    ContentModel.deleted_at.is_(None),
                )
            )
            .order_by(distance_expr)
            .limit(limit)
        )

        if type:
            stmt = stmt.where(ContentModel.type == type)

        result = await self.db.execute(stmt)
        return [(row.ContentModel, row.distance) for row in result.all()]

    # =========================================================================
    # Embedding 管理
    # =========================================================================

    async def upsert_embedding(
        self,
        content_id: str,
        model_name: str,
        embedding: list[float],
    ) -> None:
        """
        更新或插入内容向量
        """
        from sqlalchemy.dialects.postgresql import insert

        stmt = insert(ContentEmbeddingModel).values(
            content_id=content_id,
            model_name=model_name,
            embedding=embedding,
            updated_at=datetime.now(),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["content_id", "model_name"],
            set_={
                "embedding": embedding,
                "updated_at": datetime.now(),
            },
        )
        await self.db.execute(stmt)

    async def delete_embedding(self, content_id: str) -> None:
        """
        删除内容的所有向量
        """
        from sqlalchemy import delete

        stmt = delete(ContentEmbeddingModel).where(
            ContentEmbeddingModel.content_id == content_id
        )
        await self.db.execute(stmt)

    # =========================================================================
    # 内部方法
    # =========================================================================

    def _build_permission_condition(
        self,
        content_id: str,
        actor_id: str,
        *,
        require_admin: bool = False,
    ):
        """
        构建权限条件

        Args:
            content_id: 内容 ID
            actor_id: 操作者 ID
            require_admin: 是否要求 admin 权限（用于删除等危险操作）

        Returns:
            SQLAlchemy 条件表达式
        """
        acl_conditions = [
            ContentAclModel.content_id == content_id,
            ContentAclModel.teacher_id == actor_id,
        ]
        if require_admin:
            acl_conditions.append(ContentAclModel.permission == "admin")

        return or_(
            ContentModel.owner_teacher_id == actor_id,
            exists(select(ContentAclModel.content_id).where(and_(*acl_conditions))),
        )

    def _to_jsonable(self, value: Any) -> Any:
        """将对象转换为可写入 JSON 字段的值"""
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, dict):
            return {k: self._to_jsonable(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._to_jsonable(v) for v in value]
        if isinstance(value, tuple):
            return [self._to_jsonable(v) for v in value]
        return value

    async def _audit(
        self,
        content_id: str,
        actor_id: str,
        action: AuditAction,
        diff: dict[str, Any] | None = None,
    ) -> None:
        """写审计日志"""
        audit = ContentAuditModel(
            id=str(uuid4()),
            content_id=content_id,
            actor_user_id=actor_id,
            action=action,
            diff=self._to_jsonable(diff or {}),
        )
        self.db.add(audit)

    async def _push_event(
        self,
        event_type: OutboxEventType,
        payload: dict[str, Any],
    ) -> None:
        """写 outbox 事件"""
        event = OutboxEventModel(
            id=str(uuid4()),
            type=event_type,
            payload=payload,
        )
        self.db.add(event)
