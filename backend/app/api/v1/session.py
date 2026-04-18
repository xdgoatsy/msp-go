"""
学习会话接口

处理学生与多智能体系统的交互会话
"""

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Query
from sse_starlette.sse import EventSourceResponse

from app.api.deps import CurrentUserId, DbSession
from app.api.v1.schemas.session import (
    BatchDeleteRequest,
    BatchDeleteResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    DeleteSessionResponse,
    HistoryResponse,
    MessageResponse,
    SendMessageRequest,
    SessionListResponse,
    SessionResponse,
    TaskCancelResponse,
    UpdateModeRequest,
    UpdateModeResponse,
)
from app.core.json_utils import json_dumps
from app.services.session_service import get_session_service
from app.services.task_manager import TaskManager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/start", response_model=CreateSessionResponse)
async def start_session(
    db: DbSession,
    user_id: CurrentUserId,
    request: CreateSessionRequest | None = None,
) -> CreateSessionResponse:
    """
    开始学习会话

    创建新的学习会话，返回会话信息和欢迎消息

    Args:
        request: 创建会话请求（可选）

    Returns:
        会话信息和欢迎消息
    """
    service = get_session_service(db)

    topic = request.topic if request else None
    mode = request.mode if request else "chat"

    result = await service.create_session(
        user_id=user_id,
        topic=topic,
        mode=mode,
    )

    return CreateSessionResponse(
        session_id=result["session_id"],
        user_id=result["user_id"],
        topic=result["topic"],
        mode=result["mode"],
        status=result["status"],
        created_at=result["created_at"],
        welcome_message=MessageResponse(
            id=result["welcome_message"]["id"],
            role=result["welcome_message"]["role"],
            content=result["welcome_message"]["content"],
            agent=result["welcome_message"]["agent"],
            timestamp=result["welcome_message"]["timestamp"],
            attachments=result["welcome_message"]["attachments"],
        ),
    )


@router.post("/{session_id}/chat")
async def chat_stream(
    session_id: str,
    db: DbSession,
    user_id: CurrentUserId,
    request: SendMessageRequest,
) -> EventSourceResponse:
    """
    流式聊天 (SSE)

    发送消息并以 SSE 流式返回 AI 响应

    SSE 事件格式:
    - event: message, data: {"type": "chunk", "content": "...", "agent": "tutor", "message_id": "..."}
    - event: message, data: {"type": "done", "message_id": "...", "agent": "tutor"}
    - event: error, data: {"type": "error", "code": "...", "message": "..."}

    Args:
        session_id: 会话 ID
        request: 发送消息请求

    Returns:
        SSE 事件流
    """
    service = get_session_service(db)

    # 生成任务 ID
    task_id = TaskManager.generate_task_id()

    async def event_generator():
        """SSE 事件生成器"""
        task = asyncio.current_task()
        if task is not None:
            TaskManager.register_task(
                task=task,
                task_id=task_id,
                session_id=session_id,
                user_id=user_id,
            )

        try:
            # 发送任务 ID（用于取消）
            yield {
                "event": "task_info",
                "data": json_dumps({"task_id": task_id}),
            }

            # 处理消息流
            async for chunk in service.process_message_stream(
                session_id=session_id,
                user_id=user_id,
                message=request.message,
                attachments=request.attachments,
            ):
                event_type = chunk.get("type", "message")

                if event_type == "error":
                    yield {
                        "event": "error",
                        "data": json_dumps(chunk),
                    }
                elif event_type == "cancelled":
                    yield {
                        "event": "cancelled",
                        "data": json_dumps(chunk),
                    }
                else:
                    yield {
                        "event": "message",
                        "data": json_dumps(chunk),
                    }

        except asyncio.CancelledError:
            logger.info("SSE 流被取消: session_id=%s, task_id=%s", session_id, task_id)
            yield {
                "event": "cancelled",
                "data": json_dumps({"type": "cancelled", "task_id": task_id}),
            }
        except Exception as e:
            logger.error("SSE 流错误: %s", e, exc_info=True)
            yield {
                "event": "error",
                "data": json_dumps({
                    "type": "error",
                    "code": "STREAM_ERROR",
                    "message": "流式处理失败，请稍后重试",
                }),
            }
        finally:
            # 清理任务
            TaskManager.cleanup_task(task_id)

    # 创建 SSE 响应
    return EventSourceResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        },
    )


