"""
智能体工具函数单元测试

测试 app/agents/core/utils.py 中的纯函数
"""


from app.agents.core.utils import (
    clean_latex,
    detect_emotion_keywords,
    estimate_difficulty,
    extract_code_block,
    extract_concepts_from_text,
    extract_latex_blocks,
    format_conversation_history,
    format_steps,
    get_error_type_description,
    is_math_expression,
    normalize_math_expression,
    parse_steps,
    truncate_history,
    truncate_text,
    validate_python_syntax,
)

# ========== clean_latex ==========

class TestCleanLatex:
    def test_removes_multiple_spaces(self):
        # 多个空格应被合并为一个
        assert clean_latex("a  b   c") == "a b c"

    def test_removes_latex_comments(self):
        # % 后的内容应被移除
        assert clean_latex("x^2 % this is a comment") == "x^2"

    def test_removes_multiline_comments(self):
        # 多行注释都应被移除
        result = clean_latex("a % comment1\nb % comment2")
        assert "comment1" not in result
        assert "comment2" not in result

    def test_strips_whitespace(self):
        # 首尾空白应被去除
        assert clean_latex("  hello  ") == "hello"

    def test_empty_string(self):
        assert clean_latex("") == ""

    def test_no_changes_needed(self):
        assert clean_latex("x^2+1") == "x^2+1"


# ========== extract_latex_blocks ==========

class TestExtractLatexBlocks:
    def test_extracts_inline_math(self):
        # 提取 $...$ 行内公式
        blocks = extract_latex_blocks("这是 $x^2$ 的例子")
        assert len(blocks) == 1
        assert "x^2" in blocks[0]

    def test_extracts_display_math(self):
        # 提取 $$...$$ 展示公式
        blocks = extract_latex_blocks("公式 $$\\int_0^1 x dx$$ 如下")
        assert len(blocks) == 1
        assert "\\int_0^1 x dx" in blocks[0]

    def test_handles_mixed_inline_and_display(self):
        # 同时包含行内和展示公式
        blocks = extract_latex_blocks("$a$ 和 $$b$$")
        assert len(blocks) == 2

    def test_returns_empty_for_no_math(self):
        # 无数学公式时返回空列表
        assert extract_latex_blocks("普通文本") == []

    def test_cleans_extracted_blocks(self):
        # 提取的块应经过 clean_latex 处理
        blocks = extract_latex_blocks("$x  +  y$")
        assert blocks[0] == "x + y"

    def test_display_math_not_duplicated(self):
        # $$...$$ 不应被当作两个 $...$ 重复提取
        blocks = extract_latex_blocks("$$x^2$$")
        assert len(blocks) == 1


# ========== extract_code_block ==========

class TestExtractCodeBlock:
    def test_extracts_python_block(self):
        # 提取 ```python ... ``` 代码块
        text = "```python\nprint('hello')\n```"
        result = extract_code_block(text)
        assert result == "print('hello')"

    def test_extracts_py_shorthand(self):
        # 提取 ```py ... ``` 代码块
        text = "```py\nx = 1\n```"
        result = extract_code_block(text)
        assert result == "x = 1"

    def test_extracts_generic_block(self):
        # 提取无语言标记的代码块
        text = "```\nsome code\n```"
        result = extract_code_block(text)
        assert result == "some code"

    def test_returns_none_when_not_found(self):
        # 无代码块时返回 None
        assert extract_code_block("no code here") is None

    def test_strips_whitespace_from_code(self):
        # 提取的代码应去除首尾空白
        text = "```python\n\n  x = 1  \n\n```"
        result = extract_code_block(text)
        assert result == "x = 1"

    def test_multiline_code(self):
        # 多行代码块
        text = "```python\ndef foo():\n    return 1\n```"
        result = extract_code_block(text)
        assert "def foo():" in result
        assert "return 1" in result


# ========== validate_python_syntax ==========

