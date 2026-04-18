"""
资源查询工具

为 AI 智能体提供资源中心查询能力
"""

import logging
from typing import Any
from urllib.parse import quote

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.repositories.resource_repository import ResourceRepository

logger = logging.getLogger(__name__)


def build_resource_link(resource: dict[str, Any]) -> str:
    """生成推荐资源链接：优先外部资源 URL，缺失时回落到资源中心搜索页。"""
    url = resource.get("url")
    if isinstance(url, str) and url.strip():
        normalized_url = url.strip()
        if normalized_url.startswith(("http://", "https://", "/")):
            return normalized_url
        return f"https://{normalized_url}"

    query = (
        resource.get("title")
        or resource.get("topic")
        or resource.get("chapter")
        or "学习资源"
    )
    return f"/resources?search={quote(str(query).strip())}"


async def search_resources(
    db: AsyncSession,
    chapter: str | None = None,
    topic: str | None = None,
    resource_type: str | None = None,
    difficulty: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    搜索学习资源

    参数：
    - db: 数据库会话
    - chapter: 章节名称（如 "极限与连续"）
    - topic: 主题关键词（如 "洛必达法则"）
    - resource_type: 资源类型（"video" 或 "document"）
    - difficulty: 难度级别（"beginner", "intermediate", "advanced"）
    - limit: 返回数量限制（默认 5，最大 3）

    返回：资源列表，每个资源包含 id, title, type, url, chapter, topic, difficulty, source, tags
    """
    try:
        # 限制返回数量
        limit = max(1, min(limit, 3))

        repository = ResourceRepository(db)

        resources = await repository.search_recommendations(
            query=topic,
            resource_type=resource_type,
            chapter=chapter,
            topic=topic,
            difficulty=difficulty,
            limit=limit,
        )

        # 简化返回格式（LLM 友好）
        simplified_resources = []
        for resource in resources:
            simplified = {
                "id": resource.get("id"),
                "title": resource.get("title"),
                "type": resource.get("type"),
                "url": build_resource_link(resource),
                "chapter": resource.get("chapter"),
                "topic": resource.get("topic"),
                "difficulty": resource.get("difficulty"),
                "source": resource.get("source"),
                "tags": resource.get("tags"),
            }

            # 过滤掉 None 值
            simplified = {k: v for k, v in simplified.items() if v is not None}
            simplified_resources.append(simplified)

        logger.info(
            f"Tool search_resources: found {len(simplified_resources)} resources",
            extra={
                "chapter": chapter,
                "topic": topic,
                "resource_type": resource_type,
                "difficulty": difficulty,
            },
        )

        return simplified_resources

    except Exception as e:
        logger.error(f"Error in search_resources tool: {e}", exc_info=True)
        return []


async def get_resource_by_id(
    db: AsyncSession, resource_id: str
) -> dict[str, Any] | None:
    """
    获取资源详细信息

    参数：
    - db: 数据库会话
    - resource_id: 资源 ID

    返回：资源详情，包含完整的 body（内容描述）
    """
    try:
        repository = ResourceRepository(db)

        # 获取资源详情
        resource = await repository.get_resource_by_id(resource_id, user_id=None)

        if not resource:
            logger.warning(f"Tool get_resource_by_id: resource not found: {resource_id}")
            return None

        # 简化返回格式
        simplified = {
            "id": resource.get("id"),
            "title": resource.get("title"),
            "type": resource.get("type"),
            "body": resource.get("body"),
            "url": build_resource_link(resource),
            "chapter": resource.get("chapter"),
            "topic": resource.get("topic"),
            "difficulty": resource.get("difficulty"),
            "duration": resource.get("duration"),
            "pages": resource.get("pages"),
            "tags": resource.get("tags"),
        }

        # 过滤掉 None 值
        simplified = {k: v for k, v in simplified.items() if v is not None}

        logger.info(
            f"Tool get_resource_by_id: found resource {resource_id}",
            extra={"resource_title": simplified.get("title")},
        )

        return simplified

    except Exception as e:
        logger.error(f"Error in get_resource_by_id tool: {e}", exc_info=True)
        return None
