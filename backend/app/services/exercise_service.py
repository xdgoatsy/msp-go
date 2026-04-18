"""
练习服务

处理自适应出题、答案提交、解析生成等用例

核心流程：出题 → 答题(文本/图片) → OCR识别 → 等价性匹配 → 诊断 → 追踪
"""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import (
    ClassEnrollmentModel,
    ClassModel,
    ContentAttemptModel,
    ContentModel,
    ContentStatus,
    ContentType,
    DiagnosisReportModel,
    LearningSessionModel,
    StudentProfileModel,
)
from app.services.bkt_service import BKTService

logger = logging.getLogger(__name__)


class ExerciseService:
    """练习服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.bkt_service = BKTService(db)

    # ------------------------------------------------------------------
    # 权限检查辅助方法
    # ------------------------------------------------------------------

    async def _check_student_enrollment(self, user_id: str) -> str:
        """
        检查学生是否加入班级，并返回班级教师 ID（Redis 缓存 + 单次 JOIN 查询）
        """
        from fastapi import HTTPException, status

        # 尝试 Redis 缓存（TTL 30 分钟）
        cache_key = f"msp:enrollment:{user_id}"
        try:
            from app.infrastructure.cache.redis import get_redis_client_safe
            redis = await get_redis_client_safe()
            if redis:
                cached_teacher_id = await redis.get(cache_key)
                if cached_teacher_id:
                    return cached_teacher_id
        except Exception:
            pass

        # 缓存未命中，查询 DB（单次 JOIN）
        stmt = (
            select(ClassModel.teacher_id)
            .join(ClassEnrollmentModel, ClassEnrollmentModel.class_id == ClassModel.id)
            .where(ClassEnrollmentModel.student_id == user_id)
        )
        result = await self.db.execute(stmt)
        teacher_id = result.scalar_one_or_none()

        if teacher_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="请先加入班级后再开始练习"
            )

        # 写入 Redis 缓存
        try:
            from app.infrastructure.cache.redis import get_redis_client_safe
            redis = await get_redis_client_safe()
            if redis:
                await redis.setex(cache_key, 1800, teacher_id)  # 30 分钟
        except Exception:
            pass

        return teacher_id

    # ------------------------------------------------------------------
    # 自适应选题
    # ------------------------------------------------------------------

    async def get_next_exercise(
        self,
        user_id: str,
        concept_id: str | None = None,
        difficulty: float | None = None,
    ) -> dict | None:
        """
        获取下一道自适应练习题（防跳题版本）

        选题策略：
        1. 检查是否有未完成的题目（防止刷新跳题）
        2. 如果没有，执行自适应选题
        3. 将新题目设置为 current_content_id
        """
        # 1. 获取或创建学习会话
        session = await self._get_or_create_session(user_id)

        # 2. 检查是否有未完成的题目
        if session.current_content_id:
            # 返回当前题目（防止刷新跳题）
            exercise = await self._get_exercise_model(session.current_content_id)
            if exercise and exercise.status == ContentStatus.PUBLISHED:
                # 题目仍然有效，返回该题目
                meta = exercise.meta or {}
                return {
                    "id": exercise.id,
                    "title": exercise.title,
                    "content": exercise.body,
                    "difficulty": exercise.difficulty,
                    "type": meta.get("type", "short_answer"),
                    "knowledge_points": exercise.concept_ids or [],
                    "hints_available": bool(meta.get("hints")),
                    "estimated_time_seconds": meta.get("estimated_time_seconds", 300),
                    "options": meta.get("options"),
                }
            else:
                # 题目已被删除或下架，清空 current_content_id
                session.current_content_id = None
                await self.db.commit()

        # 3. 没有未完成题目，执行自适应选题
        # 并行加载：班级教师 ID + 学生画像（两个独立查询）
        teacher_id, profile = await asyncio.gather(
            self._check_student_enrollment(user_id),
            self._get_student_profile(user_id),
        )
        mastery = profile.mastery_vector if profile else {}

        # 确定目标知识点和难度
        target_concept = concept_id
        target_difficulty = difficulty

        if target_concept is None and mastery:
            weakest_concept: str | None = None
            weakest_mastery = 1.0
            mid_concept: str | None = None
            mid_mastery: float | None = None

            for concept, concept_mastery in mastery.items():
                if concept_mastery < 0.4 and concept_mastery < weakest_mastery:
                    weakest_concept = concept
                    weakest_mastery = concept_mastery
                elif 0.4 <= concept_mastery < 0.8 and mid_concept is None:
                    mid_concept = concept
                    mid_mastery = concept_mastery

            if weakest_concept is not None:
                target_concept = weakest_concept
                target_difficulty = target_difficulty or max(0.2, weakest_mastery)
            elif mid_concept is not None and mid_mastery is not None:
                target_concept = mid_concept
                target_difficulty = target_difficulty or (mid_mastery + 0.1)

        target_difficulty = target_difficulty or 0.5

        # 获取最近做过的题目 ID（排除）
        recent_stmt = (
            select(ContentAttemptModel.content_id)
            .where(ContentAttemptModel.student_id == user_id)
            .order_by(ContentAttemptModel.started_at.desc())
            .limit(20)
        )
        recent_result = await self.db.execute(recent_stmt)
        recent_ids = [r[0] for r in recent_result.all()]

        # 构建查询（只查询该教师的已发布题目）
        stmt = select(ContentModel).where(
            ContentModel.type == ContentType.PROBLEM,
            ContentModel.status == ContentStatus.PUBLISHED,
            ContentModel.deleted_at.is_(None),
            ContentModel.owner_teacher_id == teacher_id,  # 关键：只查询班级教师的题目
        )

        # 难度范围 ± 0.15
        stmt = stmt.where(
            ContentModel.difficulty.between(
                max(0.0, target_difficulty - 0.15),
                min(1.0, target_difficulty + 0.15),
            )
        )

        # 排除最近做过的
        if recent_ids:
            stmt = stmt.where(ContentModel.id.notin_(recent_ids))

        # 限制候选数量
        stmt = stmt.limit(20)

        result = await self.db.execute(stmt)
        candidates = result.scalars().all()

        # 如果有目标知识点，优先筛选包含该知识点的题目
        if target_concept and candidates:
            matched = [
                c for c in candidates if target_concept in (c.concept_ids or [])
            ]
            if matched:
                candidates = matched

        if not candidates:
            # 放宽条件：不限难度，但仍然只查询该教师的题目
            fallback_stmt = (
                select(ContentModel)
                .where(
                    ContentModel.type == ContentType.PROBLEM,
                    ContentModel.status == ContentStatus.PUBLISHED,
                    ContentModel.deleted_at.is_(None),
                    ContentModel.owner_teacher_id == teacher_id,  # 关键：只查询班级教师的题目
                )
                .limit(10)
            )
            if recent_ids:
                fallback_stmt = fallback_stmt.where(
                    ContentModel.id.notin_(recent_ids)
                )
            fallback_result = await self.db.execute(fallback_stmt)
            candidates = fallback_result.scalars().all()

        if not candidates:
            return None

        # 随机选一道
        exercise = random.choice(candidates)

        # 4. 设置为当前题目（防止刷新跳题）
        session.current_content_id = exercise.id
        await self.db.commit()

        meta = exercise.meta or {}

        return {
            "id": exercise.id,
            "title": exercise.title,
            "content": exercise.body,
            "difficulty": exercise.difficulty,
            "type": meta.get("type", "short_answer"),
            "knowledge_points": exercise.concept_ids or [],
            "hints_available": bool(meta.get("hints")),
            "estimated_time_seconds": meta.get("estimated_time_seconds", 300),
            "options": meta.get("options"),
        }
    def _is_safe_answer_image_url(self, image_url: str) -> bool:
        """校验答案图片 URL，只允许本地上传路径。"""
        return bool(image_url) and image_url.startswith("/uploads/")

    # ------------------------------------------------------------------
    # 答案提交 + 判题
    # ------------------------------------------------------------------

    async def submit_answer(
        self,
        user_id: str,
        exercise_id: str,
        answer_text: str | None = None,
        answer_image_url: str | None = None,
        answer_steps: list[str] | None = None,
        time_spent_seconds: int = 0,
    ) -> dict:
        """
        提交答案，执行完整判题流程

        流程：
        1. 获取题目和标准答案
        2. 处理学生答案（文本 or 图片OCR）
        3. 等价性匹配
        4. 记录作答
        5. 错误诊断（答错时）
        6. 学习追踪
        7. 返回反馈
        """
        from app.agents.core.llm_client import get_agent_llm_client
        from app.agents.core.math_equivalence import check_equivalence
        from app.agents.roles.diagnostician import DiagnosticianAgent

        # 1. 获取题目
        exercise = await self._get_exercise_model(exercise_id)
        if exercise is None or exercise.status != ContentStatus.PUBLISHED:
            return {"error": "题目不存在", "is_correct": False}

        # 权限检查：只允许访问本班教师的题目
        teacher_id = await self._check_student_enrollment(user_id)
        if exercise.owner_teacher_id != teacher_id:
            return {"error": "题目不存在或无权访问", "is_correct": False}

        meta = exercise.meta or {}
        correct_answer = meta.get("answer", "")

        if not correct_answer:
            return {"error": "题目缺少标准答案", "is_correct": False}

        # 2. 处理学生答案
        llm_client = get_agent_llm_client("diagnostician")

        student_latex = ""
        if answer_image_url:
            if not self._is_safe_answer_image_url(answer_image_url):
                return {"error": "图片地址不安全或不受支持", "is_correct": False}

            # 图片答案 → OCR 识别
            diagnostician = DiagnosticianAgent(llm_client=llm_client)
            student_latex = await diagnostician.ocr_recognize(answer_image_url)
        elif answer_text:
            student_latex = answer_text.strip()

        if not student_latex:
            return {"error": "未提供有效答案", "is_correct": False}

        # 3. 等价性匹配
        eq_result = await check_equivalence(
            student_answer=student_latex,
            correct_answer=correct_answer,
            answer_type=meta.get("answer_type", "auto"),
            llm_client=llm_client,
        )

        is_correct = eq_result.is_equivalent
        score = 1.0 if is_correct else 0.0

        # 4. 记录作答
        attempt = ContentAttemptModel(
            id=str(uuid4()),
            content_id=exercise_id,
            student_id=user_id,
            student_answer=student_latex,
            student_steps=answer_steps or [],
            is_correct=is_correct,
            score=score,
            started_at=datetime.now(),
            submitted_at=datetime.now(),
            time_spent_seconds=time_spent_seconds,
        )
        self.db.add(attempt)

        # 将题目 ID 添加到已做列表，并清空当前题目（允许获取下一题）
        session = await self._get_or_create_session(user_id)
        if exercise_id not in session.contents_attempted:
            session.contents_attempted.append(exercise_id)

        # 清空当前题目（允许获取下一题）
        session.current_content_id = None
        # 5. 错误诊断（答错时，带超时保护）
        diagnosis_detail = None
        if not is_correct:
            try:
                diagnostician = DiagnosticianAgent(llm_client=llm_client)
                # 诊断超时保护：最多等待 8 秒，超时则跳过诊断
                diag_result = await asyncio.wait_for(
                    diagnostician.diagnose(
                        problem=exercise.body,
                        student_answer=student_latex,
                        student_steps=answer_steps,
                    ),
                    timeout=8.0,
                )

                if diag_result:
                    report = DiagnosisReportModel(
                        id=str(uuid4()),
                        attempt_id=attempt.id,
                        error_step_index=diag_result.error_step_index,
                        error_type=diag_result.error_type,
                        error_subtype=diag_result.error_subtype,
                        severity=diag_result.severity or "medium",
                        related_concept_ids=diag_result.related_concepts,
                        related_misconception_ids=diag_result.related_misconceptions,
                        explanation=diag_result.explanation or "答案不正确",
                        suggestion=diag_result.suggestion or "请重新检查解题过程",
                        recommended_resources=[],
                        created_at=datetime.now(),
                    )
                    self.db.add(report)

                    diagnosis_detail = {
                        "error_type": (
                            diag_result.error_type.value
                            if diag_result.error_type
                            else None
                        ),
                        "error_description": diag_result.explanation,
                        "error_step_index": diag_result.error_step_index,
                        "severity": diag_result.severity,
                        "suggestion": diag_result.suggestion,
                        "related_concepts": diag_result.related_concepts,
                    }
            except TimeoutError:
                logger.warning("诊断超时 (8s)，跳过详细诊断")
                # 超时：创建基础诊断报告
                report = DiagnosisReportModel(
                    id=str(uuid4()),
                    attempt_id=attempt.id,
                    error_step_index=None,
                    error_type=None,
                    error_subtype=None,
                    severity="medium",
                    related_concept_ids=[],
                    related_misconception_ids=[],
                    explanation="答案不正确（诊断处理中）",
                    suggestion="请重新检查解题过程",
                    recommended_resources=[],
                    created_at=datetime.now(),
                )
                self.db.add(report)
            except Exception as e:
                logger.error("诊断过程异常: %s", e)
                report = DiagnosisReportModel(
                    id=str(uuid4()),
                    attempt_id=attempt.id,
                    error_step_index=None,
                    error_type=None,
                    error_subtype=None,
                    severity="medium",
                    related_concept_ids=[],
                    related_misconception_ids=[],
                    explanation="答案不正确",
                    suggestion="请重新检查解题过程",
                    recommended_resources=[],
                    created_at=datetime.now(),
                )
                self.db.add(report)

        # 6. 学习追踪 — 更新 mastery_vector
        mastery_update = await self._update_tracking(
            user_id=user_id,
            concept_ids=exercise.concept_ids or [],
            is_correct=is_correct,
            difficulty=exercise.difficulty,
            error_type=(
                diagnosis_detail.get("error_type") if diagnosis_detail else None
            ),
        )

        # 7. 生成反馈
        if is_correct:
            feedback = f"回答正确！{eq_result.reason}"
        else:
            feedback = diagnosis_detail.get("suggestion", "") if diagnosis_detail else ""
            if not feedback:
                feedback = f"答案不正确。{eq_result.reason}"

        await self.db.commit()

        # 判断下一步建议
        if is_correct:
            next_rec = "continue"
        elif mastery_update:
            avg_mastery = sum(mastery_update.values()) / max(len(mastery_update), 1)
            next_rec = "review" if avg_mastery < 0.3 else "continue"
        else:
            next_rec = "continue"

        return {
            "is_correct": is_correct,
            "score": score,
            "student_answer_latex": student_latex,
            "correct_answer_latex": correct_answer if is_correct else "",
            "diagnosis": diagnosis_detail,
            "feedback": feedback,
            "mastery_update": mastery_update,
            "mastery_model": "bkt",
            "next_recommendation": next_rec,
            "equivalence_layer": eq_result.layer_used.value,
            "equivalence_confidence": eq_result.confidence,
        }
    # ------------------------------------------------------------------
    # 题目详情 & 解析
    # ------------------------------------------------------------------

    async def get_exercise(self, exercise_id: str, user_id: str) -> dict | None:
        """
        获取题目详情（需要权限检查）

        Args:
            exercise_id: 题目 ID
            user_id: 学生 ID

        Returns:
            题目详情字典，如果无权访问则返回 None
        """
        # 检查学生班级并获取教师 ID
        teacher_id = await self._check_student_enrollment(user_id)

        # 获取题目
        exercise = await self._get_exercise_model(exercise_id)
        if exercise is None:
            return None

        # 权限检查：只能查看本班教师的题目
        if exercise.owner_teacher_id != teacher_id:
            return None

        meta = exercise.meta or {}
        return {
            "id": exercise.id,
            "title": exercise.title,
            "content": exercise.body,
            "difficulty": exercise.difficulty,
            "type": meta.get("type", "short_answer"),
            "knowledge_points": exercise.concept_ids or [],
            "hints": meta.get("hints", []),
            "options": meta.get("options"),
        }

    async def get_solution(self, exercise_id: str, user_id: str) -> dict | None:
        """
        获取题目解析（需要权限检查）

        优先从 meta 中读取预存解析，否则调用 MathSolver 生成

        Args:
            exercise_id: 题目 ID
            user_id: 学生 ID

        Returns:
            题目解析字典，如果无权访问则返回 None
        """
        # 检查学生班级并获取教师 ID
        teacher_id = await self._check_student_enrollment(user_id)

        # 获取题目
        exercise = await self._get_exercise_model(exercise_id)
        if exercise is None:
            return None

        # 权限检查：只能查看本班教师的题目
        if exercise.owner_teacher_id != teacher_id:
            return None

        # 必须先作答过该题，才允许查看解析与答案
        attempt_exists_stmt = (
            select(ContentAttemptModel.id)
            .where(
                ContentAttemptModel.content_id == exercise_id,
                ContentAttemptModel.student_id == user_id,
            )
            .order_by(ContentAttemptModel.submitted_at.desc())
            .limit(1)
        )
        attempt_exists_result = await self.db.execute(attempt_exists_stmt)
        if attempt_exists_result.scalar_one_or_none() is None:
            return None

        meta = exercise.meta or {}

        # 优先使用预存的解析
        if meta.get("solution_steps"):
            return {
                "exercise_id": exercise_id,
                "answer": meta.get("answer", ""),
                "steps": meta["solution_steps"],
                "source": "cached",
            }

        # 调用 MathSolver 生成
        try:
            from app.agents.core.llm_client import get_agent_llm_client
            from app.agents.roles.math_solver import SymPySolver

            llm_client = get_agent_llm_client("math_solver")
            solver = SymPySolver(llm_client)
            result = await solver.solve(exercise.body)

            if result.success and result.answer:
                steps = await solver.generate_steps(exercise.body, result.answer)
                return {
                    "exercise_id": exercise_id,
                    "answer": result.answer,
                    "steps": steps,
                    "source": "generated",
                }
        except Exception as e:
            logger.error("生成解析失败: %s", e)

        return {
            "exercise_id": exercise_id,
            "answer": meta.get("answer", ""),
            "steps": [],
            "source": "unavailable",
        }

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    async def _get_or_create_session(
        self, user_id: str
    ) -> LearningSessionModel:
        """获取或创建学习会话"""
        result = await self.db.execute(
            select(LearningSessionModel)
            .where(LearningSessionModel.student_id == user_id)
            .order_by(LearningSessionModel.started_at.desc())
            .limit(1)
        )
        session = result.scalar_one_or_none()

        if not session:
            session = LearningSessionModel(
                id=str(uuid4()),
                student_id=user_id,
                is_active=True,
                current_topic=None,
                current_content_id=None,
                contents_attempted=[],
                concepts_discussed=[],
            )
            self.db.add(session)
            await self.db.commit()
            await self.db.refresh(session)

        return session

    async def _get_student_profile(
        self, user_id: str
    ) -> StudentProfileModel | None:
        """获取学生画像"""
        stmt = select(StudentProfileModel).where(
            StudentProfileModel.student_id == user_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_exercise_model(
        self, exercise_id: str
    ) -> ContentModel | None:
        """获取题目 ORM 对象（L1 内存缓存 + DB）"""
        from app.infrastructure.cache.memory import exercise_cache

        cache_key = f"exercise:{exercise_id}"
        cached = exercise_cache.get(cache_key)
        if cached is not None:
            return cached

        stmt = select(ContentModel).where(
            ContentModel.id == exercise_id,
            ContentModel.type == ContentType.PROBLEM,
            ContentModel.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        if model is not None:
            exercise_cache.set(cache_key, model)
        return model
    async def _update_tracking(
        self,
        user_id: str,
        concept_ids: list[str],
        is_correct: bool,
        difficulty: float,
        error_type: str | None = None,
    ) -> dict[str, float] | None:
        """
        更新学习追踪数据（BKT 实时更新）

        低算力场景下使用 BKT 替代 DKT，写回 student_profiles.mastery_vector
        作为兼容与查询缓存。
        """
        profile = await self._get_student_profile(user_id)
        if profile is None:
            return None

        bkt_result = await self.bkt_service.update_after_attempt(
            student_id=user_id,
            concept_ids=concept_ids,
            is_correct=is_correct,
            difficulty=difficulty,
            preferred_difficulty=profile.preferred_difficulty,
            learning_pace=profile.learning_pace,
            error_type=error_type,
            fallback_mastery=dict(profile.mastery_vector or {}),
        )

        _raw = bkt_result.get("mastery_update", {})
        mastery_update: dict[str, float] = _raw if isinstance(_raw, dict) else {}
        mastery = dict(profile.mastery_vector or {})
        mastery.update(
            {
                concept_id: float(value)
                for concept_id, value in mastery_update.items()
            }
        )
        profile.mastery_vector = mastery

        # 更新 error_tendency
        if error_type and not is_correct:
            tendency = dict(profile.error_tendency or {})
            tendency[error_type] = tendency.get(error_type, 0) + 1
            profile.error_tendency = tendency

        # 更新统计
        profile.total_exercises = (profile.total_exercises or 0) + 1
        if is_correct:
            profile.correct_count = (profile.correct_count or 0) + 1

        return {
            concept_id: float(value)
            for concept_id, value in mastery_update.items()
        }
