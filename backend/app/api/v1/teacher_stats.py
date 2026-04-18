"""
教师统计数据与分析 API

提供教师工作台、学生管理、数据分析、班级分析、学生详情的统计数据
"""

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSession, TeacherUserId
from app.api.v1.schemas.teacher_analytics import (
    AnalyticsOverview,
    ClassAlert,
    ClassAnalyticsResponse,
    ClassAnalyticsStats,
    ClassCommonError,
    ClassStudentRank,
    ClassTopicMastery,
    KnowledgePointMastery,
    StudentBasicInfo,
    StudentDetailResponse,
    StudentMistake,
    StudentRecentActivity,
    StudentTopicMastery,
    TeacherAnalyticsResponse,
    TopStudentItem,
    WeeklyActivityItem,
)
from app.infrastructure.database.models import (
    ClassEnrollmentModel,
    ClassModel,
    ContentAttemptModel,
    ContentModel,
    DiagnosisReportModel,
    KnowledgeNodeModel,
    LearningSessionModel,
    StudentProfileModel,
    UserModel,
)

logger = logging.getLogger(__name__)

router = APIRouter()

DAY_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


# =============================================================================
# 公共辅助函数
# =============================================================================


async def _get_teacher_class_ids(db: AsyncSession, teacher_id: str) -> list[str]:
    """获取教师的所有班级 ID"""
    result = await db.execute(
        select(ClassModel.id).where(ClassModel.teacher_id == teacher_id)
    )
    return [row[0] for row in result.fetchall()]


async def _get_class_student_ids(db: AsyncSession, class_ids: list[str]) -> list[str]:
    """获取班级列表中所有学生 ID"""
    result = await db.execute(
        select(ClassEnrollmentModel.student_id).where(
            ClassEnrollmentModel.class_id.in_(class_ids)
        )
    )
    return [row[0] for row in result.fetchall()]


async def _get_concept_name_map(db: AsyncSession, concept_ids: set[str]) -> dict[str, str]:
    """批量获取知识点 ID -> 名称映射"""
    if not concept_ids:
        return {}
    result = await db.execute(
        select(KnowledgeNodeModel.id, KnowledgeNodeModel.name).where(
            KnowledgeNodeModel.id.in_(list(concept_ids))
        )
    )
    return {row[0]: row[1] for row in result.fetchall()}


def _get_time_range_start(time_range: str) -> datetime:
    """根据时间范围字符串计算起始时间"""
    now = datetime.now()
    if time_range == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_range == "week":
        return now - timedelta(days=7)
    elif time_range == "month":
        return now - timedelta(days=30)
    elif time_range == "semester":
        return now - timedelta(days=180)
    return now - timedelta(days=7)


def _aggregate_mastery_vectors(
    profiles: list[StudentProfileModel],
) -> dict[str, dict]:
    """聚合多个学生的 mastery_vector，返回 {concept_id: {total, count}}"""
    agg: dict[str, dict] = defaultdict(lambda: {"total": 0.0, "count": 0})
    for profile in profiles:
        if not profile.mastery_vector:
            continue
        for concept_id, value in profile.mastery_vector.items():
            if isinstance(value, (int, float)):
                agg[concept_id]["total"] += float(value)
                agg[concept_id]["count"] += 1
    return dict(agg)


# =============================================================================
# 现有端点（重构使用公共辅助函数）
# =============================================================================


@router.get(
    "/dashboard/stats",
    summary="获取教师工作台统计数据",
    description="获取教师工作台首页的统计卡片数据",
)
async def get_dashboard_stats(
    teacher_id: TeacherUserId,
    db: DbSession,
) -> dict:
    """获取教师工作台统计数据"""
    class_ids = await _get_teacher_class_ids(db, teacher_id)
    if not class_ids:
        return {"total_students": 0, "active_today": 0.0, "avg_completion_rate": 0.0, "pending_grading": 0}

    student_ids = await _get_class_student_ids(db, class_ids)
    total_students = len(student_ids)
    if total_students == 0:
        return {"total_students": 0, "active_today": 0.0, "avg_completion_rate": 0.0, "pending_grading": 0}

    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count(func.distinct(LearningSessionModel.student_id))).where(
            LearningSessionModel.student_id.in_(student_ids),
            LearningSessionModel.started_at >= today_start,
        )
    )
    active_count = result.scalar() or 0
    active_rate = round((active_count / total_students) * 100, 1)

    return {
        "total_students": total_students,
        "active_today": active_rate,
        "avg_completion_rate": 0.0,
        "pending_grading": 0,
    }


