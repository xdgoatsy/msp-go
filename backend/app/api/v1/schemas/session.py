"""
学习会话 API Schema

定义会话相关的请求和响应数据结构
"""

from datetime import datetime

from pydantic import BaseModel, Field

# ========== 请求模型 ==========


class CreateSessionRequest(BaseModel):
    """创建会话请求"""

    topic: str | None = Field(None, max_length=200, description="会话主题")
    mode: str = Field("chat", description="会话模式: study/chat/practice/explain")


class SendMessageRequest(BaseModel):
    """发送消息请求"""

    message: str = Field(..., min_length=1, max_length=10000, description="消息内容")
    attachments: list[str] | None = Field(None, description="附件 URL 列表")


class ControlTaskRequest(BaseModel):
    """控制任务请求"""

    task_id: str = Field(..., description="任务 ID")


class UpdateModeRequest(BaseModel):
    """更新会话模式请求"""

    mode: str = Field(..., description="会话模式: study/chat/practice/explain")


# ========== 响应模型 ==========


class MessageResponse(BaseModel):
    """消息响应"""

    id: str = Field(..., description="消息 ID")
    role: str = Field(..., description="角色: user/assistant/system")
    content: str = Field(..., description="消息内容")
    agent: str | None = Field(None, description="智能体类型")
    timestamp: datetime = Field(..., description="时间戳")
    attachments: list[str] = Field(default_factory=list, description="附件列表")

    model_config = {"from_attributes": True}


class CreateSessionResponse(BaseModel):
    """创建会话响应"""

    session_id: str = Field(..., description="会话 ID")
    user_id: str = Field(..., description="用户 ID")
    topic: str | None = Field(None, description="会话主题")
    mode: str = Field(..., description="会话模式")
    status: str = Field(..., description="会话状态")
    created_at: datetime = Field(..., description="创建时间")
    welcome_message: MessageResponse = Field(..., description="欢迎消息")


class SessionResponse(BaseModel):
    """会话响应"""

    session_id: str = Field(..., description="会话 ID")
    user_id: str = Field(..., description="用户 ID")
    topic: str | None = Field(None, description="会话主题")
    status: str = Field(..., description="会话状态: active/completed/paused")
    started_at: datetime = Field(..., description="开始时间")
    ended_at: datetime | None = Field(None, description="结束时间")
    message_count: int = Field(0, description="消息数量")

    model_config = {"from_attributes": True}


class SessionListResponse(BaseModel):
    """会话列表响应"""

    sessions: list[SessionResponse] = Field(..., description="会话列表")
    total: int = Field(..., description="总数")


class HistoryResponse(BaseModel):
    """历史消息响应"""

    messages: list[MessageResponse] = Field(..., description="消息列表")
    total: int = Field(..., description="总数")
    has_more: bool = Field(..., description="是否有更多")


# ========== SSE 事件数据模型 ==========


class SSEChunkData(BaseModel):
    """SSE 流式内容块"""

    type: str = Field("chunk", description="事件类型")
    content: str = Field(..., description="内容片段")
    agent: str | None = Field(None, description="智能体类型")
    message_id: str = Field(..., description="消息 ID")


class SSEDoneData(BaseModel):
    """SSE 完成事件"""

    type: str = Field("done", description="事件类型")
    message_id: str = Field(..., description="消息 ID")
    agent: str | None = Field(None, description="智能体类型")


class SSEErrorData(BaseModel):
    """SSE 错误事件"""

    type: str = Field("error", description="事件类型")
    code: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误消息")


class TaskCancelResponse(BaseModel):
    """任务取消响应"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="消息")


class UpdateModeResponse(BaseModel):
    """更新模式响应"""

    session_id: str = Field(..., description="会话 ID")
    mode: str = Field(..., description="新模式")
    topic: str | None = Field(None, description="会话主题")


class DeleteSessionResponse(BaseModel):
    """删除会话响应"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="消息")


class BatchDeleteRequest(BaseModel):
    """批量删除会话请求"""

    session_ids: list[str] = Field(..., min_length=1, description="要删除的会话 ID 列表")


class BatchDeleteResponse(BaseModel):
    """批量删除会话响应"""

    success: bool = Field(..., description="是否成功")
    deleted_count: int = Field(..., description="成功删除的数量")
    message: str = Field(..., description="消息")
