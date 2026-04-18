"""
管理员 API 模块
"""

from app.api.v1.admin.ai_config import router as ai_config_router
from app.api.v1.admin.security_logs import router as security_logs_router
from app.api.v1.admin.users import router as users_router

__all__ = ["ai_config_router", "users_router", "security_logs_router"]
