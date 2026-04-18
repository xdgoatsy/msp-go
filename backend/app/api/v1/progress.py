"""
学习进度接口

提供学生知识掌握度和学习路径信息
"""

from fastapi import APIRouter, Query

from app.api.deps import CurrentUserId, DbSession
from app.api.v1.schemas.progress import ClassRankingResponse
from app.domain.models.knowledge_node import NodeType
from app.infrastructure.repositories.knowledge_repository import KnowledgeRepository
from app.services.progress_service import ProgressService

router = APIRouter()


def get_progress_service(db: DbSession) -> ProgressService:
    return ProgressService(db)


@router.get("/overview")
async def get_progress_overview(
    db: DbSession,
    user_id: CurrentUserId,
) -> dict:
    """获取学习进度概览：做题数、正确率、学习时长、连续打卡、掌握概念数"""
    service = get_progress_service(db)
    return await service.get_overview(user_id)


@router.get("/mastery")
async def get_mastery_vector(
    db: DbSession,
    user_id: CurrentUserId,
) -> dict:
    """获取知识点掌握度向量，供学习统计页使用"""
    service = get_progress_service(db)
    return await service.get_mastery_vector(user_id)


@router.get("/path")
async def get_learning_path(
    db: DbSession,
    user_id: CurrentUserId,
    target: str | None = Query(None, description="目标知识点 ID（可选）"),
) -> dict:
    """
    获取个性化学习路径

    基于 BKT 掌握度和知识图谱前置关系生成推荐学习顺序
    """
    service = get_progress_service(db)
    return await service.get_learning_path(user_id, target=target)


@router.get("/knowledge-graph")
async def get_knowledge_graph_view(
    db: DbSession,
    user_id: CurrentUserId,
    chapter: str | None = Query(None, description="章节筛选"),
    type: str | None = Query(None, description="节点类型筛选 (concept/theorem/method)"),
    search: str | None = Query(None, description="搜索关键词"),
) -> dict:
    """
    获取知识图谱可视化数据

    返回适合前端渲染的知识图谱结构

    Args:
        chapter: 章节筛选（可选）
        type: 节点类型筛选（可选）
        search: 搜索关键词（可选）

    Returns:
        包含 nodes, edges, statistics 的字典
    """
    service = ProgressService(db)

    # 类型转换
    node_type = None
    if type:
        type_map = {
            "concept": NodeType.CONCEPT,
            "theorem": NodeType.THEOREM,
            "method": NodeType.METHOD,
        }
        node_type = type_map.get(type)

    return await service.get_knowledge_graph_view(
        user_id=user_id,
        chapter=chapter,
        node_type=node_type,
        search=search,
    )


@router.get("/statistics")
async def get_learning_statistics(
    db: DbSession,
    user_id: CurrentUserId,
    range: str = Query(
        "week",
        description="统计范围: week=当前周, month=当前月, semester=当前学期, all=近一年",
    ),
) -> dict:
    """获取学习统计数据，支持当前周/当前月/当前学期/近一年"""
    service = get_progress_service(db)
    return await service.get_statistics(user_id, range_type=range)


@router.get("/class-ranking", response_model=ClassRankingResponse)
async def get_class_ranking(
    db: DbSession,
    user_id: CurrentUserId,
) -> ClassRankingResponse:
    """获取当前学生在所在班级中的排名（按学习时长、做题数）"""
    service = get_progress_service(db)
    data = await service.get_class_ranking(user_id)
    return ClassRankingResponse(**data)


@router.get("/chapters")
async def get_chapters(
    db: DbSession,
    _user_id: CurrentUserId,
) -> dict:
    """
    获取所有章节列表

    从知识节点中聚合不重复的章节名称，供前端动态构建筛选选项
    """
    repo = KnowledgeRepository(db)
    chapters = await repo.get_distinct_chapters()
    return {"chapters": chapters}