class TestValidatePythonSyntax:
    def test_valid_python_returns_true_none(self):
        # 有效 Python 代码返回 (True, None)
        valid, err = validate_python_syntax("x = 1 + 2")
        assert valid is True
        assert err is None

    def test_invalid_python_returns_false_with_message(self):
        # 无效 Python 代码返回 (False, 错误信息)
        valid, err = validate_python_syntax("def foo(:\n    pass")
        assert valid is False
        assert err is not None
        assert "语法错误" in err

    def test_empty_string_is_valid(self):
        # 空字符串是有效的 Python
        valid, err = validate_python_syntax("")
        assert valid is True
        assert err is None

    def test_complex_valid_code(self):
        code = "def foo(x):\n    return x ** 2\nresult = foo(3)"
        valid, err = validate_python_syntax(code)
        assert valid is True
        assert err is None


# ========== truncate_text ==========

class TestTruncateText:
    def test_short_text_unchanged(self):
        # 短文本不截断
        assert truncate_text("hello", 10) == "hello"

    def test_long_text_truncated_with_suffix(self):
        # 长文本截断并加后缀
        result = truncate_text("a" * 100, 10)
        assert result.endswith("...")
        assert len(result) == 10

    def test_custom_suffix(self):
        # 自定义后缀
        result = truncate_text("a" * 20, 10, suffix="…")
        assert result.endswith("…")

    def test_exact_boundary_length(self):
        # 恰好等于最大长度时不截断
        text = "a" * 500
        assert truncate_text(text, 500) == text

    def test_default_max_length(self):
        # 默认最大长度 500
        long_text = "x" * 600
        result = truncate_text(long_text)
        assert len(result) == 500
        assert result.endswith("...")


# ========== truncate_history ==========

class TestTruncateHistory:
    def test_short_history_unchanged(self):
        # 短历史不截断
        history = [{"role": "user", "content": str(i)} for i in range(5)]
        assert truncate_history(history, 10) == history

    def test_long_history_keeps_last_n(self):
        # 长历史保留最后 N 条
        history = [{"role": "user", "content": str(i)} for i in range(20)]
        result = truncate_history(history, 10)
        assert len(result) == 10
        # 保留的是最后 10 条
        assert result[0]["content"] == "10"
        assert result[-1]["content"] == "19"

    def test_exact_boundary(self):
        history = [{"role": "user", "content": str(i)} for i in range(10)]
        assert truncate_history(history, 10) == history


# ========== format_conversation_history ==========

class TestFormatConversationHistory:
    def test_formats_messages_as_role_content(self):
        # 格式化为 "role: content"
        history = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！"},
        ]
        result = format_conversation_history(history)
        assert "user: 你好" in result
        assert "assistant: 你好！" in result

    def test_truncates_long_content(self):
        # 过长内容被截断
        history = [{"role": "user", "content": "x" * 300}]
        result = format_conversation_history(history)
        # 内容被截断到 200 字符
        assert len(result) < 300

    def test_limits_message_count(self):
        # 限制消息数量
        history = [{"role": "user", "content": str(i)} for i in range(20)]
        result = format_conversation_history(history, max_messages=5)
        lines = result.strip().split("\n")
        assert len(lines) == 5

    def test_empty_history(self):
        assert format_conversation_history([]) == ""


# ========== parse_steps ==========

class TestParseSteps:
    def test_parses_numbered_steps(self):
        # 解析数字编号步骤
        text = "1. 第一步\n2. 第二步\n3. 第三步"
        steps = parse_steps(text)
        assert len(steps) == 3
        assert steps[0] == "第一步"
        assert steps[1] == "第二步"

    def test_parses_latex_line_breaks(self):
        # 解析 LaTeX 换行符 \\
        text = "步骤一\\\\步骤二\\\\步骤三"
        steps = parse_steps(text)
        assert len(steps) == 3
        assert steps[0] == "步骤一"

    def test_parses_plain_newlines(self):
        # 无编号的纯文本行会被合并为一个步骤（因为 parse_steps 优先按编号分割）
        text = "行一\n行二\n行三"
        steps = parse_steps(text)
        # 没有编号时，所有行合并为一个步骤
        assert len(steps) == 1
        assert "行一" in steps[0]

    def test_handles_empty_input(self):
        # 空输入返回空列表
        assert parse_steps("") == []

    def test_ignores_blank_lines(self):
        # 忽略空行
        text = "1. 步骤一\n\n2. 步骤二"
        steps = parse_steps(text)
        assert len(steps) == 2


