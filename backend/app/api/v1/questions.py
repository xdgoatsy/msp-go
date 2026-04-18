"""题目管理 API 端点"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSession, TeacherUserId
from app.api.v1.schemas.questions import (
    AIParseQuestionItem,
    AIParseRequest,
    AIParseResponse,
    BatchImportRequest,
    BatchOperationRequest,
    BatchOperationResponse,
    QuestionCreateRequest,
    QuestionGroupsResponse,
    QuestionListResponse,
    QuestionResponse,
    QuestionStatsResponse,
    QuestionUpdateRequest,
)
from app.infrastructure.database.models import (
    ContentAttemptModel,
    ContentModel,
    ContentStatus,
    ContentType,
    KnowledgeNodeModel,
    UserModel,
)
from app.services.content_service import ContentService

router = APIRouter(tags=["questions"])


async def _match_concept_ids_by_group(db: AsyncSession, group_name: str) -> list[str]:
    """
    根据分组名关键词匹配知识点 ID 列表。

    匹配策略：将分组名拆分为关键词，在 knowledge_nodes 的 name、chapter、tags 中模糊搜索。
    例如 "极限与连续" → 搜索 "极限"、"连续"，返回匹配到的知识点 ID。
    """
    if not group_name or not group_name.strip():
        return []

    # 拆分关键词：按常见分隔符拆分
    import re
    keywords = re.split(r'[与和、,，/\s]+', group_name.strip())
    keywords = [kw.strip() for kw in keywords if len(kw.strip()) >= 2]

    if not keywords:
        # 分组名本身作为整体关键词
        keywords = [group_name.strip()]

    # 构建 OR 条件：任一关键词匹配 name 或 chapter
    conditions = []
    for kw in keywords:
        pattern = f"%{kw}%"
        conditions.append(KnowledgeNodeModel.name.ilike(pattern))
        conditions.append(KnowledgeNodeModel.chapter.ilike(pattern))

    stmt = (
        select(KnowledgeNodeModel.id)
        .where(or_(*conditions))
        .distinct()
    )
    result = await db.execute(stmt)
    return [row[0] for row in result.all()]


async def _get_content_stats(db: AsyncSession, content_id: str) -> tuple[int, float]:
    """查询单个题目的使用次数和正确率"""
    stmt = select(
        func.count(ContentAttemptModel.id).label("usage_count"),
        func.coalesce(
            func.sum(case((ContentAttemptModel.is_correct.is_(True), 1), else_=0))
            / func.nullif(func.count(ContentAttemptModel.id), 0),
            0.0,
        ).label("correct_rate"),
    ).where(ContentAttemptModel.content_id == content_id)
    result = await db.execute(stmt)
    row = result.one()
    return int(row.usage_count), float(row.correct_rate)


async def _get_user(db: AsyncSession, user_id: str) -> UserModel:
    """获取用户对象"""
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    return user


@router.post("", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
async def create_question(
    data: QuestionCreateRequest,
    teacher_id: TeacherUserId,
    db: DbSession,
) -> QuestionResponse:
    """创建题目（教师权限）"""
    # 获取教师用户对象
    teacher = await _get_user(db, teacher_id)

    service = ContentService(db)

    # 构建 meta 字段
    meta = {
        "answer": data.answer,
        "answer_type": data.answer_type,
        "type": data.type,
        "hints": data.hints,
        "solution_steps": data.solution_steps,
        "estimated_time_seconds": data.estimated_time_seconds,
    }
    if data.options:
        meta["options"] = data.options

    # 根据分组名自动匹配知识点（如果前端未手动指定）
    concept_ids = data.concept_ids
    if not concept_ids and data.title:
        concept_ids = await _match_concept_ids_by_group(db, data.title)

    # 创建题目
    content = await service.create_content(
        type=ContentType.PROBLEM,
        title=data.title,
        body=data.body,
        actor=teacher,
        difficulty=data.difficulty,
        concept_ids=concept_ids,
        tags=data.tags,
        meta=meta,
    )

    return QuestionResponse(
        id=content.id,
        title=content.title,
        body=content.body,
        type=content.meta.get("type", "short_answer"),
        difficulty=content.difficulty,
        concept_ids=content.concept_ids or [],
        tags=content.tags or [],
        status=content.status.value,
        meta=content.meta,
        created_at=content.created_at,
        updated_at=content.updated_at,
        usage_count=0,  # 新创建的题目，使用次数为 0
        correct_rate=0.0,  # 新创建的题目，正确率为 0
    )


@router.get("/groups", response_model=QuestionGroupsResponse)
async def list_question_groups(
    teacher_id: TeacherUserId,
    db: DbSession,
) -> QuestionGroupsResponse:
    """获取题目分组列表（教师权限，从已有题目的 title 字段去重获取）"""
    stmt = (
        select(func.distinct(ContentModel.title))
        .where(
            ContentModel.owner_teacher_id == teacher_id,
            ContentModel.deleted_at.is_(None),
            ContentModel.type == ContentType.PROBLEM,
            ContentModel.title != "",
        )
        .order_by(ContentModel.title)
    )
    result = await db.execute(stmt)
    groups = [row[0] for row in result.all()]
    return QuestionGroupsResponse(groups=groups)


@router.get("/stats", response_model=QuestionStatsResponse)
async def get_question_stats(
    teacher_id: TeacherUserId,
    db: DbSession,
) -> QuestionStatsResponse:
    """获取题目统计数据（教师权限）"""
    from app.infrastructure.repositories.content_repository import ContentRepository

    repo = ContentRepository(db)
    stats = await repo.get_stats_by_owner(teacher_id, type=ContentType.PROBLEM)

    # 按难度分类
    by_difficulty = {
        "easy": 0,
        "medium": 0,
        "hard": 0,
    }

    # 按题型分类
    by_type = {
        "short_answer": 0,
        "multiple_choice": 0,
        "proof": 0,
    }

    # 按状态分类
    by_status = {
        "draft": stats["draft_count"],
        "published": stats["published_count"],
        "archived": stats["archived_count"],
    }

    return QuestionStatsResponse(
        total=stats["total_count"],
        by_difficulty=by_difficulty,
        by_type=by_type,
        by_status=by_status,
    )


@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question(
    question_id: str,
    teacher_id: TeacherUserId,
    db: DbSession,
) -> QuestionResponse:
    """获取题目详情（教师权限，只能查看自己的题目）"""
    # 获取教师用户对象
    teacher = await _get_user(db, teacher_id)

    service = ContentService(db)

    content = await service.get_content(question_id, actor=teacher)
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="题目不存在或无权访问",
        )

    # 检查是否为题目类型
    if content.type != ContentType.PROBLEM:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该内容不是题目类型",
        )

    # 权限检查：只能查看自己的题目
    if content.owner_teacher_id != teacher_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此题目",
        )

    # 统计使用次数和正确率
    usage_count, correct_rate = await _get_content_stats(db, content.id)

    return QuestionResponse(
        id=content.id,
        title=content.title,
        body=content.body,
        type=content.meta.get("type", "short_answer"),
        difficulty=content.difficulty,
        concept_ids=content.concept_ids or [],
        tags=content.tags or [],
        status=content.status.value,
        meta=content.meta,
        created_at=content.created_at,
        updated_at=content.updated_at,
        usage_count=usage_count,
        correct_rate=correct_rate,
    )


@router.put("/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: str,
    data: QuestionUpdateRequest,
    teacher_id: TeacherUserId,
    db: DbSession,
) -> QuestionResponse:
    """更新题目（教师权限，只能更新自己的题目）"""
    import logging
    logger = logging.getLogger(__name__)

    try:
        # 获取教师用户对象
        teacher = await _get_user(db, teacher_id)

        service = ContentService(db)

        # 获取题目（权限检查）
        content = await service.get_content(question_id, actor=teacher)
        if content is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="题目不存在或无权访问",
            )

        # 权限检查
        if content.owner_teacher_id != teacher_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权修改此题目",
            )

        if content.type != ContentType.PROBLEM:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该内容不是题目类型",
            )

        # 构建更新数据
        updates = {}
        if data.title is not None:
            updates["title"] = data.title
        if data.body is not None:
            updates["body"] = data.body
        if data.difficulty is not None:
            updates["difficulty"] = data.difficulty
        if data.concept_ids is not None:
            updates["concept_ids"] = data.concept_ids
        if data.tags is not None:
            updates["tags"] = data.tags

        # 分组名变更时，自动重新匹配知识点（仅当前端未手动指定 concept_ids 时）
        if data.title is not None and data.concept_ids is None:
            matched_ids = await _match_concept_ids_by_group(db, data.title)
            if matched_ids:
                updates["concept_ids"] = matched_ids
        if data.status is not None:
            try:
                updates["status"] = ContentStatus(data.status)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"无效的状态值: {data.status}",
                ) from None

        # 更新 meta 字段
        meta = content.meta.copy() if content.meta else {}
        if data.answer is not None:
            meta["answer"] = data.answer
        if data.answer_type is not None:
            meta["answer_type"] = data.answer_type
        if data.type is not None:
            meta["type"] = data.type
        if data.hints is not None:
            meta["hints"] = data.hints
        if data.solution_steps is not None:
            meta["solution_steps"] = data.solution_steps
        if data.options is not None:
            meta["options"] = data.options
        if data.estimated_time_seconds is not None:
            meta["estimated_time_seconds"] = data.estimated_time_seconds

        updates["meta"] = meta

        logger.info(f"Updating question {question_id} with updates: {list(updates.keys())}")

        # 执行更新
        updated_content = await service.update_content(question_id, teacher, updates)
        if updated_content is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="更新失败",
            )

        # 统计使用次数和正确率
        usage_count, correct_rate = await _get_content_stats(db, updated_content.id)

        return QuestionResponse(
            id=updated_content.id,
            title=updated_content.title,
            body=updated_content.body,
            type=updated_content.meta.get("type", "short_answer"),
            difficulty=updated_content.difficulty,
            concept_ids=updated_content.concept_ids or [],
            tags=updated_content.tags or [],
            status=updated_content.status.value,
            meta=updated_content.meta,
            created_at=updated_content.created_at,
            updated_at=updated_content.updated_at,
            usage_count=usage_count,
            correct_rate=correct_rate,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating question {question_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新题目时发生错误: {str(e)}",
        ) from e


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: str,
    teacher_id: TeacherUserId,
    db: DbSession,
) -> None:
    """删除题目（软删除，教师权限，只能删除自己的题目）"""
    # ���取教师用户对象
    teacher = await _get_user(db, teacher_id)

    service = ContentService(db)

    # 获取题目（权限检查）
    content = await service.get_content(question_id, actor=teacher)
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="题目不存在或无权访问",
        )

    if content.type != ContentType.PROBLEM:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该内容不是题目类型",
        )

    # 权限检查
    if content.owner_teacher_id != teacher_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权删除此题目",
        )

    # 软删除
    success = await service.delete_content(question_id, teacher)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除失败",
        )


@router.get("", response_model=QuestionListResponse)
async def list_questions(
    teacher_id: TeacherUserId,
    db: DbSession,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    difficulty: str | None = None,
    type: str | None = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    tags: list[str] | None = None,
    group: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> QuestionListResponse:
    """
    获取题目列表（教师权限，只能查看自己的题目）

    Args:
        page: 页码（从 1 开始）
        page_size: 每页数量
        search: 搜索关键词（分组名/内容）
        difficulty: 难度筛选（easy/medium/hard）
        type: 题型筛选
        status_filter: 状态筛选（draft/published/archived）
        tags: 标签筛选
        group: 分组筛选（精确匹配）
        sort_by: 排序字段（created_at/difficulty/usage_count）
        sort_order: 排序方向（asc/desc）
    """
    from app.infrastructure.repositories.content_repository import ContentRepository

    # 难度映射
    difficulty_map = {
        "easy": (0.0, 0.33),
        "medium": (0.33, 0.67),
        "hard": (0.67, 1.0),
    }
    difficulty_min, difficulty_max = None, None
    if difficulty and difficulty in difficulty_map:
        difficulty_min, difficulty_max = difficulty_map[difficulty]

    # 状态映射
    content_status = None
    if status_filter:
        try:
            content_status = ContentStatus(status_filter)
        except ValueError:
            pass

    # 计算偏移量
    skip = (page - 1) * page_size

    # 查询
    repo = ContentRepository(db)
    items, total = await repo.list_by_owner_with_stats(
        owner_id=teacher_id,
        type=ContentType.PROBLEM,
        meta_type=type,
        status=content_status,
        difficulty_min=difficulty_min,
        difficulty_max=difficulty_max,
        search=search,
        tags=tags or [],
        group=group,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=page_size,
    )

    # 构建响应
    question_responses = []
    for content, usage_count, correct_rate in items:
        question_responses.append(
            QuestionResponse(
                id=content.id,
                title=content.title,
                body=content.body,
                type=content.meta.get("type", "short_answer"),
                difficulty=content.difficulty,
                concept_ids=content.concept_ids or [],
                tags=content.tags or [],
                status=content.status.value,
                meta=content.meta,
                created_at=content.created_at,
                updated_at=content.updated_at,
                usage_count=usage_count,
                correct_rate=correct_rate,
            )
        )

    return QuestionListResponse(
        items=question_responses,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/batch/publish", response_model=BatchOperationResponse)
async def batch_publish_questions(
    data: BatchOperationRequest,
    teacher_id: TeacherUserId,
    db: DbSession,
) -> BatchOperationResponse:
    """批量发布题目（教师权限）"""
    from app.infrastructure.repositories.content_repository import ContentRepository

    repo = ContentRepository(db)

    try:
        count = await repo.batch_update_status(
            content_ids=data.question_ids,
            owner_id=teacher_id,
            status=ContentStatus.PUBLISHED,
            type=ContentType.PROBLEM,
        )
        await db.commit()

        failed = len(data.question_ids) - count
        return BatchOperationResponse(
            success=count,
            failed=failed,
            failed_ids=[],
            errors=[],
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量发布失败: {str(e)}",
        ) from e


@router.post("/batch/delete", response_model=BatchOperationResponse)
async def batch_delete_questions(
    data: BatchOperationRequest,
    teacher_id: TeacherUserId,
    db: DbSession,
) -> BatchOperationResponse:
    """批量删除题目（软删除，教师权限）"""
    from app.infrastructure.repositories.content_repository import ContentRepository

    repo = ContentRepository(db)

    try:
        count = await repo.batch_soft_delete(
            content_ids=data.question_ids,
            owner_id=teacher_id,
            type=ContentType.PROBLEM,
        )
        await db.commit()

        failed = len(data.question_ids) - count
        return BatchOperationResponse(
            success=count,
            failed=failed,
            failed_ids=[],
            errors=[],
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量删除失败: {str(e)}",
        ) from e


@router.post("/batch/duplicate", response_model=BatchOperationResponse)
async def batch_duplicate_questions(
    data: BatchOperationRequest,
    teacher_id: TeacherUserId,
    db: DbSession,
) -> BatchOperationResponse:
    """批量复制题目（教师权限）"""
    from app.infrastructure.repositories.content_repository import ContentRepository

    repo = ContentRepository(db)

    success_count = 0
    failed_ids = []
    errors = []

    try:
        for question_id in data.question_ids:
            try:
                new_content = await repo.duplicate_content(
                    content_id=question_id,
                    owner_id=teacher_id,
                    type=ContentType.PROBLEM,
                )
                if new_content:
                    success_count += 1
                else:
                    failed_ids.append(question_id)
                    errors.append(f"题目 {question_id} 不存在或无权访问")
            except Exception as e:
                failed_ids.append(question_id)
                errors.append(f"题目 {question_id} 复制失败: {str(e)}")

        await db.commit()

        return BatchOperationResponse(
            success=success_count,
            failed=len(failed_ids),
            failed_ids=failed_ids,
            errors=errors,
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量复制失败: {str(e)}",
        ) from e


# ==================== 导入/导出相关端点 ====================


@router.post("/ai-parse", response_model=AIParseResponse)
async def ai_parse_questions(
    data: AIParseRequest,
    teacher_id: TeacherUserId,
    db: DbSession,
) -> AIParseResponse:
    """
    AI 辅助识别题目结构（教师权限）

    接收原始文本数组，调用 LLM 进行结构化提取。
    限制：每次最多 10 段文本，每段最多 3000 字符。
    """
    import logging

    logger = logging.getLogger(__name__)

    # 校验每段文本长度
    for i, text in enumerate(data.raw_texts):
        if len(text) > 3000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"第 {i + 1} 段文本超过 3000 字符限制（当前 {len(text)} 字符）",
            )

    try:
        from app.services.question_ai_service import QuestionAIService

        service = QuestionAIService()
        results = await service.parse_questions(data.raw_texts)

        # 转换为响应格式
        questions = []
        for item in results:
            questions.append(
                AIParseQuestionItem(
                    title=item.get("title", ""),
                    body=item.get("body", ""),
                    type=item.get("type", "short_answer"),
                    difficulty=max(0.0, min(1.0, float(item.get("difficulty", 0.5)))),
                    answer=item.get("answer", ""),
                    answer_type=item.get("answer_type", "expression"),
                    options=item.get("options"),
                    hints=item.get("hints", []),
                    solution_steps=item.get("solution_steps", []),
                    tags=item.get("tags", []),
                )
            )

        return AIParseResponse(questions=questions)

    except Exception as e:
        logger.error(f"AI 题目识别失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI 题目识别失败: {str(e)}",
        ) from e


@router.post("/batch/import", response_model=BatchOperationResponse)
async def batch_import_questions(
    data: BatchImportRequest,
    teacher_id: TeacherUserId,
    db: DbSession,
) -> BatchOperationResponse:
    """
    批量导入题目（教师权限）

    接收前端解析好的题目数组，直接入库。
    文件解析在前端完成，此端点仅负责入库。
    最多 200 道题目/次。
    """
    teacher = await _get_user(db, teacher_id)
    service = ContentService(db)

    success_count = 0
    failed_ids: list[str] = []
    errors: list[str] = []

    try:
        for idx, q in enumerate(data.questions):
            try:
                # 构建 meta 字段
                meta = {
                    "answer": q.answer,
                    "answer_type": q.answer_type,
                    "type": q.type,
                    "hints": q.hints,
                    "solution_steps": q.solution_steps,
                    "estimated_time_seconds": q.estimated_time_seconds,
                }
                if q.options:
                    meta["options"] = q.options

                # 根据分组名自动匹配知识点
                concept_ids = q.concept_ids
                if not concept_ids and q.title:
                    concept_ids = await _match_concept_ids_by_group(db, q.title)

                await service.create_content(
                    type=ContentType.PROBLEM,
                    title=q.title,
                    body=q.body,
                    actor=teacher,
                    difficulty=q.difficulty,
                    concept_ids=concept_ids,
                    tags=q.tags,
                    meta=meta,
                )
                success_count += 1

            except Exception as e:
                failed_ids.append(f"index_{idx}")
                errors.append(f"第 {idx + 1} 道题目导入失败: {str(e)}")

        await db.commit()

        return BatchOperationResponse(
            success=success_count,
            failed=len(failed_ids),
            failed_ids=failed_ids,
            errors=errors[:20],  # 最多返回 20 条错误
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量导入失败: {str(e)}",
        ) from e
