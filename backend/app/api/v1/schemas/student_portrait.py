"""
学生画像 API Schema

定义学生画像相关的响应模型
"""

from datetime import datetime

from pydantic import BaseModel


class StudentPortraitResponse(BaseModel):
    """学生画像响应"""

    student_id: str
    portrait_content: str | None = None
    portrait_generated_at: datetime | None = None
    portrait_version: int = 0
    total_exercises: int = 0
    correct_rate: float = 0.0
    total_study_time_minutes: int = 0
    has_content: bool = False


class GeneratePortraitResponse(BaseModel):
    """生成画像响应"""

    portrait_content: str
    portrait_generated_at: datetime
    portrait_version: int


class ClearPortraitResponse(BaseModel):
    """清除画像响应"""

    cleared: bool
    message: str
