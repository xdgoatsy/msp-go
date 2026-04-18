"""
知识图谱领域模型

定义知识节点和关系实体，对应 HM-KG（高等数学知识图谱）
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class NodeType(str, Enum):
    """
    知识节点类型

    参考规划文档 2.1.1 核心实体类型
    """

    CONCEPT = "concept"  # 概念：数学知识的基本单元
    THEOREM = "theorem"  # 定理：连接概念的形式化命题
    METHOD = "method"  # 方法：解决特定问题的算法流程
    PROBLEM = "problem"  # 习题：用于评估的具体题目
    MISCONCEPTION = "misconception"  # 迷思：学生常见的认知错误模式
    RESOURCE = "resource"  # 资源：教学媒体实体


class RelationType(str, Enum):
    """
    知识关系类型

    参考规划文档 2.1.2 语义关系
    """

    HAS_PREREQUISITE = "has_prerequisite"  # 先修关系
    IS_A_SPECIAL_CASE_OF = "is_a_special_case_of"  # 特例关系
    USED_IN = "used_in"  # 应用于
    PRONE_TO_ERROR = "prone_to_error"  # 易错连接
    RELATED_TO = "related_to"  # 一般关联


@dataclass
class KnowledgeNode:
    """
    知识节点实体

    知识图谱的基本单元
    """

    id: str
    name: str
    name_en: str | None  # 英文名称
    node_type: NodeType
    description: str = ""

    # 所属章节/模块
    chapter: str | None = None
    section: str | None = None

    # 难度系数 (0-1)
    difficulty: float = 0.5

    # LaTeX 公式表示（如果适用）
    latex_formula: str | None = None

    # 向量嵌入（用于语义检索）
    embedding: list[float] | None = None

    # 元数据
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class KnowledgeRelation:
    """
    知识关系实体

    连接两个知识节点
    """

    id: str
    source_id: str  # 源节点 ID
    target_id: str  # 目标节点 ID
    relation_type: RelationType

    # 关系权重/强度 (0-1)
    weight: float = 1.0

    # 关系描述
    description: str | None = None

    # 元数据
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class LearningPath:
    """
    学习路径

    由知识节点组成的有序序列
    """

    id: str
    student_id: str
    target_concept_id: str  # 目标知识点

    # 路径节点序列
    node_sequence: list[str] = field(default_factory=list)

    # 当前进度（已完成的节点索引）
    current_index: int = 0

    # 预估练习题数量
    estimated_exercises: int = 0

    # 状态
    is_completed: bool = False

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @property
    def progress(self) -> float:
        """学习进度 (0-1)"""
        if not self.node_sequence:
            return 0.0
        return self.current_index / len(self.node_sequence)

    @property
    def current_node_id(self) -> str | None:
        """当前学习的节点"""
        if self.current_index < len(self.node_sequence):
            return self.node_sequence[self.current_index]
        return None
