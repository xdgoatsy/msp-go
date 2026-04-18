"""
智能体工具函数

提供智能体系统的通用工具函数

包含：
- LaTeX 处理
- 文本处理
- 数学表达式处理
- 历史记录处理
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


# ========== LaTeX 处理 ==========

def format_latex(expr: Any) -> str:
    """
    将 SymPy 表达式转换为 LaTeX 字符串

    Args:
        expr: SymPy 表达式

    Returns:
        LaTeX 字符串
    """
    try:
        from sympy import latex
        return latex(expr)
    except ImportError:
        logger.warning("sympy 未安装，无法格式化 LaTeX")
        return str(expr)
    except Exception as e:
        logger.warning(f"LaTeX 格式化失败: {e}")
        return str(expr)


def parse_latex_safe(latex_str: str) -> Any | None:
    """
    安全解析 LaTeX 字符串为 SymPy 表达式

    Args:
        latex_str: LaTeX 字符串

    Returns:
        SymPy 表达式，解析失败返回 None
    """
    try:
        from sympy.parsing.latex import parse_latex
        return parse_latex(latex_str)
    except ImportError:
        logger.warning("sympy 未安装，无法解析 LaTeX")
        return None
    except Exception as e:
        logger.warning(f"LaTeX 解析失败: {e}")
        return None


def clean_latex(text: str) -> str:
    """
    清理 LaTeX 文本

    移除多余的空格和换行

    Args:
        text: 原始 LaTeX 文本

    Returns:
        清理后的文本
    """
    # 移除多余空格
    text = re.sub(r"\s+", " ", text)
    # 移除 LaTeX 注释
    text = re.sub(r"%.*$", "", text, flags=re.MULTILINE)
    return text.strip()


def extract_latex_blocks(text: str) -> list[str]:
    """
    从文本中提取 LaTeX 数学块

    支持 $...$ 和 $$...$$ 格式

    Args:
        text: 包含 LaTeX 的文本

    Returns:
        LaTeX 块列表
    """
    blocks = []

    # 提取 $$...$$ 块
    display_math = re.findall(r"\$\$(.*?)\$\$", text, re.DOTALL)
    blocks.extend(display_math)

    # 提取 $...$ 块（排除已提取的 $$...$$）
    text_without_display = re.sub(r"\$\$.*?\$\$", "", text, flags=re.DOTALL)
    inline_math = re.findall(r"\$(.*?)\$", text_without_display)
    blocks.extend(inline_math)

    return [clean_latex(b) for b in blocks]


# ========== 代码处理 ==========

def extract_code_block(text: str, language: str = "python") -> str | None:
    """
    从文本中提取代码块

    支持 Markdown 代码块格式

    Args:
        text: 包含代码块的文本
        language: 代码语言（用于匹配）

    Returns:
        代码内容，未找到返回 None
    """
    # 匹配 ```python ... ``` 或 ```py ... ```
    patterns = [
        rf"```{language}\s*\n(.*?)```",
        rf"```{language[:2]}\s*\n(.*?)```",
        r"```\s*\n(.*?)```",  # 无语言标记的代码块
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return None


def validate_python_syntax(code: str) -> tuple[bool, str | None]:
    """
    验证 Python 代码语法

    Args:
        code: Python 代码

    Returns:
        (是否有效, 错误信息)
    """
    try:
        compile(code, "<string>", "exec")
        return True, None
    except SyntaxError as e:
        return False, f"语法错误: 第 {e.lineno} 行 - {e.msg}"


# ========== 文本处理 ==========

def truncate_text(text: str, max_length: int = 500, suffix: str = "...") -> str:
    """
    截断文本

    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 截断后缀

    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def truncate_history(
    history: list[dict[str, Any]],
    max_length: int = 10,
) -> list[dict[str, Any]]:
    """
    截断对话历史

    保留最近的消息

    Args:
        history: 对话历史列表
        max_length: 最大保留数量

    Returns:
        截断后的历史
    """
    if len(history) <= max_length:
        return history
    return history[-max_length:]


def format_conversation_history(
    history: list[dict[str, Any]],
    max_messages: int = 10,
) -> str:
    """
    格式化对话历史为字符串

    用于构建 LLM Prompt

    Args:
        history: 对话历史
        max_messages: 最大消息数

    Returns:
        格式化的字符串
    """
    truncated = truncate_history(history, max_messages)
    lines = []
    for msg in truncated:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        # 截断过长的内容
        content = truncate_text(content, 200)
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


# ========== 步骤处理 ==========

def parse_steps(text: str) -> list[str]:
    """
    将文本解析为步骤列表

    支持多种格式：
    - 换行分隔
    - 数字编号 (1. 2. 3.)
    - LaTeX 换行符 (\\\\)

    Args:
        text: 包含步骤的文本

    Returns:
        步骤列表
    """
    # 尝试按 LaTeX 换行符分割
    if "\\\\" in text:
        steps = text.split("\\\\")
        return [s.strip() for s in steps if s.strip()]

    # 尝试按数字编号分割
    numbered_pattern = r"^\d+[.、)]\s*"
    lines = text.strip().split("\n")
    steps = []
    current_step = ""

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if re.match(numbered_pattern, line):
            if current_step:
                steps.append(current_step)
            current_step = re.sub(numbered_pattern, "", line)
        else:
            if current_step:
                current_step += " " + line
            else:
                current_step = line

    if current_step:
        steps.append(current_step)

    # 如果没有找到编号，按换行分割
    if not steps:
        steps = [line.strip() for line in lines if line.strip()]

    return steps


