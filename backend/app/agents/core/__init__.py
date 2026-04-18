"""
基础设施层导出入口。

为了避免在应用启动阶段无意加载 LLM 重依赖，
该模块改为惰性导出：仅在访问符号时再导入对应子模块。
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
    "merge_dicts": "app.agents.core.state",
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
    "format_latex": "app.agents.core.utils",
    "parse_latex_safe": "app.agents.core.utils",
    "clean_latex": "app.agents.core.utils",
    "extract_latex_blocks": "app.agents.core.utils",
    "extract_code_block": "app.agents.core.utils",
    "validate_python_syntax": "app.agents.core.utils",
    "truncate_text": "app.agents.core.utils",
    "truncate_history": "app.agents.core.utils",
    "format_conversation_history": "app.agents.core.utils",
    "parse_steps": "app.agents.core.utils",
    "format_steps": "app.agents.core.utils",
    "normalize_math_expression": "app.agents.core.utils",
    "is_math_expression": "app.agents.core.utils",
    "get_error_type_description": "app.agents.core.utils",
    "detect_emotion_keywords": "app.agents.core.utils",
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
