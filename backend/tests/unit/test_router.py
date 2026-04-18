"""Agent router intent classification tests."""

from app.agents.core.router import IntentType, classify_intent, get_target_node


def test_resource_request_with_math_keyword_routes_to_tutor() -> None:
    intent = classify_intent("我想学习不定积分有没有资源推荐")

    assert intent == IntentType.TEACH
    assert get_target_node(intent) == "tutor"


def test_short_resource_query_with_math_keyword_routes_to_tutor() -> None:
    assert classify_intent("不定积分视频") == IntentType.TEACH


def test_solve_keyword_without_math_expression_routes_to_tutor() -> None:
    assert classify_intent("泰勒展开") == IntentType.TEACH
    assert classify_intent("什么是泰勒展开") == IntentType.TEACH
    assert classify_intent("不定积分一般求法") == IntentType.TEACH
    assert classify_intent("这份资料里的积分怎么求解") == IntentType.TEACH


def test_solve_keyword_with_math_expression_routes_to_solver() -> None:
    intent = classify_intent("求导 x^2")

    assert intent == IntentType.SOLVE
    assert get_target_node(intent) == "math_solver"
