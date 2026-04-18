"""
LangGraph 工作流模块

4 节点统一工作流：entry → [math_solver|tutor|diagnostician] → tracker → END

模块结构：
- nodes.py: 节点定义
- edges.py: 边与路由
- graph.py: 工作流编译
"""

from app.agents.workflow.edges import (
    route_by_intent,
)
from app.agents.workflow.graph import (
    CONTENT_AGENTS,
    compile_workflow,
    create_workflow,
    get_workflow_app,
    get_workflow_app_async,
    run_workflow,
    stream_workflow,
)
from app.agents.workflow.nodes import (
    diagnostician_node,
    entry_node,
    math_solver_node,
    tracker_node,
    tutor_node,
)

__all__ = [
    # 工作流
    "create_workflow",
    "compile_workflow",
    "get_workflow_app",
    "get_workflow_app_async",
    "run_workflow",
    "stream_workflow",
    "CONTENT_AGENTS",
    # 节点
    "entry_node",
    "math_solver_node",
    "tutor_node",
    "diagnostician_node",
    "tracker_node",
    # 路由
    "route_by_intent",
]
