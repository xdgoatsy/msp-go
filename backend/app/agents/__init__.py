"""
AI/多智能体包导出入口。

为避免启动阶段被动导入整套 LangGraph/LLM 依赖，
使用惰性导出机制，仅在访问符号时再导入对应模块。
"""

from importlib import import_module
from typing import Any

_SYMBOL_TO_MODULE: dict[str, str] = {
    "AgentType": "app.agents.core.base",
    "AgentOutput": "app.agents.core.base",
    "AgentError": "app.agents.core.base",
    "BaseAgent": "app.agents.core.base",
    "StreamingState": "app.agents.core.state",
    "create_initial_state": "app.agents.core.state",
    "update_state": "app.agents.core.state",
    "add_message": "app.agents.core.state",
    "get_recent_messages": "app.agents.core.state",
    "get_conversation_context": "app.agents.core.state",
    "LLMClient": "app.agents.core.llm_client",
    "LLMClientError": "app.agents.core.llm_client",
    "create_llm_client": "app.agents.core.llm_client",
    "CacheManager": "app.agents.core.cache",
    "CacheError": "app.agents.core.cache",
    "hash_problem": "app.agents.core.cache",
    "make_cache_key": "app.agents.core.cache",
    "get_solver_cache": "app.agents.core.cache",
    "get_profile_cache": "app.agents.core.cache",
    "IntentType": "app.agents.core.router",
    "classify_intent": "app.agents.core.router",
    "get_target_node": "app.agents.core.router",
    "MathSolverAgent": "app.agents.roles.math_solver",
    "SolverResult": "app.agents.roles.math_solver",
    "SymPySolver": "app.agents.roles.math_solver",
    "check_code_safety": "app.agents.roles.math_solver",
    "TutorAgent": "app.agents.roles.tutor",
    "TutorMode": "app.agents.roles.tutor",
    "TutorResponse": "app.agents.roles.tutor",
    "DiagnosticianAgent": "app.agents.roles.diagnostician",
    "DiagnosisResult": "app.agents.roles.diagnostician",
    "ErrorType": "app.agents.roles.diagnostician",
    "StepAligner": "app.agents.roles.diagnostician",
    "ErrorClassifier": "app.agents.roles.diagnostician",
    "TrackerAgent": "app.agents.roles.tracker",
    "create_workflow": "app.agents.workflow",
    "compile_workflow": "app.agents.workflow",
    "get_workflow_app": "app.agents.workflow",
    "get_workflow_app_async": "app.agents.workflow",
    "run_workflow": "app.agents.workflow",
    "stream_workflow": "app.agents.workflow",
    "CONTENT_AGENTS": "app.agents.workflow",
}

__all__ = list(_SYMBOL_TO_MODULE.keys())


def __getattr__(name: str) -> Any:
    module_name = _SYMBOL_TO_MODULE.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(module_name)
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals().keys()) | set(__all__))
