"""
学习进度 API Schema

定义进度概览、统计、班级排名等接口的请求/响应结构
"""

from pydantic import BaseModel, Field


class ClassRankingResponse(BaseModel):
    """班级排名响应"""

    in_class: bool = Field(..., description="是否已加入班级")
    rank: int | None = Field(None, description="当前名次（1-based），未加入班级时为 null")
    total: int = Field(0, description="班级总人数")
    percentile: float | None = Field(
        None,
        description="超过班级中其他学生的百分比（0-100），未加入或无人时为 null",
    )