def format_steps(steps: list[str], numbered: bool = True) -> str:
    """
    格式化步骤列表为字符串

    Args:
        steps: 步骤列表
        numbered: 是否添加编号

    Returns:
        格式化的字符串
    """
    if numbered:
        return "\n".join(f"{i + 1}. {step}" for i, step in enumerate(steps))
    return "\n".join(steps)


# ========== 数学处理 ==========

def normalize_math_expression(expr: str) -> str:
    """
    标准化数学表达式

    用于比较和缓存

    Args:
        expr: 数学表达式字符串

    Returns:
        标准化后的表达式
    """
    # 移除空格
    expr = re.sub(r"\s+", "", expr)
    # 统一乘号
    expr = expr.replace("×", "*").replace("·", "*")
    # 统一除号
    expr = expr.replace("÷", "/")
    # 统一幂次
    expr = expr.replace("^", "**")
    return expr.lower()


def is_math_expression(text: str) -> bool:
    """
    判断文本是否为数学表达式

    Args:
        text: 文本

    Returns:
        是否为数学表达式
    """
    # 包含数学符号
    math_symbols = r"[+\-*/^=∫∑∏√πθαβγδεζηλμνξρστφχψω]"
    if re.search(math_symbols, text):
        return True

    # 包含 LaTeX 数学命令
    latex_commands = r"\\(frac|sqrt|int|sum|prod|lim|sin|cos|tan|log|ln|exp)"
    if re.search(latex_commands, text):
        return True

    return False


# ========== 错误类型处理 ==========

ERROR_TYPE_DESCRIPTIONS = {
    "conceptual": "概念性错误 - 对数学概念的理解有误",
    "procedural": "过程性错误 - 解题步骤或方法使用不当",
    "logical": "逻辑错误 - 推理过程存在逻辑漏洞",
    "symbolic": "符号错误 - 数学符号使用或运算错误",
    "calculation": "计算错误 - 数值计算出错",
}


def get_error_type_description(error_type: str) -> str:
    """
    获取错误类型的描述

    Args:
        error_type: 错误类型代码

    Returns:
        错误类型描述
    """
    return ERROR_TYPE_DESCRIPTIONS.get(
        error_type.lower(),
        f"未知错误类型: {error_type}",
    )


# ========== 情感关键词 ==========

FRUSTRATION_KEYWORDS = [
    "不懂", "太难", "放弃", "不会", "不理解", "搞不懂",
    "好难", "做不出", "不明白", "算不出", "怎么办",
]

CONFUSION_KEYWORDS = [
    "什么意思", "为什么", "怎么理解", "不清楚", "迷糊",
    "搞混", "分不清", "哪里错", "什么是",
]

POSITIVE_KEYWORDS = [
    "懂了", "明白", "原来", "谢谢", "太棒", "学会",
    "理解", "清楚", "简单", "有趣",
]


def detect_emotion_keywords(text: str) -> dict[str, float]:
    """
    检测文本中的情感关键词

    Args:
        text: 文本

    Returns:
        情感分数字典
    """
    text_lower = text.lower()

    frustration_count = sum(1 for kw in FRUSTRATION_KEYWORDS if kw in text_lower)
    confusion_count = sum(1 for kw in CONFUSION_KEYWORDS if kw in text_lower)
    positive_count = sum(1 for kw in POSITIVE_KEYWORDS if kw in text_lower)

    frustration_count + confusion_count + positive_count + 1  # +1 避免除零

    return {
        "frustration": frustration_count / len(FRUSTRATION_KEYWORDS),
        "confusion": confusion_count / len(CONFUSION_KEYWORDS),
        "positive": positive_count / len(POSITIVE_KEYWORDS),
    }


# ========== 知识点提取 ==========