@router.get(
    "/students/stats",
    summary="获取学生管理统计数据",
    description="获取学生管理页面的统计卡片数据",
)
async def get_students_stats(
    teacher_id: TeacherUserId,
    db: DbSession,
) -> dict:
    """获取学生管理统计数据"""
    class_ids = await _get_teacher_class_ids(db, teacher_id)
    if not class_ids:
        return {"total_students": 0, "avg_score": 0.0, "active_today": 0.0, "need_attention": 0}

    student_ids = await _get_class_student_ids(db, class_ids)
    total_students = len(student_ids)
    if total_students == 0:
        return {"total_students": 0, "avg_score": 0.0, "active_today": 0.0, "need_attention": 0}

    # 平均成绩
    avg_result = await db.execute(
        select(func.avg(ContentAttemptModel.score)).where(
            ContentAttemptModel.student_id.in_(student_ids),
            ContentAttemptModel.score.isnot(None),
        )
    )
    avg_score_val = avg_result.scalar()
    avg_score = round(float(avg_score_val), 1) if avg_score_val is not None else 0.0

    # 今日活跃率
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    active_result = await db.execute(
        select(func.count(func.distinct(LearningSessionModel.student_id))).where(
            LearningSessionModel.student_id.in_(student_ids),
            LearningSessionModel.started_at >= today_start,
        )
    )
    active_count = active_result.scalar() or 0
    active_rate = round((active_count / total_students) * 100, 1)

    # 需关注学生
    seven_days_ago = datetime.now() - timedelta(days=7)
    low_result = await db.execute(
        select(func.distinct(ContentAttemptModel.student_id)).where(
            ContentAttemptModel.student_id.in_(student_ids),
            ContentAttemptModel.score < 60,
        )
    )
    low_score_students = {row[0] for row in low_result.fetchall()}

    recent_result = await db.execute(
        select(func.distinct(LearningSessionModel.student_id)).where(
            LearningSessionModel.student_id.in_(student_ids),
            LearningSessionModel.started_at >= seven_days_ago,
        )
    )
    recent_active = {row[0] for row in recent_result.fetchall()}
    inactive = set(student_ids) - recent_active
    need_attention = len(low_score_students | inactive)

    return {
        "total_students": total_students,
        "avg_score": avg_score,
        "active_today": active_rate,
        "need_attention": need_attention,
    }


# =============================================================================
# 数据分析页端点
# =============================================================================


