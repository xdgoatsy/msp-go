"""
管理员系统设置接口

提供系统配置的管理功能
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.api.deps import AdminUserId, DbSession
from app.api.v1.schemas.database import (
    DatabaseMonitorResponse,
    DataExportRequest,
    DataExportResponse,
    DataImportResponse,
    ExportableTableItem,
    ExportableTablesResponse,
)
from app.services.database_management_service import (
    EXPORTABLE_TABLES,
    DatabaseManagementService,
)
from app.services.system_setting_service import SystemSettingService

router = APIRouter()


# =============================================================================
# 请求/响应模型
# =============================================================================


class RegistrationSettingsResponse(BaseModel):
    """注册配置响应"""

    allow_student: bool
    allow_teacher: bool


class RegistrationSettingsRequest(BaseModel):
    """注册配置请求"""

    allow_student: bool
    allow_teacher: bool


class GeneralSettingsResponse(BaseModel):
    """基本信息响应"""

    system_name: str
    system_description: str
    system_version: str


class GeneralSettingsRequest(BaseModel):
    """基本信息更新请求"""

    system_name: str = Field(..., min_length=1, max_length=100)
    system_description: str = Field("", max_length=500)


# =============================================================================
# 依赖注入
# =============================================================================


def get_system_setting_service(db: DbSession) -> SystemSettingService:
    """获取系统配置服务"""
    return SystemSettingService(db)


SystemSettingServiceDep = Annotated[
    SystemSettingService, Depends(get_system_setting_service)
]


def get_database_management_service(db: DbSession) -> DatabaseManagementService:
    """获取数据库管理服务"""
    return DatabaseManagementService(db)


DatabaseManagementServiceDep = Annotated[
    DatabaseManagementService, Depends(get_database_management_service)
]


# =============================================================================
# API 端点
# =============================================================================


@router.get("/registration", response_model=RegistrationSettingsResponse)
async def get_registration_settings(
    _admin_id: AdminUserId,
    service: SystemSettingServiceDep,
) -> RegistrationSettingsResponse:
    """
    获取注册配置

    需要管理员权限
    """
    settings = await service.get_registration_settings()
    return RegistrationSettingsResponse(**settings)


@router.put("/registration", response_model=RegistrationSettingsResponse)
async def update_registration_settings(
    request: RegistrationSettingsRequest,
    _admin_id: AdminUserId,
    service: SystemSettingServiceDep,
) -> RegistrationSettingsResponse:
    """
    更新注册配置

    需要管理员权限
    """
    settings = await service.update_registration_settings(
        allow_student=request.allow_student,
        allow_teacher=request.allow_teacher,
    )
    return RegistrationSettingsResponse(**settings)


@router.get("/general", response_model=GeneralSettingsResponse)
async def get_general_settings(
    _admin_id: AdminUserId,
    service: SystemSettingServiceDep,
) -> GeneralSettingsResponse:
    """
    获取系统基本信息

    需要管理员权限
    """
    settings = await service.get_general_settings()
    return GeneralSettingsResponse(**settings)


@router.put("/general", response_model=GeneralSettingsResponse)
async def update_general_settings(
    request: GeneralSettingsRequest,
    _admin_id: AdminUserId,
    service: SystemSettingServiceDep,
) -> GeneralSettingsResponse:
    """
    更新系统基本信息

    需要管理员权限
    """
    settings = await service.update_general_settings(
        system_name=request.system_name,
        system_description=request.system_description,
    )
    return GeneralSettingsResponse(**settings)


# =============================================================================
# 数据库管理端点
# =============================================================================


@router.get(
    "/database/exportable-tables",
    response_model=ExportableTablesResponse,
)
async def get_exportable_tables(
    _admin_id: AdminUserId,
) -> ExportableTablesResponse:
    """
    获取可导出的表列表

    需要管理员权限
    """
    tables = [
        ExportableTableItem(name=name, display_name=display)
        for name, display in EXPORTABLE_TABLES.items()
    ]
    return ExportableTablesResponse(tables=tables)


@router.post("/database/export", response_model=DataExportResponse)
async def export_database(
    request: DataExportRequest,
    admin_id: AdminUserId,
    service: DatabaseManagementServiceDep,
) -> DataExportResponse:
    """
    导出数据库数据

    将选定的表数据导出为 JSON 格式（Base64 编码）。
    需要管理员权限。
    """
    try:
        result = await service.export_data(
            tables=request.tables,
            admin_id=admin_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return DataExportResponse(**result)


@router.post("/database/import", response_model=DataImportResponse)
async def import_database(
    admin_id: AdminUserId,
    service: DatabaseManagementServiceDep,
    file: Annotated[UploadFile, File(..., description="JSON 备份文件")],
) -> DataImportResponse:
    """
    导入数据库数据

    从 JSON 备份文件恢复数据，使用 ON CONFLICT DO NOTHING 策略。
    需要管理员权限。
    """
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="请上传 JSON 格式的备份文件")

    content = await file.read()
    if len(content) > 100 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小不能超过 100MB")

    try:
        result = await service.import_data(
            file_content=content,
            admin_id=admin_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return DataImportResponse(**result)


@router.get("/database/monitor", response_model=DatabaseMonitorResponse)
async def get_database_monitor(
    _admin_id: AdminUserId,
    service: DatabaseManagementServiceDep,
) -> DatabaseMonitorResponse:
    """
    获取数据库监控数据

    包含连接池状态、表统计、数据库概览。
    需要管理员权限。
    """
    result = await service.get_database_monitor()
    return DatabaseMonitorResponse(**result)
