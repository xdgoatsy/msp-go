"""Resource repository unit tests."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.dialects import postgresql

from app.domain.models.content import AssetKind, ContentStatus, ContentType
from app.domain.models.student import UserRole, UserStatus
from app.infrastructure.database.models import (
    ContentAssetModel,
    ContentModel,
    UserModel,
)
from app.infrastructure.repositories.resource_repository import ResourceRepository


class _FakeScalarResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class _FakeExecuteResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return _FakeScalarResult(self._items)


def _build_loaded_content(
    content_id: str = "content-1",
    title: str = "Calculus video",
) -> ContentModel:
    now = datetime(2026, 4, 6, 12, 0, 0)
    content = ContentModel(
        id=content_id,
        type=ContentType.VIDEO,
        owner_teacher_id="teacher-1",
        status=ContentStatus.PUBLISHED,
        title=title,
        body="",
        difficulty=0.5,
        tags=[],
        meta={
            "chapter": "Chapter 1",
            "topic": "Limits",
            "source": "Bilibili",
            "duration": None,
            "pages": None,
            "storage_type": "external",
            "views": 0,
            "likes": 0,
        },
        created_at=now,
        updated_at=now,
        published_at=now,
    )
    content.assets = [
        ContentAssetModel(
            id="asset-1",
            content_id=content_id,
            kind=AssetKind.VIDEO,
            url="https://example.com/video",
            meta={"storage_type": "external"},
            created_at=now,
        )
    ]
    content.owner = UserModel(
        id="teacher-1",
        username="teacher",
        email="teacher@example.com",
        hashed_password="hashed",
        role=UserRole.TEACHER,
        status=UserStatus.ACTIVE,
        display_name="Teacher",
        created_at=now,
        updated_at=now,
    )
    return content


@pytest.mark.asyncio
async def test_create_resource_reloads_relationships_before_response() -> None:
    db = Mock()
    db.commit = AsyncMock()
    repository = ResourceRepository(db)

    loaded_content = _build_loaded_content()
    repository._get_content_for_response = AsyncMock(return_value=loaded_content)

    result = await repository.create_resource(
        "teacher-1",
        {
            "title": "Calculus video",
            "type": "video",
            "body": "",
            "chapter": "Chapter 1",
            "topic": "Limits",
            "tags": [],
            "difficulty": 0.5,
            "storage_type": "external",
            "url": "https://example.com/video",
            "duration": None,
            "pages": None,
            "source": "Bilibili",
        },
    )

    db.commit.assert_awaited_once()
    repository._get_content_for_response.assert_awaited_once()
    assert result["url"] == "https://example.com/video"
    assert result["owner_name"] == "Teacher"


@pytest.mark.asyncio
async def test_update_resource_reloads_relationships_before_response() -> None:
    db = Mock()
    db.commit = AsyncMock()
    existing_content = _build_loaded_content(title="Old title")
    db.execute = AsyncMock(
        return_value=Mock(scalar_one_or_none=Mock(return_value=existing_content))
    )
    repository = ResourceRepository(db)

    loaded_content = _build_loaded_content(title="New title")
    repository._get_content_for_response = AsyncMock(return_value=loaded_content)

    result = await repository.update_resource(
        "content-1",
        "teacher-1",
        {"title": "New title", "topic": "Derivatives"},
    )

    db.commit.assert_awaited_once()
    repository._get_content_for_response.assert_awaited_once_with("content-1")
    assert existing_content.title == "New title"
    assert result["title"] == "New title"


@pytest.mark.asyncio
async def test_search_recommendations_uses_fuzzy_fields_and_difficulty_filter() -> None:
    db = Mock()
    executed_statements = []

    async def execute(stmt):
        executed_statements.append(stmt)
        return _FakeExecuteResult([_build_loaded_content(title="洛必达法则视频")])

    db.execute = AsyncMock(side_effect=execute)
    repository = ResourceRepository(db)

    result = await repository.search_recommendations(
        query="洛必达",
        chapter="导数",
        topic="极限",
        resource_type="video",
        difficulty="beginner",
        limit=50,
    )

    sql = str(executed_statements[0].compile(dialect=postgresql.dialect()))
    assert result[0]["title"] == "洛必达法则视频"
    assert executed_statements[0]._limit_clause.value == 3
    assert "contents.status" in sql
    assert "contents.deleted_at IS NULL" in sql
    assert "contents.type IN" in sql
    assert "contents.difficulty >=" in sql
    assert "contents.difficulty <=" in sql
    assert "contents.title ILIKE" in sql
    assert "contents.body ILIKE" in sql
    assert "contents.meta" in sql
    assert "CAST(contents.tags AS VARCHAR) ILIKE" in sql


@pytest.mark.asyncio
async def test_get_resources_keeps_exact_topic_filter_for_list_queries() -> None:
    db = Mock()
    executed_statements = []

    async def execute(stmt):
        executed_statements.append(stmt)
        if len(executed_statements) == 1:
            return Mock(scalar=Mock(return_value=0))
        return _FakeExecuteResult([])

    db.execute = AsyncMock(side_effect=execute)
    repository = ResourceRepository(db)
    repository._get_user_favorites = AsyncMock(return_value=set())

    resources, total = await repository.get_resources(
        user_id="user-1",
        topic="Limits",
    )

    data_sql = str(executed_statements[1].compile(dialect=postgresql.dialect()))
    assert resources == []
    assert total == 0
    assert "ILIKE" not in data_sql
    assert "contents.meta" in data_sql
