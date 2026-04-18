"""Question API unit tests."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

from app.api.v1 import questions as questions_api
from app.api.v1.schemas.questions import BatchOperationRequest, QuestionUpdateRequest
from app.domain.models.content import ContentStatus, ContentType
from app.domain.models.student import UserRole, UserStatus
from app.infrastructure.database.models import ContentModel, UserModel
from app.infrastructure.repositories import (
    content_repository as content_repository_module,
)


def _build_content(
    *,
    content_id: str = "content-1",
    content_type: ContentType = ContentType.PROBLEM,
    owner_id: str = "teacher-1",
) -> ContentModel:
    now = datetime(2026, 4, 6, 12, 0, 0)
    return ContentModel(
        id=content_id,
        type=content_type,
        owner_teacher_id=owner_id,
        status=ContentStatus.PUBLISHED,
        title="不定积分",
        body="题目内容",
        difficulty=0.5,
        concept_ids=[],
        tags=[],
        meta={
            "type": "short_answer",
            "answer": "1",
            "answer_type": "expression",
            "hints": [],
            "solution_steps": [],
            "estimated_time_seconds": 300,
        },
        created_at=now,
        updated_at=now,
        published_at=now,
    )


def _build_teacher() -> UserModel:
    now = datetime(2026, 4, 6, 12, 0, 0)
    return UserModel(
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


@pytest.mark.asyncio
async def test_list_questions_always_scopes_query_to_problem_content(monkeypatch) -> None:
    repo = Mock()
    repo.list_by_owner_with_stats = AsyncMock(
        return_value=([(_build_content(), 0, 0.0)], 1)
    )
    monkeypatch.setattr(
        content_repository_module, "ContentRepository", Mock(return_value=repo)
    )

    result = await questions_api.list_questions(
        teacher_id="teacher-1",
        db=Mock(),
        type="short_answer",
    )

    kwargs = repo.list_by_owner_with_stats.await_args.kwargs
    assert kwargs["type"] == ContentType.PROBLEM
    assert kwargs["meta_type"] == "short_answer"
    assert result.total == 1
    assert result.items[0].id == "content-1"


@pytest.mark.asyncio
async def test_question_stats_only_count_problem_content(monkeypatch) -> None:
    repo = Mock()
    repo.get_stats_by_owner = AsyncMock(
        return_value={
            "total_count": 1,
            "published_count": 1,
            "draft_count": 0,
            "archived_count": 0,
            "avg_difficulty": 0.5,
            "total_usage": 0,
            "avg_correct_rate": 0.0,
        }
    )
    monkeypatch.setattr(
        content_repository_module, "ContentRepository", Mock(return_value=repo)
    )

    result = await questions_api.get_question_stats(
        teacher_id="teacher-1",
        db=Mock(),
    )

    repo.get_stats_by_owner.assert_awaited_once_with(
        "teacher-1", type=ContentType.PROBLEM
    )
    assert result.total == 1


@pytest.mark.asyncio
async def test_batch_publish_only_updates_problem_content(monkeypatch) -> None:
    repo = Mock()
    repo.batch_update_status = AsyncMock(return_value=1)
    monkeypatch.setattr(
        content_repository_module, "ContentRepository", Mock(return_value=repo)
    )
    db = Mock()
    db.commit = AsyncMock()

    result = await questions_api.batch_publish_questions(
        BatchOperationRequest(question_ids=["question-1", "resource-1"]),
        teacher_id="teacher-1",
        db=db,
    )

    assert repo.batch_update_status.await_args.kwargs["type"] == ContentType.PROBLEM
    assert result.success == 1
    assert result.failed == 1


@pytest.mark.asyncio
async def test_update_question_rejects_non_problem_content(monkeypatch) -> None:
    service = Mock()
    service.get_content = AsyncMock(
        return_value=_build_content(
            content_id="resource-1",
            content_type=ContentType.ARTICLE,
        )
    )
    service.update_content = AsyncMock()
    monkeypatch.setattr(
        questions_api, "_get_user", AsyncMock(return_value=_build_teacher())
    )
    monkeypatch.setattr(questions_api, "ContentService", Mock(return_value=service))

    with pytest.raises(HTTPException) as exc_info:
        await questions_api.update_question(
            question_id="resource-1",
            data=QuestionUpdateRequest(title="新标题"),
            teacher_id="teacher-1",
            db=Mock(),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "该内容不是题目类型"
    service.update_content.assert_not_awaited()
