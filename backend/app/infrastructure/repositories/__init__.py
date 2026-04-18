"""
数据仓储包

提供数据访问抽象层
"""

from app.infrastructure.repositories.base import BaseRepository
from app.infrastructure.repositories.content_repository import ContentRepository

__all__ = [
    "BaseRepository",
    "ContentRepository",
]
