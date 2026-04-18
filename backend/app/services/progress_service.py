"""
学习进度服务

处理学习进度查询、路径规划等用例
"""

from __future__ import annotations

import heapq
import logging
from datetime import date, datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.exercise import ErrorType
from app.domain.models.knowledge_node import NodeType, RelationType
from app.infrastructure.database.models import (
    ClassEnrollmentModel,
    ContentAttemptModel,
    DiagnosisReportModel,
    StudentProfileModel,
)
from app.infrastructure.repositories.knowledge_repository import KnowledgeRepository
from app.services.bkt_service import BKTService

# 连续学习天数向前查找的最大天数（可配置）
STREAK_LOOKBACK_DAYS = 365

logger = logging.getLogger(__name__)


class ProgressService:
    """学习进度服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.knowledge_repo = KnowledgeRepository(db)
        self.bkt_service = BKTService(db)

    async def _safe_get_mastery_map(
        self,
        user_id: str,
        fallback: dict[str, float] | None = None,
        concept_ids: list[str] | None = None,
    ) -> dict[str, float]:
        """安全获取 BKT 掌握度映射，查询失败时回退到 profile 数据。"""
        try:
            return await self.bkt_service.get_mastery_map(
                student_id=user_id,
                concept_ids=concept_ids,
                fallback_mastery=fallback,
            )
        except Exception as e:
            logger.warning("BKT 掌握度查询失败，回退到 profile 数据: %s", e)
            return dict(fallback or {})

    async def _safe_get_confidence_map(
        self,
        user_id: str,
        concept_ids: list[str] | None = None,
    ) -> dict[str, float]:
        """安全获取 BKT 置信度映射，查询失败时返回空字典。"""
        try:
            return await self.bkt_service.get_mastery_confidence_map(
                student_id=user_id,
                concept_ids=concept_ids,
            )
        except Exception as e:
            logger.warning("BKT 置信度查询失败: %s", e)
            return {}

    async def _safe_get_attempt_count_map(
        self,
        user_id: str,
        concept_ids: list[str] | None = None,
    ) -> dict[str, int]:
        """安全获取 BKT 练习次数映射，查询失败时返回空字典。"""
        try:
            return await self.bkt_service.get_attempt_count_map(
                student_id=user_id,
                concept_ids=concept_ids,
            )
        except Exception as e:
            logger.warning("BKT 练习次数查询失败: %s", e)
            return {}

    async def get_overview(self, user_id: str) -> dict:
        """
        获取学习进度概览：总做题数、正确率、累计学习时长、连续打卡天数、掌握概念数、今日统计。
        学习时长始终从 content_attempts 汇总。
        """
        stmt_profile = select(StudentProfileModel).where(
            StudentProfileModel.student_id == user_id
        )
        result_profile = await self.db.execute(stmt_profile)
        profile = result_profile.scalar_one_or_none()

        total_exercises = (profile.total_exercises or 0) if profile else 0
        correct_count = (profile.correct_count or 0) if profile else 0
        mastery_vector = await self._safe_get_mastery_map(
            user_id=user_id,
            fallback=(profile.mastery_vector if profile else {}),
        )
        mastered_concepts = sum(
            1 for v in mastery_vector.values() if isinstance(v, (int, float)) and v >= 0.8
        )

        stmt_time = (
            select(func.coalesce(func.sum(ContentAttemptModel.time_spent_seconds), 0)).where(
                ContentAttemptModel.student_id == user_id
            )
        )
        res_time = await self.db.execute(stmt_time)
        study_time_minutes = int((res_time.scalar() or 0) // 60)

        if not profile:
            stmt_attempts = (
                select(
                    func.count(ContentAttemptModel.id),
                    func.coalesce(
                        func.sum(
                            case(
                                (ContentAttemptModel.is_correct.is_(True), 1),
                                else_=0,
                            )
                        ),
                        0,
                    ),
                ).where(ContentAttemptModel.student_id == user_id)
            )
            res_attempts = await self.db.execute(stmt_attempts)
            row = res_attempts.one_or_none()
            if row:
                total_exercises = int(row[0] or 0)
                correct_count = int(row[1] or 0)

        correct_rate = (
            float(correct_count) / float(total_exercises) * 100.0
            if total_exercises > 0
            else 0.0
        )
        streak_days = await self._calculate_streak_days(user_id)

        # 今日统计
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # 今日学习时长
        stmt_today_time = (
            select(func.coalesce(func.sum(ContentAttemptModel.time_spent_seconds), 0)).where(
                ContentAttemptModel.student_id == user_id,
                ContentAttemptModel.started_at >= today_start,
            )
        )
        res_today_time = await self.db.execute(stmt_today_time)
        today_study_time_minutes = int((res_today_time.scalar() or 0) // 60)

        # 今日刷题数
        stmt_today_exercises = (
            select(func.count(ContentAttemptModel.id)).where(
                ContentAttemptModel.student_id == user_id,
                ContentAttemptModel.started_at >= today_start,
            )
        )
        res_today_exercises = await self.db.execute(stmt_today_exercises)
        today_exercises_completed = int(res_today_exercises.scalar() or 0)

        # 最近学习内容（可选）
        stmt_recent = (
            select(ContentAttemptModel.started_at)
            .where(ContentAttemptModel.student_id == user_id)
            .order_by(ContentAttemptModel.started_at.desc())
            .limit(1)
        )
        res_recent = await self.db.execute(stmt_recent)
        recent_row = res_recent.scalar_one_or_none()
        recent_content = None
        if recent_row:
            recent_content = {
                "last_accessed": recent_row.isoformat(),
            }

        return {
            "total_exercises": int(total_exercises),
            "correct_count": int(correct_count),
            "correct_rate": round(correct_rate, 1),
            "study_time_minutes": int(study_time_minutes),
            "streak_days": int(streak_days),
            "mastered_concepts": int(mastered_concepts),
            "today_stats": {
                "study_time_minutes": today_study_time_minutes,
                "exercises_completed": today_exercises_completed,
            },
            "recent_content": recent_content,
        }

    async def get_mastery_vector(self, user_id: str) -> dict:
        """
        获取知识点掌握度向量，供学习统计页使用。
        返回 { topics: [ { topic, mastery, exercises } ] }，无数据时 exercises 为 0。
        """
        stmt = select(StudentProfileModel).where(
            StudentProfileModel.student_id == user_id
        )
        result = await self.db.execute(stmt)
        profile = result.scalar_one_or_none()

        mastery_vector = await self._safe_get_mastery_map(
            user_id=user_id,
            fallback=(profile.mastery_vector if profile else {}),
        )
        confidence_map = await self._safe_get_confidence_map(
            user_id=user_id,
        )
        attempt_count_map = await self._safe_get_attempt_count_map(
            user_id=user_id,
        )

        topics = [
            {
                "topic": k,
                "mastery": float(v) if isinstance(v, (int, float)) else 0.0,
                "exercises": attempt_count_map.get(k, 0),
                "confidence": float(confidence_map.get(k, 0.0)),
            }
            for k, v in mastery_vector.items()
        ]
        return {"topics": topics, "model": "bkt"}

    async def get_learning_path(self, user_id: str, target: str | None = None) -> dict:
        """
        获取个性化学习路径

        1. 获取当前掌握度
        2. 获取知识图谱节点和前置关系
        3. 拓扑排序 + 按掌握度优先推荐薄弱节点
        """
        # 1. 获取掌握度
        stmt_p = select(StudentProfileModel).where(
            StudentProfileModel.student_id == user_id
        )
        res_p = await self.db.execute(stmt_p)
        profile = res_p.scalar_one_or_none()

        mastery_vector = await self._safe_get_mastery_map(
            user_id=user_id,
            fallback=(profile.mastery_vector if profile else {}),
        )
        confidence_map = await self._safe_get_confidence_map(
            user_id=user_id,
        )
        attempt_map = await self._safe_get_attempt_count_map(
            user_id=user_id,
        )

        # 2. 获取知识图谱
        nodes = await self.knowledge_repo.get_all_nodes()
        all_relations = await self.knowledge_repo.get_all_relations()

        valid_types = {NodeType.CONCEPT, NodeType.THEOREM, NodeType.METHOD}
        node_map = {n.id: n for n in nodes if n.node_type in valid_types}

        if not node_map:
            return {"path": [], "estimated_exercises": 0, "statistics": {}}

        # 3. 构建前置关系图
        prereq_edges: dict[str, set[str]] = {nid: set() for nid in node_map}
        dependents: dict[str, set[str]] = {nid: set() for nid in node_map}

        for rel in all_relations:
            if rel.relation_type != RelationType.HAS_PREREQUISITE:
                continue
            src, tgt = rel.source_id, rel.target_id
            if src in node_map and tgt in node_map:
                prereq_edges[src].add(tgt)
                dependents[tgt].add(src)

        # 4. 拓扑排序（Kahn 算法 + 最小堆，薄弱节点优先）
        in_degree = {nid: len(prereq_edges[nid]) for nid in node_map}
        heap: list[tuple[float, str]] = [
            (mastery_vector.get(nid, 0.5), nid)
            for nid, deg in in_degree.items()
            if deg == 0
        ]
        heapq.heapify(heap)
        sorted_ids: list[str] = []

        while heap:
            _mastery, nid = heapq.heappop(heap)
            sorted_ids.append(nid)
            for dep in dependents.get(nid, set()):
                in_degree[dep] -= 1
                if in_degree[dep] == 0:
                    heapq.heappush(heap, (mastery_vector.get(dep, 0.5), dep))

        remaining = set(node_map.keys()) - set(sorted_ids)
        sorted_ids.extend(sorted(remaining, key=lambda x: mastery_vector.get(x, 0.5)))

        # 5. 目标节点过滤
        if target and target in node_map:
            needed: set[str] = set()
            stack = [target]
            while stack:
                cur = stack.pop()
                if cur in needed:
                    continue
                needed.add(cur)
                stack.extend(prereq_edges.get(cur, set()))
            sorted_ids = [nid for nid in sorted_ids if nid in needed]

        # 6. 构建路径数据
        mastery_threshold = 0.8
        path_items = []
        for nid in sorted_ids:
            node = node_map[nid]
            m = mastery_vector.get(nid, 0.0)
            conf = confidence_map.get(nid, 0.0)
            exercises = attempt_map.get(nid, 0)

            if m >= mastery_threshold and conf >= 0.5:
                node_status = "completed"
            elif exercises > 0:
                node_status = "current"
            else:
                prereqs_met = all(
                    mastery_vector.get(pid, 0.0) >= mastery_threshold * 0.7
                    for pid in prereq_edges.get(nid, set())
                )
                node_status = "available" if prereqs_met else "locked"

            path_items.append({
                "id": nid,
                "title": node.name,
                "description": node.description or "",
                "chapter": node.chapter,
                "status": node_status,
                "mastery": round(m, 4),
                "confidence": round(conf, 4),
                "exercises": exercises,
                "difficulty": node.difficulty,
            })

        completed_count = sum(1 for p in path_items if p["status"] == "completed")
        total_count = len(path_items)
        estimated_remaining = sum(
            max(5 - p["exercises"], 0)
            for p in path_items
            if p["status"] != "completed"
        )

        return {
            "path": path_items,
            "estimated_exercises": estimated_remaining,
            "statistics": {
                "total": total_count,
                "completed": completed_count,
                "progress": round(completed_count / max(total_count, 1), 2),
            },
        }

    async def get_knowledge_graph_view(
        self,
        user_id: str,
        chapter: str | None = None,
        node_type: NodeType | None = None,
        search: str | None = None,
    ) -> dict:
        """
        获取知识图谱可视化数据

        返回适合前端渲染的节点和边数据

        Args:
            user_id: 用户 ID
            chapter: 章节筛选（可选）
            node_type: 节点类型筛选（可选）
            search: 搜索关键词（可选）

        Returns:
            包含 nodes, edges, statistics 的字典
        """
        # 1. 获取学生的掌握度向量
        stmt = select(StudentProfileModel).where(
            StudentProfileModel.student_id == user_id
        )
        result = await self.db.execute(stmt)
        profile = result.scalar_one_or_none()

        mastery_vector = await self._safe_get_mastery_map(
            user_id=user_id,
            fallback=(profile.mastery_vector if profile else {}),
        )

        # 2. 查询知识节点（支持筛选）
        nodes = await self.knowledge_repo.get_nodes_with_filters(
            chapter=chapter,
            node_type=node_type,
            search=search,
        )

        # 3. 查询所有知识关系
        all_relations = await self.knowledge_repo.get_all_relations()

        # 4. 过滤关系：只保留节点集合内的关系
        node_ids = {node.id for node in nodes}
        filtered_relations = [
            rel
            for rel in all_relations
            if rel.source_id in node_ids and rel.target_id in node_ids
        ]

        # 5. 转换为前端格式
        nodes_data = []
        for node in nodes:
            # 获取该节点的掌握度（默认 0.0）
            mastery = mastery_vector.get(node.id, 0.0)

            # 类型映���：只返回前端支持的类型
            node_type_map = {
                NodeType.CONCEPT: "concept",
                NodeType.THEOREM: "theorem",
                NodeType.METHOD: "method",
            }

            # 跳过前端不支持的类型
            if node.node_type not in node_type_map:
                continue

            nodes_data.append(
                {
                    "id": node.id,
                    "label": node.name,
                    "type": node_type_map[node.node_type],
                    "mastery": mastery,
                    "chapter": node.chapter,
                    "description": node.description,
                }
            )

        edges_data = []
        for rel in filtered_relations:
            # 关系类型映射：只返回前端支持的类型
            relation_type_map = {
                RelationType.HAS_PREREQUISITE: "prerequisite",
                RelationType.USED_IN: "used_in",
                RelationType.RELATED_TO: "related",
            }

            # 跳过前端不支持的类型
            if rel.relation_type not in relation_type_map:
                continue

            edges_data.append(
                {
                    "source": rel.source_id,
                    "target": rel.target_id,
                    "relation": relation_type_map[rel.relation_type],
                }
            )

        # 6. 计算统计信息
        total_nodes = len(nodes_data)
        mastered_nodes = sum(1 for node in nodes_data if node["mastery"] >= 0.8)
        overall_mastery = (
            sum(node["mastery"] for node in nodes_data) / total_nodes
            if total_nodes > 0
            else 0.0
        )

        return {
            "nodes": nodes_data,
            "edges": edges_data,
            "statistics": {
                "total_nodes": total_nodes,
                "mastered_nodes": mastered_nodes,
                "overall_mastery": round(overall_mastery, 2),
            },
        }

    async def get_statistics(
        self, user_id: str, range_type: str = "week"
    ) -> dict:
        """
        学习统计：当前周/当前月/当前学期/近一年。
        week=当前周(周一至今)按日, month=当前月(1号至今)按日,
        semester=当前学期按周, all=近365天按周。
        返回 range_days, interval, start_date, end_date, daily[], error_type_distribution.
        """
        today = date.today()
        interval = "day"
        range_days = 7
        start_date = today - timedelta(days=today.weekday())

        if range_type == "month":
            start_date = today.replace(day=1)
            range_days = (today - start_date).days + 1
        elif range_type == "semester":
            interval = "week"
            if today.month >= 9:
                start_date = today.replace(month=9, day=1)
            elif today.month == 1:
                start_date = date(today.year - 1, 9, 1)
            else:
                start_date = today.replace(month=2, day=1)
            range_days = (today - start_date).days + 1
        elif range_type == "all":
            interval = "week"
            range_days = 365
            start_date = today - timedelta(days=364)
        else:
            range_days = min(7, (today - start_date).days + 1)

        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(today, datetime.max.time())

        if interval == "day":
            day_col = func.date_trunc("day", ContentAttemptModel.submitted_at).label("day")
            stmt_daily = (
                select(
                    day_col,
                    func.count(ContentAttemptModel.id).label("total"),
                    func.coalesce(
                        func.sum(
                            case(
                                (ContentAttemptModel.is_correct.is_(True), 1),
                                else_=0,
                            )
                        ),
                        0,
                    ).label("correct"),
                    func.coalesce(
                        func.sum(ContentAttemptModel.time_spent_seconds), 0
                    ).label("time_spent"),
                )
                .where(
                    ContentAttemptModel.student_id == user_id,
                    ContentAttemptModel.submitted_at.is_not(None),
                    ContentAttemptModel.submitted_at >= start_dt,
                    ContentAttemptModel.submitted_at <= end_dt,
                )
                .group_by(day_col)
                .order_by(day_col)
            )
            res_daily = await self.db.execute(stmt_daily)
            rows_daily = res_daily.all()
            daily_map: dict[date, dict[str, int]] = {}
            for row in rows_daily:
                d = row.day.date() if hasattr(row.day, "date") else row.day
                daily_map[d] = {
                    "exercises": int(row.total or 0),
                    "correct_exercises": int(row.correct or 0),
                    "study_minutes": int((row.time_spent or 0) // 60),
                }
            daily: list[dict[str, str | int]] = []
            for i in range(range_days):
                d = start_date + timedelta(days=i)
                if d > today:
                    break
                rec = daily_map.get(
                    d,
                    {"exercises": 0, "correct_exercises": 0, "study_minutes": 0},
                )
                daily.append({"date": d.isoformat(), **rec})
        else:
            week_col = func.date_trunc("week", ContentAttemptModel.submitted_at).label("week")
            stmt_weekly = (
                select(
                    week_col,
                    func.count(ContentAttemptModel.id).label("total"),
                    func.coalesce(
                        func.sum(
                            case(
                                (ContentAttemptModel.is_correct.is_(True), 1),
                                else_=0,
                            )
                        ),
                        0,
                    ).label("correct"),
                    func.coalesce(
                        func.sum(ContentAttemptModel.time_spent_seconds), 0
                    ).label("time_spent"),
                )
                .where(
                    ContentAttemptModel.student_id == user_id,
                    ContentAttemptModel.submitted_at.is_not(None),
                    ContentAttemptModel.submitted_at >= start_dt,
                    ContentAttemptModel.submitted_at <= end_dt,
                )
                .group_by(week_col)
                .order_by(week_col)
            )
            res_weekly = await self.db.execute(stmt_weekly)
            week_map: dict[date, dict[str, int]] = {}
            for row in res_weekly.all():
                w = row.week.date() if hasattr(row.week, "date") else row.week
                week_map[w] = {
                    "exercises": int(row.total or 0),
                    "correct_exercises": int(row.correct or 0),
                    "study_minutes": int((row.time_spent or 0) // 60),
                }
            days_since_monday = start_date.weekday() % 7
            first_monday = start_date - timedelta(days=days_since_monday)
            daily: list[dict[str, str | int]] = []
            for i in range(53):
                week_start = first_monday + timedelta(days=i * 7)
                if week_start > today:
                    break
                if week_start < start_date:
                    continue
                rec = week_map.get(
                    week_start,
                    {"exercises": 0, "correct_exercises": 0, "study_minutes": 0},
                )
                daily.append({"date": week_start.isoformat(), **rec})

        stmt_errors = (
            select(
                DiagnosisReportModel.error_type,
                func.count(DiagnosisReportModel.id),
            )
            .join(
                ContentAttemptModel,
                DiagnosisReportModel.attempt_id == ContentAttemptModel.id,
            )
            .where(
                ContentAttemptModel.student_id == user_id,
                ContentAttemptModel.submitted_at.is_not(None),
                ContentAttemptModel.submitted_at >= start_dt,
                ContentAttemptModel.submitted_at <= end_dt,
            )
            .group_by(DiagnosisReportModel.error_type)
        )
        res_errors = await self.db.execute(stmt_errors)
        error_counts: dict[str, int] = {}
        total_errors = 0
        for err_type, cnt in res_errors.all():
            key = err_type.value if isinstance(err_type, ErrorType) else (err_type or "UNKNOWN")
            error_counts[key] = error_counts.get(key, 0) + int(cnt or 0)
            total_errors += int(cnt or 0)
        error_type_distribution: dict[str, dict[str, int | float]] = {}
        for key, cnt in error_counts.items():
            pct = (float(cnt) / float(total_errors) * 100.0) if total_errors > 0 else 0.0
            error_type_distribution[key] = {"count": cnt, "percentage": round(pct, 1)}

        return {
            "range_days": range_days,
            "interval": interval,
            "start_date": start_date.isoformat(),
            "end_date": today.isoformat(),
            "daily": daily,
            "error_type_distribution": error_type_distribution,
        }

    async def get_class_ranking(self, user_id: str) -> dict:
        """班级排名：按学习时长、做题数排序。未加入班级返回 in_class=False。"""
        res_my = await self.db.execute(
            select(ClassEnrollmentModel.class_id).where(
                ClassEnrollmentModel.student_id == user_id
            )
        )
        class_id = res_my.scalar_one_or_none()
        if class_id is None:
            return {"in_class": False, "rank": None, "total": 0, "percentile": None}

        res_students = await self.db.execute(
            select(ClassEnrollmentModel.student_id).where(
                ClassEnrollmentModel.class_id == class_id
            )
        )
        student_ids = [r[0] for r in res_students.all() if r[0]]
        if not student_ids:
            return {"in_class": True, "rank": None, "total": 0, "percentile": None}

        stmt_stats = (
            select(
                ContentAttemptModel.student_id,
                func.coalesce(
                    func.sum(ContentAttemptModel.time_spent_seconds), 0
                ).label("total_seconds"),
                func.count(ContentAttemptModel.id).label("attempt_count"),
            )
            .where(ContentAttemptModel.student_id.in_(student_ids))
            .group_by(ContentAttemptModel.student_id)
        )
        res_stats = await self.db.execute(stmt_stats)
        stats_map = {
            row.student_id: (int(row.total_seconds or 0), int(row.attempt_count or 0))
            for row in res_stats.all()
        }
        rows_for_rank = [
            (sid, stats_map.get(sid, (0, 0))[0], stats_map.get(sid, (0, 0))[1])
            for sid in student_ids
        ]
        rows_for_rank.sort(key=lambda x: (x[1], x[2]), reverse=True)
        total = len(rows_for_rank)
        rank = 1
        for i, (sid, _ts, _n) in enumerate(rows_for_rank, start=1):
            if sid == user_id:
                rank = i
                break
        percentile = (
            round((1.0 - (rank - 1) / total) * 100.0, 1) if total > 0 else None
        )
        return {
            "in_class": True,
            "rank": rank,
            "total": total,
            "percentile": percentile,
        }

    async def _calculate_streak_days(self, user_id: str) -> int:
        """连续学习天数：按 content_attempts 有提交的日期向前数。"""
        today = date.today()
        day_col = func.date_trunc("day", ContentAttemptModel.submitted_at).label("day")
        stmt = (
            select(day_col)
            .where(
                ContentAttemptModel.student_id == user_id,
                ContentAttemptModel.submitted_at.is_not(None),
            )
            .group_by(day_col)
            .order_by(day_col.desc())
            .limit(STREAK_LOOKBACK_DAYS)
        )
        res = await self.db.execute(stmt)
        active_days: set[date] = set()
        for row in res.all():
            if row.day is None:
                continue
            day_val = row.day
            day_date = day_val.date() if hasattr(day_val, "date") else day_val
            active_days.add(day_date)
        if not active_days:
            return 0
        streak = 0
        current = today
        while current in active_days:
            streak += 1
            current -= timedelta(days=1)
        return streak
