"""
学生领域模型

定义学生和学生画像实体
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """用户角色"""

    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class UserStatus(str, Enum):
    """用户状态"""

    ACTIVE = "active"  # 活跃
    SUSPENDED = "suspended"  # 已停用


@dataclass
class Student:
    """学生实体"""

    id: str
    username: str
    email: str
    role: UserRole = UserRole.STUDENT
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # 可选字段
    display_name: str | None = None
    avatar_url: str | None = None


@dataclass
class StudentProfile:
    """
    学生画像

    包含学习状态、知识掌握度等信息
    """

    student_id: str

    # 知识掌握度向量：{concept_id: mastery_probability}
    mastery_vector: dict[str, float] = field(default_factory=dict)

    # 错误倾向：{error_type: count}
    error_tendency: dict[str, int] = field(default_factory=dict)

    # 学习偏好
    preferred_difficulty: float = 0.5  # 0-1，偏好难度
    learning_pace: float = 1.0  # 学习节奏系数

    # 统计数据
    total_exercises: int = 0
    correct_count: int = 0
    total_study_time_minutes: int = 0

    # 最近活跃的知识点
    recent_concepts: list[str] = field(default_factory=list)

    # 学生画像（AI 生成）
    portrait_content: str | None = None
    portrait_generated_at: datetime | None = None
    portrait_version: int = 0

    # 更新时间
    updated_at: datetime = field(default_factory=datetime.now)

    @property
    def correct_rate(self) -> float:
        """正确率"""
        if self.total_exercises == 0:
            return 0.0
        return self.correct_count / self.total_exercises

    def update_mastery(self, concept_id: str, probability: float) -> None:
        """更新知识点掌握度"""
        self.mastery_vector[concept_id] = max(0.0, min(1.0, probability))
        self.updated_at = datetime.now()

    def record_error(self, error_type: str) -> None:
        """记录错误类型"""
        self.error_tendency[error_type] = self.error_tendency.get(error_type, 0) + 1
        self.updated_at = datetime.now()
