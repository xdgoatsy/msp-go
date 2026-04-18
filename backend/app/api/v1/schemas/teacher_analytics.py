"""
教师数据分析 API 响应模型

为教师端数据分析页面、班级详情页、学生详情页提供类型定义
"""

from pydantic import BaseModel

# =============================================================================
# TeacherAnalyticsPage 响应模型
# =============================================================================


class AnalyticsOverview(BaseModel):
    """数据分析页概览统计"""

    total_students: int
    avg_completion_rate: float
    avg_score: float
    avg_study_hours: float


class KnowledgePointMastery(BaseModel):
    """知识点掌握度"""

    concept_id: str
    name: str
    mastery: float
    student_count: int


class WeeklyActivityItem(BaseModel):
    """周活跃度数据项"""

    date: str
    day_label: str
    active_rate: float


class TopStudentItem(BaseModel):
    """成绩排行学生"""

    rank: int
    student_id: str
    name: str
    avg_score: float


class TeacherAnalyticsResponse(BaseModel):
    """教师数据分析页完整响应"""

    overview: AnalyticsOverview
    knowledge_points: list[KnowledgePointMastery]
    weekly_activity: list[WeeklyActivityItem]
    top_students: list[TopStudentItem]


# =============================================================================
# ClassDetailPage 响应模型
# =============================================================================


class ClassAnalyticsStats(BaseModel):
    """班级分析统计"""

    average_mastery: float
    average_score: float
    weekly_study_hours: float


class ClassTopicMastery(BaseModel):
    """班级知识点掌握度"""

    concept_id: str
    topic: str
    mastery: float
    student_count: int


class ClassCommonError(BaseModel):
    """班级高频错题"""

    id: str
    content: str
    count: int
    topic: str
    error_type: str


class ClassAlert(BaseModel):
    """学情预警"""

    id: str
    student_id: str
    student_name: str
    type: str
    message: str
    severity: str


class ClassStudentRank(BaseModel):
    """班级学生排名"""

    student_id: str
    name: str
    avg_score: float


class ClassAnalyticsResponse(BaseModel):
    """班级分析完整响应"""

    stats: ClassAnalyticsStats
    topic_mastery: list[ClassTopicMastery]
    common_errors: list[ClassCommonError]
    alerts: list[ClassAlert]
    student_rankings: list[ClassStudentRank]


# =============================================================================
# StudentDetailPage 响应模型
# =============================================================================


class StudentBasicInfo(BaseModel):
    """学生基本信息"""

    id: str
    name: str
    username: str
    email: str
    class_name: str
    joined_at: str | None = None
    last_active: str | None = None
    total_study_hours: float
    total_exercises: int
    correct_rate: float
    avg_score: float
    rank: int
    total_class_students: int
    streak_days: int


class StudentTopicMastery(BaseModel):
    """学生知识点掌握度"""

    concept_id: str
    topic: str
    mastery: float
    exercise_count: int


class StudentRecentActivity(BaseModel):
    """学生最近学习动态"""

    id: str
    type: str
    content: str
    time: str
    status: str


class StudentMistake(BaseModel):
    """学生最近错题"""

    id: str
    content: str
    error_type: str
    date: str
    explanation: str | None = None


class StudentDetailResponse(BaseModel):
    """学生详情完整响应"""

    student: StudentBasicInfo
    topic_mastery: list[StudentTopicMastery]
    recent_activity: list[StudentRecentActivity]
    recent_mistakes: list[StudentMistake]