@router.get(
    "/analytics",
    summary="获取教师数据分析",
    description="获取数据分析页面的全量数据（概览、知识点掌握度、周活跃度、成绩排行）",
    response_model=TeacherAnalyticsResponse,
)
async def get_analytics(
    teacher_id: TeacherUserId,
    db: DbSession,
    time_range: str = Query("week", pattern="^(today|week|month|semester)$"),
) -> TeacherAnalyticsResponse:
    """获取教师数据分析页全量数据"""
    class_ids = await _get_teacher_class_ids(db, teacher_id)
    empty_response = TeacherAnalyticsResponse(
        overview=AnalyticsOverview(total_students=0, avg_completion_rate=0, avg_score=0, avg_study_hours=0),
        knowledge_points=[],
        weekly_activity=[],
        top_students=[],
    )
    if not class_ids:
        return empty_response

    student_ids = await _get_class_student_ids(db, class_ids)
    total_students = len(student_ids)
    if total_students == 0:
        return empty_response

    range_start = _get_time_range_start(time_range)

    # --- 概览统计 ---
    # 平均成绩
    avg_score_result = await db.execute(
        select(func.avg(ContentAttemptModel.score)).where(
            ContentAttemptModel.student_id.in_(student_ids),
            ContentAttemptModel.score.isnot(None),
            ContentAttemptModel.started_at >= range_start,
        )
    )
    avg_score_val = avg_score_result.scalar()
    avg_score = round(float(avg_score_val), 1) if avg_score_val else 0.0

    # 平均学习时长（小时/人）
    study_time_result = await db.execute(
        select(func.coalesce(func.sum(ContentAttemptModel.time_spent_seconds), 0)).where(
            ContentAttemptModel.student_id.in_(student_ids),
            ContentAttemptModel.started_at >= range_start,
        )
    )
    total_seconds = study_time_result.scalar() or 0
    avg_study_hours = round(total_seconds / max(total_students, 1) / 3600, 1)

    # 完成率（有做题记录的学生比例）
    active_students_result = await db.execute(
        select(func.count(func.distinct(ContentAttemptModel.student_id))).where(
            ContentAttemptModel.student_id.in_(student_ids),
            ContentAttemptModel.started_at >= range_start,
        )
    )
    active_student_count = active_students_result.scalar() or 0
    avg_completion_rate = round((active_student_count / total_students) * 100, 1)

    overview = AnalyticsOverview(
        total_students=total_students,
        avg_completion_rate=avg_completion_rate,
        avg_score=avg_score,
        avg_study_hours=avg_study_hours,
    )

    # --- 知识点掌握度 ---
    profiles_result = await db.execute(
        select(StudentProfileModel).where(
            StudentProfileModel.student_id.in_(student_ids)
        )
    )
    profiles = list(profiles_result.scalars().all())
    mastery_agg = _aggregate_mastery_vectors(profiles)

    all_concept_ids = set(mastery_agg.keys())
    concept_names = await _get_concept_name_map(db, all_concept_ids)

    knowledge_points: list[KnowledgePointMastery] = []
    for cid, data in sorted(
        mastery_agg.items(), key=lambda x: x[1]["total"] / max(x[1]["count"], 1), reverse=True
    )[:10]:
        avg_mastery = round((data["total"] / data["count"]) * 100, 1) if data["count"] > 0 else 0
        knowledge_points.append(KnowledgePointMastery(
            concept_id=cid,
            name=concept_names.get(cid, "未知知识点"),
            mastery=avg_mastery,
            student_count=data["count"],
        ))

    # --- 周活跃度 ---
    seven_days_ago = datetime.now() - timedelta(days=7)
    activity_result = await db.execute(
        select(
            func.date(LearningSessionModel.started_at).label("session_date"),
            func.count(func.distinct(LearningSessionModel.student_id)).label("active_count"),
        )
        .where(
            LearningSessionModel.student_id.in_(student_ids),
            LearningSessionModel.started_at >= seven_days_ago,
        )
        .group_by(func.date(LearningSessionModel.started_at))
    )
    activity_map = {row.session_date: row.active_count for row in activity_result.fetchall()}

    weekly_activity: list[WeeklyActivityItem] = []
    for i in range(6, -1, -1):
        d = date.today() - timedelta(days=i)
        active_count = activity_map.get(d, 0)
        rate = round((active_count / total_students) * 100, 1) if total_students > 0 else 0
        weekly_activity.append(WeeklyActivityItem(
            date=d.isoformat(),
            day_label=DAY_LABELS[d.weekday()],
            active_rate=rate,
        ))

    # --- 成绩排行 ---
    ranking_result = await db.execute(
        select(
            ContentAttemptModel.student_id,
            func.avg(ContentAttemptModel.score).label("avg_score"),
        )
        .where(
            ContentAttemptModel.student_id.in_(student_ids),
            ContentAttemptModel.score.isnot(None),
        )
        .group_by(ContentAttemptModel.student_id)
        .order_by(func.avg(ContentAttemptModel.score).desc())
        .limit(5)
    )
    ranking_rows = ranking_result.fetchall()

    top_student_ids = [row.student_id for row in ranking_rows]
    if top_student_ids:
        names_result = await db.execute(
            select(UserModel.id, UserModel.display_name, UserModel.username).where(
                UserModel.id.in_(top_student_ids)
            )
        )
        name_map = {r.id: r.display_name or r.username for r in names_result.fetchall()}
    else:
        name_map = {}

    top_students = [
        TopStudentItem(
            rank=idx + 1,
            student_id=row.student_id,
            name=name_map.get(row.student_id, "未知"),
            avg_score=round(float(row.avg_score), 1),
        )
        for idx, row in enumerate(ranking_rows)
    ]

    return TeacherAnalyticsResponse(
        overview=overview,
        knowledge_points=knowledge_points,
        weekly_activity=weekly_activity,
        top_students=top_students,
    )


