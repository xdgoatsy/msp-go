"""
数学答案等价性匹配引擎

多层级验证策略，按成本从低到高依次尝试：
  Layer 1: 标准化字符串比较（零成本）
  Layer 2: SymPy 符号等价 — simplify / trigsimp / expand / factor（零 LLM）
  Layer 3: 数值采样验证 — 多点随机采样比较（零 LLM）
  Layer 4: LLM 辅助判断（仅前三层无法确定时，1 次 LLM 调用）
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from app.agents.core.utils import normalize_math_expression, parse_latex_safe
from app.core.middleware.metrics import record_sympy_check

if TYPE_CHECKING:
    from app.agents.core.llm_client import ConfigurableLLMClient, LLMClient

logger = logging.getLogger(__name__)

# SymPy 进程池（懒初始化，避免多 worker 部署时进程数膨胀）
_sympy_executor: ProcessPoolExecutor | None = None


def _get_sympy_executor() -> ProcessPoolExecutor:
    """懒初始化 SymPy 进程池"""
    global _sympy_executor
    if _sympy_executor is None:
        _sympy_executor = ProcessPoolExecutor(max_workers=2)
    return _sympy_executor


@lru_cache(maxsize=1024)
def _cached_parse_to_sympy(expr_str: str):
    """
    缓存标准答案的 SymPy 解析结果

    标准答案是固定的，缓存解析结果可以避免重复解析开销。
    """
    return _parse_to_sympy(expr_str)


# ========== 数据类 ==========


class AnswerType(str, Enum):
    """答案类型"""

    EXPRESSION = "expression"  # 数学表达式（默认）
    SET = "set"  # 集合 {1, 2, 3}
    INTERVAL = "interval"  # 区间 [a, b)
    EQUATION = "equation"  # 方程 x = ...
    NUMERIC = "numeric"  # 数值答案
    TEXT = "text"  # 文本答案
    AUTO = "auto"  # 自动检测


class VerifyLayer(str, Enum):
    """验证层级"""

    EXACT = "exact"  # 精确字符串匹配
    NORMALIZED = "normalized"  # 标准化后匹配
    SYMBOLIC = "symbolic"  # SymPy 符号等价
    NUMERIC = "numeric"  # 数值采样验证
    LLM = "llm"  # LLM 辅助判断
@dataclass
class EquivalenceResult:
    """等价性验证结果"""

    is_equivalent: bool
    confidence: float  # 0.0 ~ 1.0
    reason: str
    layer_used: VerifyLayer
    student_normalized: str = ""  # 标准化后的学生答案
    correct_normalized: str = ""  # 标准化后的正确答案


def _strip_latex_math_delimiters(expr: str) -> str:
    """去掉常见 Markdown/LaTeX 数学分隔符。"""
    stripped = expr.strip()

    delimiter_pairs = (
        ("$$", "$$"),
        ("$", "$"),
        (r"\(", r"\)"),
        (r"\[", r"\]"),
    )

    changed = True
    while changed:
        changed = False
        for prefix, suffix in delimiter_pairs:
            if stripped.startswith(prefix) and stripped.endswith(suffix):
                stripped = stripped[len(prefix) : len(stripped) - len(suffix)].strip()
                changed = True

    return stripped


def _read_braced_group(expr: str, start: int) -> tuple[str, int] | None:
    """读取从 start 位置开始的 {...} 分组，返回内容和结束位置。"""
    if start >= len(expr) or expr[start] != "{":
        return None

    depth = 0
    for index in range(start, len(expr)):
        char = expr[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return expr[start + 1 : index], index + 1

    return None


def _replace_latex_fracs(expr: str) -> str:
    """将常见 LaTeX 分数命令转换为 SymPy 可解析的除法表达式。"""
    pattern = re.compile(r"\\(?:dfrac|tfrac|frac)\s*")
    result: list[str] = []
    cursor = 0

    while True:
        match = pattern.search(expr, cursor)
        if match is None:
            result.append(expr[cursor:])
            break

        result.append(expr[cursor : match.start()])
        numerator = _read_braced_group(expr, match.end())
        if numerator is None:
            result.append(match.group(0))
            cursor = match.end()
            continue

        denominator = _read_braced_group(expr, numerator[1])
        if denominator is None:
            result.append(match.group(0))
            cursor = match.end()
            continue

        numerator_text = _latex_to_sympy_text(numerator[0])
        denominator_text = _latex_to_sympy_text(denominator[0])
        result.append(f"(({numerator_text})/({denominator_text}))")
        cursor = denominator[1]

    return "".join(result)


def _replace_latex_sqrts(expr: str) -> str:
    """将常见 LaTeX 平方根命令转换为 SymPy 可解析的 sqrt(...)。"""
    pattern = re.compile(r"\\sqrt\s*")
    result: list[str] = []
    cursor = 0

    while True:
        match = pattern.search(expr, cursor)
        if match is None:
            result.append(expr[cursor:])
            break

        result.append(expr[cursor : match.start()])
        radicand = _read_braced_group(expr, match.end())
        if radicand is None:
            result.append(match.group(0))
            cursor = match.end()
            continue

        radicand_text = _latex_to_sympy_text(radicand[0])
        result.append(f"sqrt({radicand_text})")
        cursor = radicand[1]

    return "".join(result)


def _latex_to_sympy_text(expr: str) -> str:
    """把学生常见 LaTeX 输入规整为 SymPy 友好的表达式文本。"""
    converted = _strip_latex_math_delimiters(expr)
    converted = re.sub(r"\\(?:left|right)\s*", "", converted)
    converted = re.sub(r"\\(?:,|;|:|!|quad|qquad)\s*", "", converted)
    converted = _replace_latex_fracs(converted)
    converted = _replace_latex_sqrts(converted)

    replacements = {
        r"\cdot": "*",
        r"\times": "*",
        r"\div": "/",
        r"\pi": "pi",
        r"\infty": "oo",
        r"\leq": "<=",
        r"\geq": ">=",
        r"\le": "<=",
        r"\ge": ">=",
        r"\ln": "log",
        r"\sin": "sin",
        r"\cos": "cos",
        r"\tan": "tan",
        r"\log": "log",
        r"\exp": "exp",
    }
    for latex, plain in replacements.items():
        converted = converted.replace(latex, plain)

    converted = converted.replace(r"\{", "{").replace(r"\}", "}")
    converted = converted.replace("{", "(").replace("}", ")")
    return converted


def _normalize_for_sympy(expr: str) -> str:
    """统一普通输入和常见 LaTeX 输入，供 SymPy 解析。"""
    return normalize_math_expression(_latex_to_sympy_text(expr))


# ========== 答案类型自动检测 ==========


def detect_answer_type(answer: str) -> AnswerType:
    """
    根据答案字符串特征自动判断类型

    Args:
        answer: 答案字符串（LaTeX 或纯文本）

    Returns:
        检测到的答案类型
    """
    cleaned = _strip_latex_math_delimiters(answer)

    # 集合: {1, 2, 3} 或 \{1, 2, 3\}
    if re.match(r"^\\?\{.*\\?\}$", cleaned):
        return AnswerType.SET

    # 区间: [a, b) 或 (a, b] 或 (-\infty, 0)
    if re.match(r"^[\[\(].*,.*[\]\)]$", cleaned):
        return AnswerType.INTERVAL

    # 方程: x = ... （但排除 f(x) = ... 这种函数定义）
    if re.match(r"^[a-zA-Z]\s*=\s*", cleaned) and "==" not in cleaned:
        return AnswerType.EQUATION

    # 纯数值: 整数或小数（可能带负号）
    if re.match(r"^-?\d+(\.\d+)?$", cleaned):
        return AnswerType.NUMERIC

    # 纯文本: 不包含数学符号的文本
    math_symbols = r"[+\-*/^=<>()[\]{}\\]"
    if not re.search(math_symbols, cleaned):
        return AnswerType.TEXT

    return AnswerType.EXPRESSION


# ========== Layer 1: 标准化字符串比较 ==========


def _check_exact(student: str, correct: str) -> EquivalenceResult | None:
    """精确匹配（去除空格后）"""
    s = student.strip()
    c = correct.strip()
    if s == c:
        return EquivalenceResult(
            is_equivalent=True,
            confidence=1.0,
            reason="精确匹配",
            layer_used=VerifyLayer.EXACT,
            student_normalized=s,
            correct_normalized=c,
        )
    return None


def _check_normalized(student: str, correct: str) -> EquivalenceResult | None:
    """标准化后比较"""
    s = normalize_math_expression(student)
    c = normalize_math_expression(correct)
    if s == c:
        return EquivalenceResult(
            is_equivalent=True,
            confidence=1.0,
            reason="标准化后相等",
            layer_used=VerifyLayer.NORMALIZED,
            student_normalized=s,
            correct_normalized=c,
        )
    return None


def _check_numeric(student: str, correct: str) -> EquivalenceResult | None:
    """数值答案比较（带容差）"""
    try:
        def to_number(answer: str) -> float | None:
            parsed = _parse_to_sympy(answer)
            if parsed is None or getattr(parsed, "free_symbols", set()):
                return None
            return float(parsed.evalf())

        s_val = to_number(student)
        c_val = to_number(correct)
        if s_val is None or c_val is None:
            return None

        # 使用相对容差和绝对容差
        abs_tol = 1e-9
        rel_tol = 1e-6

        diff = abs(s_val - c_val)
        threshold = abs_tol + rel_tol * abs(c_val)

        is_eq = diff <= threshold

        return EquivalenceResult(
            is_equivalent=is_eq,
            confidence=1.0 if is_eq else 0.0,
            reason=f"数值比较: {s_val} {'≈' if is_eq else '≠'} {c_val}",
            layer_used=VerifyLayer.NUMERIC,
            student_normalized=_normalize_for_sympy(student),
            correct_normalized=_normalize_for_sympy(correct),
        )
    except (ValueError, TypeError):
        return None


def _check_text(student: str, correct: str) -> EquivalenceResult | None:
    """文本答案比较（标准化后精确匹配）"""
    # 标准化：去除首尾空格、统一为小写、去除多余空格
    def normalize_text(text: str) -> str:
        return " ".join(text.strip().lower().split())

    s_norm = normalize_text(student)
    c_norm = normalize_text(correct)

    is_eq = s_norm == c_norm

    return EquivalenceResult(
        is_equivalent=is_eq,
        confidence=1.0 if is_eq else 0.0,
        reason=f"文本比较: {'匹配' if is_eq else '不匹配'}",
        layer_used=VerifyLayer.NORMALIZED,
        student_normalized=s_norm,
        correct_normalized=c_norm,
    )
# ========== Layer 2: SymPy 符号等价 ==========


def _parse_to_sympy(expr_str: str) -> Any | None:
    """
    尝试将字符串解析为 SymPy 表达式

    优先尝试轻量规整后 sympify，失败后再尝试 LaTeX 解析
    """
    # 优先走轻量规整 + sympify，避免要求学生必须输入完整 LaTeX。
    try:
        from sympy import sympify

        normalized = _normalize_for_sympy(expr_str)
        return sympify(normalized)
    except Exception:
        pass

    # 复杂 LaTeX 再尝试 SymPy 自带解析器（如果运行环境安装了 antlr）。
    result = parse_latex_safe(_strip_latex_math_delimiters(expr_str))
    if result is not None:
        return result

    return None


def _check_symbolic_expression(
    student: str, correct: str
) -> EquivalenceResult | None:
    """SymPy 符号等价性验证（表达式类型）"""
    try:
        from sympy import expand, factor, simplify, trigsimp

        expr_s = _parse_to_sympy(student)
        expr_c = _cached_parse_to_sympy(correct)  # 标准答案使用缓存

        if expr_s is None or expr_c is None:
            return None

        # 1. 直接化简
        diff = simplify(expr_s - expr_c)
        if diff == 0:
            return EquivalenceResult(
                is_equivalent=True,
                confidence=1.0,
                reason="SymPy 化简后相等",
                layer_used=VerifyLayer.SYMBOLIC,
            )

        # 2. 三角恒等式化简
        diff_trig = trigsimp(expr_s - expr_c)
        if diff_trig == 0:
            return EquivalenceResult(
                is_equivalent=True,
                confidence=1.0,
                reason="三角化简后相等",
                layer_used=VerifyLayer.SYMBOLIC,
            )

        # 3. 展开后比较
        diff_expand = simplify(expand(expr_s) - expand(expr_c))
        if diff_expand == 0:
            return EquivalenceResult(
                is_equivalent=True,
                confidence=1.0,
                reason="展开后相等",
                layer_used=VerifyLayer.SYMBOLIC,
            )

        # 4. 因式分解后比较
        diff_factor = simplify(factor(expr_s) - factor(expr_c))
        if diff_factor == 0:
            return EquivalenceResult(
                is_equivalent=True,
                confidence=1.0,
                reason="因式分解后相等",
                layer_used=VerifyLayer.SYMBOLIC,
            )

        return None  # 符号层无法确定

    except Exception as e:
        logger.warning(f"SymPy 符号等价性检查异常: {e}")
        return None


def _check_symbolic_set(student: str, correct: str) -> EquivalenceResult | None:
    """集合类型等价性验证"""
    try:
        from sympy import FiniteSet, sympify

        # 提取集合元素
        def parse_set(s: str) -> FiniteSet | None:
            cleaned = re.sub(r"[\\{}]", "", s).strip()
            if not cleaned:
                return FiniteSet()
            elements = [sympify(e.strip()) for e in cleaned.split(",")]
            return FiniteSet(*elements)

        set_s = parse_set(student)
        set_c = parse_set(correct)

        if set_s is None or set_c is None:
            return None

        if set_s == set_c:
            return EquivalenceResult(
                is_equivalent=True,
                confidence=1.0,
                reason="集合元素相等",
                layer_used=VerifyLayer.SYMBOLIC,
            )

        return EquivalenceResult(
            is_equivalent=False,
            confidence=0.9,
            reason=f"集合不等: {set_s} ≠ {set_c}",
            layer_used=VerifyLayer.SYMBOLIC,
        )

    except Exception as e:
        logger.warning(f"集合等价性检查异常: {e}")
        return None
def _run_symbolic_check(student: str, correct: str):
    """在独立进程中运行 SymPy 符号等价性检查（进程级隔离）"""
    return _check_symbolic_expression(student, correct)


def _run_symbolic_set_check(student: str, correct: str):
    """在独立进程中运行集合等价性检查"""
    return _check_symbolic_set(student, correct)


def _run_numeric_sampling(student: str, correct: str):
    """在独立进程中运行数值采样验证"""
    return _check_numeric_sampling(student, correct)


async def _check_symbolic_with_timeout(
    student: str, correct: str, timeout: float = 5.0
) -> EquivalenceResult | None:
    """
    带超时保护的 SymPy 符号等价性检查

    使用 ProcessPoolExecutor 隔离 CPU 密集型操作：
    - 避免阻塞事件循环
    - SymPy 非线程安全，必须使用进程隔离
    - 进程级超时是唯一可靠的超时机制（SymPy 无内置超时）
    """
    loop = asyncio.get_running_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(_get_sympy_executor(), _run_symbolic_check, student, correct),
            timeout=timeout,
        )
        return result
    except TimeoutError:
        logger.warning("SymPy 符号等价性检查超时 (%.1fs)", timeout)
        return None
    except Exception as e:
        logger.warning("SymPy 符号等价性检查进程异常: %s", e)
        return None


async def _check_numeric_sampling_with_timeout(
    student: str, correct: str, timeout: float = 3.0
) -> EquivalenceResult | None:
    """带超时保护的数值采样验证"""
    loop = asyncio.get_running_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(_get_sympy_executor(), _run_numeric_sampling, student, correct),
            timeout=timeout,
        )
        return result
    except TimeoutError:
        logger.warning("数值采样验证超时 (%.1fs)", timeout)
        return None
    except Exception as e:
        logger.warning("数值采样验证进程异常: %s", e)
        return None


async def _check_symbolic_set_with_timeout(
    student: str, correct: str, timeout: float = 5.0
) -> EquivalenceResult | None:
    """带超时保护的集合等价性检查"""
    loop = asyncio.get_running_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(_get_sympy_executor(), _run_symbolic_set_check, student, correct),
            timeout=timeout,
        )
        return result
    except TimeoutError:
        logger.warning("集合等价性检查超时 (%.1fs)", timeout)
        return None
    except Exception as e:
        logger.warning("集合等价性检查进程异常: %s", e)
        return None


# ========== Layer 3: 数值采样验证 ==========

# 采样配置
_NUM_SAMPLES = 10
_NUMERIC_TOLERANCE = 1e-8


def _check_numeric_sampling(
    student: str, correct: str
) -> EquivalenceResult | None:
    """
    数值采样验证

    在多个随机点对两个表达式求值，比较数值是否一致。
    适用于 SymPy 无法化简的复杂表达式。
    """
    try:
        from sympy import N as sympy_N

        expr_s = _parse_to_sympy(student)
        expr_c = _parse_to_sympy(correct)

        if expr_s is None or expr_c is None:
            return None

        free_symbols = expr_s.free_symbols | expr_c.free_symbols

        # 无自由变量的常数表达式
        if not free_symbols:
            try:
                v_s = complex(sympy_N(expr_s))
                v_c = complex(sympy_N(expr_c))
                is_eq = abs(v_s - v_c) < _NUMERIC_TOLERANCE
                return EquivalenceResult(
                    is_equivalent=is_eq,
                    confidence=1.0 if is_eq else 0.0,
                    reason="常数值比较" if is_eq else f"常数值不等: {v_s} ≠ {v_c}",
                    layer_used=VerifyLayer.NUMERIC,
                )
            except Exception:
                return None

        # 多点采样
        match_count = 0
        valid_count = 0

        for _ in range(_NUM_SAMPLES):
            subs = {s: random.uniform(-5, 5) for s in free_symbols}
            try:
                v_s = complex(sympy_N(expr_s.subs(subs)))
                v_c = complex(sympy_N(expr_c.subs(subs)))

                # 跳过无穷大或 NaN
                if not (
                    all(abs(v) < 1e15 for v in (v_s, v_c))
                    and v_s == v_s
                    and v_c == v_c
                ):
                    continue

                valid_count += 1
                if abs(v_s - v_c) < _NUMERIC_TOLERANCE * max(1, abs(v_c)):
                    match_count += 1
            except Exception:
                continue

        if valid_count < 3:
            return None  # 有效采样点太少，无法判断

        confidence = match_count / valid_count
        is_eq = confidence > 0.95

        return EquivalenceResult(
            is_equivalent=is_eq,
            confidence=confidence,
            reason=f"数值采样 {match_count}/{valid_count} 匹配",
            layer_used=VerifyLayer.NUMERIC,
        )

    except Exception as e:
        logger.warning(f"数值采样验证异常: {e}")
        return None


# ========== Layer 4: LLM 辅助判断 ==========

_LLM_EQUIVALENCE_PROMPT = """判断以下两个数学表达式/答案是否等价（数学意义上相同）。

