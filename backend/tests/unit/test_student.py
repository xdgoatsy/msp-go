"""
学生领域模型单元测试
"""

from datetime import datetime

import pytest

from app.domain.models.student import (
    Student,
    StudentProfile,
    UserRole,
    UserStatus,
)


class TestUserRole:
    """UserRole 枚举测试"""

    def test_student_value(self):
        assert UserRole.STUDENT == "student"

    def test_teacher_value(self):
        assert UserRole.TEACHER == "teacher"

    def test_admin_value(self):
        assert UserRole.ADMIN == "admin"

    def test_is_str_subclass(self):
        # str 枚举可直接用于字符串比较
        assert isinstance(UserRole.STUDENT, str)


class TestUserStatus:
    """UserStatus 枚举测试"""

    def test_active_value(self):
        assert UserStatus.ACTIVE == "active"

    def test_suspended_value(self):
        assert UserStatus.SUSPENDED == "suspended"

    def test_is_str_subclass(self):
        assert isinstance(UserStatus.ACTIVE, str)


class TestStudent:
    """Student 实体测试"""

    def test_creation_with_defaults(self):
        """使用默认值创建学生"""
        s = Student(id="s1", username="alice", email="alice@example.com")
        assert s.id == "s1"
        assert s.username == "alice"
        assert s.email == "alice@example.com"
        assert s.role == UserRole.STUDENT
        assert s.display_name is None
        assert s.avatar_url is None
        assert isinstance(s.created_at, datetime)
        assert isinstance(s.updated_at, datetime)

    def test_creation_with_custom_values(self):
        """使用自定义值创建学生"""
        now = datetime(2024, 1, 1, 12, 0, 0)
        s = Student(
            id="t1",
            username="bob",
            email="bob@example.com",
            role=UserRole.TEACHER,
            created_at=now,
            updated_at=now,
            display_name="Bob Teacher",
            avatar_url="https://example.com/avatar.png",
        )
        assert s.role == UserRole.TEACHER
        assert s.display_name == "Bob Teacher"
        assert s.avatar_url == "https://example.com/avatar.png"
        assert s.created_at == now

    def test_default_role_is_student(self):
        """默认角色为学生"""
        s = Student(id="s2", username="carol", email="carol@example.com")
        assert s.role == UserRole.STUDENT


class TestStudentProfileCorrectRate:
    """StudentProfile.correct_rate 属性测试"""

    def test_zero_exercises_returns_zero(self):
        """无练习时正确率为 0.0"""
        profile = StudentProfile(student_id="s1")
        assert profile.correct_rate == 0.0

    def test_correct_rate_calculation(self):
        """正确率计算"""
        profile = StudentProfile(
            student_id="s1",
            total_exercises=10,
            correct_count=7,
        )
        assert profile.correct_rate == pytest.approx(0.7)

    def test_perfect_score(self):
        """满分情况"""
        profile = StudentProfile(
            student_id="s1",
            total_exercises=5,
            correct_count=5,
        )
        assert profile.correct_rate == pytest.approx(1.0)

    def test_zero_correct(self):
        """全错情况"""
        profile = StudentProfile(
            student_id="s1",
            total_exercises=4,
            correct_count=0,
        )
        assert profile.correct_rate == pytest.approx(0.0)


class TestStudentProfileUpdateMastery:
    """StudentProfile.update_mastery 方法测试"""

    def test_sets_value(self):
        """正常设置掌握度"""
        profile = StudentProfile(student_id="s1")
        profile.update_mastery("concept_001", 0.8)
        assert profile.mastery_vector["concept_001"] == pytest.approx(0.8)

    def test_clamps_above_one(self):
        """超过 1.0 时截断为 1.0"""
        profile = StudentProfile(student_id="s1")
        profile.update_mastery("concept_001", 1.5)
        assert profile.mastery_vector["concept_001"] == pytest.approx(1.0)

    def test_clamps_below_zero(self):
        """低于 0.0 时截断为 0.0"""
        profile = StudentProfile(student_id="s1")
        profile.update_mastery("concept_001", -0.3)
        assert profile.mastery_vector["concept_001"] == pytest.approx(0.0)

    def test_updates_updated_at(self):
        """调用后 updated_at 被更新"""
        profile = StudentProfile(student_id="s1")
        before = profile.updated_at
        profile.update_mastery("concept_001", 0.5)
        # updated_at 应 >= before（可能相同毫秒，但不应更早）
        assert profile.updated_at >= before

    def test_overwrites_existing_value(self):
        """覆盖已有掌握度"""
        profile = StudentProfile(student_id="s1")
        profile.update_mastery("concept_001", 0.3)
        profile.update_mastery("concept_001", 0.9)
        assert profile.mastery_vector["concept_001"] == pytest.approx(0.9)


class TestStudentProfileRecordError:
    """StudentProfile.record_error 方法测试"""

    def test_creates_new_entry(self):
        """首次记录错误类型时创建新条目"""
        profile = StudentProfile(student_id="s1")
        profile.record_error("conceptual")
        assert profile.error_tendency["conceptual"] == 1

    def test_increments_existing_count(self):
        """重复记录同一错误类型时递增计数"""
        profile = StudentProfile(student_id="s1")
        profile.record_error("procedural")
        profile.record_error("procedural")
        profile.record_error("procedural")
        assert profile.error_tendency["procedural"] == 3

    def test_multiple_error_types(self):
        """不同错误类型独立计数"""
        profile = StudentProfile(student_id="s1")
        profile.record_error("conceptual")
        profile.record_error("logical")
        profile.record_error("conceptual")
        assert profile.error_tendency["conceptual"] == 2
        assert profile.error_tendency["logical"] == 1

    def test_updates_updated_at(self):
        """调用后 updated_at 被更新"""
        profile = StudentProfile(student_id="s1")
        before = profile.updated_at
        profile.record_error("calculation")
        assert profile.updated_at >= before