# =============================================================================
# 班级分析端点
# =============================================================================


@router.get(
    "/classes/{class_id}/analytics",
    summary="获取班级分析数据",
    description="获取班级详情页的分析数据（统计、知识点掌握、高频错题、学情预警、排名）",
    response_model=ClassAnalyticsResponse,
)
async def get_class_analytics(
    class_id: str,
    teacher_id: TeacherUserId,
    db: DbSession,
) -> ClassAnalyticsResponse:
    """获取班级分析数据"""
    # 验证班级归属
    cls_result = await db.execute(
        select(ClassModel).where(ClassModel.id == class_id, ClassModel.teacher_id == teacher_id)
    )
    if cls_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="班级不存在或无权限访问")

    student_ids = await _get_class_student_ids(db, [class_id])
    total_students = len(student_ids)
    empty_response = ClassAnalyticsResponse(
        stats=ClassAnalyticsStats(average_mastery=0, average_score=0, weekly_study_hours=0),
        topic_mastery=[],
        common_errors=[],
        alerts=[],
        student_rankings=[],
    )
    if total_students == 0:
        return empty_response

    # --- 统计卡片 ---
    # 平均掌握度
    profiles_result = await db.execute(
        select(StudentProfileModel).where(
            StudentProfileModel.student_id.in_(student_ids)
        )
    )
    profiles = list(profiles_result.scalars().all())

    all_values = []
    for p in profiles:
        if p.mastery_vector:
            all_values.extend(
                v for v in p.mastery_vector.values() if isinstance(v, (int, float))
            )
    average_mastery = round(sum(all_values) / len(all_values), 3) if all_values else 0.0

    # 平均成绩
    avg_score_result = await db.execute(
        select(func.avg(ContentAttemptModel.score)).where(
            ContentAttemptModel.student_id.in_(student_ids),
            ContentAttemptModel.score.isnot(None),
        )
    )
    avg_score_val = avg_score_result.scalar()
    average_score = round(float(avg_score_val), 1) if avg_score_val else 0.0

    # 周均学习时长
    seven_days_ago = datetime.now() - timedelta(days=7)
    study_result = await db.execute(
        select(func.coalesce(func.sum(ContentAttemptModel.time_spent_seconds), 0)).where(
            ContentAttemptModel.student_id.in_(student_ids),
            ContentAttemptModel.started_at >= seven_days_ago,
        )
    )
    weekly_seconds = study_result.scalar() or 0
    weekly_study_hours = round(weekly_seconds / max(total_students, 1) / 3600, 1)

    stats = ClassAnalyticsStats(
        average_mastery=average_mastery,
        average_score=average_score,
        weekly_study_hours=weekly_study_hours,
    )

    # --- 知识点掌握度 ---
    mastery_agg = _aggregate_mastery_vectors(profiles)
    concept_names = await _get_concept_name_map(db, set(mastery_agg.keys()))
    topic_mastery = []
    for cid, data in sorted(
        mastery_agg.items(), key=lambda x: x[1]["total"] / max(x[1]["count"], 1), reverse=True
    )[:10]:
        avg_m = round(data["total"] / data["count"], 3) if data["count"] > 0 else 0
        topic_mastery.append(ClassTopicMastery(
            concept_id=cid,
            topic=concept_names.get(cid, "未知知识点"),
            mastery=avg_m,
            student_count=data["count"],
        ))

    # --- 高频错题 ---
    error_result = await db.execute(
        select(
            DiagnosisReportModel.error_type,
            DiagnosisReportModel.error_subtype,
            DiagnosisReportModel.explanation,
            func.count().label("cnt"),
        )
        .join(ContentAttemptModel, ContentAttemptModel.id == DiagnosisReportModel.attempt_id)
        .where(
            ContentAttemptModel.student_id.in_(student_ids),
            DiagnosisReportModel.error_type.isnot(None),
        )
        .group_by(
            DiagnosisReportModel.error_type,
            DiagnosisReportModel.error_subtype,
            DiagnosisReportModel.explanation,
        )
        .order_by(func.count().desc())
        .limit(10)
    )
    common_errors = []
    for row in error_result.fetchall():
        error_type_str = row.error_type.value if hasattr(row.error_type, "value") else str(row.error_type)
        common_errors.append(ClassCommonError(
            id=str(uuid4()),
            content=row.explanation or row.error_subtype or "未知错误",
            count=row.cnt,
            topic=row.error_subtype or "未分类",
            error_type=error_type_str,
        ))

    # --- 学情预警 ---
    alerts = []

    # 低分学生（平均分 < 60）
    low_score_result = await db.execute(
        select(
            ContentAttemptModel.student_id,
            func.avg(ContentAttemptModel.score).label("avg_score"),
        )
        .where(
            ContentAttemptModel.student_id.in_(student_ids),
            ContentAttemptModel.score.isnot(None),
        )
        .group_by(ContentAttemptModel.student_id)
        .having(func.avg(ContentAttemptModel.score) < 60)
    )
    low_score_rows = low_score_result.fetchall()
    low_ids = [r.student_id for r in low_score_rows]

    # 不活跃学生（7 天无 session）
    recent_active_result = await db.execute(
        select(func.distinct(LearningSessionModel.student_id)).where(
            LearningSessionModel.student_id.in_(student_ids),
            LearningSessionModel.started_at >= seven_days_ago,
        )
    )
    recent_active_set = {row[0] for row in recent_active_result.fetchall()}
    inactive_ids = [sid for sid in student_ids if sid not in recent_active_set]

    # 获取预警学生姓名
    alert_student_ids = list(set(low_ids + inactive_ids))
    if alert_student_ids:
        alert_names_result = await db.execute(
            select(UserModel.id, UserModel.display_name, UserModel.username).where(
                UserModel.id.in_(alert_student_ids)
            )
        )
        alert_name_map = {r.id: r.display_name or r.username for r in alert_names_result.fetchall()}
    else:
        alert_name_map = {}

    for row in low_score_rows:
        alerts.append(ClassAlert(
            id=str(uuid4()),
            student_id=row.student_id,
            student_name=alert_name_map.get(row.student_id, "未知"),
            type="low_score",
            message=f"平均成绩 {round(float(row.avg_score), 1)} 分，低于及格线",
            severity="high",
        ))
    for sid in inactive_ids:
        if sid not in low_ids:  # 避免重复
            alerts.append(ClassAlert(
                id=str(uuid4()),
                student_id=sid,
                student_name=alert_name_map.get(sid, "未知"),
                type="inactive",
                message="超过 7 天未学习",
                severity="medium",
            ))

    # --- 成绩排名 ---
    rank_result = await db.execute(
        select(
            ContentAttemptModel.student_id,
            func.avg(ContentAttemptModel.score).label("avg_score"),
        )
        .where(
            ContentAttemptModel.student_id.in_(student_ids),
            ContentAttemptModel.score.isnot(None),
        )
        .group_by(ContentAttemptModel.student_id)
        .order_by(func.avg(ContentAttemptModel.score).desc())
        .limit(5)
    )
    rank_rows = rank_result.fetchall()

    rank_student_ids = [r.student_id for r in rank_rows]
    if rank_student_ids:
        rank_names_result = await db.execute(
            select(UserModel.id, UserModel.display_name, UserModel.username).where(
                UserModel.id.in_(rank_student_ids)
            )
        )
        rank_name_map = {r.id: r.display_name or r.username for r in rank_names_result.fetchall()}
    else:
        rank_name_map = {}

    student_rankings = [
        ClassStudentRank(
            student_id=row.student_id,
            name=rank_name_map.get(row.student_id, "未知"),
            avg_score=round(float(row.avg_score), 1),
        )
        for row in rank_rows
    ]

    return ClassAnalyticsResponse(
        stats=stats,
        topic_mastery=topic_mastery,
        common_errors=common_errors,
        alerts=alerts,
        student_rankings=student_rankings,
    )


