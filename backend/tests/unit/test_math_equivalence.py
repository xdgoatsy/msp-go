"""
数学答案等价性引擎单元测试

测试 app/agents/core/math_equivalence.py 中的纯函数和异步函数
"""

import pytest

from app.agents.core.math_equivalence import (
    AnswerType,
    EquivalenceResult,
    VerifyLayer,
    _check_exact,
    _check_normalized,
    _check_numeric,
    _check_text,
    check_equivalence,
    detect_answer_type,
)

# ========== detect_answer_type ==========

class TestDetectAnswerType:
    def test_set_with_braces(self):
        # {1, 2, 3} 识别为集合
        assert detect_answer_type("{1, 2, 3}") == AnswerType.SET

    def test_set_with_latex_braces(self):
        # \{1, 2\} 识别为集合
        assert detect_answer_type("\\{1, 2\\}") == AnswerType.SET

    def test_interval_closed_open(self):
        # [0, 1) 识别为区间
        assert detect_answer_type("[0, 1)") == AnswerType.INTERVAL

    def test_interval_open_closed(self):
        # (a, b] 识别为区间
        assert detect_answer_type("(a, b]") == AnswerType.INTERVAL

    def test_interval_open_open(self):
        # (0, 1) 识别为区间
        assert detect_answer_type("(0, 1)") == AnswerType.INTERVAL

    def test_interval_closed_closed(self):
        # [0, 1] 识别为区间
        assert detect_answer_type("[0, 1]") == AnswerType.INTERVAL

    def test_equation_x_equals(self):
        # x = 5 识别为方程
        assert detect_answer_type("x = 5") == AnswerType.EQUATION

    def test_integer_numeric(self):
        # 整数识别为数值
        assert detect_answer_type("42") == AnswerType.NUMERIC

    def test_negative_numeric(self):
        # 负数识别为数值
        assert detect_answer_type("-3") == AnswerType.NUMERIC

    def test_decimal_numeric(self):
        # 小数识别为数值
        assert detect_answer_type("-3.14") == AnswerType.NUMERIC

    def test_numeric_with_math_delimiters(self):
        # 带行内公式分隔符的小数仍识别为数值
        assert detect_answer_type("$0.5$") == AnswerType.NUMERIC

    def test_chinese_text(self):
        # 中文文本识别为文本类型
        assert detect_answer_type("连续") == AnswerType.TEXT

    def test_expression_default(self):
        # 数学表达式识别为表达式类型
        assert detect_answer_type("x^2 + 1") == AnswerType.EXPRESSION

    def test_expression_with_fraction(self):
        # 含分数的表达式
        assert detect_answer_type("x/2 + 1") == AnswerType.EXPRESSION


# ========== _check_exact ==========

class TestCheckExact:
    def test_exact_match_returns_result(self):
        # 精确匹配返回置信度 1.0 的结果
        result = _check_exact("x^2", "x^2")
        assert result is not None
        assert result.is_equivalent is True
        assert result.confidence == 1.0

    def test_different_strings_returns_none(self):
        # 不同字符串返回 None
        result = _check_exact("x^2", "x^3")
        assert result is None

    def test_strips_whitespace_before_comparing(self):
        # 比较前去除首尾空白
        result = _check_exact("  x^2  ", "x^2")
        assert result is not None
        assert result.is_equivalent is True

    def test_layer_used_is_exact(self):
        # 使用的验证层为 EXACT
        result = _check_exact("42", "42")
        assert result is not None
        assert result.layer_used == VerifyLayer.EXACT

    def test_case_sensitive(self):
        # 精确匹配区分大小写
        result = _check_exact("X", "x")
        assert result is None


# ========== _check_normalized ==========

class TestCheckNormalized:
    def test_caret_vs_double_star(self):
        # x^2 和 x**2 标准化后相等
        result = _check_normalized("x^2 + 1", "x**2+1")
        assert result is not None
        assert result.is_equivalent is True

    def test_times_symbol_vs_star(self):
        # 2×3 和 2*3 标准化后相等
        result = _check_normalized("2×3", "2*3")
        assert result is not None
        assert result.is_equivalent is True

    def test_different_expressions_return_none(self):
        # 不同表达式标准化后仍不等，返回 None
        result = _check_normalized("x^2", "x^3")
        assert result is None

    def test_spaces_ignored(self):
        # 空格被忽略
        result = _check_normalized("x + y", "x+y")
        assert result is not None
        assert result.is_equivalent is True

    def test_layer_used_is_normalized(self):
        result = _check_normalized("x^2", "x**2")
        assert result is not None
        assert result.layer_used == VerifyLayer.NORMALIZED


# ========== _check_numeric ==========

