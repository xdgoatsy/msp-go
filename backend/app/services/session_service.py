"""
会话服务

处理学习会话的创建、消息处理、历史记录等用例
"""

import asyncio
import hashlib
import logging
import time
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.resource_tools import build_resource_link
from app.domain.models.learning_session import AgentType, MessageRole
from app.infrastructure.database.models import (
    LearningSessionModel,
    SessionMessageModel,
    StudentProfileModel,
)
from app.infrastructure.repositories.resource_repository import ResourceRepository

logger = logging.getLogger(__name__)


# 欢迎消息模板
WELCOME_MESSAGES = {
    "study": "你好！我是你的 AI 高数学习助手。在学习模式下，我会系统性地引导你学习数学概念，从基础到进阶，确保你理解每个知识点。现在，你想学习什么主题？",
    "chat": "你好！我是你的 AI 高数辅导助手。在聊天模式下，你可以随时问我任何数学问题，我会尽力给你最清晰的解答。有什么想问的吗？",
    "practice": "你好！欢迎进入练习模式！我会根据你的学习进度推荐适合的题目，并在你做题过程中提供实时反馈。准备好开始练习了吗？请告诉我你想练习的知识点。",
    "explain": "你好！在讲解模式下，我会对数学概念进行深入、详细的讲解，帮助你从本质上理解问题。请告诉我你想深入了解的主题或遇到的困惑。",
}

# 定义应该收集消息的内容智能体节点
# 辅助节点（entry、tracker）的输出不应累积到最终响应
CONTENT_AGENTS = {"math_solver", "tutor", "diagnostician"}

RESOURCE_RECOMMENDATION_HEADING = "推荐资源"
RESOURCE_RECOMMENDATION_LINK_MARKERS = ("](", "http://", "https://", "/resources")
RESOURCE_REQUEST_KEYWORDS = ("资源", "资料", "视频", "文档", "课件", "材料")
RESOURCE_RECOMMENDATION_KEYWORD = "推荐"
RESOURCE_RECOMMENDATION_EXCLUDED_KEYWORDS = (
    "题",
    "练习",
    "学习路径",
    "学习计划",
    "路径",
    "计划",
)
RESOURCE_QUERY_STOPWORDS = (
    "推荐",
    "资源",
    "资料",
    "视频",
    "文档",
    "课件",
    "材料",
    "帮我",
    "给我",
    "找",
    "查找",
    "搜索",
    "一些",
    "几个",
    "关于",
    "相关",
    "有没有",
    "我想学习",
    "想学习",
    "我想学",
    "想学",
    "我想要",
    "想要",
    "我想",
    "想",
    "的",
    "一下",
    "学习",
)


def _message_requests_resource_recommendations(message: str) -> bool:
    """判断学生是否明确请求资源类推荐。"""
    normalized = message.strip().lower()
    if any(keyword in normalized for keyword in RESOURCE_REQUEST_KEYWORDS):
        return True

    if RESOURCE_RECOMMENDATION_KEYWORD not in normalized:
        return False

    return not any(
        keyword in normalized for keyword in RESOURCE_RECOMMENDATION_EXCLUDED_KEYWORDS
    )


def _has_resource_recommendation_links(response_content: str) -> bool:
    """判断回复里的资源推荐段落是否已经包含真实可点击链接。"""
    heading_index = response_content.find(RESOURCE_RECOMMENDATION_HEADING)
    if heading_index == -1:
        return False
    recommendation_section = response_content[heading_index:]
    return any(
        marker in recommendation_section
        for marker in RESOURCE_RECOMMENDATION_LINK_MARKERS
    )


def _extract_resource_query(message: str) -> str | None:
    """从自然语言请求中提取尽量短的资源检索关键词。"""
    query = message.strip()
    for punctuation in "，。！？、,.!?;；:：":
        query = query.replace(punctuation, " ")
    for stopword in RESOURCE_QUERY_STOPWORDS:
        query = query.replace(stopword, " ")
    query = " ".join(query.split())
    return query[:80] if query else None


def _resource_type_from_message(message: str) -> str | None:
    if "视频" in message:
        return "video"
    if "文档" in message or "课件" in message:
        return "document"
    return None


def _profile_difficulty_level(student_profile: dict[str, Any] | None) -> str | None:
    if not student_profile:
        return None
    try:
        preferred = float(student_profile.get("preferred_difficulty", 0.5))
    except (TypeError, ValueError):
        return None
    if preferred < 0.34:
        return "beginner"
    if preferred < 0.67:
        return "intermediate"
    return "advanced"