# 高等数学知识点关键词映射：关键词 -> 知识点名称
_CONCEPT_KEYWORD_MAP: list[tuple[list[str], str]] = [
    # 极限
    (["极限", "lim", "\\lim", "趋向", "趋近", "无穷小", "无穷大"], "极限"),
    (["连续", "间断点", "连续性"], "连续性"),
    (["夹逼", "夹逼定理", "squeeze"], "夹逼定理"),
    (["洛必达", "L'Hôpital", "lhopital"], "洛必达法则"),
    # 导数与微分
    (["导数", "求导", "微分", "导函数", "\\frac{d", "f'(", "f'("], "导数"),
    (["链式法则", "复合函数求导"], "链式法则"),
    (["隐函数", "隐函数求导"], "隐函数求导"),
    (["参数方程", "参数求导"], "参数方程求导"),
    (["高阶导数", "二阶导", "n阶导"], "高阶导数"),
    (["中值定理", "罗尔", "拉格朗日", "柯西中值"], "中值定理"),
    (["泰勒", "泰勒展开", "麦克劳林", "Taylor"], "泰勒公式"),
    # 积分
    (["不定积分", "原函数", "\\int"], "不定积分"),
    (["定积分", "积分上限", "积分下限"], "定积分"),
    (["换元积分", "换元法", "substitution"], "换元积分法"),
    (["分部积分", "integration by parts"], "分部积分法"),
    (["反常积分", "广义积分", "瑕积分"], "反常积分"),
    # 级数
    (["级数", "收敛", "发散", "\\sum"], "级数"),
    (["幂级数", "收敛半径", "收敛域"], "幂级数"),
    (["傅里叶", "Fourier"], "傅里叶级数"),
    # 多元函数
    (["偏导", "偏微分", "\\partial"], "偏导数"),
    (["全微分", "全导数"], "全微分"),
    (["多元函数", "二元函数"], "多元函数"),
    (["重积分", "二重积分", "三重积分"], "重积分"),
    (["曲线积分", "曲面积分"], "曲线曲面积分"),
    # 微分方程
    (["微分方程", "ODE", "常微分"], "微分方程"),
    (["齐次方程", "齐次"], "齐次微分方程"),
    (["线性方程", "一阶线性"], "线性微分方程"),
    # 线性代数
    (["矩阵", "matrix", "行列式", "det"], "矩阵与行列式"),
    (["特征值", "特征向量", "eigenvalue"], "特征值与特征向量"),
    (["线性变换", "线性映射"], "线性变换"),
    (["向量空间", "子空间", "基底", "维数"], "向量空间"),
    (["线性方程组", "高斯消元"], "线性方程组"),
    # 基础
    (["函数", "定义域", "值域", "映射"], "函数"),
    (["三角函数", "sin", "cos", "tan", "\\sin", "\\cos", "\\tan"], "三角函数"),
    (["指数", "对数", "ln", "log", "\\ln", "\\log", "e^"], "指数与对数"),
]


def extract_concepts_from_text(text: str) -> list[str]:
    """
    从数学文本中提取涉及的知识点

    通过关键词匹配识别文本中涉及的数学概念。

    Args:
        text: 数学问题或回答文本

    Returns:
        匹配到的知识点名称列表（去重）
    """
    if not text:
        return []

    text_lower = text.lower()
    matched = []

    for keywords, concept in _CONCEPT_KEYWORD_MAP:
        for kw in keywords:
            if kw.lower() in text_lower:
                matched.append(concept)
                break  # 一个概念只需匹配一个关键词

    # 去重并保持顺序
    seen = set()
    result = []
    for c in matched:
        if c not in seen:
            seen.add(c)
            result.append(c)

    return result


# ========== 难度评估 ==========

# 难度指标关键词
_DIFFICULTY_INDICATORS: dict[str, float] = {
    # 高难度指标 (0.7-0.9)
    "证明": 0.8, "prove": 0.8,
    "反常积分": 0.8, "瑕积分": 0.8,
    "傅里叶": 0.85, "Fourier": 0.85,
    "重积分": 0.75, "三重积分": 0.85,
    "曲面积分": 0.85, "曲线积分": 0.8,
    "特征值": 0.7, "特征向量": 0.7,
    "泰勒": 0.7, "麦克劳林": 0.7,
    "微分方程": 0.75,
    "幂级数": 0.7, "收敛半径": 0.7,
    "全微分": 0.7,
    # 中等难度指标 (0.4-0.6)
    "定积分": 0.5, "不定积分": 0.45,
    "换元": 0.5, "分部积分": 0.55,
    "偏导": 0.55,
    "中值定理": 0.6, "洛必达": 0.55,
    "隐函数": 0.55, "参数方程": 0.5,
    "矩阵": 0.5, "行列式": 0.5,
    "级数": 0.6, "收敛": 0.55,
    "高阶导数": 0.5,
    # 低难度指标 (0.1-0.3)
    "求导": 0.3, "导数": 0.3,
    "极限": 0.3, "连续": 0.25,
    "函数": 0.2, "定义域": 0.2,
    "三角函数": 0.25,
}


def estimate_difficulty(text: str) -> float:
    """
    根据数学文本内容估算难度等级

    通过关键词匹配和文本复杂度综合评估。

    Args:
        text: 数学问题或回答文本

    Returns:
        难度值 (0.0-1.0)
    """
    if not text:
        return 0.5

    text_lower = text.lower()
    matched_difficulties = []

    for keyword, difficulty in _DIFFICULTY_INDICATORS.items():
        if keyword.lower() in text_lower:
            matched_difficulties.append(difficulty)

    if not matched_difficulties:
        return 0.5

    # 取匹配到的最高难度和平均难度的加权平均
    max_diff = max(matched_difficulties)
    avg_diff = sum(matched_difficulties) / len(matched_difficulties)
    # 偏向最高难度（题目难度由最难的部分决定）
    return round(0.6 * max_diff + 0.4 * avg_diff, 2)