# =============================================================================
# 学生详情端点
# =============================================================================


@router.get(
    "/students/{student_id}/detail",
    summary="获取学生详情",
    description="获取教师视角的学生详情数据（基本信息、知识掌握、学习动态、错题）",
    response_model=StudentDetailResponse,
)
async def get_student_detail(
    student_id: str,
    teacher_id: TeacherUserId,
    db: DbSession,
) -> StudentDetailResponse:
    """获取教师视角的学生详情"""
    # 验证学生属于教师的班级
    enrollment_result = await db.execute(
        select(ClassEnrollmentModel, ClassModel.name.label("class_name"))
        .join(ClassModel, ClassModel.id == ClassEnrollmentModel.class_id)
        .where(
            ClassEnrollmentModel.student_id == student_id,
            ClassModel.teacher_id == teacher_id,
        )
    )
    enrollment_row = enrollment_result.first()
    if enrollment_row is None:
        raise HTTPException(status_code=404, detail="学生不存在或无权限访问")

    enrollment = enrollment_row[0]
    class_name = enrollment_row.class_name

    # 获取学生基本信息
    user_result = await db.execute(
        select(UserModel).where(UserModel.id == student_id)
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="学生不存在")

    # 获取学生画像
    profile_result = await db.execute(
        select(StudentProfileModel).where(StudentProfileModel.student_id == student_id)
    )
    profile = profile_result.scalar_one_or_none()

    total_exercises = profile.total_exercises if profile else 0
    correct_count = profile.correct_count if profile else 0
    correct_rate = round((correct_count / total_exercises) * 100, 1) if total_exercises > 0 else 0.0
    study_hours = round((profile.total_study_time_minutes or 0) / 60, 1) if profile else 0.0

    # 平均成绩
    avg_result = await db.execute(
        select(func.avg(ContentAttemptModel.score)).where(
            ContentAttemptModel.student_id == student_id,
            ContentAttemptModel.score.isnot(None),
        )
    )
    avg_score_val = avg_result.scalar()
    avg_score = round(float(avg_score_val), 1) if avg_score_val else 0.0

    # 班级排名
    class_student_ids = await _get_class_student_ids(db, [enrollment.class_id])
    total_class_students = len(class_student_ids)

    rank_result = await db.execute(
        select(
            ContentAttemptModel.student_id,
            func.avg(ContentAttemptModel.score).label("avg_score"),
        )
        .where(
            ContentAttemptModel.student_id.in_(class_student_ids),
            ContentAttemptModel.score.isnot(None),
        )
        .group_by(ContentAttemptModel.student_id)
        .order_by(func.avg(ContentAttemptModel.score).desc())
    )
    rank = 0
    for idx, row in enumerate(rank_result.fetchall(), 1):
        if row.student_id == student_id:
            rank = idx
            break

    # 最后活跃时间
    last_session_result = await db.execute(
        select(func.max(LearningSessionModel.started_at)).where(
            LearningSessionModel.student_id == student_id
        )
    )
    last_active_dt = last_session_result.scalar()
    last_active = last_active_dt.isoformat() if last_active_dt else None

    # 连续学习天数
    session_dates_result = await db.execute(
        select(func.distinct(func.date(LearningSessionModel.started_at)))
        .where(LearningSessionModel.student_id == student_id)
        .order_by(func.date(LearningSessionModel.started_at).desc())
    )
    session_dates = [row[0] for row in session_dates_result.fetchall()]
    streak_days = 0
    check_date = date.today()
    for d in session_dates:
        if d == check_date:
            streak_days += 1
            check_date -= timedelta(days=1)
        elif d < check_date:
            break

    student_info = StudentBasicInfo(
        id=user.id,
        name=user.display_name or user.username,
        username=user.username,
        email=user.email or "",
        class_name=class_name,
        joined_at=enrollment.joined_at.isoformat() if enrollment.joined_at else None,
        last_active=last_active,
        total_study_hours=study_hours,
        total_exercises=total_exercises,
        correct_rate=correct_rate,
        avg_score=avg_score,
        rank=rank,
        total_class_students=total_class_students,
        streak_days=streak_days,
    )

    # --- 知识点掌握度 ---
    mastery_items = []
    if profile and profile.mastery_vector:
        concept_ids = set(profile.mastery_vector.keys())
        concept_names = await _get_concept_name_map(db, concept_ids)

        # 统计每个知识点的做题数
        attempt_concepts: dict[str, int] = defaultdict(int)
        attempt_contents_result = await db.execute(
            select(ContentModel.concept_ids).join(
                ContentAttemptModel, ContentAttemptModel.content_id == ContentModel.id
            ).where(ContentAttemptModel.student_id == student_id)
        )
        for row in attempt_contents_result.fetchall():
            if row[0]:
                for cid in row[0]:
                    attempt_concepts[cid] += 1

        for cid, value in sorted(
            profile.mastery_vector.items(),
            key=lambda x: float(x[1]) if isinstance(x[1], (int, float)) else 0,
            reverse=True,
        ):
            if isinstance(value, (int, float)):
                mastery_items.append(StudentTopicMastery(
                    concept_id=cid,
                    topic=concept_names.get(cid, "未知知识点"),
                    mastery=round(float(value), 3),
                    exercise_count=attempt_concepts.get(cid, 0),
                ))

    # --- 最近学习动态 ---
    # 最近做题记录
    recent_attempts_result = await db.execute(
        select(
            ContentAttemptModel.id,
            ContentAttemptModel.is_correct,
            ContentAttemptModel.score,
            ContentAttemptModel.started_at,
            ContentModel.title,
        )
        .join(ContentModel, ContentModel.id == ContentAttemptModel.content_id)
        .where(ContentAttemptModel.student_id == student_id)
        .order_by(ContentAttemptModel.started_at.desc())
        .limit(10)
    )
    recent_activity = []
    for row in recent_attempts_result.fetchall():
        score_str = f"得分 {round(float(row.score), 0):.0f}" if row.score else ""
        status = "success" if row.is_correct else "warning"
        content_text = f'完成"{row.title or "未知题目"}"练习'
        if score_str:
            content_text += f"，{score_str}"
        recent_activity.append(StudentRecentActivity(
            id=row.id,
            type="exercise",
            content=content_text,
            time=row.started_at.isoformat() if row.started_at else "",
            status=status,
        ))

    # 最近会话记录
    recent_sessions_result = await db.execute(
        select(LearningSessionModel.id, LearningSessionModel.started_at, LearningSessionModel.ended_at)
        .where(LearningSessionModel.student_id == student_id)
        .order_by(LearningSessionModel.started_at.desc())
        .limit(5)
    )
    for row in recent_sessions_result.fetchall():
        duration = ""
        if row.ended_at and row.started_at:
            mins = int((row.ended_at - row.started_at).total_seconds() / 60)
            duration = f" {mins} 分钟"
        recent_activity.append(StudentRecentActivity(
            id=row.id,
            type="session",
            content=f"与 AI 导师对话{duration}",
            time=row.started_at.isoformat() if row.started_at else "",
            status="info",
        ))

    # 按时间排序，取前 10 条
    recent_activity.sort(key=lambda x: x.time, reverse=True)
    recent_activity = recent_activity[:10]

    # --- 最近错题 ---
    mistakes_result = await db.execute(
        select(
            ContentAttemptModel.id,
            ContentAttemptModel.started_at,
            ContentModel.title,
            DiagnosisReportModel.error_type,
            DiagnosisReportModel.explanation,
        )
        .join(ContentModel, ContentModel.id == ContentAttemptModel.content_id)
        .outerjoin(DiagnosisReportModel, DiagnosisReportModel.attempt_id == ContentAttemptModel.id)
        .where(
            ContentAttemptModel.student_id == student_id,
            ContentAttemptModel.is_correct.is_(False),
        )
        .order_by(ContentAttemptModel.started_at.desc())
        .limit(5)
    )
    recent_mistakes = []
    for row in mistakes_result.fetchall():
        error_type_str = ""
        if row.error_type:
            error_type_str = row.error_type.value if hasattr(row.error_type, "value") else str(row.error_type)
        recent_mistakes.append(StudentMistake(
            id=row.id,
            content=row.title or "未知题目",
            error_type=error_type_str,
            date=row.started_at.isoformat() if row.started_at else "",
            explanation=row.explanation,
        ))

    return StudentDetailResponse(
        student=student_info,
        topic_mastery=mastery_items,
        recent_activity=recent_activity,
        recent_mistakes=recent_mistakes,
    )
