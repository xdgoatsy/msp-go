"""
系统配置服务

提供系统配置的业务逻辑
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)

logger = logging.getLogger(__name__)

# 配置键常量
ALLOW_STUDENT_REGISTRATION = "allow_student_registration"
ALLOW_TEACHER_REGISTRATION = "allow_teacher_registration"
SYSTEM_NAME = "system_name"
SYSTEM_DESCRIPTION = "system_description"


class SystemSettingService:
    """系统配置服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SystemSettingRepository(db)

    async def get_registration_settings(self) -> dict:
        """
        获取注册配置

        Returns:
            {
                "allow_student": bool,
                "allow_teacher": bool
            }
        """
        settings = await self.repo.get_by_keys(
            [ALLOW_STUDENT_REGISTRATION, ALLOW_TEACHER_REGISTRATION]
        )

        result = {
            "allow_student": True,  # 默认允许
            "allow_teacher": True,  # 默认允许
        }

        for setting in settings:
            if setting.key == ALLOW_STUDENT_REGISTRATION:
                result["allow_student"] = setting.value.lower() == "true"
            elif setting.key == ALLOW_TEACHER_REGISTRATION:
                result["allow_teacher"] = setting.value.lower() == "true"

        return result

    async def update_registration_settings(
        self, allow_student: bool, allow_teacher: bool
    ) -> dict:
        """
        更新注册配置

        Args:
            allow_student: 是否允许学生注册
            allow_teacher: 是否允许教师注册

        Returns:
            更新后的配置
        """
        await self.repo.set(
            key=ALLOW_STUDENT_REGISTRATION,
            value=str(allow_student).lower(),
            description="是否允许学生注册",
        )

        await self.repo.set(
            key=ALLOW_TEACHER_REGISTRATION,
            value=str(allow_teacher).lower(),
            description="是否允许教师注册",
        )

        await self.db.commit()

        logger.info(
            f"注册配置已更新: allow_student={allow_student}, allow_teacher={allow_teacher}"
        )

        return {
            "allow_student": allow_student,
            "allow_teacher": allow_teacher,
        }

    async def is_student_registration_allowed(self) -> bool:
        """检查是否允许学生注册"""
        setting = await self.repo.get(ALLOW_STUDENT_REGISTRATION)
        if setting is None:
            return True  # 默认允许
        return setting.value.lower() == "true"

    async def is_teacher_registration_allowed(self) -> bool:
        """检查是否允许教师注册"""
        setting = await self.repo.get(ALLOW_TEACHER_REGISTRATION)
        if setting is None:
            return True  # 默认允许
        return setting.value.lower() == "true"

    async def get_general_settings(self) -> dict:
        """
        获取系统基本信息

        Returns:
            {
                "system_name": str,
                "system_description": str,
                "system_version": str (只读，来自 config)
            }
        """
        from app.config import settings as app_settings

        db_settings = await self.repo.get_by_keys(
            [SYSTEM_NAME, SYSTEM_DESCRIPTION]
        )

        result = {
            "system_name": app_settings.app_name,
            "system_description": "",
            "system_version": app_settings.app_version,
        }

        for setting in db_settings:
            if setting.key == SYSTEM_NAME:
                result["system_name"] = setting.value
            elif setting.key == SYSTEM_DESCRIPTION:
                result["system_description"] = setting.value

        return result

    async def update_general_settings(
        self, system_name: str, system_description: str
    ) -> dict:
        """
        更新系统基本信息

        Args:
            system_name: 系统名称
            system_description: 系统描述

        Returns:
            更新后的基本信息
        """
        from app.config import settings as app_settings

        await self.repo.set(
            key=SYSTEM_NAME,
            value=system_name,
            description="系统名称",
        )

        await self.repo.set(
            key=SYSTEM_DESCRIPTION,
            value=system_description,
            description="系统描述",
        )

        await self.db.commit()

        logger.info(f"系统基本信息已更新: name={system_name}")

        return {
            "system_name": system_name,
            "system_description": system_description,
            "system_version": app_settings.app_version,
        }
