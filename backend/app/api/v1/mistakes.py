"""
错题本相关接口

处理错题查询、统计分析、复习推荐等
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import DbSession, StudentUserId
from app.services.mistake_service import MistakeService

router = APIRouter()


# ========== 请求/响应模型 ==========


class MistakeExercise(BaseModel):
    """错题中的题目信息"""

    id: str
    title: str
    content: str
    difficulty: float
    knowledge_points: list[str]


class MistakeAttempt(BaseModel):
    """错题中的作答信息"""

    student_answer: str
    correct_answer: str
    is_correct: bool
    score: float
    submitted_at: str | None
    time_spent_seconds: int


class MistakeDiagnosis(BaseModel):
    """错题中的诊断信息"""

    error_type: str | None
    error_subtype: str
    severity: str
    explanation: str
    suggestion: str
    related_concepts: list[str]


class MistakeMastery(BaseModel):
    """错题中的掌握度信息"""

    current: float
    previous: float
    trend: str


class MistakeItem(BaseModel):
    """错题列表项"""

    id: str
    exercise: MistakeExercise
    attempt: MistakeAttempt
    diagnosis: MistakeDiagnosis
    mastery: MistakeMastery
    error_count: int
    last_reviewed_at: str | None


class PaginationInfo(BaseModel):
    """分页信息"""

    page: int
    page_size: int
    total: int
    total_pages: int


class MistakeStatistics(BaseModel):
    """错题统计信息"""

    total_mistakes: int
    weak_concepts: int
    avg_mastery: float


class MistakeListResponse(BaseModel):
    """错题列表响应"""

    items: list[MistakeItem]
    pagination: PaginationInfo
    statistics: MistakeStatistics


class ErrorTypeDistribution(BaseModel):
    """错误类型分布"""

    count: int
    percentage: float
    label: str


class ConceptWeakness(BaseModel):
    """知识点薄弱度"""

    concept_id: str
    concept_name: str
    mistake_count: int
    mastery: float
    recent_mistakes: int


class StatisticsOverview(BaseModel):
    """统计总览"""

    total_mistakes: int
    total_exercises: int
    mistake_rate: float
    avg_mastery: float


class MistakeStatisticsResponse(BaseModel):
    """错题统计响应"""

    overview: StatisticsOverview
    error_type_distribution: dict[str, ErrorTypeDistribution]
    concept_weakness: list[ConceptWeakness]


class MistakeDetailExercise(BaseModel):
    """错题详情中的题目信息"""

    id: str
    title: str
    content: str
    difficulty: float
    knowledge_points: list[str]
    hints: list[str]


class MistakeDetailAttempt(BaseModel):
    """错题详情中的作答信息"""

    student_answer: str
    student_steps: list[str]
    correct_answer: str
    submitted_at: str | None
    time_spent_seconds: int


class MistakeDetailDiagnosis(BaseModel):
    """错题详情中的诊断信息"""

    error_type: str | None
    error_step_index: int | None
    explanation: str
    suggestion: str
    related_concepts: list[str]


class MistakeSolution(BaseModel):
    """错题解析"""

    answer: str
    steps: list[str]
    source: str


class MistakeHistory(BaseModel):
    """错题历史记录"""

    attempt_id: str
    submitted_at: str | None
    is_correct: bool
    score: float


class MistakeDetailResponse(BaseModel):
    """错题详情响应"""

    attempt_id: str
    exercise: MistakeDetailExercise
    attempt: MistakeDetailAttempt
    diagnosis: MistakeDetailDiagnosis
    solution: MistakeSolution
    history: list[MistakeHistory]


class MarkAsMasteredResponse(BaseModel):
    """标记已掌握响应"""

    success: bool
    mastered_at: str
    mastery_update: dict[str, float]


class ReviewExercise(BaseModel):
    """复习题目信息"""

    id: str
    title: str
    content: str
    difficulty: float
    type: str
    knowledge_points: list[str]
    hints_available: bool


class ReviewContext(BaseModel):
    """复习上下文"""

    is_review: bool
    original_attempt_id: str
    previous_error_type: str | None
    mastery_before: float
    error_count: int


class ReviewExerciseResponse(BaseModel):
    """复习题目响应"""

    exercise: ReviewExercise
    context: ReviewContext


# ========== 路由处理函数 ==========


@router.get("", response_model=MistakeListResponse)
async def get_mistakes(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    error_type: str | None = Query(None, description="错误类型筛选 (C/P/L/S)"),
    concept_id: str | None = Query(None, description="知识点筛选"),
    difficulty_min: float = Query(0.0, ge=0.0, le=1.0, description="最小难度"),
    difficulty_max: float = Query(1.0, ge=0.0, le=1.0, description="最大难度"),
    date_from: str | None = Query(None, description="开始时间 (ISO 8601)"),
    date_to: str | None = Query(None, description="结束时间 (ISO 8601)"),
    mastery_status: str = Query("all", description="掌握状态 (all/weak/improving/mastered)"),
    sort_by: str = Query("time", description="排序字段 (time/error_count/mastery)"),
    sort_order: str = Query("desc", description="排序方向 (asc/desc)"),
    user_id: StudentUserId = None,
    db: DbSession = None,
):
    """
    获取错题列表

    支持分页、筛选、排序功能
    """
    service = MistakeService(db)

    # 解析日期参数
    date_from_dt = None
    date_to_dt = None
    if date_from:
        try:
            date_from_dt = datetime.fromisoformat(date_from)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="开始时间格式错误，请使用 ISO 8601 格式",
            ) from e

    if date_to:
        try:
            date_to_dt = datetime.fromisoformat(date_to)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="结束时间格式错误，请使用 ISO 8601 格式",
            ) from e

    try:
        result = await service.get_mistakes(
            user_id=user_id,
            page=page,
            page_size=page_size,
            error_type=error_type,
            concept_id=concept_id,
            difficulty_min=difficulty_min,
            difficulty_max=difficulty_max,
            date_from=date_from_dt,
            date_to=date_to_dt,
            mastery_status=mastery_status,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询错题列表失败: {str(e)}",
        ) from e


@router.get("/statistics", response_model=MistakeStatisticsResponse)
async def get_statistics(
    time_range: str = Query("month", description="时间范围 (week/month/semester/all)"),
    user_id: StudentUserId = None,
    db: DbSession = None,
):
    """
    获取错题统计分析

    包含错误类型分布、知识点薄弱度等
    """
    service = MistakeService(db)

    try:
        result = await service.get_statistics(user_id=user_id, time_range=time_range)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询错题统计失败: {str(e)}",
        ) from e


@router.get("/{attempt_id}", response_model=MistakeDetailResponse)
async def get_mistake_detail(
    attempt_id: str,
    user_id: StudentUserId = None,
    db: DbSession = None,
):
    """
    获取错题详情

    包含题目、作答、诊断、解析、历史记录
    """
    service = MistakeService(db)

    try:
        result = await service.get_mistake_detail(user_id=user_id, attempt_id=attempt_id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询错题详情失败: {str(e)}",
        ) from e


@router.post("/{attempt_id}/master", response_model=MarkAsMasteredResponse)
async def mark_as_mastered(
    attempt_id: str,
    user_id: StudentUserId = None,
    db: DbSession = None,
):
    """
    标记错题已掌握

    提升相关知识点掌握度到 0.8+
    """
    service = MistakeService(db)

    try:
        result = await service.mark_as_mastered(user_id=user_id, attempt_id=attempt_id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"标记已掌握失败: {str(e)}",
        ) from e


@router.delete("/{attempt_id}")
async def delete_mistake(
    attempt_id: str,
    user_id: StudentUserId = None,
    db: DbSession = None,
):
    """
    删除错题记录（硬删除）

    警告：删除后无法恢复
    """
    service = MistakeService(db)

    try:
        await service.delete_mistake(user_id=user_id, attempt_id=attempt_id)
        return {"success": True, "message": "错题记录已删除"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除错题失败: {str(e)}",
        ) from e


@router.get("/review/next", response_model=ReviewExerciseResponse)
async def get_review_exercise(
    focus_concept: str | None = Query(None, description="聚焦知识点"),
    focus_error_type: str | None = Query(None, description="聚焦错误类型"),
    user_id: StudentUserId = None,
    db: DbSession = None,
):
    """
    获取复习题目（智能推荐）

    根据掌握度和错误次数推荐最需要复习的题目
    """
    service = MistakeService(db)

    try:
        result = await service.get_review_exercise(
            user_id=user_id,
            focus_concept=focus_concept,
            focus_error_type=focus_error_type,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取复习题目失败: {str(e)}",
        ) from e
