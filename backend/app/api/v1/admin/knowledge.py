"""
管理员知识点管理 API

提供知识节点和关系的 CRUD 接口，仅管理员可访问
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import AdminUserId, DbSession
from app.api.v1.schemas.knowledge import (
    ChapterListResponse,
    KnowledgeNodeCreateRequest,
    KnowledgeNodeDeleteResponse,
    KnowledgeNodeItem,
    KnowledgeNodeListResponse,
    KnowledgeNodeResponse,
    KnowledgeNodeUpdateRequest,
    KnowledgeRelationCreateRequest,
    KnowledgeRelationDeleteResponse,
    KnowledgeRelationItem,
    KnowledgeRelationListResponse,
    KnowledgeRelationResponse,
    KnowledgeRelationUpdateRequest,
    KnowledgeStatsResponse,
    SimpleNodeItem,
)
from app.services.knowledge_admin_service import KnowledgeAdminService

logger = logging.getLogger(__name__)

router = APIRouter()


# ========== 依赖注入 ==========


async def get_knowledge_admin_service(db: DbSession) -> KnowledgeAdminService:
    """获取知识点管理服务"""
    return KnowledgeAdminService(db=db)


KnowledgeAdminServiceDep = Annotated[
    KnowledgeAdminService, Depends(get_knowledge_admin_service)
]


# ========== 统计和元数据 ==========


@router.get(
    "/stats",
    response_model=KnowledgeStatsResponse,
    summary="获取知识点统计",
    description="获取知识节点和关系的统计数据",
)
async def get_knowledge_stats(
    _admin_id: AdminUserId,
    service: KnowledgeAdminServiceDep,
) -> KnowledgeStatsResponse:
    stats = await service.get_stats()
    return KnowledgeStatsResponse(**stats)


@router.get(
    "/chapters",
    response_model=ChapterListResponse,
    summary="获取章节列表",
    description="获取所有不重复的章节名称",
)
async def get_chapters(
    _admin_id: AdminUserId,
    service: KnowledgeAdminServiceDep,
) -> ChapterListResponse:
    chapters = await service.get_chapters()
    return ChapterListResponse(chapters=chapters)


# ========== 知识节点 CRUD ==========


@router.get(
    "/nodes",
    response_model=KnowledgeNodeListResponse,
    summary="获取知识节点列表",
    description="分页查询知识节点，支持按章节、类型、关键词筛选",
)
async def list_nodes(
    _admin_id: AdminUserId,
    service: KnowledgeAdminServiceDep,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    chapter: str | None = Query(None, description="章节筛选"),
    node_type: str | None = Query(None, alias="type", description="类型筛选"),
    search: str | None = Query(None, description="搜索关键词"),
) -> KnowledgeNodeListResponse:
    result = await service.list_nodes(
        page=page,
        page_size=page_size,
        chapter=chapter,
        node_type=node_type,
        search=search,
    )
    return KnowledgeNodeListResponse(
        items=[KnowledgeNodeItem.model_validate(n) for n in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"],
    )


@router.get(
    "/nodes/all",
    response_model=list[SimpleNodeItem],
    summary="获取所有节点简要信息",
    description="获取所有节点的 ID 和名称，用于关系管理的下拉选择",
)
async def get_all_nodes_simple(
    _admin_id: AdminUserId,
    service: KnowledgeAdminServiceDep,
) -> list[SimpleNodeItem]:
    nodes = await service.get_all_nodes_simple()
    return [SimpleNodeItem(**n) for n in nodes]


@router.post(
    "/nodes",
    response_model=KnowledgeNodeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建知识节点",
)
async def create_node(
    data: KnowledgeNodeCreateRequest,
    _admin_id: AdminUserId,
    service: KnowledgeAdminServiceDep,
) -> KnowledgeNodeResponse:
    try:
        node = await service.create_node(
            name=data.name,
            node_type=data.node_type,
            description=data.description,
            name_en=data.name_en,
            chapter=data.chapter,
            section=data.section,
            difficulty=data.difficulty,
            latex_formula=data.latex_formula,
            tags=data.tags,
        )
        return KnowledgeNodeResponse(
            success=True,
            message="创建成功",
            node=KnowledgeNodeItem.model_validate(node),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/nodes/{node_id}",
    response_model=KnowledgeNodeItem,
    summary="获取单个知识节点",
)
async def get_node(
    node_id: str,
    _admin_id: AdminUserId,
    service: KnowledgeAdminServiceDep,
) -> KnowledgeNodeItem:
    node = await service.get_node(node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="知识节点不存在")
    return KnowledgeNodeItem.model_validate(node)


@router.put(
    "/nodes/{node_id}",
    response_model=KnowledgeNodeResponse,
    summary="更新知识节点",
)
async def update_node(
    node_id: str,
    data: KnowledgeNodeUpdateRequest,
    _admin_id: AdminUserId,
    service: KnowledgeAdminServiceDep,
) -> KnowledgeNodeResponse:
    update_data = data.model_dump(exclude_unset=True)
    node, message = await service.update_node(node_id, **update_data)
    if node is None:
        raise HTTPException(status_code=400, detail=message)
    return KnowledgeNodeResponse(
        success=True,
        message=message,
        node=KnowledgeNodeItem.model_validate(node),
    )


@router.delete(
    "/nodes/{node_id}",
    response_model=KnowledgeNodeDeleteResponse,
    summary="删除知识节点",
    description="删除知识节点及其关联的所有关系",
)
async def delete_node(
    node_id: str,
    _admin_id: AdminUserId,
    service: KnowledgeAdminServiceDep,
) -> KnowledgeNodeDeleteResponse:
    success, message = await service.delete_node(node_id)
    if not success:
        raise HTTPException(
            status_code=404 if message == "知识节点不存在" else 400,
            detail=message,
        )
    return KnowledgeNodeDeleteResponse(success=True, message=message)


# ========== 知识关系 CRUD ==========


@router.get(
    "/relations",
    response_model=KnowledgeRelationListResponse,
    summary="获取知识关系列表",
    description="查询知识关系，可按节点 ID 筛选",
)
async def list_relations(
    _admin_id: AdminUserId,
    service: KnowledgeAdminServiceDep,
    node_id: str | None = Query(None, description="按节点 ID 筛选"),
) -> KnowledgeRelationListResponse:
    relations = await service.list_relations(node_id=node_id)
    return KnowledgeRelationListResponse(
        items=[KnowledgeRelationItem(**r) for r in relations],
        total=len(relations),
    )


@router.post(
    "/relations",
    response_model=KnowledgeRelationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建知识关系",
)
async def create_relation(
    data: KnowledgeRelationCreateRequest,
    _admin_id: AdminUserId,
    service: KnowledgeAdminServiceDep,
) -> KnowledgeRelationResponse:
    relation, message = await service.create_relation(
        source_id=data.source_id,
        target_id=data.target_id,
        relation_type=data.relation_type,
        weight=data.weight,
        description=data.description,
    )
    if relation is None:
        raise HTTPException(status_code=400, detail=message)
    return KnowledgeRelationResponse(
        success=True,
        message=message,
        relation=KnowledgeRelationItem(
            id=relation.id,
            source_id=relation.source_id,
            target_id=relation.target_id,
            source_name=getattr(relation, "source_name", None),
            target_name=getattr(relation, "target_name", None),
            relation_type=(
                relation.relation_type.value
                if hasattr(relation.relation_type, "value")
                else relation.relation_type
            ),
            weight=relation.weight,
            description=relation.description,
            created_at=relation.created_at,
        ),
    )


@router.put(
    "/relations/{relation_id}",
    response_model=KnowledgeRelationResponse,
    summary="更新知识关系",
)
async def update_relation(
    relation_id: str,
    data: KnowledgeRelationUpdateRequest,
    _admin_id: AdminUserId,
    service: KnowledgeAdminServiceDep,
) -> KnowledgeRelationResponse:
    update_data = data.model_dump(exclude_unset=True)
    relation, message = await service.update_relation(relation_id, **update_data)
    if relation is None:
        raise HTTPException(status_code=400, detail=message)
    return KnowledgeRelationResponse(
        success=True,
        message=message,
        relation=KnowledgeRelationItem(
            id=relation.id,
            source_id=relation.source_id,
            target_id=relation.target_id,
            source_name=getattr(relation, "source_name", None),
            target_name=getattr(relation, "target_name", None),
            relation_type=(
                relation.relation_type.value
                if hasattr(relation.relation_type, "value")
                else relation.relation_type
            ),
            weight=relation.weight,
            description=relation.description,
            created_at=relation.created_at,
        ),
    )


@router.delete(
    "/relations/{relation_id}",
    response_model=KnowledgeRelationDeleteResponse,
    summary="删除知识关系",
)
async def delete_relation(
    relation_id: str,
    _admin_id: AdminUserId,
    service: KnowledgeAdminServiceDep,
) -> KnowledgeRelationDeleteResponse:
    result = await service.delete_relation(relation_id)
    if not result:
        raise HTTPException(status_code=404, detail="知识关系不存在")
    return KnowledgeRelationDeleteResponse(success=True, message="删除成功")
