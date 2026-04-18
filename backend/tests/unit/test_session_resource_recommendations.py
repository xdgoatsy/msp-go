"""Session fallback resource recommendation tests."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.domain.models.learning_session import MessageRole
from app.infrastructure.database.models import SessionMessageModel
from app.services import session_service as session_module
from app.services.session_service import (
    SessionService,
    _extract_resource_query,
    _message_requests_resource_recommendations,
)


def test_resource_request_detection_avoids_exercise_recommendations() -> None:
    assert _message_requests_resource_recommendations("推荐一些洛必达资料") is True
    assert _message_requests_resource_recommendations("有没有极限视频") is True
    assert _message_requests_resource_recommendations("推荐一道练习题") is False


def test_extract_resource_query_removes_request_words() -> None:
    assert _extract_resource_query("帮我推荐一些关于洛必达法则的视频资料") == "洛必达法则"
    assert _extract_resource_query("我想学习不定积分有没有资源推荐") == "不定积分"


@pytest.mark.asyncio
async def test_build_resource_recommendation_markdown_appends_search_links(
    monkeypatch,
) -> None:
    calls = []

    class FakeRepository:
        def __init__(self, db):
            self.db = db

        async def search_recommendations(self, **kwargs):
            calls.append(kwargs)
            return [
                {
                    "title": "洛必达法则视频",
                    "type": "video",
                    "url": None,
                    "topic": "洛必达法则",
                    "difficulty": 0.2,
                }
            ]

    monkeypatch.setattr(session_module, "ResourceRepository", FakeRepository)

    service = SessionService(Mock())
    markdown = await service._build_resource_recommendation_markdown(
        message="帮我推荐一些关于洛必达法则的视频资料",
        response_content="可以先理解洛必达法则的适用条件。",
        student_profile={"preferred_difficulty": 0.2},
    )

    assert calls[0]["query"] == "洛必达法则"
    assert calls[0]["resource_type"] == "video"
    assert calls[0]["difficulty"] == "beginner"
    assert "### 推荐资源" in markdown
    assert "[洛必达法则视频](/resources?search=" in markdown
    assert "视频 · 入门 · 洛必达法则" in markdown


@pytest.mark.asyncio
async def test_build_resource_recommendation_markdown_does_not_duplicate_heading() -> None:
    service = SessionService(Mock())

    markdown = await service._build_resource_recommendation_markdown(
        message="推荐资料",
        response_content="### 推荐资源\n1. [已有](https://example.com)",
        student_profile=None,
    )

    assert markdown == ""


@pytest.mark.asyncio
async def test_build_resource_recommendation_markdown_appends_when_heading_has_no_link(
    monkeypatch,
) -> None:
    class FakeRepository:
        def __init__(self, db):
            self.db = db

        async def search_recommendations(self, **kwargs):
            return [
                {
                    "title": "极限入门视频",
                    "type": "video",
                    "url": None,
                    "topic": "极限",
                    "difficulty": 0.2,
                }
            ]

    monkeypatch.setattr(session_module, "ResourceRepository", FakeRepository)

    service = SessionService(Mock())
    markdown = await service._build_resource_recommendation_markdown(
        message="推荐极限资料",
        response_content="### 推荐资源\n我会在后面帮你列出来。",
        student_profile=None,
    )

    assert "### 推荐资源" in markdown
    assert "[极限入门视频](/resources?search=" in markdown


@pytest.mark.asyncio
async def test_build_resource_recommendation_markdown_does_not_fabricate_links(
    monkeypatch,
) -> None:
    class EmptyRepository:
        def __init__(self, db):
            self.db = db

        async def search_recommendations(self, **kwargs):
            return []

    monkeypatch.setattr(session_module, "ResourceRepository", EmptyRepository)

    service = SessionService(Mock())
    markdown = await service._build_resource_recommendation_markdown(
        message="推荐极限资料",
        response_content="可以从定义开始复习。",
        student_profile=None,
    )

    assert "暂未在资源中心找到匹配资料" in markdown
    assert "](" not in markdown


@pytest.mark.asyncio
async def test_process_message_stream_yields_and_persists_fallback_recommendations(
    monkeypatch,
) -> None:
    async def fake_stream_workflow(**kwargs):
        yield {
            "type": "message",
            "content": "可以先看洛必达法则的适用条件。",
            "metadata": {"agent_type": "tutor", "streaming": True},
        }

    monkeypatch.setattr(
        "app.agents.workflow.graph.stream_workflow",
        fake_stream_workflow,
    )

    db = Mock()
    db.add = Mock()
    db.commit = AsyncMock()
    service = SessionService(db)
    service._get_session = AsyncMock(return_value=SimpleNamespace(is_active=True))
    service._load_student_profile = AsyncMock(return_value={"preferred_difficulty": 0.5})
    service._build_resource_recommendation_markdown = AsyncMock(
        return_value="\n\n### 推荐资源\n1. [洛必达法则视频](/resources?search=洛必达法则视频)"
    )

    events = [
        event
        async for event in service.process_message_stream(
            session_id="session-1",
            user_id="student-1",
            message="推荐洛必达资料",
        )
    ]

    chunk_contents = [
        event["content"] for event in events if event.get("type") == "chunk"
    ]
    assert chunk_contents == [
        "可以先看洛必达法则的适用条件。",
        "\n\n### 推荐资源\n1. [洛必达法则视频](/resources?search=洛必达法则视频)",
    ]
    assistant_messages = [
        call.args[0]
        for call in db.add.call_args_list
        if isinstance(call.args[0], SessionMessageModel)
        and call.args[0].role == MessageRole.ASSISTANT
    ]
    assert "### 推荐资源" in assistant_messages[-1].content
    assert events[-1]["type"] == "done"
