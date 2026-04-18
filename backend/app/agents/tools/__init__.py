"""
AI 智能体工具模块

提供智能体可以调用的工具函数
"""

from app.agents.tools.resource_tools import get_resource_by_id, search_resources

__all__ = ["search_resources", "get_resource_by_id"]
