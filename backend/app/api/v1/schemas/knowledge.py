"""
知识点管理 API Schema

定义知识节点和关系的 CRUD 接口数据结构
"""

from datetime import datetime

from pydantic import BaseModel, Field

# ========== 知识节点 Schema ==========


class KnowledgeNodeItem(BaseModel):
    """知识节点列表项"""

    id: str = Field(..., description="节点 ID")
    name: str = Field(..., description="名称")
    name_en: str | None = Field(None, description="英文名称")
    node_type: str = Field(..., description="节点类型")
    description: str = Field("", description="描述")
    chapter: str | None = Field(None, description="章节")
    section: str | None = Field(None, description="小节")
    difficulty: float = Field(0.5, description="难度系数 (0-1)")
    latex_formula: str | None = Field(None, description="LaTeX 公式")
    tags: list[str] = Field(default_factory=list, description="标签")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = {"from_attributes": True}


class KnowledgeNodeListResponse(BaseModel):
    """知识节点列表响应（分页）"""

    items: list[KnowledgeNodeItem] = Field(..., description="节点列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    total_pages: int = Field(..., description="总页数")


class KnowledgeNodeCreateRequest(BaseModel):
    """创建知识节点请求"""

    name: str = Field(..., min_length=1, max_length=200, description="名称")
    name_en: str | None = Field(None, max_length=200, description="英文名称")
    node_type: str = Field(
        ...,
        pattern=r"^(concept|theorem|method|problem|misconception|resource)$",
        description="节点类型",
    )
    description: str = Field("", max_length=2000, description="描述")
    chapter: str | None = Field(None, max_length=100, description="章节")
    section: str | None = Field(None, max_length=100, description="小节")
    difficulty: float = Field(0.5, ge=0.0, le=1.0, description="难度系数")
    latex_formula: str | None = Field(None, description="LaTeX 公式")
    tags: list[str] = Field(default_factory=list, description="标签")


class KnowledgeNodeUpdateRequest(BaseModel):
    """更新知识节点请求（所有字段可选）"""

    name: str | None = Field(None, min_length=1, max_length=200, description="名称")
    name_en: str | None = Field(None, max_length=200, description="英文名称")
    node_type: str | None = Field(
        None,
        pattern=r"^(concept|theorem|method|problem|misconception|resource)$",
        description="节点类型",
    )
    description: str | None = Field(None, max_length=2000, description="描述")
    chapter: str | None = Field(None, max_length=100, description="章节")
    section: str | None = Field(None, max_length=100, description="小节")
    difficulty: float | None = Field(None, ge=0.0, le=1.0, description="难度系数")
    latex_formula: str | None = Field(None, description="LaTeX 公式")
    tags: list[str] | None = Field(None, description="标签")


class KnowledgeNodeResponse(BaseModel):
    """知识节点操作响应"""

    success: bool = Field(True, description="是否成功")
    message: str = Field(..., description="消息")
    node: KnowledgeNodeItem | None = Field(None, description="节点信息")


class KnowledgeNodeDeleteResponse(BaseModel):
    """删除知识节点响应"""

    success: bool = Field(True, description="是否成功")
    message: str = Field(..., description="消息")


# ========== 知识关系 Schema ==========


class KnowledgeRelationItem(BaseModel):
    """知识关系列表项"""

    id: str = Field(..., description="关系 ID")
    source_id: str = Field(..., description="源节点 ID")
    target_id: str = Field(..., description="目标节点 ID")
    source_name: str | None = Field(None, description="源节点名称")
    target_name: str | None = Field(None, description="目标节点名称")
    relation_type: str = Field(..., description="关系类型")
    weight: float = Field(1.0, description="权重")
    description: str | None = Field(None, description="描述")
    created_at: datetime = Field(..., description="创建时间")

    model_config = {"from_attributes": True}


class KnowledgeRelationListResponse(BaseModel):
    """知识关系列表响应"""

    items: list[KnowledgeRelationItem] = Field(..., description="关系列表")
    total: int = Field(..., description="总数")


class KnowledgeRelationCreateRequest(BaseModel):
    """创建知识关系请求"""

    source_id: str = Field(..., description="源节点 ID")
    target_id: str = Field(..., description="目标节点 ID")
    relation_type: str = Field(
        ...,
        pattern=r"^(has_prerequisite|is_a_special_case_of|used_in|prone_to_error|related_to)$",
        description="关系类型",
    )
    weight: float = Field(1.0, ge=0.0, le=1.0, description="权重")
    description: str | None = Field(None, max_length=500, description="描述")


class KnowledgeRelationUpdateRequest(BaseModel):
    """更新知识关系请求"""

    relation_type: str | None = Field(
        None,
        pattern=r"^(has_prerequisite|is_a_special_case_of|used_in|prone_to_error|related_to)$",
        description="关系类型",
    )
    weight: float | None = Field(None, ge=0.0, le=1.0, description="权重")
    description: str | None = Field(None, max_length=500, description="描述")


class KnowledgeRelationResponse(BaseModel):
    """知识关系操作响应"""

    success: bool = Field(True, description="是否成功")
    message: str = Field(..., description="消息")
    relation: KnowledgeRelationItem | None = Field(None, description="关系信息")


class KnowledgeRelationDeleteResponse(BaseModel):
    """删除知识关系响应"""

    success: bool = Field(True, description="是否成功")
    message: str = Field(..., description="消息")


# ========== 公共 Schema ==========


class ChapterListResponse(BaseModel):
    """章节列表响应"""

    chapters: list[str] = Field(..., description="章节列表")


class SimpleNodeItem(BaseModel):
    """简要节点信息（用于下拉选择和图谱视图）"""

    id: str = Field(..., description="节点 ID")
    name: str = Field(..., description="名称")
    chapter: str | None = Field(None, description="章节")
    node_type: str | None = Field(None, description="节点类型")

    model_config = {"from_attributes": True}


class KnowledgeStatsResponse(BaseModel):
    """知识点统计响应"""

    total_nodes: int = Field(..., description="节点总数")
    total_relations: int = Field(..., description="关系总数")
    chapters_count: int = Field(..., description="章节数")
    type_distribution: dict[str, int] = Field(..., description="类型分布")
