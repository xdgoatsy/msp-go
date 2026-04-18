"""
班级管理服务

提供教师创建班级、学生加入/退出班级等业务逻辑
"""

import logging
import secrets
import string
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.student import UserRole
from app.infrastructure.database.models import (
    ClassEnrollmentModel,
    ClassModel,
    UserModel,
)

logger = logging.getLogger(__name__)


class ClassService:
    """班级管理服务"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_class(
        self, teacher_id: str, name: str, description: str | None = None
    ) -> ClassModel:
        """创建班级"""
        teacher = await self._get_user(teacher_id)
        if teacher is None or teacher.role not in (UserRole.TEACHER, UserRole.ADMIN):
            raise PermissionError("非教师账号，无法创建班级")

        for attempt in range(1, 4):
            class_code = await self._generate_unique_code()
            class_model = ClassModel(
                name=name,
                code=class_code,
                teacher_id=teacher_id,
                description=description,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            self.db.add(class_model)
            try:
                await self.db.commit()
            except IntegrityError as exc:
                await self.db.rollback()
                logger.warning(
                    "班级号冲突，正在重试",
                    extra={
                        "attempt": attempt,
                        "class_code": class_model.code,
                        "teacher_id": class_model.teacher_id,
                        "name": class_model.name,
                    },
                )
                if attempt == 3:
                    raise ValueError("班级号生成冲突，请稍后重试") from exc
                continue

            await self.db.refresh(class_model)
            logger.info("班级已创建", extra={"class_id": class_model.id})
            return class_model

        raise ValueError("班级号生成冲突，请稍后重试")

    async def list_teacher_classes(self, teacher_id: str) -> list[dict]:
        """获取教师班级列表（含学生数）"""
        query = (
            select(ClassModel, func.count(ClassEnrollmentModel.id))
            .outerjoin(
                ClassEnrollmentModel,
                ClassEnrollmentModel.class_id == ClassModel.id,
            )
            .where(ClassModel.teacher_id == teacher_id)
            .group_by(ClassModel.id)
            .order_by(ClassModel.created_at.desc())
        )
        result = await self.db.execute(query)
        rows = result.all()
        return [
            {
                "class": row[0],
                "student_count": row[1] or 0,
            }
            for row in rows
        ]

    async def get_teacher_class_detail(
        self, teacher_id: str, class_id: str
    ) -> tuple[ClassModel | None, list[UserModel], UserModel | None]:
        """获取教师班级详情与学生列表"""
        class_result = await self.db.execute(
            select(ClassModel).where(
                ClassModel.id == class_id, ClassModel.teacher_id == teacher_id
            )
        )
        class_model = class_result.scalar_one_or_none()
        if class_model is None:
            return None, [], None

        students_result = await self.db.execute(
            select(UserModel)
            .join(
                ClassEnrollmentModel,
                ClassEnrollmentModel.student_id == UserModel.id,
            )
            .where(ClassEnrollmentModel.class_id == class_id)
            .order_by(UserModel.created_at.desc())
        )
        students = students_result.scalars().all()
        teacher = await self._get_user(class_model.teacher_id)
        return class_model, students, teacher

    async def disband_class(self, teacher_id: str, class_id: str) -> bool:
        """教师解散班级"""
        class_result = await self.db.execute(
            select(ClassModel).where(
                ClassModel.id == class_id, ClassModel.teacher_id == teacher_id
            )
        )
        class_model = class_result.scalar_one_or_none()
        if class_model is None:
            return False

        await self.db.delete(class_model)
        await self.db.commit()
        return True

    async def remove_student(
        self, teacher_id: str, class_id: str, student_id: str
    ) -> bool:
        """教师移除学生"""
        class_result = await self.db.execute(
            select(ClassModel).where(
                ClassModel.id == class_id, ClassModel.teacher_id == teacher_id
            )
        )
        class_model = class_result.scalar_one_or_none()
        if class_model is None:
            return False

        enrollment_result = await self.db.execute(
            select(ClassEnrollmentModel).where(
                ClassEnrollmentModel.class_id == class_id,
                ClassEnrollmentModel.student_id == student_id,
            )
        )
        enrollment = enrollment_result.scalar_one_or_none()
        if enrollment is None:
            return False

        await self.db.delete(enrollment)
        await self.db.commit()
        return True

    async def lookup_class_by_code(
        self, code: str
    ) -> tuple[ClassModel | None, UserModel | None]:
        """根据班级号查询班级"""
        normalized_code = code.strip().upper()
        class_result = await self.db.execute(
            select(ClassModel).where(ClassModel.code == normalized_code)
        )
        class_model = class_result.scalar_one_or_none()
        if class_model is None:
            return None, None

        teacher = await self._get_user(class_model.teacher_id)
        return class_model, teacher

    async def join_class(self, student_id: str, code: str) -> ClassModel:
        """学生通过班级号加入班级"""
        student = await self._get_user(student_id)
        if student is None or student.role != UserRole.STUDENT:
            raise PermissionError("非学生账号，无法加入班级")

        enrollment_result = await self.db.execute(
            select(ClassEnrollmentModel).where(
                ClassEnrollmentModel.student_id == student_id
            )
        )
        if enrollment_result.scalar_one_or_none() is not None:
            raise ValueError("当前已加入班级，请先退出后再加入")

        class_model, _teacher = await self.lookup_class_by_code(code)
        if class_model is None:
            raise LookupError("班级号不存在")

        enrollment = ClassEnrollmentModel(
            class_id=class_model.id,
            student_id=student_id,
            joined_at=datetime.now(),
        )
        self.db.add(enrollment)
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise ValueError("当前已加入班级，请先退出后再加入") from exc
        return class_model

    async def leave_class(self, student_id: str) -> bool:
        """学生退出当前班级"""
        enrollment_result = await self.db.execute(
            select(ClassEnrollmentModel).where(
                ClassEnrollmentModel.student_id == student_id
            )
        )
        enrollment = enrollment_result.scalar_one_or_none()
        if enrollment is None:
            return False

        await self.db.delete(enrollment)
        await self.db.commit()
        return True

    async def get_student_class(
        self, student_id: str
    ) -> tuple[ClassModel | None, UserModel | None, int, datetime | None]:
        """获取学生当前班级（含教师信息、人数、加入时间）"""
        result = await self.db.execute(
            select(ClassModel, ClassEnrollmentModel.joined_at)
            .join(
                ClassEnrollmentModel,
                ClassEnrollmentModel.class_id == ClassModel.id,
            )
            .where(ClassEnrollmentModel.student_id == student_id)
        )
        row = result.one_or_none()
        if row is None:
            return None, None, 0, None

        class_model, joined_at = row

        # 获取教师信息
        teacher = await self._get_user(class_model.teacher_id)

        # 获取班级人数
        count_result = await self.db.execute(
            select(func.count(ClassEnrollmentModel.id)).where(
                ClassEnrollmentModel.class_id == class_model.id
            )
        )
        student_count = count_result.scalar() or 0

        return class_model, teacher, student_count, joined_at

    async def _generate_unique_code(self, length: int = 6) -> str:
        alphabet = string.ascii_uppercase + string.digits
        for _ in range(12):
            code = "".join(secrets.choice(alphabet) for _ in range(length))
            exists_result = await self.db.execute(
                select(ClassModel.id).where(ClassModel.code == code)
            )
            if exists_result.scalar_one_or_none() is None:
                return code
        raise RuntimeError("生成班级号失败，请稍后重试")

    async def _get_user(self, user_id: str) -> UserModel | None:
        result = await self.db.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        return result.scalar_one_or_none()
