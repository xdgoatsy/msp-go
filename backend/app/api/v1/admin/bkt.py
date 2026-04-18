"""
管理员 BKT 参数管理 API

提供知识点 BKT 参数的查看、编辑、重置和批量种子化接口
"""

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import AdminUserId, DbSession
from app.infrastructure.repositories.bkt_repository import BKTRepository

router = APIRouter()


# ========== 请求/响应模型 ==========


class BKTParamItem(BaseModel):
    concept_id: str
    p_l0: float
    p_t: float
    p_g: float
    p_s: float


class BKTParamListResponse(BaseModel):
    items: list[BKTParamItem]
    total: int
    offset: int
    limit: int


class BKTParamUpdateRequest(BaseModel):
    p_l0: float | None = Field(None, ge=0.0, le=1.0)
    p_t: float | None = Field(None, ge=0.0, le=1.0)
    p_g: float | None = Field(None, ge=0.0, le=0.5)
    p_s: float | None = Field(None, ge=0.0, le=0.5)


class SeedResponse(BaseModel):
    seeded_count: int
    message: str


# ========== 路由 ==========


@router.get("/params", response_model=BKTParamListResponse)
async def list_bkt_params(
    db: DbSession,
    _admin: AdminUserId,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> BKTParamListResponse:
    """列出所有知识点 BKT 参数（分页）"""
    repo = BKTRepository(db)
    items = await repo.get_all_concept_params(offset=offset, limit=limit)
    total = await repo.count_concept_params()
    return BKTParamListResponse(
        items=[
            BKTParamItem(
                concept_id=row.concept_id,
                p_l0=float(row.p_l0),
                p_t=float(row.p_t),
                p_g=float(row.p_g),
                p_s=float(row.p_s),
            )
            for row in items
        ],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.put("/params/{concept_id}", response_model=BKTParamItem)
async def update_bkt_param(
    concept_id: str,
    body: BKTParamUpdateRequest,
    db: DbSession,
    _admin: AdminUserId,
) -> BKTParamItem:
    """更新单个知识点 BKT 参数"""
    repo = BKTRepository(db)
    row = await repo.update_concept_param(
        concept_id,
        p_l0=body.p_l0,
        p_t=body.p_t,
        p_g=body.p_g,
        p_s=body.p_s,
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"知识点 {concept_id} 的 BKT 参数不存在",
        )
    await db.commit()
    return BKTParamItem(
        concept_id=row.concept_id,
        p_l0=float(row.p_l0),
        p_t=float(row.p_t),
        p_g=float(row.p_g),
        p_s=float(row.p_s),
    )


@router.post("/params/reset/{concept_id}", response_model=BKTParamItem)
async def reset_bkt_param(
    concept_id: str,
    db: DbSession,
    _admin: AdminUserId,
) -> BKTParamItem:
    """将知识点 BKT 参数重置为默认值"""
    repo = BKTRepository(db)
    row = await repo.reset_concept_param(concept_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"知识点 {concept_id} 的 BKT 参数不存在",
        )
    await db.commit()
    return BKTParamItem(
        concept_id=row.concept_id,
        p_l0=float(row.p_l0),
        p_t=float(row.p_t),
        p_g=float(row.p_g),
        p_s=float(row.p_s),
    )


@router.post("/seed", response_model=SeedResponse)
async def seed_bkt_params(
    db: DbSession,
    _admin: AdminUserId,
) -> SeedResponse:
    """为缺少 BKT 参数的知识点批量插入默认值"""
    repo = BKTRepository(db)
    count = await repo.seed_default_params()
    await db.commit()
    return SeedResponse(
        seeded_count=count,
        message=f"已为 {count} 个知识点创建默认 BKT 参数" if count > 0 else "所有知识点已有 BKT 参数",
    )
