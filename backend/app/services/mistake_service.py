"""
错题本服务

处理错题查询、统计分析、复习推荐等用例
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import (
    ContentAttemptModel,
    ContentModel,
    DiagnosisReportModel,
    StudentProfileModel,
)


class MistakeService:
    """错题本服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_mistakes(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        error_type: str | None = None,
        concept_id: str | None = None,
        difficulty_min: float = 0.0,
        difficulty_max: float = 1.0,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        mastery_status: str = "all",
        sort_by: str = "time",
        sort_order: str = "desc",
    ) -> dict[str, Any]:
        """
        获取错题列表（分页 + 筛选 + 排序）

        Args:
            user_id: 学生ID
            page: 页码
            page_size: 每页数量
            error_type: 错误类型筛选 (C/P/L/S)
            concept_id: 知识点筛选
            difficulty_min: 最小难度
            difficulty_max: 最大难度
            date_from: 开始时间
            date_to: 结束时间
            mastery_status: 掌握状态 (all/weak/improving/mastered)
            sort_by: 排序字段 (time/error_count/mastery)
            sort_order: 排序方向 (asc/desc)

        Returns:
            包含错题列表、分页信息、统计数据的字典
        """
        # 1. 构建基础查询
        query = (
            select(ContentAttemptModel, DiagnosisReportModel, ContentModel)
            .join(
                DiagnosisReportModel,
                ContentAttemptModel.id == DiagnosisReportModel.attempt_id,
            )
            .join(ContentModel, ContentAttemptModel.content_id == ContentModel.id)
            .where(
                ContentAttemptModel.student_id == user_id,
                ContentAttemptModel.is_correct == False,  # noqa: E712
                ContentAttemptModel.submitted_at.is_not(None),
            )
        )

        # 2. 应用筛选条件
        if error_type:
            query = query.where(DiagnosisReportModel.error_type == error_type)

        if concept_id:
            # PostgreSQL 数组包含查询
            query = query.where(ContentModel.concept_ids.contains([concept_id]))

        if difficulty_min > 0.0 or difficulty_max < 1.0:
            query = query.where(
                ContentModel.difficulty >= difficulty_min,
                ContentModel.difficulty <= difficulty_max,
            )

        if date_from:
            query = query.where(ContentAttemptModel.submitted_at >= date_from)

        if date_to:
            query = query.where(ContentAttemptModel.submitted_at <= date_to)

        # 3. 获取学生掌握度向量
        profile = await self._get_student_profile(user_id)
        mastery_vector = profile.mastery_vector if profile else {}

        # 4. 执行查询获取所有结果（用于掌握度筛选和排序）
        result = await self.db.execute(query)
        all_rows = result.all()

        # 5. 计算每个题目的错误次数
        error_counts = await self._get_error_counts(user_id)

        # 6. 组装数据并应用掌握度筛选
        items = []
        for row in all_rows:
            attempt, diagnosis, content = row

            # 计算该题目相关知识点的平均掌握度
            avg_mastery = self._calculate_avg_mastery(
                content.concept_ids or [], mastery_vector
            )

            # 应用掌握度筛选
            if mastery_status == "weak" and avg_mastery >= 0.4:
                continue
            elif mastery_status == "improving" and (avg_mastery < 0.4 or avg_mastery >= 0.7):
                continue
            elif mastery_status == "mastered" and avg_mastery < 0.7:
                continue

            # 获取错误次数
            error_count = error_counts.get(content.id, 1)

            items.append({
                "attempt": attempt,
                "diagnosis": diagnosis,
                "content": content,
                "avg_mastery": avg_mastery,
                "error_count": error_count,
            })

        # 7. 排序
        if sort_by == "time":
            items.sort(
                key=lambda x: x["attempt"].submitted_at or datetime.min,
                reverse=(sort_order == "desc"),
            )
        elif sort_by == "error_count":
            items.sort(
                key=lambda x: x["error_count"],
                reverse=(sort_order == "desc"),
            )
        elif sort_by == "mastery":
            items.sort(
                key=lambda x: x["avg_mastery"],
                reverse=(sort_order == "desc"),
            )

        # 8. 分页
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_items = items[start:end]

        # 9. 格式化响应
        formatted_items = []
        for item in paginated_items:
            attempt = item["attempt"]
            diagnosis = item["diagnosis"]
            content = item["content"]

            # 计算掌握度趋势
            mastery_trend = self._calculate_mastery_trend(
                content.concept_ids or [], mastery_vector
            )

            formatted_items.append({
                "id": attempt.id,
                "exercise": {
                    "id": content.id,
                    "title": content.title or "无标题",
                    "content": content.body or "",
                    "difficulty": content.difficulty,
                    "knowledge_points": content.concept_ids or [],
                },
                "attempt": {
                    "student_answer": attempt.student_answer,
                    # 题目答案存放在 contents.meta（历史 Exercise 模型已合并为 Content）
                    "correct_answer": (content.meta or {}).get("answer", ""),
                    "is_correct": attempt.is_correct,
                    "score": attempt.score,
                    "submitted_at": attempt.submitted_at.isoformat() if attempt.submitted_at else None,
                    "time_spent_seconds": attempt.time_spent_seconds,
                },
                "diagnosis": {
                    "error_type": diagnosis.error_type.value if diagnosis.error_type else None,
                    "error_subtype": diagnosis.error_subtype or "",
                    "severity": diagnosis.severity,
                    "explanation": diagnosis.explanation,
                    "suggestion": diagnosis.suggestion,
                    "related_concepts": diagnosis.related_concept_ids or [],
                },
                "mastery": {
                    "current": item["avg_mastery"],
                    "previous": item["avg_mastery"],  # 简化处理，实际应该查询历史
                    "trend": mastery_trend,
                },
                "error_count": item["error_count"],
                "last_reviewed_at": None,  # 暂不实现复习时间追踪
            })

        # 10. 计算统计信息
        statistics = {
            "total_mistakes": total,
            "weak_concepts": sum(1 for v in mastery_vector.values() if isinstance(v, (int, float)) and v < 0.4),
            "avg_mastery": sum(mastery_vector.values()) / len(mastery_vector) if mastery_vector else 0.0,
        }

        return {
            "items": formatted_items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size,
            },
            "statistics": statistics,
        }

    async def get_statistics(
        self, user_id: str, time_range: str = "month"
    ) -> dict[str, Any]:
        """
        获取错题统计分析

        Args:
            user_id: 学生ID
            time_range: 时间范围 (week/month/semester/all)

        Returns:
            统计数据字典
        """
        # 1. 确定时间范围
        start_date, end_date = self._get_time_range(time_range)

        # 2. 基础查询
        base_query = (
            select(ContentAttemptModel, DiagnosisReportModel, ContentModel)
            .join(
                DiagnosisReportModel,
                ContentAttemptModel.id == DiagnosisReportModel.attempt_id,
            )
            .join(ContentModel, ContentAttemptModel.content_id == ContentModel.id)
            .where(
                ContentAttemptModel.student_id == user_id,
                ContentAttemptModel.is_correct == False,  # noqa: E712
                ContentAttemptModel.submitted_at.is_not(None),
            )
        )

        if start_date:
            base_query = base_query.where(ContentAttemptModel.submitted_at >= start_date)
        if end_date:
            base_query = base_query.where(ContentAttemptModel.submitted_at <= end_date)

        result = await self.db.execute(base_query)
        rows = result.all()

        # 3. 错误类型分布
        error_type_dist = {}
        error_type_labels = {
            "conceptual": "概念性错误",
            "procedural": "过程性错误",
            "logical": "逻辑错误",
            "symbolic": "符号错误",
            "calculation": "计算错误",
        }

        for row in rows:
            _, diagnosis, _ = row
            if diagnosis.error_type:
                error_type_key = diagnosis.error_type.value
                error_type_dist[error_type_key] = error_type_dist.get(error_type_key, 0) + 1

        total_mistakes = len(rows)
        error_type_distribution = {}
        for key, count in error_type_dist.items():
            error_type_distribution[key] = {
                "count": count,
                "percentage": round(count / total_mistakes * 100, 1) if total_mistakes > 0 else 0,
                "label": error_type_labels.get(key, "未知错误"),
            }

        # 4. 知识点薄弱度分析
        profile = await self._get_student_profile(user_id)
        mastery_vector = profile.mastery_vector if profile else {}

        concept_mistakes = {}
        for row in rows:
            _, _, content = row
            for concept_id in content.concept_ids or []:
                concept_mistakes[concept_id] = concept_mistakes.get(concept_id, 0) + 1

        concept_weakness = []
        for concept_id, mistake_count in concept_mistakes.items():
            mastery = mastery_vector.get(concept_id, 0.5)
            concept_weakness.append({
                "concept_id": concept_id,
                "concept_name": concept_id,  # 简化处理，实际应该查询知识点名称
                "mistake_count": mistake_count,
                "mastery": mastery,
                "recent_mistakes": mistake_count,  # 简化处理
            })

        # 按错误次数排序，取前10个
        concept_weakness.sort(key=lambda x: x["mistake_count"], reverse=True)
        concept_weakness = concept_weakness[:10]

        # 5. 总览统计
        total_exercises_query = select(func.count(ContentAttemptModel.id)).where(
            ContentAttemptModel.student_id == user_id,
            ContentAttemptModel.submitted_at.is_not(None),
        )
        if start_date:
            total_exercises_query = total_exercises_query.where(
                ContentAttemptModel.submitted_at >= start_date
            )
        if end_date:
            total_exercises_query = total_exercises_query.where(
                ContentAttemptModel.submitted_at <= end_date
            )

        total_exercises_result = await self.db.execute(total_exercises_query)
        total_exercises = total_exercises_result.scalar() or 0

        overview = {
            "total_mistakes": total_mistakes,
            "total_exercises": total_exercises,
            "mistake_rate": round(total_mistakes / total_exercises * 100, 1) if total_exercises > 0 else 0,
            "avg_mastery": round(sum(mastery_vector.values()) / len(mastery_vector), 2) if mastery_vector else 0.0,
        }

        return {
            "overview": overview,
            "error_type_distribution": error_type_distribution,
            "concept_weakness": concept_weakness,
        }

    async def get_mistake_detail(
        self, user_id: str, attempt_id: str
    ) -> dict[str, Any]:
        """
        获取错题详情

        Args:
            user_id: 学生ID
            attempt_id: 作答记录ID

        Returns:
            错题详情字典
        """
        # 1. 查询作答记录
        query = (
            select(ContentAttemptModel, DiagnosisReportModel, ContentModel)
            .join(
                DiagnosisReportModel,
                ContentAttemptModel.id == DiagnosisReportModel.attempt_id,
            )
            .join(ContentModel, ContentAttemptModel.content_id == ContentModel.id)
            .where(
                ContentAttemptModel.id == attempt_id,
                ContentAttemptModel.student_id == user_id,
            )
        )

        result = await self.db.execute(query)
        row = result.one_or_none()

        if not row:
            raise ValueError("错题记录不存在")

        attempt, diagnosis, content = row
        meta = content.meta or {}

        # 2. 查询该题目的历史作答记录
        history_query = (
            select(ContentAttemptModel)
            .where(
                ContentAttemptModel.content_id == content.id,
                ContentAttemptModel.student_id == user_id,
                ContentAttemptModel.submitted_at.is_not(None),
            )
            .order_by(ContentAttemptModel.submitted_at.desc())
        )

        history_result = await self.db.execute(history_query)
        history_attempts = history_result.scalars().all()

        history = []
        for hist_attempt in history_attempts:
            if hist_attempt.id != attempt_id:  # 排除当前记录
                history.append({
                    "attempt_id": hist_attempt.id,
                    "submitted_at": hist_attempt.submitted_at.isoformat() if hist_attempt.submitted_at else None,
                    "is_correct": hist_attempt.is_correct,
                    "score": hist_attempt.score,
                })

        # 3. 格式化响应
        return {
            "attempt_id": attempt.id,
            "exercise": {
                "id": content.id,
                "title": content.title or "无标题",
                "content": content.body or "",
                "difficulty": content.difficulty,
                "knowledge_points": content.concept_ids or [],
                "hints": meta.get("hints", []) or [],
            },
            "attempt": {
                "student_answer": attempt.student_answer,
                "student_steps": attempt.student_steps or [],
                "correct_answer": meta.get("answer", ""),
                "submitted_at": attempt.submitted_at.isoformat() if attempt.submitted_at else None,
                "time_spent_seconds": attempt.time_spent_seconds,
            },
            "diagnosis": {
                "error_type": diagnosis.error_type.value if diagnosis.error_type else None,
                "error_step_index": diagnosis.error_step_index,
                "explanation": diagnosis.explanation,
                "suggestion": diagnosis.suggestion,
                "related_concepts": diagnosis.related_concept_ids or [],
            },
            "solution": {
                "answer": meta.get("answer", ""),
                "steps": meta.get("solution_steps", []) or [],
                "source": "cached" if meta.get("solution_steps") else "unavailable",
            },
            "history": history,
        }

    async def mark_as_mastered(
        self, user_id: str, attempt_id: str
    ) -> dict[str, Any]:
        """
        标记错题已掌握

        Args:
            user_id: 学生ID
            attempt_id: 作答记录ID

        Returns:
            更新结果
        """
        # 1. 验证 attempt 属于该用户
        query = (
            select(ContentAttemptModel, ContentModel)
            .join(ContentModel, ContentAttemptModel.content_id == ContentModel.id)
            .where(
                ContentAttemptModel.id == attempt_id,
                ContentAttemptModel.student_id == user_id,
            )
        )

        result = await self.db.execute(query)
        row = result.one_or_none()

        if not row:
            raise ValueError("错题记录不存在")

        attempt, content = row

        # 2. 更新 mastery_vector（提升相关知识点掌握度到 0.8+）
        profile = await self._get_student_profile(user_id)
        if profile:
            mastery_vector = profile.mastery_vector or {}
            mastery_update = {}

            for concept_id in content.concept_ids or []:
                # 提升掌握度到至少 0.8
                current_mastery = mastery_vector.get(concept_id, 0.5)
                new_mastery = max(0.8, current_mastery + 0.2)
                mastery_vector[concept_id] = min(1.0, new_mastery)
                mastery_update[concept_id] = mastery_vector[concept_id]

            profile.mastery_vector = mastery_vector
            await self.db.commit()

            return {
                "success": True,
                "mastered_at": datetime.now().isoformat(),
                "mastery_update": mastery_update,
            }

        return {
            "success": False,
            "message": "学生画像不存在",
        }

    async def delete_mistake(self, user_id: str, attempt_id: str) -> None:
        """
        删除错题记录（硬删除）

        Args:
            user_id: 学生ID
            attempt_id: 作答记录ID
        """
        # 1. 验证 attempt 属于该用户
        query = select(ContentAttemptModel).where(
            ContentAttemptModel.id == attempt_id,
            ContentAttemptModel.student_id == user_id,
        )

        result = await self.db.execute(query)
        attempt = result.scalar_one_or_none()

        if not attempt:
            raise ValueError("错题记录不存在")

        # 2. 删除作答记录（诊断报告会通过外键级联自动删除）
        await self.db.delete(attempt)
        await self.db.commit()

    async def get_review_exercise(
        self,
        user_id: str,
        focus_concept: str | None = None,
        focus_error_type: str | None = None,
    ) -> dict[str, Any]:
        """
        获取复习题目（智能推荐）

        Args:
            user_id: 学生ID
            focus_concept: 聚焦知识点
            focus_error_type: 聚焦错误类型

        Returns:
            复习题目信息
        """
        # 1. 获取学生掌握度向量
        profile = await self._get_student_profile(user_id)
        mastery_vector = profile.mastery_vector if profile else {}

        # 2. 查询错题记录
        query = (
            select(ContentAttemptModel, DiagnosisReportModel, ContentModel)
            .join(
                DiagnosisReportModel,
                ContentAttemptModel.id == DiagnosisReportModel.attempt_id,
            )
            .join(ContentModel, ContentAttemptModel.content_id == ContentModel.id)
            .where(
                ContentAttemptModel.student_id == user_id,
                ContentAttemptModel.is_correct == False,  # noqa: E712
                ContentAttemptModel.submitted_at.is_not(None),
            )
        )

        if focus_error_type:
            query = query.where(DiagnosisReportModel.error_type == focus_error_type)

        if focus_concept:
            query = query.where(ContentModel.concept_ids.contains([focus_concept]))

        result = await self.db.execute(query)
        rows = result.all()

        # 3. 计算每个题目的优先级（掌握度最低 + 错误次数最多）
        error_counts = await self._get_error_counts(user_id)

        candidates = []
        for row in rows:
            attempt, diagnosis, content = row

            # 计算平均掌握度
            avg_mastery = self._calculate_avg_mastery(
                content.concept_ids or [], mastery_vector
            )

            # 筛选条件：掌握度 < 0.5、错误次数 >= 2
            error_count = error_counts.get(content.id, 1)
            if avg_mastery < 0.5 and error_count >= 2:
                # 优先级 = (1 - 掌握度) * 错误次数
                priority = (1 - avg_mastery) * error_count
                candidates.append({
                    "content": content,
                    "attempt": attempt,
                    "diagnosis": diagnosis,
                    "avg_mastery": avg_mastery,
                    "error_count": error_count,
                    "priority": priority,
                })

        if not candidates:
            raise ValueError("没有可复习的错题")

        # 4. 按优先级排序，选择第一个
        candidates.sort(key=lambda x: x["priority"], reverse=True)
        selected = candidates[0]

        content = selected["content"]
        attempt = selected["attempt"]
        diagnosis = selected["diagnosis"]
        meta = content.meta or {}

        return {
            "exercise": {
                "id": content.id,
                "title": content.title or "无标题",
                "content": content.body or "",
                "difficulty": content.difficulty,
                "type": content.type.value if content.type else "short_answer",
                "knowledge_points": content.concept_ids or [],
                "hints_available": bool(meta.get("hints")),
            },
            "context": {
                "is_review": True,
                "original_attempt_id": attempt.id,
                "previous_error_type": diagnosis.error_type.value if diagnosis.error_type else None,
                "mastery_before": selected["avg_mastery"],
                "error_count": selected["error_count"],
            },
        }

    # ========== 辅助方法 ==========

    async def _get_student_profile(self, user_id: str) -> StudentProfileModel | None:
        """获取学生画像"""
        query = select(StudentProfileModel).where(
            StudentProfileModel.student_id == user_id
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _get_error_counts(self, user_id: str) -> dict[str, int]:
        """获取每个题目的错误次数"""
        query = (
            select(
                ContentAttemptModel.content_id,
                func.count(ContentAttemptModel.id).label("error_count"),
            )
            .where(
                ContentAttemptModel.student_id == user_id,
                ContentAttemptModel.is_correct == False,  # noqa: E712
            )
            .group_by(ContentAttemptModel.content_id)
        )

        result = await self.db.execute(query)
        rows = result.all()

        return {row.content_id: row.error_count for row in rows}

    def _calculate_avg_mastery(
        self, concept_ids: list[str], mastery_vector: dict[str, float]
    ) -> float:
        """计算知识点的平均掌握度"""
        if not concept_ids:
            return 0.5

        masteries = [mastery_vector.get(cid, 0.5) for cid in concept_ids]
        return sum(masteries) / len(masteries)

    def _calculate_mastery_trend(
        self, concept_ids: list[str], mastery_vector: dict[str, float]
    ) -> str:
        """计算掌握度趋势（简化版本）"""
        avg_mastery = self._calculate_avg_mastery(concept_ids, mastery_vector)

        if avg_mastery < 0.4:
            return "declining"
        elif avg_mastery >= 0.7:
            return "improving"
        else:
            return "stable"

    def _get_time_range(self, time_range: str) -> tuple[datetime | None, datetime | None]:
        """获取时间范围"""
        now = datetime.now()

        if time_range == "week":
            start_date = now - timedelta(days=7)
            return start_date, now
        elif time_range == "month":
            start_date = now - timedelta(days=30)
            return start_date, now
        elif time_range == "semester":
            start_date = now - timedelta(days=120)
            return start_date, now
        else:  # all
            return None, None
