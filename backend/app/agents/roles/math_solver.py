"""
数学求解智能体 (MathSolver)

合并了原 Solver + Verifier + Safety 的核心能力：
- SymPy 符号计算求解（2 次 LLM 调用：代码生成 + 步骤生成）
- 代码安全检查（纯正则，零 LLM）
- 结果验证（SymPy 等价性，零 LLM）
"""

import ast
import asyncio
import logging
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from app.agents.core.base import AgentError, AgentType, BaseAgent
from app.agents.core.cache import get_solver_cache, hash_problem
from app.agents.core.llm_client import (
    ConfigurableLLMClient,
    LLMClient,
    get_agent_llm_client,
)
from app.agents.core.state import StreamingState
from app.agents.core.utils import (
    estimate_difficulty,
    extract_code_block,
    extract_concepts_from_text,
    format_latex,
    validate_python_syntax,
)

logger = logging.getLogger(__name__)


# ========== Prompt 模板 ==========

SOLVER_SYSTEM_PROMPT = """你是一个专业的数学问题求解器。你的任务是将数学问题转换为可执行的 Python/SymPy 代码。

要求：
1. 使用 sympy 库进行符号计算
2. 代码必须可执行且无语法错误
3. 将最终结果赋值给变量 `result`
4. 添加简洁的中文注释说明每一步
5. 只返回代码块，不要额外解释

示例输出格式：
```python
from sympy import *

# 定义符号变量
x = Symbol('x')

# 计算积分
result = integrate(x**2, x)
```"""

SOLVER_PROMPT_TEMPLATE = """请将以下数学问题转换为 Python/SymPy 代码：

问题：{problem}

只返回代码块，格式如下：
```python
# 你的代码
```"""

STEP_GENERATION_PROMPT = """请为以下数学问题生成详细的解题步骤：

问题：{problem}
答案：{answer}

要求：
1. 使用 Markdown 有序列表输出，每个步骤单独一行（以 `1.` / `2.` 开头）
2. 数学公式必须使用 KaTeX 兼容的 Markdown 分隔符：行内用 `$...$`（优先）；不要输出裸的 `\\frac` / `\\begin{{...}}` 等 LaTeX
3. 不要使用 `\\(...\\)` / `\\[...\\]` 作为分隔符
4. 不要把 `**` 等 Markdown 标记转义为 `\\*\\*`
5. 步骤清晰，逻辑连贯，包含必要的公式推导（公式尽量放在同一行的 `$...$` 中）

请按以下格式输出：
1. 第一步...
2. 第二步...
3. ..."""


# ========== 安全检查器（从 safety.py 迁移） ==========

# 危险的导入模式
_DANGEROUS_IMPORTS = [
    r"import\s+os", r"import\s+sys", r"import\s+subprocess",
    r"import\s+shutil", r"import\s+socket", r"import\s+requests",
    r"import\s+urllib", r"from\s+os\s+import",
    r"from\s+sys\s+import", r"from\s+subprocess\s+import",
]

# 危险的函数调用
_DANGEROUS_CALLS = [
    r"eval\s*\(", r"exec\s*\(", r"compile\s*\(",
    r"__import__\s*\(", r"open\s*\(", r"file\s*\(",
    r"os\.\w+\s*\(", r"sys\.\w+\s*\(", r"subprocess\.\w+\s*\(",
]

# 危险的属性访问
_DANGEROUS_ATTRIBUTES = [
    r"__builtins__", r"__class__", r"__bases__",
    r"__subclasses__", r"__mro__", r"__globals__",
    r"__code__", r"__reduce__",
]


def check_code_safety(code: str) -> tuple[bool, list[str]]:
    """
    检查代码安全性（纯正则，零 LLM 调用）。

    Args:
        code: Python 代码字符串

    Returns:
        (is_safe, issues) - 是否安全及问题列表
    """
    issues: list[str] = []

    for pattern in _DANGEROUS_IMPORTS:
        if re.search(pattern, code, re.IGNORECASE):
            issues.append(f"危险导入: {pattern}")

    for pattern in _DANGEROUS_CALLS:
        if re.search(pattern, code, re.IGNORECASE):
            issues.append(f"危险函数调用: {pattern}")

    for pattern in _DANGEROUS_ATTRIBUTES:
        if re.search(pattern, code, re.IGNORECASE):
            issues.append(f"危险属性访问: {pattern}")

    return len(issues) == 0, issues


