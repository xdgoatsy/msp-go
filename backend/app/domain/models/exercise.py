"""
练习诊断领域模型

定义错误类型和诊断报告实体
注意：Exercise 已重构为 Content，参见 content.py
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ErrorType(str, Enum):
    """
    错误类型

    参考规划文档 5.1 数学错误分类学
    """

    CONCEPTUAL = "conceptual"  # 概念性错误
    PROCEDURAL = "procedural"  # 过程性错误
    LOGICAL = "logical"  # 逻辑错误
    SYMBOLIC = "symbolic"  # 符号错误
    CALCULATION = "calculation"  # 计算错误


@dataclass
class DiagnosisReport:
    """
    诊断报告

    由诊断智能体生成的错误分析
    """

    id: str
    attempt_id: str

    # 错误定位
    error_step_index: int | None = None  # 出错步骤索引
    bifurcation_point: str | None = None  # 分歧点描述

    # 错误分类
    error_type: ErrorType | None = None
    error_subtype: str | None = None  # 细分类型

    # 严重程度
    severity: str = "medium"  # low, medium, high

    # 关联知识点
    related_concept_ids: list[str] = field(default_factory=list)

    # 关联迷思概念
    related_misconception_ids: list[str] = field(default_factory=list)

    # 诊断说明
    explanation: str = ""

    # 建议
    suggestion: str = ""
    recommended_resources: list[str] = field(default_factory=list)

    created_at: datetime = field(default_factory=datetime.now)
