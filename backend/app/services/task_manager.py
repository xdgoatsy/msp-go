"""
异步任务管理器

管理 asyncio.Task 生命周期，支持任务取消和状态查询
"""

import asyncio
import json
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """任务状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class TaskInfo:
    """任务信息"""

    task_id: str
    session_id: str
    user_id: str
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None


class TaskManager:
    """
    异步任务管理器

    管理流式响应任务的生命周期，支持:
    - 任务创建和注册
    - 任务取消
    - 状态查询
    - Redis 持久化（可选）
    """

    # 内存中的任务映射
    _tasks: dict[str, asyncio.Task[Any]] = {}
    _task_info: dict[str, TaskInfo] = {}

    # 会话到运行中任务 ID 的索引
    _session_running_tasks: dict[str, set[str]] = {}

    # 已终态任务队列（用于延迟清理）
    _completed_task_queue: deque[tuple[float, str]] = deque()

    # 内存治理参数
    COMPLETED_TASK_TTL_SECONDS = 600
    MAX_COMPLETED_TASK_INFOS = 2000

    # Redis 键前缀
    REDIS_PREFIX = "msp:task"

    @classmethod
    def generate_task_id(cls) -> str:
        """生成任务 ID"""
        return str(uuid4())

    @classmethod
    def _add_task_to_session_index(cls, session_id: str, task_id: str) -> None:
        """将任务加入会话运行索引。"""
        cls._session_running_tasks.setdefault(session_id, set()).add(task_id)

    @classmethod
    def _remove_task_from_session_index(cls, session_id: str, task_id: str) -> None:
        """从会话运行索引移除任务。"""
        session_tasks = cls._session_running_tasks.get(session_id)
        if not session_tasks:
            return

        session_tasks.discard(task_id)
        if not session_tasks:
            cls._session_running_tasks.pop(session_id, None)

    @classmethod
    def _mark_task_terminal(
        cls,
        task_id: str,
        status: TaskStatus,
        error: str | None = None,
    ) -> None:
        """将任务标记为终态并维护相关索引。"""
        info = cls._task_info.get(task_id)
        if info is None:
            return

        if info.status == TaskStatus.RUNNING:
            cls._remove_task_from_session_index(info.session_id, task_id)
        elif info.completed_at is not None:
            return

        completed_at = datetime.now()
        info.status = status
        info.completed_at = completed_at
        info.error = error
        cls._completed_task_queue.append((completed_at.timestamp(), task_id))

    @classmethod
    def _infer_terminal_status_from_task(
        cls,
        task: asyncio.Task[Any],
    ) -> tuple[TaskStatus, str | None]:
        """根据 asyncio.Task 状态推断终态状态。"""
        if task.cancelled():
            return TaskStatus.CANCELLED, None

        try:
            exc = task.exception()
        except asyncio.CancelledError:
            return TaskStatus.CANCELLED, None
        except Exception as e:
            return TaskStatus.FAILED, str(e)

        if exc is not None:
            return TaskStatus.FAILED, str(exc)

        return TaskStatus.COMPLETED, None

    @classmethod
    def _cleanup_completed_tasks_if_needed(cls) -> None:
        """按 TTL 和容量约束清理已终态任务，避免内存增长。"""
        if not cls._completed_task_queue and cls._tasks:
            done_task_ids = [task_id for task_id, task in cls._tasks.items() if task.done()]
            for task_id in done_task_ids:
                cls._tasks.pop(task_id, None)
            return

        now_ts = datetime.now().timestamp()

        while cls._completed_task_queue:
            completed_at_ts, task_id = cls._completed_task_queue[0]
            is_expired = (now_ts - completed_at_ts) >= cls.COMPLETED_TASK_TTL_SECONDS
            over_capacity = len(cls._task_info) > cls.MAX_COMPLETED_TASK_INFOS
            if not is_expired and not over_capacity:
                break

            cls._completed_task_queue.popleft()

            info = cls._task_info.get(task_id)
            if info and info.status != TaskStatus.RUNNING:
                cls._task_info.pop(task_id, None)

        # 双重保障：避免 _tasks 残留已结束的任务对象
        done_task_ids = [task_id for task_id, task in cls._tasks.items() if task.done()]
        for task_id in done_task_ids:
            cls._tasks.pop(task_id, None)

    @classmethod
    def register_task(
        cls,
        task: asyncio.Task[Any],
        task_id: str,
        session_id: str,
        user_id: str,
    ) -> TaskInfo:
        """
        注册任务

        Args:
            task: asyncio.Task 实例
            task_id: 任务 ID
            session_id: 会话 ID
            user_id: 用户 ID

        Returns:
            任务信息
        """
        info = TaskInfo(
            task_id=task_id,
            session_id=session_id,
            user_id=user_id,
            status=TaskStatus.RUNNING,
            started_at=datetime.now(),
        )

        cls._tasks[task_id] = task
        cls._task_info[task_id] = info
        cls._add_task_to_session_index(session_id, task_id)
        cls._cleanup_completed_tasks_if_needed()

        logger.info("任务已注册: %s, session=%s", task_id, session_id)

        return info

    @classmethod
    def get_task(cls, task_id: str) -> asyncio.Task[Any] | None:
        """获取任务"""
        cls._cleanup_completed_tasks_if_needed()
        return cls._tasks.get(task_id)

    @classmethod
    def get_task_info(cls, task_id: str) -> TaskInfo | None:
        """获取任务信息"""
        cls._cleanup_completed_tasks_if_needed()
        return cls._task_info.get(task_id)

    @classmethod
    def cancel_task(cls, task_id: str) -> bool:
        """
        取消任务

        Args:
            task_id: 任务 ID

        Returns:
            是否成功取消
        """
        task = cls._tasks.get(task_id)
        if task is None:
            logger.warning("任务不存在: %s", task_id)
            return False

        info = cls._task_info.get(task_id)

        if task.done():
            if info:
                status, error = cls._infer_terminal_status_from_task(task)
                cls._mark_task_terminal(task_id=task_id, status=status, error=error)
            cls._tasks.pop(task_id, None)
            logger.info("任务已完成，无需取消: %s", task_id)
            return False

        # 取消任务
        cancelled = task.cancel()

        if cancelled:
            cls._mark_task_terminal(task_id=task_id, status=TaskStatus.CANCELLED)
            logger.info("任务已取消: %s", task_id)

        cls._cleanup_completed_tasks_if_needed()
        return cancelled

    @classmethod
    def complete_task(cls, task_id: str, error: str | None = None) -> None:
        """
        标记任务完成

        Args:
            task_id: 任务 ID
            error: 错误信息（如果有）
        """
        cls._mark_task_terminal(
            task_id=task_id,
            status=TaskStatus.FAILED if error else TaskStatus.COMPLETED,
            error=error,
        )

        info = cls._task_info.get(task_id)
        if info:
            logger.info("任务已完成: %s, status=%s", task_id, info.status)

        cls._cleanup_completed_tasks_if_needed()

    @classmethod
    def cleanup_task(cls, task_id: str) -> None:
        """
        清理任务（从内存中移除）

        Args:
            task_id: 任务 ID
        """
        info = cls._task_info.get(task_id)
        if info and info.status == TaskStatus.RUNNING:
            cls._remove_task_from_session_index(info.session_id, task_id)

        cls._tasks.pop(task_id, None)
        cls._task_info.pop(task_id, None)

        # 不再重建 deque（O(n)），deque 中残留的 task_id 会在
        # _cleanup_completed_tasks_if_needed 中被惰性跳过（_task_info 已删除）

        logger.debug("任务已清理: %s", task_id)

    @classmethod
    def get_session_active_task(cls, session_id: str) -> str | None:
        """
        获取会话的活跃任务 ID

        Args:
            session_id: 会话 ID

        Returns:
            活跃任务 ID，如果没有则返回 None
        """
        task_ids = cls._session_running_tasks.get(session_id)
        if not task_ids:
            return None

        stale_task_ids: list[str] = []
        for task_id in task_ids:
            task = cls._tasks.get(task_id)
            if task and not task.done():
                return task_id
            stale_task_ids.append(task_id)

        if stale_task_ids:
            for task_id in stale_task_ids:
                cls._session_running_tasks.get(session_id, set()).discard(task_id)
                info = cls._task_info.get(task_id)
                if info and info.status == TaskStatus.RUNNING:
                    cls._mark_task_terminal(task_id=task_id, status=TaskStatus.COMPLETED)
            if not cls._session_running_tasks.get(session_id):
                cls._session_running_tasks.pop(session_id, None)

        cls._cleanup_completed_tasks_if_needed()
        return None

    @classmethod
    def cancel_session_tasks(cls, session_id: str) -> int:
        """
        取消会话的所有任务

        Args:
            session_id: 会话 ID

        Returns:
            取消的任务数量
        """
        cancelled_count = 0

        task_ids_to_cancel = list(cls._session_running_tasks.get(session_id, set()))
        if not task_ids_to_cancel:
            task_ids_to_cancel = [
                task_id
                for task_id, info in cls._task_info.items()
                if info.session_id == session_id and info.status == TaskStatus.RUNNING
            ]
            if not task_ids_to_cancel:
                return 0

        stale_task_ids: list[str] = []
        for task_id in task_ids_to_cancel:
            task = cls._tasks.get(task_id)
            if task is None:
                stale_task_ids.append(task_id)
                info = cls._task_info.get(task_id)
                if info and info.status == TaskStatus.RUNNING:
                    cls._mark_task_terminal(task_id=task_id, status=TaskStatus.COMPLETED)
                continue

            if cls.cancel_task(task_id):
                cancelled_count += 1

        if stale_task_ids:
            session_tasks = cls._session_running_tasks.get(session_id)
            if session_tasks:
                for task_id in stale_task_ids:
                    session_tasks.discard(task_id)
                if not session_tasks:
                    cls._session_running_tasks.pop(session_id, None)

        cls._cleanup_completed_tasks_if_needed()
        return cancelled_count

    # ========== Redis 持久化方法（可选） ==========

    @classmethod
    async def save_to_redis(cls, task_id: str) -> bool:
        """
        保存任务状态到 Redis

        Args:
            task_id: 任务 ID

        Returns:
            是否成功
        """
        try:
            from app.infrastructure.cache.redis import get_redis_client_safe

            redis = await get_redis_client_safe()
            if redis is None:
                return False

            info = cls._task_info.get(task_id)
            if info is None:
                return False

            key = f"{cls.REDIS_PREFIX}:{task_id}"
            data = {
                "task_id": info.task_id,
                "session_id": info.session_id,
                "user_id": info.user_id,
                "status": info.status.value,
                "created_at": info.created_at.isoformat(),
                "started_at": info.started_at.isoformat() if info.started_at else None,
                "completed_at": (
                    info.completed_at.isoformat() if info.completed_at else None
                ),
                "error": info.error,
            }

            await redis.set(key, json.dumps(data), ex=3600)  # 1 小时过期
            return True

        except Exception as e:
            logger.error("保存任务状态到 Redis 失败: %s", e)
            return False

    @classmethod
    async def load_from_redis(cls, task_id: str) -> TaskInfo | None:
        """
        从 Redis 加载任务状态

        Args:
            task_id: 任务 ID

        Returns:
            任务信息
        """
        try:
            from app.infrastructure.cache.redis import get_redis_client_safe

            redis = await get_redis_client_safe()
            if redis is None:
                return None

            key = f"{cls.REDIS_PREFIX}:{task_id}"
            data_str = await redis.get(key)

            if data_str is None:
                return None

            data = json.loads(data_str)
            return TaskInfo(
                task_id=data["task_id"],
                session_id=data["session_id"],
                user_id=data["user_id"],
                status=TaskStatus(data["status"]),
                created_at=datetime.fromisoformat(data["created_at"]),
                started_at=(
                    datetime.fromisoformat(data["started_at"])
                    if data["started_at"]
                    else None
                ),
                completed_at=(
                    datetime.fromisoformat(data["completed_at"])
                    if data["completed_at"]
                    else None
                ),
                error=data["error"],
            )

        except Exception as e:
            logger.error("从 Redis 加载任务状态失败: %s", e)
            return None