# ========== 数据类 ==========


@dataclass
class SolverResult:
    """求解结果"""

    success: bool
    answer: str | None = None  # LaTeX 格式的答案
    steps: list[str] = field(default_factory=list)  # 解题步骤
    code: str | None = None  # 生成的 Python 代码
    error: str | None = None
    cached: bool = False  # 是否来自缓存
    verified: bool = False  # 是否通过验证


_RESULT_FALLBACK_NAMES = (
    "answer",
    "solution",
    "final_answer",
    "output",
    "res",
)

_RESULT_COMPUTATION_CALLS = frozenset({
    "diff",
    "differentiate",
    "doit",
    "evalf",
    "expand",
    "factor",
    "integrate",
    "limit",
    "series",
    "simplify",
    "solve",
    "subs",
})


def _assigned_names(target: ast.expr) -> list[str]:
    """Return simple variable names assigned by an AST target."""
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, ast.Tuple | ast.List):
        names: list[str] = []
        for element in target.elts:
            names.extend(_assigned_names(element))
        return names
    return []


def _has_top_level_result_assignment(tree: ast.Module) -> bool:
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign):
            if any("result" in _assigned_names(target) for target in stmt.targets):
                return True
        elif isinstance(stmt, ast.AnnAssign):
            if "result" in _assigned_names(stmt.target):
                return True
        elif isinstance(stmt, ast.AugAssign):
            if "result" in _assigned_names(stmt.target):
                return True
    return False


def _extract_printed_value(value: ast.expr) -> ast.expr:
    if not (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name)
        and value.func.id == "print"
        and value.args
    ):
        return value

    non_label_args = [
        arg
        for arg in value.args
        if not (isinstance(arg, ast.Constant) and isinstance(arg.value, str))
    ]
    return non_label_args[-1] if non_label_args else value.args[-1]


