"""
学生画像 API 路由

提供学生画像的获取、生成和清除接口
"""

import logging

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUserId, DbSession
from app.api.v1.schemas.student_portrait import (
    ClearPortraitResponse,
    GeneratePortraitResponse,
    StudentPortraitResponse,
)
from app.services.student_portrait_service import get_student_portrait_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=StudentPortraitResponse)
async def get_portrait(user_id: CurrentUserId, db: DbSession):
    """获取当前学生画像"""
    service = get_student_portrait_service(db)
    profile = await service.get_portrait(user_id)

    return StudentPortraitResponse(
        student_id=profile.student_id,
        portrait_content=profile.portrait_content,
        portrait_generated_at=profile.portrait_generated_at,
        portrait_version=profile.portrait_version,
        total_exercises=profile.total_exercises,
        correct_rate=(
            round(profile.correct_count / profile.total_exercises, 2)
            if profile.total_exercises > 0
            else 0.0
        ),
        total_study_time_minutes=profile.total_study_time_minutes,
        has_content=profile.portrait_content is not None,
    )


@router.post("/generate", response_model=GeneratePortraitResponse)
async def generate_portrait(user_id: CurrentUserId, db: DbSession):
    """生成/重新生成学生画像"""
    service = get_student_portrait_service(db)
    try:
        profile = await service.generate_portrait(user_id)
    except Exception as e:
        logger.error(f"生成画像失败: {e}")
        raise HTTPException(status_code=500, detail="画像生成失败，请稍后重试") from e

    return GeneratePortraitResponse(
        portrait_content=profile.portrait_content,  # type: ignore[arg-type]
        portrait_generated_at=profile.portrait_generated_at,  # type: ignore[arg-type]
        portrait_version=profile.portrait_version,
    )


@router.delete("", response_model=ClearPortraitResponse)
async def clear_portrait(user_id: CurrentUserId, db: DbSession):
    """清除学生画像"""
    service = get_student_portrait_service(db)
    await service.clear_portrait(user_id)

    return ClearPortraitResponse(cleared=True, message="画像已清除")