class TestCheckNumeric:
    def test_equal_integers(self):
        # 相同整数匹配
        result = _check_numeric("42", "42")
        assert result is not None
        assert result.is_equivalent is True

    def test_equal_decimals(self):
        # 相同小数匹配
        result = _check_numeric("3.14", "3.14")
        assert result is not None
        assert result.is_equivalent is True

    def test_different_numbers_not_match(self):
        # 不同数值不匹配
        result = _check_numeric("100", "99")
        assert result is not None
        assert result.is_equivalent is False

    def test_non_numeric_returns_none(self):
        # 非数值字符串返回 None
        result = _check_numeric("x^2", "x^2")
        assert result is None

    def test_non_numeric_correct_returns_none(self):
        # 正确答案非数值时返回 None
        result = _check_numeric("42", "abc")
        assert result is None

    def test_confidence_1_for_match(self):
        # 匹配时置信度为 1.0
        result = _check_numeric("5", "5")
        assert result is not None
        assert result.confidence == 1.0

    def test_confidence_0_for_mismatch(self):
        # 不匹配时置信度为 0.0
        result = _check_numeric("1", "2")
        assert result is not None
        assert result.confidence == 0.0

    def test_decimal_matches_latex_fraction(self):
        # 小数和 LaTeX 分数值相同，应判为匹配
        result = _check_numeric("0.5", r"$\frac{1}{2}$")
        assert result is not None
        assert result.is_equivalent is True

    def test_plain_fraction_matches_latex_fraction(self):
        # 普通分数字符串和 LaTeX 分数值相同，应判为匹配
        result = _check_numeric("1/2", r"$\frac{1}{2}$")
        assert result is not None
        assert result.is_equivalent is True


# ========== _check_text ==========

class TestCheckText:
    def test_exact_chinese_match(self):
        # 中文文本精确匹配
        result = _check_text("连续", "连续")
        assert result is not None
        assert result.is_equivalent is True

    def test_whitespace_normalized(self):
        # 首尾空白被忽略
        result = _check_text("  连续  ", "连续")
        assert result is not None
        assert result.is_equivalent is True

    def test_case_insensitive(self):
        # 英文大小写不敏感
        result = _check_text("Continuous", "continuous")
        assert result is not None
        assert result.is_equivalent is True

    def test_different_text_not_match(self):
        # 不同文本不匹配
        result = _check_text("连续", "不连续")
        assert result is not None
        assert result.is_equivalent is False

    def test_always_returns_result(self):
        # _check_text 总是返回结果（不返回 None）
        result = _check_text("abc", "xyz")
        assert result is not None
        assert isinstance(result, EquivalenceResult)

    def test_layer_used_is_normalized(self):
        result = _check_text("连续", "连续")
        assert result is not None
        assert result.layer_used == VerifyLayer.NORMALIZED

    def test_confidence_1_for_match(self):
        result = _check_text("连续", "连续")
        assert result is not None
        assert result.confidence == 1.0

    def test_confidence_0_for_mismatch(self):
        result = _check_text("连续", "不连续")
        assert result is not None
        assert result.confidence == 0.0

# ========== check_equivalence (async) ==========

@pytest.mark.asyncio
class TestCheckEquivalence:
    async def test_empty_student_answer_returns_false(self):
        # 学生答案为空返回 is_equivalent=False
        result = await check_equivalence("", "x^2")
        assert result.is_equivalent is False

    async def test_empty_correct_answer_returns_false(self):
        # 正确答案为空返回 is_equivalent=False
        result = await check_equivalence("x^2", "")
        assert result.is_equivalent is False

    async def test_both_empty_returns_false(self):
        # 两者都为空返回 is_equivalent=False
        result = await check_equivalence("", "")
        assert result.is_equivalent is False

    async def test_exact_match_works(self):
        # 精确匹配有效
        result = await check_equivalence("x^2 + 1", "x^2 + 1")
        assert result.is_equivalent is True
        assert result.confidence == 1.0

    async def test_auto_detects_numeric_type(self):
        # 自动检测数值类型并比较
        result = await check_equivalence("42", "42")
        assert result.is_equivalent is True

    async def test_numeric_mismatch(self):
        # 数值不匹配
        result = await check_equivalence("1", "2")
        assert result.is_equivalent is False

    async def test_returns_equivalence_result(self):
        # 返回 EquivalenceResult 实例
        result = await check_equivalence("x", "x")
        assert isinstance(result, EquivalenceResult)
        assert hasattr(result, "is_equivalent")
        assert hasattr(result, "confidence")
        assert hasattr(result, "reason")
        assert hasattr(result, "layer_used")

    async def test_normalized_match(self):
        # 标准化后匹配（x^2 vs x**2）
        result = await check_equivalence("x^2", "x**2")
        assert result.is_equivalent is True

    @pytest.mark.parametrize(
        "student_answer",
        ["0.5", "1/2", r"\frac{1}{2}", r"$\frac{1}{2}$"],
    )
    async def test_fraction_formats_match_latex_fraction(self, student_answer):
        # 学生不必精确输入标准答案的 LaTeX 包裹格式
        result = await check_equivalence(student_answer, r"$\frac{1}{2}$")
        assert result.is_equivalent is True
