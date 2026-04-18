"""
知识图谱仓储

提供知识节点和关系的 CRUD 操作
"""

from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.knowledge_node import NodeType, RelationType
from app.infrastructure.database.models import (
    KnowledgeNodeModel,
    KnowledgeRelationModel,
)


class KnowledgeRepository:
    """
    知识图谱仓储

    提供知识节点和关系的查询操作
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # 知识节点查询
    # =========================================================================

    async def get_all_nodes(self) -> list[KnowledgeNodeModel]:
        """
        获取所有知识节点

        Returns:
            知识节点列表
        """
        stmt = select(KnowledgeNodeModel).order_by(KnowledgeNodeModel.created_at)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_node_by_id(self, node_id: str) -> KnowledgeNodeModel | None:
        """
        根据 ID 获取知识节点

        Args:
            node_id: 节点 ID

        Returns:
            知识节点，不存在返回 None
        """
        stmt = select(KnowledgeNodeModel).where(KnowledgeNodeModel.id == node_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_nodes_by_chapter(self, chapter: str) -> list[KnowledgeNodeModel]:
        """
        按章节筛选知识节点

        Args:
            chapter: 章节名称

        Returns:
            知识节点列表
        """
        stmt = (
            select(KnowledgeNodeModel)
            .where(KnowledgeNodeModel.chapter == chapter)
            .order_by(KnowledgeNodeModel.created_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_nodes_by_type(self, node_type: NodeType) -> list[KnowledgeNodeModel]:
        """
        按类型筛选知识节点

        Args:
            node_type: 节点类型

        Returns:
            知识节点列表
        """
        stmt = (
            select(KnowledgeNodeModel)
            .where(KnowledgeNodeModel.node_type == node_type)
            .order_by(KnowledgeNodeModel.created_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def search_nodes(self, keyword: str) -> list[KnowledgeNodeModel]:
        """
        按名称搜索知识节点

        Args:
            keyword: 搜索关键词

        Returns:
            知识节点列表
        """
        search_pattern = f"%{keyword}%"
        stmt = (
            select(KnowledgeNodeModel)
            .where(
                or_(
                    KnowledgeNodeModel.name.ilike(search_pattern),
                    KnowledgeNodeModel.name_en.ilike(search_pattern),
                    KnowledgeNodeModel.description.ilike(search_pattern),
                )
            )
            .order_by(KnowledgeNodeModel.created_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_nodes_with_filters(
        self,
        *,
        chapter: str | None = None,
        node_type: NodeType | None = None,
        search: str | None = None,
    ) -> list[KnowledgeNodeModel]:
        """
        组合筛选知识节点

        Args:
            chapter: 章节名称（可选）
            node_type: 节点类型（可选）
            search: 搜索关键词（可选）

        Returns:
            知识节点列表
        """
        conditions = []

        if chapter:
            conditions.append(KnowledgeNodeModel.chapter == chapter)

        if node_type:
            conditions.append(KnowledgeNodeModel.node_type == node_type)

        if search:
            search_pattern = f"%{search}%"
            conditions.append(
                or_(
                    KnowledgeNodeModel.name.ilike(search_pattern),
                    KnowledgeNodeModel.name_en.ilike(search_pattern),
                    KnowledgeNodeModel.description.ilike(search_pattern),
                )
            )

        stmt = select(KnowledgeNodeModel)
        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(KnowledgeNodeModel.created_at)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # =========================================================================
    # 知识关系查询
    # =========================================================================

    async def get_all_relations(self) -> list[KnowledgeRelationModel]:
        """
        获取所有知识关系

        Returns:
            知识关系列表
        """
        stmt = select(KnowledgeRelationModel).order_by(
            KnowledgeRelationModel.created_at
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_relations_by_node(self, node_id: str) -> list[KnowledgeRelationModel]:
        """
        获取节点相关的所有关系（作为源节点或目标节点）

        Args:
            node_id: 节点 ID

        Returns:
            知识关系列表
        """
        stmt = select(KnowledgeRelationModel).where(
            or_(
                KnowledgeRelationModel.source_id == node_id,
                KnowledgeRelationModel.target_id == node_id,
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_relations_by_type(
        self, relation_type: RelationType
    ) -> list[KnowledgeRelationModel]:
        """
        按关系类型筛选

        Args:
            relation_type: 关系类型

        Returns:
            知识关系列表
        """
        stmt = select(KnowledgeRelationModel).where(
            KnowledgeRelationModel.relation_type == relation_type
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # =========================================================================
    # 创建操作（用于数据初始化和管理）
    # =========================================================================

    async def create_node(self, node: KnowledgeNodeModel) -> KnowledgeNodeModel:
        """
        创建知识节点

        Args:
            node: 知识节点对象

        Returns:
            创建的节点
        """
        self.db.add(node)
        await self.db.flush()
        await self.db.refresh(node)
        return node

    async def create_relation(
        self, relation: KnowledgeRelationModel
    ) -> KnowledgeRelationModel:
        """
        创建知识关系

        Args:
            relation: 知识关系对象

        Returns:
            创建的关系
        """
        self.db.add(relation)
        await self.db.flush()
        await self.db.refresh(relation)
        return relation

    # =========================================================================
    # 更新和删除操作
    # =========================================================================

    async def update_node(
        self, node_id: str, **kwargs: object
    ) -> KnowledgeNodeModel | None:
        """
        更新知识节点

        Args:
            node_id: 节点 ID
            **kwargs: 要更新的字段

        Returns:
            更新后的节点，不存在返回 None
        """
        node = await self.get_node_by_id(node_id)
        if node is None:
            return None

        for key, value in kwargs.items():
            if hasattr(node, key):
                setattr(node, key, value)

        node.updated_at = datetime.now()
        await self.db.flush()
        await self.db.refresh(node)
        return node

    async def delete_node(self, node_id: str) -> bool:
        """
        删除知识节点（同时删除关联的关系）

        Args:
            node_id: 节点 ID

        Returns:
            是否成功删除
        """
        node = await self.get_node_by_id(node_id)
        if node is None:
            return False

        # 先删除关联的关系并 flush，确保外键约束不会阻止节点删除
        relations = await self.get_relations_by_node(node_id)
        if relations:
            for rel in relations:
                await self.db.delete(rel)
            await self.db.flush()

        await self.db.delete(node)
        await self.db.flush()
        return True

    async def get_relation_by_id(
        self, relation_id: str
    ) -> KnowledgeRelationModel | None:
        """根据 ID 获取知识关系"""
        stmt = select(KnowledgeRelationModel).where(
            KnowledgeRelationModel.id == relation_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_relation(
        self, relation_id: str, **kwargs: object
    ) -> KnowledgeRelationModel | None:
        """
        更新知识关系

        Args:
            relation_id: 关系 ID
            **kwargs: 要更新的字段

        Returns:
            更新后的关系，不存在返回 None
        """
        relation = await self.get_relation_by_id(relation_id)
        if relation is None:
            return None

        for key, value in kwargs.items():
            if hasattr(relation, key):
                setattr(relation, key, value)

        await self.db.flush()
        await self.db.refresh(relation)
        return relation

    async def delete_relation(self, relation_id: str) -> bool:
        """
        删除知识关系

        Args:
            relation_id: 关系 ID

        Returns:
            是否成功删除
        """
        relation = await self.get_relation_by_id(relation_id)
        if relation is None:
            return False

        await self.db.delete(relation)
        await self.db.flush()
        return True

    # =========================================================================
    # 聚合查询
    # =========================================================================

    async def get_distinct_chapters(self) -> list[str]:
        """获取所有不重复的章节名称"""
        stmt = (
            select(KnowledgeNodeModel.chapter)
            .where(KnowledgeNodeModel.chapter.isnot(None))
            .where(KnowledgeNodeModel.chapter != "")
            .distinct()
            .order_by(KnowledgeNodeModel.chapter)
        )
        result = await self.db.execute(stmt)
        return [row[0] for row in result.all()]

    async def count_nodes(
        self,
        *,
        chapter: str | None = None,
        node_type: NodeType | None = None,
        search: str | None = None,
    ) -> int:
        """统计节点数量（支持筛选条件）"""
        conditions = self._build_filter_conditions(chapter, node_type, search)

        stmt = select(func.count(KnowledgeNodeModel.id))
        if conditions:
            stmt = stmt.where(and_(*conditions))

        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def get_nodes_paginated(
        self,
        *,
        chapter: str | None = None,
        node_type: NodeType | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[KnowledgeNodeModel]:
        """组合筛选知识节点（带分页）"""
        conditions = self._build_filter_conditions(chapter, node_type, search)

        stmt = select(KnowledgeNodeModel)
        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(KnowledgeNodeModel.created_at).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # =========================================================================
    # 内部工具方法
    # =========================================================================

    @staticmethod
    def _build_filter_conditions(
        chapter: str | None,
        node_type: NodeType | None,
        search: str | None,
    ) -> list:
        """构建筛选条件列表（DRY: 复用于 count_nodes 和 get_nodes_paginated）"""
        conditions = []

        if chapter:
            conditions.append(KnowledgeNodeModel.chapter == chapter)
        if node_type:
            conditions.append(KnowledgeNodeModel.node_type == node_type)
        if search:
            search_pattern = f"%{search}%"
            conditions.append(
                or_(
                    KnowledgeNodeModel.name.ilike(search_pattern),
                    KnowledgeNodeModel.name_en.ilike(search_pattern),
                    KnowledgeNodeModel.description.ilike(search_pattern),
                )
            )

        return conditions
