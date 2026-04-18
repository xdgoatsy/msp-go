"""
API v1 路由聚合

将所有 v1 版本的路由注册到统一的 router
"""

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    classes,
    exercise,
    mistakes,
    portrait,
    progress,
    questions,
    resources,
    session,
    teacher_stats,
    upload,
    xidian,
)
from app.api.v1.admin import ai_config as admin_ai_config
from app.api.v1.admin import bkt as admin_bkt
from app.api.v1.admin import inbox as admin_inbox
from app.api.v1.admin import knowledge as admin_knowledge
from app.api.v1.admin import security_logs as admin_security_logs
from app.api.v1.admin import settings as admin_settings
from app.api.v1.admin import stats as admin_stats
from app.api.v1.admin import users as admin_users

api_router = APIRouter()

# 注册各模块路由
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(session.router, prefix="/session", tags=["学习会话"])
api_router.include_router(exercise.router, prefix="/exercise", tags=["练习"])
api_router.include_router(mistakes.router, prefix="/mistakes", tags=["错题本"])
api_router.include_router(questions.router, prefix="/questions", tags=["题目管理"])
api_router.include_router(progress.router, prefix="/progress", tags=["学习进度"])
api_router.include_router(resources.router, prefix="/resources", tags=["资源中心"])
api_router.include_router(upload.router, prefix="/upload", tags=["文件上传"])
api_router.include_router(xidian.router, prefix="/xidian", tags=["西电教务"])
api_router.include_router(classes.router, prefix="/classes", tags=["班级管理"])
api_router.include_router(teacher_stats.router, prefix="/teacher", tags=["教师统计"])
api_router.include_router(portrait.router, prefix="/portrait", tags=["学生画像"])

# 管理员路由
api_router.include_router(
    admin_ai_config.router, prefix="/admin/ai-config", tags=["管理员-AI配置"]
)
api_router.include_router(
    admin_settings.router, prefix="/admin/settings", tags=["管理员-系统设置"]
)
api_router.include_router(
    admin_stats.router, prefix="/admin/stats", tags=["管理员-统计"]
)
api_router.include_router(
    admin_users.router, prefix="/admin/users", tags=["管理员-用户管理"]
)
api_router.include_router(
    admin_security_logs.router, prefix="/admin/security-logs", tags=["管理员-安全日志"]
)
api_router.include_router(
    admin_knowledge.router, prefix="/admin/knowledge", tags=["管理员-知识点管理"]
)
api_router.include_router(
    admin_inbox.router, prefix="/admin/inbox", tags=["管理员-信箱"]
)
api_router.include_router(
    admin_bkt.router, prefix="/admin/bkt", tags=["管理员-BKT参数"]
)