# ========== format_steps ==========

class TestFormatSteps:
    def test_numbered_format(self):
        # 带编号格式
        steps = ["步骤一", "步骤二", "步骤三"]
        result = format_steps(steps, numbered=True)
        assert "1. 步骤一" in result
        assert "2. 步骤二" in result
        assert "3. 步骤三" in result

    def test_unnumbered_format(self):
        # 不带编号格式
        steps = ["步骤一", "步骤二"]
        result = format_steps(steps, numbered=False)
        assert "1." not in result
        assert "步骤一" in result
        assert "步骤二" in result

    def test_empty_steps(self):
        assert format_steps([]) == ""


# ========== normalize_math_expression ==========

class TestNormalizeMathExpression:
    def test_removes_spaces(self):
        # 移除空格
        assert normalize_math_expression("x + y") == "x+y"

    def test_converts_times_to_star(self):
        # × 转换为 *
        assert normalize_math_expression("2×3") == "2*3"

    def test_converts_div_to_slash(self):
        # ÷ 转换为 /
        assert normalize_math_expression("6÷2") == "6/2"

    def test_converts_caret_to_double_star(self):
        # ^ 转换为 **
        assert normalize_math_expression("x^2") == "x**2"

    def test_lowercases(self):
        # 转换为小写
        assert normalize_math_expression("X+Y") == "x+y"

    def test_combined_normalization(self):
        # 综合标准化
        result = normalize_math_expression("x^2 + 2×x")
        assert result == "x**2+2*x"


# ========== is_math_expression ==========

class TestIsMathExpression:
    def test_detects_plus_sign(self):
        assert is_math_expression("a + b") is True

    def test_detects_equals_sign(self):
        assert is_math_expression("x = 5") is True

    def test_detects_power_sign(self):
        assert is_math_expression("x^2") is True

    def test_detects_latex_frac(self):
        # 检测 LaTeX 命令
        assert is_math_expression("\\frac{1}{2}") is True

    def test_detects_latex_sqrt(self):
        assert is_math_expression("\\sqrt{x}") is True

    def test_detects_latex_int(self):
        assert is_math_expression("\\int_0^1") is True

    def test_returns_false_for_plain_text(self):
        # 纯文本返回 False
        assert is_math_expression("这是普通文本") is False

    def test_detects_multiplication(self):
        assert is_math_expression("2 * 3") is True


# ========== get_error_type_description ==========

class TestGetErrorTypeDescription:
    def test_conceptual_error(self):
        desc = get_error_type_description("conceptual")
        assert "概念" in desc

    def test_procedural_error(self):
        desc = get_error_type_description("procedural")
        assert "过程" in desc

    def test_logical_error(self):
        desc = get_error_type_description("logical")
        assert "逻辑" in desc

    def test_symbolic_error(self):
        desc = get_error_type_description("symbolic")
        assert "符号" in desc

    def test_calculation_error(self):
        desc = get_error_type_description("calculation")
        assert "计算" in desc

    def test_unknown_type_returns_default(self):
        # 未知类型返回默认描述
        desc = get_error_type_description("unknown_xyz")
        assert "未知错误类型" in desc

    def test_case_insensitive(self):
        # 大小写不敏感
        desc = get_error_type_description("CONCEPTUAL")
        assert "概念" in desc


# ========== detect_emotion_keywords ==========

