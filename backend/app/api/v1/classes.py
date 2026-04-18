"""
班级管理 API

提供教师创建班级、学生加入/退出班级等接口
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUserId, DbSession, StudentUserId, TeacherUserId
from app.api.v1.schemas.classes import (
    ClassCreateRequest,
    ClassCreateResponse,
    ClassDetailResponse,
    ClassListItem,
    ClassListResponse,
    ClassLookupResponse,
    DisbandClassResponse,
    JoinClassRequest,
    JoinClassResponse,
    LeaveClassResponse,
    RemoveStudentResponse,
    StudentClassResponse,
    StudentItem,
)
from app.services.class_service import ClassService

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_class_service(db: DbSession) -> ClassService:
    """获取班级服务"""
    return ClassService(db=db)


ClassServiceDep = Annotated[ClassService, Depends(get_class_service)]


@router.post(
    "",
    response_model=ClassCreateResponse,
    summary="创建班级",
    description="教师创建班级并生成班级号",
)
async def create_class(
    data: ClassCreateRequest,
    teacher_id: TeacherUserId,
    service: ClassServiceDep,
) -> ClassCreateResponse:
    try:
        class_model = await service.create_class(
            teacher_id=teacher_id,
            name=data.name,
            description=data.description,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return ClassCreateResponse(
        success=True,
        message="班级创建成功",
        class_info=class_model,
    )


@router.get(
    "/teacher",
    response_model=ClassListResponse,
    summary="获取教师班级列表",
    description="教师查看自己创建的班级",
)
async def list_teacher_classes(
    teacher_id: TeacherUserId,
    service: ClassServiceDep,
) -> ClassListResponse:
    rows = await service.list_teacher_classes(teacher_id)
    items = [
        ClassListItem(
            id=row["class"].id,
            name=row["class"].name,
            code=row["class"].code,
            teacher_id=row["class"].teacher_id,
            description=row["class"].description,
            created_at=row["class"].created_at,
            student_count=row["student_count"],
        )
        for row in rows
    ]
    return ClassListResponse(items=items)


@router.get(
    "/teacher/{class_id}",
    response_model=ClassDetailResponse,
    summary="获取班级详情",
    description="教师查看班级详情和学生列表",
    responses={404: {"description": "班级不存在"}},
)
async def get_teacher_class_detail(
    class_id: str,
    teacher_id: TeacherUserId,
    service: ClassServiceDep,
) -> ClassDetailResponse:
    class_model, students, teacher = await service.get_teacher_class_detail(
        teacher_id=teacher_id, class_id=class_id
    )
    if class_model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="班级不存在或无权限访问",
        )

    from app.api.v1.schemas.classes import ClassBase

    class_info = ClassBase(
        id=class_model.id,
        name=class_model.name,
        code=class_model.code,
        teacher_id=class_model.teacher_id,
        description=class_model.description,
        created_at=class_model.created_at,
        teacher_name=teacher.display_name or teacher.username if teacher else None,
        teacher_email=teacher.email if teacher else None,
        teacher_avatar_url=teacher.avatar_url if teacher else None,
        student_count=len(students),
        joined_at=None,
    )

    return ClassDetailResponse(
        class_info=class_info,
        students=[
            StudentItem(
                id=student.id,
                username=student.username,
                email=student.email,
                display_name=student.display_name,
            )
            for student in students
        ],
    )


@router.delete(
    "/teacher/{class_id}/students/{student_id}",
    response_model=RemoveStudentResponse,
    summary="移除班级学生",
    description="教师将学生移出班级",
    responses={404: {"description": "班级或学生不存在"}},
)
async def remove_student(
    class_id: str,
    student_id: str,
    teacher_id: TeacherUserId,
    service: ClassServiceDep,
) -> RemoveStudentResponse:
    removed = await service.remove_student(teacher_id, class_id, student_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="班级或学生不存在",
        )
    return RemoveStudentResponse(success=True, message="学生已移除")


@router.delete(
    "/teacher/{class_id}",
    response_model=DisbandClassResponse,
    summary="解散班级",
    description="教师解散班级并移除所有学生",
    responses={404: {"description": "班级不存在"}},
)
async def disband_class(
    class_id: str,
    teacher_id: TeacherUserId,
    service: ClassServiceDep,
) -> DisbandClassResponse:
    disbanded = await service.disband_class(teacher_id, class_id)
    if not disbanded:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="班级不存在或无权限操作",
        )
    return DisbandClassResponse(success=True, message="班级已解散")


@router.get(
    "/lookup",
    response_model=ClassLookupResponse,
    summary="班级号查询",
    description="学生通过班级号查询班级",
)
async def lookup_class(
    _user_id: CurrentUserId,
    service: ClassServiceDep,
    code: str = Query(..., min_length=4, max_length=12, description="班级号"),
) -> ClassLookupResponse:
    class_model, teacher = await service.lookup_class_by_code(code)
    if class_model is None:
        return ClassLookupResponse(found=False, class_info=None, teacher_name=None)

    return ClassLookupResponse(
        found=True,
        class_info=class_model,
        teacher_name=teacher.display_name or teacher.username if teacher else None,
    )


@router.post(
    "/join",
    response_model=JoinClassResponse,
    summary="加入班级",
    description="学生通过班级号加入班级",
    responses={404: {"description": "班级号不存在"}, 409: {"description": "已加入班级"}},
)
async def join_class(
    data: JoinClassRequest,
    user_id: StudentUserId,
    service: ClassServiceDep,
) -> JoinClassResponse:
    try:
        class_model = await service.join_class(user_id, data.code)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return JoinClassResponse(
        success=True,
        message="已加入班级",
        class_info=class_model,
    )


@router.post(
    "/leave",
    response_model=LeaveClassResponse,
    summary="退出班级",
    description="学生退出当前班级",
)
async def leave_class(
    user_id: StudentUserId,
    service: ClassServiceDep,
) -> LeaveClassResponse:
    left = await service.leave_class(user_id)
    if not left:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未加入任何班级",
        )
    return LeaveClassResponse(success=True, message="已退出班级")


@router.get(
    "/me",
    response_model=StudentClassResponse,
    summary="获取当前班级",
    description="学生获取当前所在班级",
)
async def get_student_class(
    user_id: StudentUserId,
    service: ClassServiceDep,
) -> StudentClassResponse:
    class_model, teacher, student_count, joined_at = await service.get_student_class(
        user_id
    )
    if class_model is None:
        return StudentClassResponse(class_info=None)

    # 构建完整的班级信息
    from app.api.v1.schemas.classes import ClassBase

    class_info = ClassBase(
        id=class_model.id,
        name=class_model.name,
        code=class_model.code,
        teacher_id=class_model.teacher_id,
        description=class_model.description,
        created_at=class_model.created_at,
        teacher_name=teacher.display_name or teacher.username if teacher else None,
        teacher_email=teacher.email if teacher else None,
        teacher_avatar_url=teacher.avatar_url if teacher else None,
        student_count=student_count,
        joined_at=joined_at,
    )

    return StudentClassResponse(class_info=class_info)
