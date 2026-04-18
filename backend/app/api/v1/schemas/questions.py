"""题目管理相关的 Pydantic Schema"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class QuestionCreateRequest(BaseModel):
    """创建题目请求"""

    title: str = Field(..., min_length=1, max_length=500, description="题目分组（如：极限与连续、微分方程）")
    body: str = Field(..., min_length=1, description="题目内容（支持 LaTeX/Markdown）")
    type: str = Field(
        default="short_answer",
        description="题型：short_answer(简答题) | multiple_choice(选择题) | proof(证明题)",
    )
    difficulty: float = Field(
        default=0.5, ge=0.0, le=1.0, description="难度系数 [0, 1]"
    )
    concept_ids: list[str] = Field(default_factory=list, description="关联知识点 ID 列表")
    tags: list[str] = Field(default_factory=list, description="标签列表")
    answer: str = Field(..., description="标准答案（LaTeX 格式）")
    answer_type: str = Field(
        default="expression",
        description="答案类型：expression(表达式) | numeric(数值) | text(文本)",
    )
    hints: list[str] = Field(default_factory=list, description="提示列表（苏格拉底式引导）")
    solution_steps: list[str] = Field(default_factory=list, description="解题步骤")
    options: list[str] | None = Field(default=None, description="选择题选项（仅选择题需要）")
    estimated_time_seconds: int = Field(
        default=300, ge=0, description="预计答题时间���秒）"
    )


class QuestionUpdateRequest(BaseModel):
    """更新题目请求（所有字段可选）"""

    title: str | None = Field(None, min_length=1, max_length=500, description="题目分组")
    body: str | None = Field(None, min_length=1, description="题目内容")
    type: str | None = Field(None, description="题型")
    difficulty: float | None = Field(None, ge=0.0, le=1.0, description="难度系数")
    concept_ids: list[str] | None = Field(None, description="关联知识点 ID 列表")
    tags: list[str] | None = Field(None, description="标签列表")
    answer: str | None = Field(None, description="标准答案")
    answer_type: str | None = Field(None, description="答案类型")
    hints: list[str] | None = Field(None, description="提示列表")
    solution_steps: list[str] | None = Field(None, description="解题步骤")
    options: list[str] | None = Field(None, description="选择题选项")
    estimated_time_seconds: int | None = Field(None, ge=0, description="预计答题时间")
    status: str | None = Field(None, description="状态：draft | published | archived")


class QuestionResponse(BaseModel):
    """题目响应"""

    id: str
    title: str
    body: str
    type: str
    difficulty: float
    concept_ids: list[str]
    tags: list[str]
    status: str
    meta: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    usage_count: int = Field(default=0, description="使用次数（从 content_attempts 统计）")
    correct_rate: float = Field(default=0.0, description="正确率")

    class Config:
        from_attributes = True


class QuestionListRequest(BaseModel):
    """题目列表请求"""

    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")
    search: str | None = Field(None, description="搜索关键词（分组名、内容）")
    chapter: str | None = Field(None, description="章节筛选")
    difficulty: str | None = Field(
        None, description="难度筛选：easy(0-0.33) | medium(0.33-0.67) | hard(0.67-1)"
    )
    type: str | None = Field(None, description="题型筛选")
    status: str | None = Field(None, description="状态筛选：draft | published | archived")
    tags: list[str] = Field(default_factory=list, description="标签筛选")
    sort_by: str = Field(
        default="created_at", description="排序字段：created_at | difficulty | usage_count"
    )
    sort_order: str = Field(default="desc", description="排序方向：asc | desc")


class QuestionListResponse(BaseModel):
    """题目列表响应"""

    items: list[QuestionResponse]
    total: int
    page: int
    page_size: int


class BatchOperationRequest(BaseModel):
    """批量操作请求"""

    question_ids: list[str] = Field(..., min_length=1, max_length=100, description="题目 ID 列表")


class BatchOperationResponse(BaseModel):
    """批量操作响应"""

    success: int = Field(description="成功数量")
    failed: int = Field(description="失败数量")
    failed_ids: list[str] = Field(default_factory=list, description="失败的题目 ID 列表")
    errors: list[str] = Field(default_factory=list, description="错误信息列表")


class QuestionStatsResponse(BaseModel):
    """题目统计响应"""

    total: int
    by_difficulty: dict[str, int]
    by_type: dict[str, int]
    by_status: dict[str, int]


# ==================== 导入/导出相关 Schema ====================


class AIParseRequest(BaseModel):
    """AI 题目识别请求"""

    raw_texts: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="原始文本数组，每段最多 3000 字符",
    )


class AIParseQuestionItem(BaseModel):
    """AI 识别出的单个题目"""

    title: str = Field(default="", description="题目分组")
    body: str = Field(default="", description="题目内容（保留 LaTeX）")
    type: str = Field(default="short_answer", description="题型")
    difficulty: float = Field(default=0.5, ge=0.0, le=1.0, description="难度系数")
    answer: str = Field(default="", description="标准答案")
    answer_type: str = Field(default="expression", description="答案类型")
    options: list[str] | None = Field(default=None, description="选择题选项")
    hints: list[str] = Field(default_factory=list, description="提示列表")
    solution_steps: list[str] = Field(default_factory=list, description="解题步骤")
    tags: list[str] = Field(default_factory=list, description="标签列表")


class AIParseResponse(BaseModel):
    """AI 题目识别响应"""

    questions: list[AIParseQuestionItem]


class BatchImportRequest(BaseModel):
    """批量导入请求（前端解析后的 JSON 数组）"""

    questions: list[QuestionCreateRequest] = Field(
        ...,
        min_length=1,
        max_length=200,
        description="题目数组，最多 200 道",
    )


class QuestionGroupsResponse(BaseModel):
    """分组列表响应"""

    groups: list[str] = Field(description="去重后的分组名列表")