class TestDetectEmotionKeywords:
    def test_detects_frustration(self):
        # 检测挫败感关键词
        result = detect_emotion_keywords("我不懂这道题，太难了")
        assert result["frustration"] > 0

    def test_detects_confusion(self):
        # 检测困惑关键词
        result = detect_emotion_keywords("这是什么意思？为什么这样？")
        assert result["confusion"] > 0

    def test_detects_positive(self):
        # 检测积极关键词
        result = detect_emotion_keywords("我懂了！明白了，谢谢")
        assert result["positive"] > 0

    def test_scores_between_0_and_1(self):
        # 分数在 0 到 1 之间
        result = detect_emotion_keywords("不懂 太难 什么意思 懂了")
        for score in result.values():
            assert 0.0 <= score <= 1.0

    def test_neutral_text_has_zero_scores(self):
        # 中性文本各分数为 0
        result = detect_emotion_keywords("今天天气不错")
        assert result["frustration"] == 0.0
        assert result["confusion"] == 0.0
        assert result["positive"] == 0.0

    def test_returns_all_three_keys(self):
        result = detect_emotion_keywords("test")
        assert "frustration" in result
        assert "confusion" in result
        assert "positive" in result


# ========== extract_concepts_from_text ==========

class TestExtractConceptsFromText:
    def test_extracts_limit_concept(self):
        # 从包含"极限"的文本中提取知识点
        concepts = extract_concepts_from_text("求函数的极限")
        assert "极限" in concepts

    def test_extracts_derivative_from_qiudao(self):
        # "求导"关键词映射到"导数"知识点
        concepts = extract_concepts_from_text("对函数求导")
        assert "导数" in concepts

    def test_extracts_multiple_concepts(self):
        # 提取多个知识点
        concepts = extract_concepts_from_text("求极限和导数")
        assert "极限" in concepts
        assert "导数" in concepts

    def test_returns_empty_for_non_math_text(self):
        # 非数学文本返回空列表
        concepts = extract_concepts_from_text("今天天气很好")
        assert concepts == []

    def test_deduplicates_results(self):
        # 去重：同一知识点不重复出现
        concepts = extract_concepts_from_text("极限 极限 极限")
        assert concepts.count("极限") == 1

    def test_empty_text_returns_empty(self):
        assert extract_concepts_from_text("") == []

    def test_extracts_integral_concept(self):
        concepts = extract_concepts_from_text("计算不定积分")
        assert "不定积分" in concepts


# ========== estimate_difficulty ==========

class TestEstimateDifficulty:
    def test_empty_text_returns_0_5(self):
        # 空文本返回 0.5
        assert estimate_difficulty("") == 0.5

    def test_no_math_keywords_returns_0_5(self):
        # 无数学关键词返回 0.5
        assert estimate_difficulty("今天天气很好") == 0.5

    def test_high_difficulty_for_proof(self):
        # "证明"对应高难度
        diff = estimate_difficulty("请证明该定理")
        assert diff > 0.6

    def test_high_difficulty_for_fourier(self):
        # "傅里叶"对应高难度
        diff = estimate_difficulty("傅里叶级数展开")
        assert diff > 0.6

    def test_low_difficulty_for_function(self):
        # "函数"、"定义域"对应低难度
        diff = estimate_difficulty("求函数的定义域")
        assert diff < 0.5

    def test_returns_weighted_average(self):
        # 返回加权平均值（偏向最高难度）
        # "证明"(0.8) 和 "函数"(0.2) 混合
        diff = estimate_difficulty("证明函数的连续性")
        # 结果应在低难度和高难度之间，偏向高难度
        assert 0.2 < diff < 1.0

    def test_result_in_valid_range(self):
        # 结果在 0.0 到 1.0 之间
        for text in ["证明", "导数", "极限", "傅里叶", "函数定义域"]:
            diff = estimate_difficulty(text)
            assert 0.0 <= diff <= 1.0
