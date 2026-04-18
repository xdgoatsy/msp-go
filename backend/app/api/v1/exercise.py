"""
练习相关接口

处理自适应练习题的获取和提交
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import DbSession, StudentUserId
from app.services.exercise_service import ExerciseService

router = APIRouter()


# ========== 请求/响应模型 ==========


class SubmitAnswerRequest(BaseModel):
    """答案提交请求"""

    exercise_id: str
    answer_text: str | None = None
    answer_image_url: str | None = None
    answer_steps: list[str] | None = None
    time_spent_seconds: int = 0


class DiagnosisDetail(BaseModel):
    """诊断详情"""

    error_type: str | None = None
    error_description: str = ""
    error_step_index: int | None = None
    severity: str = "medium"
    suggestion: str = ""
    related_concepts: list[str] = []


class SubmitAnswerResponse(BaseModel):
    """答案提交响应"""

    is_correct: bool
    score: float = 0.0
    student_answer_latex: str = ""
    correct_answer_latex: str = ""
    diagnosis: DiagnosisDetail | None = None
    feedback: str = ""
    mastery_update: dict[str, float] | None = None
    mastery_model: str = "bkt"
    next_recommendation: str = "continue"


class ExerciseResponse(BaseModel):
    """题目响应"""

    id: str
    title: str
    content: str
    difficulty: float
    type: str = "short_answer"
    knowledge_points: list[str] = []
    hints_available: bool = False
    estimated_time_seconds: int = 300
    options: list[str] | None = None


class ExerciseDetailResponse(BaseModel):
    """题目详情响应"""

    id: str
    title: str
    content: str
    difficulty: float
    type: str = "short_answer"
    knowledge_points: list[str] = []
    hints: list[str] = []
    options: list[str] | None = None


class SolutionResponse(BaseModel):
    """题目解析响应"""

    exercise_id: str
    answer: str = ""
    steps: list[str] = []
    source: str = "cached"


# ========== API 端点 ==========


@router.get("/next", response_model=ExerciseResponse | None)
async def get_next_exercise(
    db: DbSession,
    user_id: StudentUserId,
    concept_id: str | None = Query(None, description="指定知识点"),
    difficulty: float | None = Query(None, ge=0, le=1, description="指定难度"),
) -> ExerciseResponse | None:
    """获取下一道自适应练习题"""
    service = ExerciseService(db)
    result = await service.get_next_exercise(
        user_id=user_id,
        concept_id=concept_id,
        difficulty=difficulty,
    )

    if result is None:
        return None

    return ExerciseResponse(**result)


@router.post("/submit", response_model=SubmitAnswerResponse)
async def submit_answer(
    request: SubmitAnswerRequest,
    db: DbSession,
    user_id: StudentUserId,
) -> SubmitAnswerResponse:
    """提交答案，触发判题和诊断"""
    if not request.answer_text and not request.answer_image_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请提供文本答案或图片答案",
        )

    service = ExerciseService(db)
    result = await service.submit_answer(
        user_id=user_id,
        exercise_id=request.exercise_id,
        answer_text=request.answer_text,
        answer_image_url=request.answer_image_url,
        answer_steps=request.answer_steps,
        time_spent_seconds=request.time_spent_seconds,
    )

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="提交失败，请检查输入后重试",
        )

    allowed_fields = SubmitAnswerResponse.model_fields
    response_data = {k: v for k, v in result.items() if k in allowed_fields}
    return SubmitAnswerResponse(**response_data)


@router.get("/{exercise_id}", response_model=ExerciseDetailResponse)
async def get_exercise(
    exercise_id: str,
    db: DbSession,
    user_id: StudentUserId,
) -> ExerciseDetailResponse:
    """获取指定题目详情（需要学生加入班级）"""
    service = ExerciseService(db)
    result = await service.get_exercise(exercise_id, user_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="题目不存在或无权访问",
        )

    return ExerciseDetailResponse(**result)


@router.get("/{exercise_id}/solution", response_model=SolutionResponse)
async def get_solution(
    exercise_id: str,
    db: DbSession,
    user_id: StudentUserId,
) -> SolutionResponse:
    """获取题目解析（需要学生加入班级）"""
    service = ExerciseService(db)
    result = await service.get_solution(exercise_id, user_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="题目不存在或无权访问",
        )

    return SolutionResponse(**result)
