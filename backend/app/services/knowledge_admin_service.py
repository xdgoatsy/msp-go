"""
管理员知识点管理服务

提供知识节点和关系的 CRUD 业务逻辑
"""

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.knowledge_node import NodeType, RelationType
from app.infrastructure.database.models import (
    KnowledgeNodeModel,
    KnowledgeRelationModel,
)
from app.infrastructure.repositories.knowledge_repository import KnowledgeRepository
from app.services.utils import calculate_offset, calculate_total_pages

logger = logging.getLogger(__name__)


# NodeType 字符串到枚举的映射
NODE_TYPE_MAP: dict[str, NodeType] = {
    "concept": NodeType.CONCEPT,
    "theorem": NodeType.THEOREM,
    "method": NodeType.METHOD,
    "problem": NodeType.PROBLEM,
    "misconception": NodeType.MISCONCEPTION,
    "resource": NodeType.RESOURCE,
}

# RelationType 字符串到枚举的映射
RELATION_TYPE_MAP: dict[str, RelationType] = {
    "has_prerequisite": RelationType.HAS_PREREQUISITE,
    "is_a_special_case_of": RelationType.IS_A_SPECIAL_CASE_OF,
    "used_in": RelationType.USED_IN,
    "prone_to_error": RelationType.PRONE_TO_ERROR,
    "related_to": RelationType.RELATED_TO,
}


