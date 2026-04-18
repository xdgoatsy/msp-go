"""
班级管理 API Schema

定义班级创建、查询、学生加入/退出等接口的数据结构
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ClassBase(BaseModel):
    """班级基础信息"""

    id: str = Field(..., description="班级 ID")
    name: str = Field(..., description="班级名称")
    code: str = Field(..., description="班级号")
    teacher_id: str = Field(..., description="教师 ID")
    description: str | None = Field(None, description="班级描述")
    created_at: datetime = Field(..., description="创建时间")
    teacher_name: str | None = Field(None, description="教师姓名")
    teacher_email: str | None = Field(None, description="教师邮箱")
    teacher_avatar_url: str | None = Field(None, description="教师头像")
    student_count: int | None = Field(None, description="班级人数")
    joined_at: datetime | None = Field(None, description="加入时间")

    model_config = {"from_attributes": True}


class ClassListItem(ClassBase):
    """班级列表项"""

    student_count: int = Field(0, description="学生数量")


class ClassListResponse(BaseModel):
    """班级列表响应"""

    items: list[ClassListItem] = Field(..., description="班级列表")


class StudentItem(BaseModel):
    """班级学生信息"""

    id: str = Field(..., description="学生 ID")
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱")
    display_name: str | None = Field(None, description="显示名称")


class ClassDetailResponse(BaseModel):
    """班级详情响应"""

    class_info: ClassBase = Field(..., description="班级信息")
    students: list[StudentItem] = Field(..., description="学生列表")


class ClassCreateRequest(BaseModel):
    """创建班级请求"""

    name: str = Field(..., min_length=2, max_length=200, description="班级名称")
    description: str | None = Field(None, max_length=500, description="班级描述")


class ClassCreateResponse(BaseModel):
    """创建班级响应"""

    success: bool = Field(True, description="是否成功")
    message: str = Field(..., description="消息")
    class_info: ClassBase = Field(..., description="班级信息")


class ClassLookupResponse(BaseModel):
    """班级号查询响应"""

    found: bool = Field(..., description="是否找到班级")
    class_info: ClassBase | None = Field(None, description="班级信息")
    teacher_name: str | None = Field(None, description="教师名称")


class JoinClassRequest(BaseModel):
    """加入班级请求"""

    code: str = Field(..., min_length=4, max_length=12, description="班级号")


class JoinClassResponse(BaseModel):
    """加入班级响应"""

    success: bool = Field(True, description="是否成功")
    message: str = Field(..., description="消息")
    class_info: ClassBase = Field(..., description="班级信息")


class LeaveClassResponse(BaseModel):
    """退出班级响应"""

    success: bool = Field(True, description="是否成功")
    message: str = Field(..., description="消息")


class StudentClassResponse(BaseModel):
    """学生当前班级响应"""

    class_info: ClassBase | None = Field(None, description="当前班级")


class RemoveStudentResponse(BaseModel):
    """移除学生响应"""

    success: bool = Field(True, description="是否成功")
    message: str = Field(..., description="消息")


class DisbandClassResponse(BaseModel):
    """解散班级响应"""

    success: bool = Field(True, description="是否成功")
    message: str = Field(..., description="消息")