def _resource_type_label(resource_type: str | None) -> str | None:
    return {"video": "视频", "document": "文档"}.get(resource_type or "")


def _difficulty_label(difficulty: Any) -> str | None:
    try:
        value = float(difficulty)
    except (TypeError, ValueError):
        return None
    if value < 0.34:
        return "入门"
    if value < 0.67:
        return "进阶"
    return "提高"


def _format_resource_recommendations(resources: list[dict[str, Any]]) -> str:
    if not resources:
        return "\n\n### 推荐资源\n暂未在资源中心找到匹配资料，可以换个关键词再试。"

    lines = ["\n\n### 推荐资源"]
    for index, resource in enumerate(resources[:3], start=1):
        title = str(resource.get("title") or "学习资源").replace("[", "\\[").replace("]", "\\]")
        link = build_resource_link(resource).replace(")", "%29")
        detail_parts = [
            _resource_type_label(resource.get("type")),
            _difficulty_label(resource.get("difficulty")),
            resource.get("topic") or resource.get("chapter") or resource.get("source"),
        ]
        details = " · ".join(str(part) for part in detail_parts if part)
        suffix = f" - {details}" if details else ""
        lines.append(f"{index}. [{title}]({link}){suffix}")
    return "\n".join(lines)


class SessionService:
    """学习会话服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _load_student_profile(self, user_id: str) -> dict[str, Any] | None:
        """
        加载学生画像数据（L1 内存缓存 + DB）

        Args:
            user_id: 用户 ID

        Returns:
            学生画像字典，不存在则返回 None
        """
        from app.infrastructure.cache.memory import profile_cache

        cache_key = f"profile:{user_id}"
        cached = profile_cache.get(cache_key)
        if cached is not None:
            return cached

        stmt = select(StudentProfileModel).where(
            StudentProfileModel.student_id == user_id
        )
        result = await self.db.execute(stmt)
        profile = result.scalar_one_or_none()

        if profile is None:
            return None

        data = {
            "mastery_vector": profile.mastery_vector or {},
            "error_tendency": profile.error_tendency or {},
            "preferred_difficulty": profile.preferred_difficulty,
            "learning_pace": profile.learning_pace,
            "total_exercises": profile.total_exercises,
            "correct_count": profile.correct_count,
        }
        profile_cache.set(cache_key, data)
        return data

    async def _apply_profile_updates(
        self, user_id: str, updates: dict[str, Any]
    ) -> None:
        """
        将 Tracker 生成的画像更新写回数据库

        Args:
            user_id: 用户 ID
            updates: Tracker 生成的 profile_updates
        """
        if not updates:
            return

        stmt = select(StudentProfileModel).where(
            StudentProfileModel.student_id == user_id
        )
        result = await self.db.execute(stmt)
        profile = result.scalar_one_or_none()

        if profile is None:
            logger.warning("学生画像不存在，跳过更新: user_id=%s", user_id)
            return

        # 更新 mastery_vector
        if "mastery_vector" in updates:
            profile.mastery_vector = updates["mastery_vector"]

        # 更新 error_tendency
        if "error_tendency" in updates:
            profile.error_tendency = updates["error_tendency"]

        # 更新 recent_concepts（存储在 mastery_vector 的 meta 中或单独字段）
        # 注意：当前 DB 模型没有 recent_concepts 字段，暂时跳过

        # 增量更新 total_exercises
        if "total_exercises_delta" in updates:
            profile.total_exercises = (
                profile.total_exercises + updates["total_exercises_delta"]
            )

        # 增量更新 correct_count
        if "correct_count_delta" in updates:
            profile.correct_count = (
                profile.correct_count + updates["correct_count_delta"]
            )

        # 更新 consecutive_errors（存储在 profile 的 error_tendency 中）
        if "consecutive_errors" in updates:
            # 可以作为 error_tendency 的一部分存储
            tendency = profile.error_tendency or {}
            tendency["_consecutive_errors"] = updates["consecutive_errors"]
            profile.error_tendency = tendency

        # 失效 L1 内存缓存，确保下次读取最新数据
        from app.infrastructure.cache.memory import profile_cache
        profile_cache.delete(f"profile:{user_id}")

        logger.info("学生画像已更新: user_id=%s, keys=%s", user_id, list(updates.keys()))

    async def _build_resource_recommendation_markdown(
        self,
        message: str,
        response_content: str,
        student_profile: dict[str, Any] | None,
    ) -> str:
        """在 AI 未主动推荐资源时，为明确资源请求追加资源中心推荐。"""
        if _has_resource_recommendation_links(response_content):
            return ""
        if not _message_requests_resource_recommendations(message):
            return ""

        query = _extract_resource_query(message)
        repository = ResourceRepository(self.db)

        try:
            resources = await repository.search_recommendations(
                query=query,
                topic=query,
                resource_type=_resource_type_from_message(message),
                difficulty=_profile_difficulty_level(student_profile),
                limit=3,
            )
        except Exception as e:
            logger.warning("资源推荐兜底检索失败: %s", e, exc_info=True)
            return ""

        return _format_resource_recommendations(resources)

    async def create_session(
        self,
        user_id: str,
        topic: str | None = None,
        mode: str = "chat",
    ) -> dict[str, Any]:
        """
        创建学习会话

        Args:
            user_id: 用户 ID
            topic: 会话主题
            mode: 会话模式 (study/chat/practice/explain)

        Returns:
            会话信息字典
        """
        session_id = str(uuid4())
        now = datetime.now()

        # 创建会话记录
        session = LearningSessionModel(
            id=session_id,
            student_id=user_id,
            is_active=True,
            current_topic=topic,
            started_at=now,
        )
        self.db.add(session)

        # 创建欢迎消息
        welcome_content = WELCOME_MESSAGES.get(mode, WELCOME_MESSAGES["chat"])
        welcome_message_id = str(uuid4())
        welcome_message = SessionMessageModel(
            id=welcome_message_id,
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=welcome_content,
            agent_type=AgentType.TUTOR,
            created_at=now,
        )
        self.db.add(welcome_message)

        await self.db.commit()

        logger.info("会话已创建: session_id=%s, user_id=%s, mode=%s", session_id, user_id, mode)

        return {
            "session_id": session_id,
            "user_id": user_id,
            "topic": topic,
            "mode": mode,
            "status": "active",
            "created_at": now,
            "welcome_message": {
                "id": welcome_message_id,
                "role": "assistant",
                "content": welcome_content,
                "agent": "tutor",
                "timestamp": now,
                "attachments": [],
            },
        }

    async def process_message_stream(
        self,
        session_id: str,
        user_id: str,
        message: str,
        attachments: list[str] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        处理用户消息并流式返回响应

        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            message: 用户消息
            attachments: 附件列表

        Yields:
            SSE 事件数据
        """
        request_started_at = time.perf_counter()
        workflow_started_at: float | None = None
        first_content_logged = False

        def _elapsed_ms(start: float | None = None) -> float:
            return (time.perf_counter() - (start or request_started_at)) * 1000

        def _log_first_content_once() -> None:
            nonlocal first_content_logged
            if first_content_logged:
                return
            first_content_logged = True
            workflow_elapsed_ms = (
                round(_elapsed_ms(workflow_started_at), 1)
                if workflow_started_at is not None
                else None
            )
            logger.info(
                "AI stream timing: stage=first_content_chunk "
                "session_id=%s elapsed_ms=%.1f workflow_elapsed_ms=%s",
                session_id,
                _elapsed_ms(),
                workflow_elapsed_ms,
            )

        logger.info(
            "AI stream timing: stage=request_start session_id=%s",
            session_id,
        )

        # 验证会话
        session = await self._get_session(session_id, user_id)
        if session is None:
            yield {
                "type": "error",
                "code": "SESSION_NOT_FOUND",
                "message": "会话不存在或无权访问",
            }
            return

        if not session.is_active:
            yield {
                "type": "error",
                "code": "SESSION_ENDED",
                "message": "会话已结束",
            }
            return

        # 保存用户消息
        user_message_id = str(uuid4())
        user_msg = SessionMessageModel(
            id=user_message_id,
            session_id=session_id,
            role=MessageRole.USER,
            content=message,
            attachments=attachments or [],
            created_at=datetime.now(),
        )
        self.db.add(user_msg)
        await self.db.commit()

        # 加载学生画像（供工作流初始化学生上下文）
        student_profile = await self._load_student_profile(user_id)

        # 生成 AI 消息 ID
        ai_message_id = str(uuid4())
        content_parts: list[str] = []
        full_content = ""
        current_agent: str | None = None
        # 使用哈希集合追踪已发送内容，优化去重检查从 O(n) 到 O(1)
        sent_hashes: set[str] = set()
        # 内容智能体输出完成标记（用于提前结束流式）
        content_finished = False
        # 追踪数据更新
        profile_updates: dict[str, Any] = {}

        def _content_hash(content: str) -> str:
            """计算内容哈希（取前16位）"""
            return hashlib.md5(content.encode()).hexdigest()[:16]

        try:
            # 调用工作流获取流式响应
            from app.agents.workflow.graph import stream_workflow

            workflow_started_at = time.perf_counter()
            logger.info(
                "AI stream timing: stage=workflow_start "
                "session_id=%s elapsed_ms=%.1f",
                session_id,
                _elapsed_ms(),
            )

            async for chunk in stream_workflow(
                session_id=session_id,
                student_id=user_id,
                message=message,
                attachments=attachments,
                student_profile=student_profile,
                db_session=self.db,  # 传递数据库会话给工作流
            ):
                chunk_type = chunk.get("type")

                if chunk_type == "message":
                    content = chunk.get("content", "")
                    metadata = chunk.get("metadata", {})
                    agent = metadata.get("agent_type")
                    is_streaming = metadata.get("streaming", False)

                    # 只处理内容智能体的输出，过滤辅助节点
                    if agent and agent not in CONTENT_AGENTS:
                        continue

                    if content:
                        # 对于流式输出，直接发送每个 chunk
                        if is_streaming:
                            content_parts.append(content)
                            current_agent = agent

                            _log_first_content_once()
                            yield {
                                "type": "chunk",
                                "content": content,
                                "agent": agent,
                                "message_id": ai_message_id,
                            }
                        else:
                            # 非流式输出（回退情况），使用哈希去重
                            chunk_hash = _content_hash(content)
                            if chunk_hash not in sent_hashes:
                                sent_hashes.add(chunk_hash)
                                content_parts.append(content)
                                current_agent = agent

                                _log_first_content_once()
                                yield {
                                    "type": "chunk",
                                    "content": content,
                                    "agent": agent,
                                    "message_id": ai_message_id,
                                }

                elif chunk_type == "node_start":
                    # 节点开始，可以用于显示状态
                    node = chunk.get("node")
                    if node in CONTENT_AGENTS:
                        logger.debug("节点开始: %s", node)

                elif chunk_type == "node_end":
                    # 节点结束
                    node = chunk.get("node")
                    if node in CONTENT_AGENTS:
                        logger.debug("节点结束: %s", node)
                        content_finished = True

                elif chunk_type == "agent_output":
                    # 处理智能体输出
                    outputs = chunk.get("outputs", {})
                    if "final_response" in outputs:
                        content = outputs["final_response"]
                        # 使用哈希去重
                        if content:
                            chunk_hash = _content_hash(content)
                            if chunk_hash not in sent_hashes:
                                sent_hashes.add(chunk_hash)
                                content_parts.append(content)
                                _log_first_content_once()
                                yield {
                                    "type": "chunk",
                                    "content": content,
                                    "agent": current_agent,
                                    "message_id": ai_message_id,
                                }

                elif chunk_type == "error":
                    # 工作流错误
                    error_content = chunk.get("content", "处理消息时发生错误")
                    yield {
                        "type": "error",
                        "code": "WORKFLOW_ERROR",
                        "message": error_content,
                    }
                    return

                elif chunk_type == "profile_updates":
                    # Tracker 生成的画像更新
                    profile_updates = chunk.get("updates", {})

            if content_finished:
                logger.debug("内容智能体输出完成，提前结束流式响应")

            full_content = "".join(content_parts)

            # 如果没有收到任何内容，使用默认响应
            if not full_content:
                full_content = "抱歉，我暂时无法处理你的请求。请稍后再试。"
                _log_first_content_once()
                yield {
                    "type": "chunk",
                    "content": full_content,
                    "agent": "tutor",
                    "message_id": ai_message_id,
                }

            recommendation_content = await self._build_resource_recommendation_markdown(
                message=message,
                response_content=full_content,
                student_profile=student_profile,
            )
            if recommendation_content:
                full_content += recommendation_content
                content_parts.append(recommendation_content)
                _log_first_content_once()
                yield {
                    "type": "chunk",
                    "content": recommendation_content,
                    "agent": current_agent or "tutor",
                    "message_id": ai_message_id,
                }

            # 保存 AI 消息到数据库
            # 检查 current_agent 是否是有效的 AgentType 值
            # 工作流节点如 "exit", "entry", "intent_classifier" 不是有效的 AgentType
            valid_agent_types = {e.value for e in AgentType}
            agent_type = (
                AgentType(current_agent)
                if current_agent and current_agent in valid_agent_types
                else AgentType.TUTOR
            )
            ai_msg = SessionMessageModel(
                id=ai_message_id,
                session_id=session_id,
                role=MessageRole.ASSISTANT,
                content=full_content,
                agent_type=agent_type,
                created_at=datetime.now(),
            )
            self.db.add(ai_msg)

            # 写回学生画像更新（与消息保存在同一事务中）
            if profile_updates:
                await self._apply_profile_updates(user_id, profile_updates)

            await self.db.commit()

            # 发送完成事件
            logger.info(
                "AI stream timing: stage=done session_id=%s "
                "elapsed_ms=%.1f first_content_seen=%s",
                session_id,
                _elapsed_ms(),
                first_content_logged,
            )
            yield {
                "type": "done",
                "message_id": ai_message_id,
                "agent": current_agent or "tutor",
            }

        except asyncio.CancelledError:
            # 任务被取消
            logger.info("消息处理被取消: session_id=%s", session_id)
            if not full_content and content_parts:
                full_content = "".join(content_parts)

            if full_content:
                # 保存已生成的部分内容
                ai_msg = SessionMessageModel(
                    id=ai_message_id,
                    session_id=session_id,
                    role=MessageRole.ASSISTANT,
                    content=full_content + "\n\n[响应已取消]",
                    agent_type=AgentType.TUTOR,
                    created_at=datetime.now(),
                )
                self.db.add(ai_msg)
                await self.db.commit()

            yield {
                "type": "cancelled",
                "message_id": ai_message_id,
            }

        except Exception as e:
            logger.error("消息处理失败: %s", e, exc_info=True)
            yield {
                "type": "error",
                "code": "PROCESSING_ERROR",
                "message": "处理消息时发生错误，请稍后重试",
            }

    async def get_history(
        self,
        session_id: str,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        获取会话历史消息

        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            历史消息列表
        """
        # 验证会话
        session = await self._get_session(session_id, user_id)
        if session is None:
            return {"messages": [], "total": 0, "has_more": False}

        # 并行执行 count 和 data 查询（减少串行等待）
        count_stmt = (
            select(func.count())
            .select_from(SessionMessageModel)
            .where(SessionMessageModel.session_id == session_id)
        )
        data_stmt = (
            select(SessionMessageModel)
            .where(SessionMessageModel.session_id == session_id)
            .order_by(SessionMessageModel.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        total_result, data_result = await asyncio.gather(
            self.db.execute(count_stmt),
            self.db.execute(data_stmt),
        )
        total = total_result.scalar() or 0
        messages = data_result.scalars().all()

        return {
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role.value,
                    "content": msg.content,
                    "agent": msg.agent_type.value if msg.agent_type else None,
                    "timestamp": msg.created_at,
                    "attachments": msg.attachments or [],
                }
                for msg in messages
            ],
            "total": total,
            "has_more": offset + limit < total,
        }

    async def get_sessions_list(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        获取用户的会话列表

        Args:
            user_id: 用户 ID
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            会话列表
        """
        # 查询总数
        count_stmt = (
            select(func.count())
            .select_from(LearningSessionModel)
            .where(LearningSessionModel.student_id == user_id)
        )
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        # 创建消息计数子查询（优化 N+1 查询问题）
        msg_count_subq = (
            select(
                SessionMessageModel.session_id,
                func.count(SessionMessageModel.id).label("msg_count"),
            )
            .group_by(SessionMessageModel.session_id)
            .subquery()
        )

        # 主查询 LEFT JOIN 子查询，一次性获取会话和消息计数
        stmt = (
            select(
                LearningSessionModel,
                func.coalesce(msg_count_subq.c.msg_count, 0).label("message_count"),
            )
            .outerjoin(
                msg_count_subq,
                LearningSessionModel.id == msg_count_subq.c.session_id,
            )
            .where(LearningSessionModel.student_id == user_id)
            .order_by(LearningSessionModel.started_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        # 构建会话列表
        session_list = [
            {
                "session_id": session.id,
                "user_id": session.student_id,
                "topic": session.current_topic,
                "status": "active" if session.is_active else "completed",
                "started_at": session.started_at,
                "ended_at": session.ended_at,
                "message_count": msg_count,
            }
            for session, msg_count in rows
        ]

        return {
            "sessions": session_list,
            "total": total,
        }

    async def end_session(self, session_id: str, user_id: str) -> dict[str, Any]:
        """
        结束会话

        Args:
            session_id: 会话 ID
            user_id: 用户 ID

        Returns:
            操作结果
        """
        session = await self._get_session(session_id, user_id)
        if session is None:
            return {"status": "error", "message": "会话不存在或无权访问"}

        if not session.is_active:
            return {"status": "already_ended", "message": "会话已结束"}

        session.is_active = False
        session.ended_at = datetime.now()
        await self.db.commit()

        logger.info("会话已结束: session_id=%s", session_id)

        return {"status": "ended", "message": "会话已成功结束"}

    async def update_session_mode(
        self,
        session_id: str,
        user_id: str,
        mode: str,
    ) -> dict[str, Any] | None:
        """
        更新会话模式

        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            mode: 新模式 (study/chat/practice/explain)

        Returns:
            更新后的会话信息，如果会话不存在则返回 None
        """
        session = await self._get_session(session_id, user_id)
        if session is None:
            return None

        # 更新会话主题以反映模式变化（可选）
        mode_names = {
            "study": "学习模式",
            "chat": "聊天模式",
            "practice": "练习模式",
            "explain": "讲解模式",
        }
        session.current_topic = mode_names.get(mode, mode)
        await self.db.commit()

        logger.info("会话模式已更新: session_id=%s, mode=%s", session_id, mode)

        return {
            "session_id": session_id,
            "mode": mode,
            "topic": session.current_topic,
        }

    async def delete_session(
        self,
        session_id: str,
        user_id: str,
    ) -> bool:
        """
        删除会话及其所有消息

        Args:
            session_id: 会话 ID
            user_id: 用户 ID

        Returns:
            是否删除成功
        """
        session = await self._get_session(session_id, user_id)
        if session is None:
            return False

        # 删除会话消息
        from sqlalchemy import delete

        await self.db.execute(
            delete(SessionMessageModel).where(
                SessionMessageModel.session_id == session_id
            )
        )

        # 删除会话
        await self.db.delete(session)
        await self.db.commit()

        logger.info("会话已删除: session_id=%s", session_id)

        return True

    async def batch_delete_sessions(
        self,
        session_ids: list[str],
        user_id: str,
    ) -> int:
        """
        批量删除会话及其所有消息

        Args:
            session_ids: 会话 ID 列表
            user_id: 用户 ID

        Returns:
            成功删除的会话数量
        """
        from sqlalchemy import delete

        # 查询属于该用户的会话
        stmt = select(LearningSessionModel).where(
            LearningSessionModel.id.in_(session_ids),
            LearningSessionModel.student_id == user_id,
        )
        result = await self.db.execute(stmt)
        sessions = result.scalars().all()

        if not sessions:
            return 0

        valid_session_ids = [s.id for s in sessions]

        # 批量删除会话消息
        await self.db.execute(
            delete(SessionMessageModel).where(
                SessionMessageModel.session_id.in_(valid_session_ids)
            )
        )

        # 批量删除会话
        await self.db.execute(
            delete(LearningSessionModel).where(
                LearningSessionModel.id.in_(valid_session_ids)
            )
        )

        await self.db.commit()

        logger.info("批量删除会话: count=%s, user_id=%s", len(valid_session_ids), user_id)

        return len(valid_session_ids)

    async def _get_session(
        self,
        session_id: str,
        user_id: str,
    ) -> LearningSessionModel | None:
        """
        获取会话（验证用户权限）

        Args:
            session_id: 会话 ID
            user_id: 用户 ID

        Returns:
            会话模型，如果不存在或无权访问则返回 None
        """
        stmt = select(LearningSessionModel).where(
            LearningSessionModel.id == session_id,
            LearningSessionModel.student_id == user_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()


def get_session_service(db: AsyncSession) -> SessionService:
    """获取会话服务实例"""
    return SessionService(db)