class KnowledgeAdminService:
    """管理员知识点管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = KnowledgeRepository(db)

    # ========== 知识节点 CRUD ==========

    async def list_nodes(
        self,
        page: int = 1,
        page_size: int = 20,
        chapter: str | None = None,
        node_type: str | None = None,
        search: str | None = None,
    ) -> dict:
        """分页查询知识节点列表"""
        nt = NODE_TYPE_MAP.get(node_type) if node_type else None
        offset = calculate_offset(page, page_size)

        total = await self.repo.count_nodes(
            chapter=chapter, node_type=nt, search=search
        )
        nodes = await self.repo.get_nodes_paginated(
            chapter=chapter,
            node_type=nt,
            search=search,
            offset=offset,
            limit=page_size,
        )

        return {
            "items": nodes,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": calculate_total_pages(total, page_size),
        }

    async def get_node(self, node_id: str) -> KnowledgeNodeModel | None:
        """获取单个知识节点"""
        return await self.repo.get_node_by_id(node_id)

    async def create_node(
        self,
        *,
        name: str,
        node_type: str,
        description: str = "",
        name_en: str | None = None,
        chapter: str | None = None,
        section: str | None = None,
        difficulty: float = 0.5,
        latex_formula: str | None = None,
        tags: list[str] | None = None,
    ) -> KnowledgeNodeModel:
        """创建知识节点"""
        nt = NODE_TYPE_MAP.get(node_type)
        if nt is None:
            raise ValueError(f"无效的节点类型: {node_type}")

        now = datetime.now()
        node = KnowledgeNodeModel(
            name=name,
            name_en=name_en,
            node_type=nt,
            description=description,
            chapter=chapter,
            section=section,
            difficulty=difficulty,
            latex_formula=latex_formula,
            tags=tags or [],
            created_at=now,
            updated_at=now,
        )
        created = await self.repo.create_node(node)
        await self.db.commit()
        logger.info("知识节点已创建: %s (%s)", name, created.id)
        return created

    async def update_node(
        self, node_id: str, **kwargs: object
    ) -> tuple[KnowledgeNodeModel | None, str]:
        """更新知识节点，返回 (节点, 消息)"""
        # 转换 node_type 字符串为枚举
        if "node_type" in kwargs and kwargs["node_type"] is not None:
            nt = NODE_TYPE_MAP.get(str(kwargs["node_type"]))
            if nt is None:
                return None, f"无效的节点类型: {kwargs['node_type']}"
            kwargs["node_type"] = nt

        # 过滤掉 None 值
        update_data = {k: v for k, v in kwargs.items() if v is not None}
        if not update_data:
            return None, "没有需要更新的字段"

        node = await self.repo.update_node(node_id, **update_data)
        if node is None:
            return None, "知识节点不存在"

        await self.db.commit()
        logger.info("知识节点已更新: %s", node_id)
        return node, "更新成功"

    async def delete_node(self, node_id: str) -> tuple[bool, str]:
        """删除知识节点（级联删除关联关系），返回 (是否成功, 消息)"""
        try:
            result = await self.repo.delete_node(node_id)
            if not result:
                return False, "知识节点不存在"
            await self.db.commit()
            logger.info("知识节点已删除: %s", node_id)
            return True, "删除成功"
        except Exception as e:
            await self.db.rollback()
            logger.error("删除知识节点失败 %s: %s", node_id, e)
            return False, f"删除失败: {e}"

    # ========== 知识关系 CRUD ==========

    async def list_relations(
        self, node_id: str | None = None
    ) -> list[dict]:
        """查询知识关系列表（可按节点筛选），补充源/目标节点名称"""
        if node_id:
            relations = await self.repo.get_relations_by_node(node_id)
        else:
            relations = await self.repo.get_all_relations()

        result = []
        for rel in relations:
            source = await self.repo.get_node_by_id(rel.source_id)
            target = await self.repo.get_node_by_id(rel.target_id)
            result.append({
                "id": rel.id,
                "source_id": rel.source_id,
                "target_id": rel.target_id,
                "source_name": source.name if source else None,
                "target_name": target.name if target else None,
                "relation_type": (
                    rel.relation_type.value
                    if hasattr(rel.relation_type, "value")
                    else rel.relation_type
                ),
                "weight": rel.weight,
                "description": rel.description,
                "created_at": rel.created_at,
            })
        return result

    async def create_relation(
        self,
        *,
        source_id: str,
        target_id: str,
        relation_type: str,
        weight: float = 1.0,
        description: str | None = None,
    ) -> tuple[KnowledgeRelationModel | None, str]:
        """创建知识关系，返回 (关系, 消息)"""
        # 验证源/目标节点存在
        source = await self.repo.get_node_by_id(source_id)
        if source is None:
            return None, "源节点不存在"

        target = await self.repo.get_node_by_id(target_id)
        if target is None:
            return None, "目标节点不存在"

        if source_id == target_id:
            return None, "源节点和目标节点不能相同"

        rt = RELATION_TYPE_MAP.get(relation_type)
        if rt is None:
            return None, f"无效的关系类型: {relation_type}"

        relation = KnowledgeRelationModel(
            source_id=source_id,
            target_id=target_id,
            relation_type=rt,
            weight=weight,
            description=description,
            created_at=datetime.now(),
        )
        created = await self.repo.create_relation(relation)
        await self.db.commit()
        logger.info("知识关系已创建: %s", created.id)
        return created, "创建成功"

    async def update_relation(
        self, relation_id: str, **kwargs: object
    ) -> tuple[KnowledgeRelationModel | None, str]:
        """更新知识关系，返回 (关系, 消息)"""
        if "relation_type" in kwargs and kwargs["relation_type"] is not None:
            rt = RELATION_TYPE_MAP.get(str(kwargs["relation_type"]))
            if rt is None:
                return None, f"无效的关系类型: {kwargs['relation_type']}"
            kwargs["relation_type"] = rt

        update_data = {k: v for k, v in kwargs.items() if v is not None}
        if not update_data:
            return None, "没有需要更新的字段"

        relation = await self.repo.update_relation(relation_id, **update_data)
        if relation is None:
            return None, "知识关系不存在"

        await self.db.commit()
        logger.info("知识关系已更新: %s", relation_id)
        return relation, "更新成功"

    async def delete_relation(self, relation_id: str) -> bool:
        """删除知识关系"""
        result = await self.repo.delete_relation(relation_id)
        if result:
            await self.db.commit()
            logger.info("知识关系已删除: %s", relation_id)
        return result

    # ========== 统计和元数据 ==========

    async def get_stats(self) -> dict:
        """获取知识点统计数据"""
        nodes = await self.repo.get_all_nodes()
        relations = await self.repo.get_all_relations()
        chapters = await self.repo.get_distinct_chapters()

        type_distribution: dict[str, int] = {}
        for node in nodes:
            type_val = (
                node.node_type.value
                if hasattr(node.node_type, "value")
                else str(node.node_type)
            )
            type_distribution[type_val] = type_distribution.get(type_val, 0) + 1

        return {
            "total_nodes": len(nodes),
            "total_relations": len(relations),
            "chapters_count": len(chapters),
            "type_distribution": type_distribution,
        }

    async def get_chapters(self) -> list[str]:
        """获取所有章节列表"""
        return await self.repo.get_distinct_chapters()

    async def get_all_nodes_simple(self) -> list[dict]:
        """获取所有节点的简要信息（用于关系管理的下拉选择）"""
        nodes = await self.repo.get_all_nodes()
        return [
            {"id": n.id, "name": n.name, "chapter": n.chapter, "node_type": n.node_type.value if hasattr(n.node_type, 'value') else n.node_type}
            for n in nodes
        ]