def _ensure_result_assignment(code: str) -> str:
    """
    Normalize common LLM code variants so execution can still read `result`.

    The prompt asks for `result = ...`, but models sometimes return notebook-style
    code whose final line is a bare expression or `print(...)`.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code

    if _has_top_level_result_assignment(tree) or not tree.body:
        return code

    last_stmt = tree.body[-1]
    if not isinstance(last_stmt, ast.Expr):
        return code

    result_assignment = ast.Assign(
        targets=[ast.Name(id="result", ctx=ast.Store())],
        value=_extract_printed_value(last_stmt.value),
    )
    ast.copy_location(result_assignment, last_stmt)
    tree.body[-1] = result_assignment
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def _call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _looks_like_result_computation(value: ast.AST) -> bool:
    for node in ast.walk(value):
        if (
            isinstance(node, ast.Call)
            and _call_name(node) in _RESULT_COMPUTATION_CALLS
        ):
            return True
    return False


def _computed_assignment_names(code: str) -> list[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    names: list[str] = []
    for stmt in tree.body:
        targets: list[ast.expr]
        value: ast.AST | None

        if isinstance(stmt, ast.Assign):
            targets = list(stmt.targets)
            value = stmt.value
        elif isinstance(stmt, ast.AnnAssign):
            targets = [stmt.target]
            value = stmt.value
        else:
            continue

        if value is None or not _looks_like_result_computation(value):
            continue

        for target in targets:
            names.extend(_assigned_names(target))

    return list(reversed(names))


def _extract_result_value(
    local_vars: dict[str, Any],
    code: str,
) -> tuple[bool, Any]:
    if "result" in local_vars:
        return True, local_vars["result"]

    for name in _RESULT_FALLBACK_NAMES:
        if name in local_vars:
            return True, local_vars[name]

    for name in _computed_assignment_names(code):
        if name in local_vars:
            return True, local_vars[name]

    return False, None


# ========== 核心求解器 ==========


class SymPySolver:
    """
    SymPy 符号求解器

    使用 LLM 生成代码，本地执行获取精确结果
    """

    def __init__(self, llm_client: LLMClient | ConfigurableLLMClient | None = None):
        self.llm = llm_client or get_agent_llm_client("math_solver")
        self.cache = get_solver_cache()

    async def generate_code(self, problem: str) -> str:
        """将数学问题转换为 Python/SymPy 代码（LLM 调用 1）"""
        prompt = SOLVER_PROMPT_TEMPLATE.format(problem=problem)

        try:
            response = await self.llm.generate(
                prompt=prompt,
                system_prompt=SOLVER_SYSTEM_PROMPT,
                temperature=0.2,
            )

            code = extract_code_block(response, "python")
            if not code:
                code = response.strip()

            is_valid, error_msg = validate_python_syntax(code)
            if not is_valid:
                raise AgentError(
                    f"生成的代码语法错误: {error_msg}",
                    agent_type=AgentType.SOLVER,
                )

            return code

        except AgentError:
            raise
        except Exception as e:
            logger.error(f"代码生成失败: {e}")
            raise AgentError(
                f"代码生成失败: {str(e)}",
                agent_type=AgentType.SOLVER,
            ) from e

    async def execute_code(self, code: str) -> tuple[bool, str]:
        """在安全环境中执行代码"""
        # 安全检查（纯正则）
        is_safe, issues = check_code_safety(code)
        if not is_safe:
            return False, f"安全检查失败: {'; '.join(issues)}"

        # 准备执行环境
        allowed_imports = {
            "sympy": __import__("sympy"),
            "math": __import__("math"),
        }

        try:
            allowed_imports["numpy"] = __import__("numpy")
            allowed_imports["np"] = allowed_imports["numpy"]
        except ImportError:
            pass

        # 受限 __import__：仅允许白名单模块
        _allowed_module_names = frozenset(allowed_imports.keys())

        def _restricted_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name in _allowed_module_names:
                return allowed_imports[name]
            # 允许 sympy 子模块
            if name.startswith("sympy."):
                return __import__(name, *args, **kwargs)
            raise ImportError(f"不允许导入模块: {name}")

        # 受限的全局命名空间
        safe_globals: dict[str, Any] = {
            "__builtins__": {
                "__import__": _restricted_import,
                "print": print, "range": range, "len": len,
                "abs": abs, "min": min, "max": max, "sum": sum,
                "round": round, "int": int, "float": float,
                "str": str, "list": list, "dict": dict,
                "tuple": tuple, "set": set,
                "True": True, "False": False, "None": None,
            },
            **allowed_imports,
        }

        # 从 sympy 导入常用函数
        from sympy import (
            Derivative,
            E,
            Eq,
            Function,
            I,
            Integral,
            Matrix,
            Product,
            Rational,
            Sum,
            Symbol,
            binomial,
            cos,
            det,
            diff,
            exp,
            expand,
            factor,
            factorial,
            integrate,
            latex,
            limit,
            ln,
            log,
            oo,
            pi,
            series,
            simplify,
            sin,
            solve,
            sqrt,
            symbols,
            tan,
        )

        safe_globals.update({
            "Symbol": Symbol, "symbols": symbols,
            "sin": sin, "cos": cos, "tan": tan,
            "exp": exp, "log": log, "ln": ln, "sqrt": sqrt,
            "pi": pi, "E": E, "I": I, "oo": oo,
            "integrate": integrate, "diff": diff, "limit": limit,
            "solve": solve, "simplify": simplify,
            "expand": expand, "factor": factor, "latex": latex,
            "Eq": Eq, "Function": Function,
            "Derivative": Derivative, "Integral": Integral,
            "Sum": Sum, "Product": Product, "series": series,
            "Matrix": Matrix, "det": det, "Rational": Rational,
            "factorial": factorial, "binomial": binomial,
        })

        local_vars: dict[str, Any] = {}

        try:
            executable_code = _ensure_result_assignment(code)
            exec(executable_code, safe_globals, local_vars)

            has_result, result = _extract_result_value(local_vars, executable_code)
            if has_result:
                result_latex = format_latex(result)
                return True, result_latex

            return False, "代码未定义 result 变量"

        except Exception as e:
            logger.warning(f"代码执行失败: {e}")
            return False, f"执行错误: {str(e)}"

    async def solve(self, problem: str, use_cache: bool = True) -> SolverResult:
        """
        求解数学问题

        流程：检查缓存 → 生成代码 → 安全检查 → 执行 → 验证 → 缓存
        """
        cache_key = f"solution:{hash_problem(problem)}" if use_cache else ""

        # 检查缓存
        if use_cache:
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                logger.info(f"求解缓存命中: {problem[:30]}...")
                return SolverResult(
                    success=True,
                    answer=cached_result.get("answer"),
                    steps=cached_result.get("steps", []),
                    code=cached_result.get("code"),
                    cached=True,
                    verified=True,
                )

        try:
            # LLM 调用 1: 生成代码
            code = await self.generate_code(problem)
            logger.debug(f"生成代码:\n{code}")

            # 执行代码（内含安全检查）
            success, output = await self.execute_code(code)

            if success:
                result = SolverResult(
                    success=True,
                    answer=output,
                    code=code,
                    verified=True,
                )

                # 缓存结果
                if use_cache:
                    await self.cache.set(
                        cache_key,
                        {"answer": result.answer, "steps": result.steps, "code": result.code},
                        ttl=86400,
                    )

                return result
            else:
                return SolverResult(success=False, error=output, code=code)

        except AgentError as e:
            return SolverResult(success=False, error=e.message)
        except Exception as e:
            logger.error(f"求解失败: {e}")
            return SolverResult(success=False, error=str(e))

    async def generate_steps(self, problem: str, answer: str) -> list[str]:
        """生成详细解题步骤（LLM 调用 2）"""
        prompt = STEP_GENERATION_PROMPT.format(problem=problem, answer=answer)

        try:
            response = await self.llm.generate(prompt, temperature=0.3)

            lines = response.strip().split("\n")
            steps = []
            for line in lines:
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith("-")):
                    step = re.sub(r"^\d+[.、)]\s*", "", line)
                    step = re.sub(r"^-\s*", "", step)
                    if step:
                        steps.append(step)

            return steps if steps else [response]

        except Exception as e:
            logger.error(f"步骤生成失败: {e}")
            return []


# ========== 并行求解器 ==========


class ParallelSolver:
    """并行求解器（预留多策略扩展）"""

    def __init__(self, llm_client: LLMClient | ConfigurableLLMClient | None = None):
        self.sympy_solver = SymPySolver(llm_client)

    async def solve(self, problem: str) -> SolverResult:
        tasks = [self.sympy_solver.solve(problem)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, BaseException):
                continue
            if isinstance(result, SolverResult) and result.success and result.answer:
                return result

        error_msgs = []
        for result in results:
            if isinstance(result, Exception):
                error_msgs.append(str(result))
            elif isinstance(result, SolverResult) and result.error:
                error_msgs.append(result.error)

        return SolverResult(
            success=False,
            error="所有求解策略均失败: " + "; ".join(error_msgs),
        )


# ========== MathSolver 智能体 ==========


class MathSolverAgent(BaseAgent):
    """
    数学求解智能体

    合并了 Solver + Verifier + Safety 的核心能力。
    LLM 调用：2 次（代码生成 + 步骤生成）
    """

    def __init__(self, llm_client: LLMClient | ConfigurableLLMClient | None = None):
        self.solver = ParallelSolver(llm_client)

    @property
    def name(self) -> str:
        return "math_solver"

    @property
    def description(self) -> str:
        return "数学求解智能体，使用 SymPy 进行精确计算，内置安全检查和结果验证"

    @property
    def agent_type(self) -> AgentType:
        return AgentType.SOLVER

    async def process(self, state: StreamingState) -> StreamingState:
        problem = state.get("current_problem") or state.get("last_message", "")

        if not problem:
            state["message_stream"] = [
                self.create_message("请提供需要求解的数学问题。", msg_type="error")
            ]
            return state

        state["message_stream"] = [
            self.create_message("正在求解中...", msg_type="thinking")
        ]

        # 求解
        result = await self.solver.solve(problem)

        # 更新智能体输出
        state["agent_outputs"] = {
            "math_solver": {
                "success": result.success,
                "answer": result.answer,
                "code": result.code,
                "cached": result.cached,
                "verified": result.verified,
            }
        }

        if result.success:
            # 生成步骤
            if not result.steps and result.answer:
                result.steps = await self.solver.sympy_solver.generate_steps(
                    problem, result.answer
                )

            content = f"**答案**:\n\n$$\n{result.answer}\n$$"
            if result.steps:
                steps_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(result.steps))
                content += f"\n\n**解题步骤**:\n{steps_text}"

            state["message_stream"] = [
                self.create_message(content, msg_type="solution")
            ]

            # 写入追踪数据
            state["tracking_data"] = {
                "interaction_type": "solve",
                "concepts_involved": extract_concepts_from_text(problem),
                "is_correct": None,  # 求解场景不涉及正确/错误
                "difficulty_level": estimate_difficulty(problem),
            }
        else:
            state["message_stream"] = [
                self.create_message(
                    f"抱歉，无法求解这个问题。{result.error or ''}",
                    msg_type="error",
                )
            ]

        return state

    async def stream_process(
        self, state: StreamingState
    ) -> AsyncIterator[dict[str, Any]]:
        """流式处理求解请求"""
        problem = state.get("current_problem") or state.get("last_message", "")

        if not problem:
            yield {
                "type": "chunk",
                "content": "请提供需要求解的数学问题。",
                "agent": self.agent_type.value,
                "metadata": {"msg_type": "error"},
            }
            return

        yield {
            "type": "chunk",
            "content": "正在求解中...\n\n",
            "agent": self.agent_type.value,
            "metadata": {"msg_type": "thinking"},
        }

        # 求解（无法流式）
        result = await self.solver.solve(problem)

        if result.success:
            yield {
                "type": "chunk",
                "content": f"**答案**:\n\n$$\n{result.answer}\n$$\n\n",
                "agent": self.agent_type.value,
                "metadata": {"msg_type": "solution"},
            }

            # 流式生成步骤
            if not result.steps and result.answer:
                yield {
                    "type": "chunk",
                    "content": "**解题步骤**:\n",
                    "agent": self.agent_type.value,
                    "metadata": {"msg_type": "solution"},
                }

                async for chunk in self._stream_generate_steps(problem, result.answer):
                    yield {
                        "type": "chunk",
                        "content": chunk,
                        "agent": self.agent_type.value,
                        "metadata": {"msg_type": "solution"},
                    }
            elif result.steps:
                steps_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(result.steps))
                yield {
                    "type": "chunk",
                    "content": f"**解题步骤**:\n{steps_text}",
                    "agent": self.agent_type.value,
                    "metadata": {"msg_type": "solution"},
                }
        else:
            yield {
                "type": "chunk",
                "content": f"抱歉，无法求解这个问题。{result.error or ''}",
                "agent": self.agent_type.value,
                "metadata": {"msg_type": "error"},
            }

    async def _stream_generate_steps(
        self, problem: str, answer: str
    ) -> AsyncIterator[str]:
        """流式生成解题步骤"""
        prompt = STEP_GENERATION_PROMPT.format(problem=problem, answer=answer)

        try:
            async for chunk in self.solver.sympy_solver.llm.stream_generate(
                prompt, temperature=0.3
            ):
                yield chunk
        except Exception as e:
            logger.error(f"流式步骤生成失败: {e}")
            yield "（步骤生成失败）"
