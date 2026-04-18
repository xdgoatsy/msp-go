"""
向量嵌入领域模型

定义 Embedding 模型版本管理和内容向量
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class DistanceMetric(str, Enum):
    """向量距离度量"""

    COSINE = "cosine"  # 余弦相似度（推荐，需归一化）
    L2 = "l2"  # 欧氏距离
    IP = "ip"  # 内积


@dataclass
class EmbeddingModel:
    """
    Embedding 模型版本

    管理不同维度/版本的 embedding 模型
    约束：同时只能有一个 is_active=True 的模型用于在线写入
    """

    name: str  # 模型名称，如 "text-embedding-3-small"
    dim: int  # 向量维度，如 1536
    distance: DistanceMetric  # 距离度量方式
    is_active: bool = False  # 是否为当前活跃模型

    created_at: datetime = field(default_factory=datetime.now)
    description: str = ""  # 模型描述


@dataclass
class ContentEmbedding:
    """
    内容向量

    存储内容的 embedding 向量
    """

    content_id: str  # 关联的内容 ID
    embedding: list[float]  # 向量数据
    model_name: str  # 使用的模型名称

    updated_at: datetime = field(default_factory=datetime.now)

    @property
    def dim(self) -> int:
        """向量维度"""
        return len(self.embedding)