表达式A（学生答案）: {expr_a}
表达式B（标准答案）: {expr_b}

请严格按以下 JSON 格式回答，不要输出其他内容：
{{"equivalent": true, "reason": "原因说明"}}
或
{{"equivalent": false, "reason": "原因说明"}}"""


async def _check_llm(
    student: str,
    correct: str,
    llm_client: LLMClient | ConfigurableLLMClient | None,
) -> EquivalenceResult | None:
    """LLM 辅助判断（最后手段）"""
    if llm_client is None:
        return None

    try:
        import json

        prompt = _LLM_EQUIVALENCE_PROMPT.format(expr_a=student, expr_b=correct)
        response = await llm_client.generate(
            prompt=prompt,
            temperature=0.1,
        )

        # 解析 JSON 响应
        text = response.strip()
        # 处理可能的 markdown 代码块
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        result = json.loads(text)
        is_eq = result.get("equivalent", False)
        reason = result.get("reason", "LLM 判断")

        return EquivalenceResult(
            is_equivalent=is_eq,
            confidence=0.85 if is_eq else 0.8,
            reason=f"LLM 判断: {reason}",
            layer_used=VerifyLayer.LLM,
        )

    except Exception as e:
        logger.warning(f"LLM 等价性判断异常: {e}")
        return None
# ========== 主入口函数 ==========


async def check_equivalence(
    student_answer: str,
    correct_answer: str,
    answer_type: str = "auto",
    llm_client: LLMClient | ConfigurableLLMClient | None = None,
) -> EquivalenceResult:
    """
    多层级数学答案等价性验证

    按成本从低到高依次尝试各验证层，直到得出结论。

    Args:
        student_answer: 学生答案（LaTeX 或纯文本）
        correct_answer: 标准答案（LaTeX 或纯文本）
        answer_type: 答案类型（auto 自动检测）
        llm_client: LLM 客户端（可选，用于 Layer 4）

    Returns:
        EquivalenceResult 包含是否等价、置信度、原因、使用的验证层
    """
    student = student_answer.strip()
    correct = correct_answer.strip()

    if not student or not correct:
        return EquivalenceResult(
            is_equivalent=False,
            confidence=1.0,
            reason="答案为空",
            layer_used=VerifyLayer.EXACT,
            student_normalized=student,
            correct_normalized=correct,
        )

    # 自动检测答案类型
    if answer_type == "auto":
        detected_type = detect_answer_type(correct)
    else:
        detected_type = AnswerType(answer_type)

    _layer_start = time.monotonic()

    # Layer 1: 精确匹配
    result = _check_exact(student, correct)
    if result is not None:
        record_sympy_check("exact", time.monotonic() - _layer_start, "hit")
        return result

    # Layer 1b: 标准化匹配
    result = _check_normalized(student, correct)
    if result is not None:
        record_sympy_check("normalized", time.monotonic() - _layer_start, "hit")
        return result

    # 特殊类型处理：数值和文本
    if detected_type == AnswerType.NUMERIC:
        result = _check_numeric(student, correct)
        if result is not None:
            record_sympy_check("numeric_type", time.monotonic() - _layer_start, "hit")
            return result

    if detected_type == AnswerType.TEXT:
        result = _check_text(student, correct)
        if result is not None:
            record_sympy_check("text_type", time.monotonic() - _layer_start, "hit")
            return result

    # Layer 2: SymPy 符号等价（进程隔离 + 超时保护）
    _sympy_start = time.monotonic()
    if detected_type == AnswerType.SET:
        result = await _check_symbolic_set_with_timeout(student, correct, timeout=5.0)
    else:
        result = await _check_symbolic_with_timeout(student, correct, timeout=5.0)

    _sympy_elapsed = time.monotonic() - _sympy_start
    if result is not None:
        record_sympy_check("symbolic", _sympy_elapsed, "hit")
        return result
    else:
        record_sympy_check("symbolic", _sympy_elapsed, "miss")

    # Layer 3: 数值采样（仅表达式类型）
    if detected_type in (AnswerType.EXPRESSION, AnswerType.AUTO):
        _sampling_start = time.monotonic()
        result = await _check_numeric_sampling_with_timeout(student, correct, timeout=3.0)
        _sampling_elapsed = time.monotonic() - _sampling_start
        if result is not None:
            record_sympy_check("numeric", _sampling_elapsed, "hit")
            return result
        else:
            record_sympy_check("numeric", _sampling_elapsed, "miss")

    # Layer 4: LLM 辅助判断
    _llm_start = time.monotonic()
    result = await _check_llm(student, correct, llm_client)
    _llm_elapsed = time.monotonic() - _llm_start
    if result is not None:
        record_sympy_check("llm", _llm_elapsed, "hit")
        return result
    else:
        record_sympy_check("llm", _llm_elapsed, "miss")

    # 所有层都无法确定
    record_sympy_check("none", time.monotonic() - _layer_start, "miss")
    return EquivalenceResult(
        is_equivalent=False,
        confidence=0.5,
        reason="所有验证层均无法确定等价性，默认判为不等",
        layer_used=VerifyLayer.NUMERIC,
        student_normalized=normalize_math_expression(student),
        correct_normalized=normalize_math_expression(correct),
    )