@router.get("/{session_id}/history", response_model=HistoryResponse)
async def get_history(
    session_id: str,
    db: DbSession,
    user_id: CurrentUserId,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> HistoryResponse:
    """
    获取会话历史

    返回指定会话的历史消息列表

    Args:
        session_id: 会话 ID
        limit: 返回数量限制 (1-100)
        offset: 偏移量

    Returns:
        历史消息列表
    """
    service = get_session_service(db)

    result = await service.get_history(
        session_id=session_id,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )

    return HistoryResponse(
        messages=[
            MessageResponse(
                id=msg["id"],
                role=msg["role"],
                content=msg["content"],
                agent=msg["agent"],
                timestamp=msg["timestamp"],
                attachments=msg["attachments"],
            )
            for msg in result["messages"]
        ],
        total=result["total"],
        has_more=result["has_more"],
    )


@router.get("/list", response_model=SessionListResponse)
async def get_sessions(
    db: DbSession,
    user_id: CurrentUserId,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SessionListResponse:
    """
    获取会话列表

    返回当前用户的所有会话

    Args:
        limit: 返回数量限制 (1-50)
        offset: 偏移量

    Returns:
        会话列表
    """
    service = get_session_service(db)

    result = await service.get_sessions_list(
        user_id=user_id,
        limit=limit,
        offset=offset,
    )

    return SessionListResponse(
        sessions=[
            SessionResponse(
                session_id=s["session_id"],
                user_id=s["user_id"],
                topic=s["topic"],
                status=s["status"],
                started_at=s["started_at"],
                ended_at=s["ended_at"],
                message_count=s["message_count"],
            )
            for s in result["sessions"]
        ],
        total=result["total"],
    )


@router.post("/{session_id}/end")
async def end_session(
    session_id: str,
    db: DbSession,
    user_id: CurrentUserId,
) -> dict:
    """
    结束会话

    将会话标记为已结束

    Args:
        session_id: 会话 ID

    Returns:
        操作结果
    """
    service = get_session_service(db)

    # 先校验会话归属，再取消该会话的活跃任务（防越权副作用）
    session = await service._get_session(session_id, user_id)
    if session is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="会话不存在或无权访问")

    cancelled_count = TaskManager.cancel_session_tasks(session_id)
    if cancelled_count > 0:
        logger.info("已取消 %s 个活跃任务: session_id=%s", cancelled_count, session_id)

    result = await service.end_session(
        session_id=session_id,
        user_id=user_id,
    )

    return result


@router.patch("/{session_id}/mode", response_model=UpdateModeResponse)
async def update_session_mode(
    session_id: str,
    db: DbSession,
    user_id: CurrentUserId,
    request: UpdateModeRequest,
) -> UpdateModeResponse:
    """
    更新会话模式

    更新会话的模式，不创建新会话

    Args:
        session_id: 会话 ID
        request: 更新模式请求

    Returns:
        更新后的会话信息
    """
    service = get_session_service(db)

    result = await service.update_session_mode(
        session_id=session_id,
        user_id=user_id,
        mode=request.mode,
    )

    if result is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="会话不存在或无权访问")

    return UpdateModeResponse(
        session_id=result["session_id"],
        mode=result["mode"],
        topic=result["topic"],
    )


@router.delete("/{session_id}", response_model=DeleteSessionResponse)
async def delete_session(
    session_id: str,
    db: DbSession,
    user_id: CurrentUserId,
) -> DeleteSessionResponse:
    """
    删除会话

    删除会话及其所有消息

    Args:
        session_id: 会话 ID

    Returns:
        删除结果
    """
    service = get_session_service(db)

    # 先校验会话归属，再取消该会话的活跃任务（防越权副作用）
    session = await service._get_session(session_id, user_id)
    if session is None:
        return DeleteSessionResponse(success=False, message="会话不存在或无权删除")

    TaskManager.cancel_session_tasks(session_id)

    success = await service.delete_session(
        session_id=session_id,
        user_id=user_id,
    )

    if success:
        return DeleteSessionResponse(success=True, message="会话已删除")
    else:
        return DeleteSessionResponse(success=False, message="会话不存在或无权删除")


@router.post("/batch-delete", response_model=BatchDeleteResponse)
async def batch_delete_sessions(
    db: DbSession,
    user_id: CurrentUserId,
    request: BatchDeleteRequest,
) -> BatchDeleteResponse:
    """
    批量删除会话

    批量删除多个会话及其所有消息

    Args:
        request: 批量删除请求

    Returns:
        批量删除结果
    """
    service = get_session_service(db)

    # batch_delete_sessions 内部已做批量归属校验，无需逐个查询
    # 先批量取消可能存在的活跃任务
    for session_id in request.session_ids:
        TaskManager.cancel_session_tasks(session_id)

    deleted_count = await service.batch_delete_sessions(
        session_ids=request.session_ids,
        user_id=user_id,
    )

    if deleted_count > 0:
        return BatchDeleteResponse(
            success=True,
            deleted_count=deleted_count,
            message=f"成功删除 {deleted_count} 个会话",
        )
    else:
        return BatchDeleteResponse(
            success=False,
            deleted_count=0,
            message="没有找到可删除的会话",
        )


@router.post("/task/{task_id}/cancel", response_model=TaskCancelResponse)
async def cancel_task(
    task_id: str,
    user_id: CurrentUserId,
) -> TaskCancelResponse:
    """
    取消任务

    取消正在进行的流式响应任务

    Args:
        task_id: 任务 ID

    Returns:
        取消结果
    """
    # 验证任务所有权
    task_info = TaskManager.get_task_info(task_id)
    if task_info is None:
        return TaskCancelResponse(
            success=False,
            message="任务不存在或已完成",
        )

    if task_info.user_id != user_id:
        return TaskCancelResponse(
            success=False,
            message="无权取消此任务",
        )

    # 取消任务
    success = TaskManager.cancel_task(task_id)

    return TaskCancelResponse(
        success=success,
        message="任务已取消" if success else "任务取消失败",
    )
