"""AI resource tool tests."""

from unittest.mock import AsyncMock

import pytest

from app.agents.tools import resource_tools


@pytest.mark.asyncio
async def test_search_resources_clamps_limit_and_normalizes_fields(monkeypatch) -> None:
    repositories = []

    class FakeRepository:
        def __init__(self, db):
            self.db = db
            self.search_recommendations = AsyncMock(
                return_value=[
                    {
                        "id": "resource-1",
                        "title": "洛必达法则视频",
                        "type": "video",
                        "url": None,
                        "chapter": "导数",
                        "topic": "洛必达法则",
                        "difficulty": 0.2,
                        "source": "资源中心",
                        "tags": ["极限"],
                    }
                ]
            )
            repositories.append(self)

    monkeypatch.setattr(resource_tools, "ResourceRepository", FakeRepository)

    result = await resource_tools.search_resources(
        db=object(),
        chapter="导数",
        topic="洛必达法则",
        resource_type="video",
        difficulty="beginner",
        limit=10,
    )

    repositories[0].search_recommendations.assert_awaited_once_with(
        query="洛必达法则",
        resource_type="video",
        chapter="导数",
        topic="洛必达法则",
        difficulty="beginner",
        limit=3,
    )
    assert result == [
        {
            "id": "resource-1",
            "title": "洛必达法则视频",
            "type": "video",
            "url": "/resources?search=%E6%B4%9B%E5%BF%85%E8%BE%BE%E6%B3%95%E5%88%99%E8%A7%86%E9%A2%91",
            "chapter": "导数",
            "topic": "洛必达法则",
            "difficulty": 0.2,
            "source": "资源中心",
            "tags": ["极限"],
        }
    ]


@pytest.mark.asyncio
async def test_search_resources_returns_empty_list_on_repository_error(monkeypatch) -> None:
    class FailingRepository:
        def __init__(self, db):
            self.db = db

        async def search_recommendations(self, **kwargs):
            raise RuntimeError("db down")

    monkeypatch.setattr(resource_tools, "ResourceRepository", FailingRepository)

    assert await resource_tools.search_resources(db=object(), topic="极限") == []


def test_build_resource_link_uses_external_url_before_fallback() -> None:
    assert (
        resource_tools.build_resource_link({"url": "example.com/video"})
        == "https://example.com/video"
    )
    assert resource_tools.build_resource_link({"url": "https://example.com/video"}) == (
        "https://example.com/video"
    )
    assert resource_tools.build_resource_link({"title": "泰勒展开"}) == (
        "/resources?search=%E6%B3%B0%E5%8B%92%E5%B1%95%E5%BC%80"
    )
