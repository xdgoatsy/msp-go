"""
领域模型包

定义核心业务实体
"""

from app.domain.models.bkt import BKTParameters, BKTUpdateResult
from app.domain.models.content import (
    AclPermission,
    AssetKind,
    AuditAction,
    Content,
    ContentAcl,
    ContentAsset,
    ContentAudit,
    ContentStatus,
    ContentType,
    ImportJob,
    ImportJobKind,
    ImportJobStatus,
    OutboxEvent,
    OutboxEventType,
)
from app.domain.models.embedding import (
    ContentEmbedding,
    DistanceMetric,
    EmbeddingModel,
)
from app.domain.models.exercise import DiagnosisReport, ErrorType
from app.domain.models.knowledge_node import KnowledgeNode, KnowledgeRelation
from app.domain.models.learning_session import LearningSession, SessionMessage
from app.domain.models.student import Student, StudentProfile

__all__ = [
    # Student
    "Student",
    "StudentProfile",
    # Knowledge
    "KnowledgeNode",
    "KnowledgeRelation",
    # Content
    "Content",
    "ContentType",
    "ContentStatus",
    "ContentAsset",
    "AssetKind",
    "ContentAcl",
    "AclPermission",
    "ContentAudit",
    "AuditAction",
    "ImportJob",
    "ImportJobKind",
    "ImportJobStatus",
    "OutboxEvent",
    "OutboxEventType",
    # Diagnosis
    "ErrorType",
    "DiagnosisReport",
    # Embedding
    "EmbeddingModel",
    "DistanceMetric",
    "ContentEmbedding",
    # Session
    "LearningSession",
    "SessionMessage",
    # BKT
    "BKTParameters",
    "BKTUpdateResult",
]
