"""
资源 API

提供资源的 CRUD 和收藏功能
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUserId, DbSession, TeacherUserId
from app.api.v1.schemas.resource import (
    FavoriteToggleResponse,
    ResourceCreate,
    ResourceFilter,
    ResourceListResponse,
    ResourceResponse,
    ResourceStats,
    ResourceType,
    ResourceUpdate,
)
from app.services.resource_service import get_resource_service

router = APIRouter()


@router.get("", response_model=ResourceListResponse)
async def get_resources(
    db: DbSession,
    current_user_id: CurrentUserId,
    type: Annotated[ResourceType | None, Query(description="资源类型")] = None,
    chapter: Annotated[str | None, Query(description="章节")] = None,
    topic: Annotated[str | None, Query(description="主题")] = None,
    search: Annotated[str | None, Query(description="搜索关键词")] = None,
    favorites_only: Annotated[bool, Query(description="仅显示收藏")] = False,
    page: Annotated[int, Query(ge=1, description="页码")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="每页数量")] = 20,
):
    """
    获取资源列表

    支持按类型、章节、主题筛选，支持搜索和收藏筛选
    """
    service = get_resource_service(db)

    filter_params = ResourceFilter(
        type=type,
        chapter=chapter,
        topic=topic,
        search=search,
        favorites_only=favorites_only,
        page=page,
        page_size=page_size,
    )

    result = await service.get_resources(current_user_id, filter_params)
    return result


@router.get("/stats", response_model=ResourceStats)
async def get_resource_stats(
    db: DbSession,
    current_user_id: CurrentUserId,
):
    """获取资源统计数据"""
    service = get_resource_service(db)
    return await service.get_stats(current_user_id)


@router.get("/favorites", response_model=ResourceListResponse)
async def get_favorites(
    db: DbSession,
    current_user_id: CurrentUserId,
    page: Annotated[int, Query(ge=1, description="页码")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="每页数量")] = 20,
):
    """获取用户收藏列表"""
    service = get_resource_service(db)
    return await service.get_favorites(current_user_id, page, page_size)


@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(
    resource_id: str,
    db: DbSession,
    current_user_id: CurrentUserId,
):
    """获取单个资源详情"""
    service = get_resource_service(db)
    resource = await service.get_resource_by_id(resource_id, current_user_id)

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="资源不存在",
        )

    return resource


@router.post("", response_model=ResourceResponse, status_code=status.HTTP_201_CREATED)
async def create_resource(
    data: ResourceCreate,
    db: DbSession,
    current_user_id: TeacherUserId,
):
    """
    创建资源

    仅教师可创建
    """
    service = get_resource_service(db)
    return await service.create_resource(current_user_id, data)


@router.put("/{resource_id}", response_model=ResourceResponse)
async def update_resource(
    resource_id: str,
    data: ResourceUpdate,
    db: DbSession,
    current_user_id: TeacherUserId,
):
    """
    更新资源

    仅资源创建者可更新
    """
    service = get_resource_service(db)
    resource = await service.update_resource(resource_id, current_user_id, data)

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="资源不存在或无权限修改",
        )

    return resource


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(
    resource_id: str,
    db: DbSession,
    current_user_id: TeacherUserId,
):
    """
    删除资源

    仅资源创建者可删除
    """
    service = get_resource_service(db)
    success = await service.delete_resource(resource_id, current_user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="资源不存在或无权限删除",
        )


@router.post("/{resource_id}/favorite", response_model=FavoriteToggleResponse)
async def toggle_favorite(
    resource_id: str,
    db: DbSession,
    current_user_id: CurrentUserId,
):
    """切换资源收藏状态"""
    service = get_resource_service(db)

    try:
        return await service.toggle_favorite(current_user_id, resource_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
