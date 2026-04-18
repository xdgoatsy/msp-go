"""
诊断智能体 (Diagnostician)

分析学生解题过程，定位错误

工作流：
1. 接收学生提交的步骤（可能通过 OCR 识别）
2. 调用 Solver 生成标准步骤
3. 逐行比对，找到分歧点
4. 利用错误分类模型判定错误类型（C/P/L/S-Type）

参考设计文档：docs/design_proposals/agents-detail.md
"""

import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from app.agents.core.base import AgentType, BaseAgent
from app.agents.core.llm_client import (
    ConfigurableLLMClient,
    LLMClient,
    get_agent_llm_client,
)
from app.agents.core.state import StreamingState
from app.agents.core.utils import estimate_difficulty, format_steps, parse_steps
from app.domain.models.exercise import ErrorType

logger = logging.getLogger(__name__)


# 错误类型描述
ERROR_TYPE_DESCRIPTIONS = {
    ErrorType.CONCEPTUAL: "概念性错误 - 对数学概念的理解有误",
    ErrorType.PROCEDURAL: "过程性错误 - 解题步骤或方法使用不当",
    ErrorType.LOGICAL: "逻辑错误 - 推理过程存在逻辑漏洞",
    ErrorType.SYMBOLIC: "符号错误 - 数学符号使用或运算错误",
    ErrorType.CALCULATION: "计算错误 - 数值计算出错",
}


# ========== Prompt 模板 ==========

STEP_COMPARISON_PROMPT = """请比对学生的解题步骤和标准步骤，找出第一个错误。

问题：{problem}

标准步骤：
{standard_steps}

学生步骤：
{student_steps}

请分析：
1. 学生的步骤是否正确
2. 如果有错误，指出第一个出错的步骤（从1开始计数）
3. 描述错误的具体内容

请按以下 JSON 格式返回：
{{"has_error": true/false, "error_step_index": 数字或null, "error_description": "描述"}}

只返回 JSON，不要其他内容。"""

ERROR_CLASSIFICATION_PROMPT = """请分析学生的错误类型。

问题：{problem}
学生在第 {step_num} 步出错：{student_step}
标准答案应该是：{standard_step}
错误描述：{error_description}

错误类型说明：
- conceptual: 概念性错误 - 对数学概念理解有误（如混淆导数和积分的概念）
- procedural: 过程性错误 - 解题方法或步骤使用不当（如积分方法选择错误）
- logical: 逻辑错误 - 推理过程有逻辑漏洞（如条件判断错误）
- symbolic: 符号错误 - 数学符号使用错误（如正负号、指数写错）
- calculation: 计算错误 - 数值计算出错（如 2+3=6）

请判断错误类型，并给出简短的分析。

按以下 JSON 格式返回：
{{"error_type": "类型", "analysis": "分析", "severity": "low/medium/high"}}

只返回 JSON，不要其他内容。"""

FEEDBACK_GENERATION_PROMPT = """请为学生生成引导性反馈。

问题：{problem}
错误位置：第 {step_num} 步
错误类型：{error_type}
错误描述：{error_description}

要求：
1. 不要直接给出正确答案
2. 温和地指出错误
3. 提供思考方向
4. 鼓励学生自己修正

请生成一段引导性的反馈（2-3句话）。"""


IMAGE_ANALYSIS_PROMPT = """请分析学生上传的图片，这是一道数学题目或学生的解答过程。

学生的问题/描述：{message}

请仔细查看图片内容，然后：
1. 识别图片中的数学内容（题目、公式、解答步骤等）
2. 如果是题目，分析题目要求
3. 如果是解答过程，检查解答是否正确
4. 给出详细的分析和指导

请用清晰、易懂的语言回答。"""


@dataclass
class DiagnosisResult:
    """诊断结果"""

    has_error: bool
    error_step_index: int | None = None  # 出错步骤索引（从0开始）
    error_type: ErrorType | None = None
    error_subtype: str | None = None
    severity: str = "medium"  # low, medium, high
    explanation: str = ""
    suggestion: str = ""
    related_concepts: list[str] = field(default_factory=list)
    related_misconceptions: list[str] = field(default_factory=list)
    standard_answer: str | None = None


class StepAligner:
    """
    步骤对齐器

    比对学生步骤和标准步骤，找出分歧点
    """

    def __init__(self, llm_client: LLMClient | ConfigurableLLMClient | None = None):
        self.llm = llm_client or get_agent_llm_client("diagnostician")

    async def align(
        self,
        problem: str,
        student_steps: list[str],
        standard_steps: list[str],
    ) -> dict[str, Any]:
        """
        步骤对齐

        Args:
            problem: 问题描述
            student_steps: 学生步骤
            standard_steps: 标准步骤

        Returns:
            对齐结果
        """
        prompt = STEP_COMPARISON_PROMPT.format(
            problem=problem,
            standard_steps=format_steps(standard_steps),
            student_steps=format_steps(student_steps),
        )

        response = ""
        try:
            response = await self.llm.generate(
                prompt=prompt,
                temperature=0.1,
            )

            # 清理响应（移除可能的 markdown 代码块标记）
            response = response.strip()
            if response.startswith("```"):
                response = response.split("\n", 1)[1]
            if response.endswith("```"):
                response = response.rsplit("```", 1)[0]
            response = response.strip()

            result = json.loads(response)

            # 转换步骤索引（从1开始转为从0开始）
            if result.get("error_step_index") is not None:
                result["error_step_index"] = result["error_step_index"] - 1

            return result

        except json.JSONDecodeError as e:
            logger.warning(f"步骤比对响应解析失败: {e}, response={response}")
            # 回退到简单比较
            return self._simple_compare(student_steps, standard_steps)
        except Exception as e:
            logger.error(f"步骤比对失败: {e}")
            return {"has_error": False, "error_step_index": None, "error_description": ""}

    def _simple_compare(
        self,
        student_steps: list[str],
        standard_steps: list[str],
    ) -> dict[str, Any]:
        """简单的字符串比较（回退方案）"""
        for i, (student, standard) in enumerate(zip(student_steps, standard_steps, strict=False)):
            # 标准化比较
            student_normalized = student.strip().lower().replace(" ", "")
            standard_normalized = standard.strip().lower().replace(" ", "")

            if student_normalized != standard_normalized:
                return {
                    "has_error": True,
                    "error_step_index": i,
                    "error_description": f"步骤 {i + 1} 与标准答案不符",
                }

        # 检查步骤数量
        if len(student_steps) < len(standard_steps):
            return {
                "has_error": True,
                "error_step_index": len(student_steps),
                "error_description": "解答不完整，缺少后续步骤",
            }

        return {"has_error": False, "error_step_index": None, "error_description": ""}


class ErrorClassifier:
    """
    错误分类器

    将错误归类为 C/P/L/S-Type
    """

    def __init__(self, llm_client: LLMClient | ConfigurableLLMClient | None = None):
        self.llm = llm_client or get_agent_llm_client("diagnostician")

    async def classify(
        self,
        problem: str,
        student_step: str,
        standard_step: str,
        error_description: str,
        step_num: int,
    ) -> tuple[ErrorType, str, str]:
        """
        错误分类

        Args:
            problem: 问题描述
            student_step: 学生的错误步骤
            standard_step: 标准步骤
            error_description: 错误描述
            step_num: 步骤编号（从1开始）

        Returns:
            (错误类型, 分析, 严重程度)
        """
        prompt = ERROR_CLASSIFICATION_PROMPT.format(
            problem=problem,
            step_num=step_num,
            student_step=student_step,
            standard_step=standard_step,
            error_description=error_description,
        )

        try:
            response = await self.llm.generate(
                prompt=prompt,
                temperature=0.1,
            )

            response = response.strip()
            if response.startswith("```"):
                response = response.split("\n", 1)[1]
            if response.endswith("```"):
                response = response.rsplit("```", 1)[0]
            response = response.strip()

            result = json.loads(response)

            error_type_str = result.get("error_type", "procedural")
            try:
                error_type = ErrorType(error_type_str)
            except ValueError:
                error_type = ErrorType.PROCEDURAL

            analysis = result.get("analysis", "")
            severity = result.get("severity", "medium")

            return error_type, analysis, severity

        except Exception as e:
            logger.error(f"错误分类失败: {e}")
            return ErrorType.PROCEDURAL, "无法确定具体错误类型", "medium"


class DiagnosticianAgent(BaseAgent):
    """
    诊断智能体

    分析学生解题过程，定位错误
    """

    def __init__(self, llm_client: LLMClient | ConfigurableLLMClient | None = None):
        """
        初始化诊断智能体

        Args:
            llm_client: LLM 客户端
        """
        self.llm = llm_client or get_agent_llm_client("diagnostician")
        self.aligner = StepAligner(self.llm)
        self.classifier = ErrorClassifier(self.llm)

    @property
    def name(self) -> str:
        return "diagnostician"

    @property
    def description(self) -> str:
        return "诊断智能体，分析学生解题过程并定位错误"

    @property
    def agent_type(self) -> AgentType:
        return AgentType.DIAGNOSTICIAN

    async def ocr_recognize(self, image_path: str) -> str:
        """
        OCR 识别手写数学公式（多模态 LLM + SymPy 语法验证重试）

        Args:
            image_path: 图片路径（本地 /uploads/xxx 或 HTTP URL）

        Returns:
            识别的 LaTeX 文本
        """
        from app.agents.core.utils import parse_latex_safe

        OCR_PROMPT = (
            "请精确识别图片中的手写数学公式，将其转换为标准 LaTeX 格式。\n\n"
            "要求：\n"
            "1. 只输出 LaTeX 代码，不要任何解释文字\n"
            "2. 使用标准 LaTeX 数学符号（\\frac, \\int, \\sum, \\sqrt 等）\n"
            "3. 如果图片中有多行公式，用 \\\\\\\\ 分隔\n"
            "4. 如果无法识别某个符号，用 \\text{?} 标记\n"
            "5. 保持原始公式的结构和顺序"
        )

        # 第一次识别
        try:
            latex_result = await self.llm.generate_with_images(
                prompt=OCR_PROMPT,
                images=[image_path],
                temperature=0.1,
            )
        except Exception as e:
            logger.error(f"OCR 多模态 LLM 调用失败: {e}")
            return ""

        # 清理结果（去除 markdown 代码块标记）
        latex_result = latex_result.strip()
        if latex_result.startswith("```"):
            lines = latex_result.split("\n")
            # 去掉首行 ```latex 和末行 ```
            inner = "\n".join(lines[1:])
            if inner.rstrip().endswith("```"):
                inner = inner.rstrip()[:-3]
            latex_result = inner.strip()

        # SymPy 语法验证
        parsed = parse_latex_safe(latex_result)
        if parsed is not None:
            logger.info(f"OCR 识别成功（首次）: {latex_result[:80]}...")
            return latex_result

        # 验证失败，带错误信息重试
        logger.info(f"OCR 首次识别的 LaTeX 语法无效，尝试重试: {latex_result[:80]}...")

        RETRY_PROMPT = (
            f'上次识别的 LaTeX "{latex_result}" 语法有误，无法被数学引擎解析。\n'
            "请重新仔细识别图片中的手写公式，确保输出有效的标准 LaTeX。\n"
            "只输出 LaTeX 代码，不要解释。"
        )

        try:
            retry_result = await self.llm.generate_with_images(
                prompt=RETRY_PROMPT,
                images=[image_path],
                temperature=0.1,
            )
            retry_result = retry_result.strip()
            if retry_result.startswith("```"):
                lines = retry_result.split("\n")
                inner = "\n".join(lines[1:])
                if inner.rstrip().endswith("```"):
                    inner = inner.rstrip()[:-3]
                retry_result = inner.strip()

            logger.info(f"OCR 重试结果: {retry_result[:80]}...")
            return retry_result

        except Exception as e:
            logger.error(f"OCR 重试失败: {e}")
            # 返回首次结果（虽然语法可能有误，但总比空好）
            return latex_result

    async def get_standard_solution(self, problem: str) -> tuple[str | None, list[str]]:
        """
        获取标准答案和步骤

        Args:
            problem: 问题描述

        Returns:
            (答案, 步骤列表)
        """
        from app.agents.roles.math_solver import SymPySolver

        solver = SymPySolver(self.llm)
        result = await solver.solve(problem)

        if result.success and result.answer:
            # 生成步骤
            steps = await solver.generate_steps(problem, result.answer)
            return result.answer, steps

        return None, []

    async def diagnose(
        self,
        problem: str,
        student_answer: str,
        student_steps: list[str] | None = None,
        image_path: str | None = None,
    ) -> DiagnosisResult:
        """
        完整诊断流程

        Args:
            problem: 问题描述
            student_answer: 学生答案
            student_steps: 学生步骤（可选）
            image_path: 图片路径（可选，用于 OCR）

        Returns:
            DiagnosisResult
        """
        # 1. 如果有图片，先进行 OCR
        if image_path:
            ocr_result = await self.ocr_recognize(image_path)
            student_steps = parse_steps(ocr_result)

        # 2. 如果没有步骤，从答案中解析
        if not student_steps:
            student_steps = parse_steps(student_answer)

        # 3. 获取标准答案和步骤
        standard_answer, standard_steps = await self.get_standard_solution(problem)

        if not standard_answer or not standard_steps:
            # 降级诊断：无法获取标准答案时，仍然标记为有错误
            # 这样可以确保错题本能够记录所有答错的题目
            return DiagnosisResult(
                has_error=True,
                error_type=ErrorType.PROCEDURAL,
                severity="low",
                explanation="答案不正确",
                suggestion="建议重新检查解题思路和计算过程",
            )

        # 4. 步骤对齐
        alignment = await self.aligner.align(problem, student_steps, standard_steps)

        if not alignment.get("has_error"):
            return DiagnosisResult(
                has_error=False,
                standard_answer=standard_answer,
                explanation="解答正确！",
            )

        # 5. 错误分类
        error_index = alignment.get("error_step_index", 0)
        error_description = alignment.get("error_description", "")

        student_step = student_steps[error_index] if error_index < len(student_steps) else ""
        standard_step = standard_steps[error_index] if error_index < len(standard_steps) else ""

        error_type, analysis, severity = await self.classifier.classify(
            problem=problem,
            student_step=student_step,
            standard_step=standard_step,
            error_description=error_description,
            step_num=error_index + 1,
        )

        # 6. 生成诊断结果
        return DiagnosisResult(
            has_error=True,
            error_step_index=error_index,
            error_type=error_type,
            severity=severity,
            explanation=f"在第 {error_index + 1} 步发现{ERROR_TYPE_DESCRIPTIONS.get(error_type, '错误')}",
            suggestion=analysis,
            standard_answer=standard_answer,
        )

    async def generate_feedback(
        self,
        diagnosis: DiagnosisResult,
        problem: str = "",
    ) -> str:
        """
        生成反馈提示

        不直接给答案，而是苏格拉底式引导

        Args:
            diagnosis: 诊断结果
            problem: 问题描述

        Returns:
            反馈文本
        """
        if not diagnosis.has_error:
            return "解答正确！做得很好！"

        error_type_desc = "未知错误"
        if diagnosis.error_type is not None:
            error_type_desc = ERROR_TYPE_DESCRIPTIONS.get(diagnosis.error_type, "未知错误")

        prompt = FEEDBACK_GENERATION_PROMPT.format(
            problem=problem,
            step_num=diagnosis.error_step_index + 1 if diagnosis.error_step_index is not None else "?",
            error_type=error_type_desc,
            error_description=diagnosis.explanation,
        )

        try:
            response = await self.llm.generate(
                prompt=prompt,
                temperature=0.7,
            )
            return response.strip()

        except Exception as e:
            logger.error(f"反馈生成失败: {e}")
            # 返回通用反馈
            if diagnosis.error_step_index is not None:
                return f"注意检查第 {diagnosis.error_step_index + 1} 步的计算。你能回顾一下这一步的思路吗？"
            return "解答中有一些小问题，让我们一起来看看。"

    async def process(self, state: StreamingState) -> StreamingState:
        """
        处理诊断请求

        Args:
            state: 当前状态

        Returns:
            更新后的状态
        """
        message = state.get("last_message", "")
        problem = state.get("current_problem", "")
        attachments = state.get("attachments", [])

        # 如果没有问题上下文，尝试从消息中提取
        if not problem:
            problem = message

        # 发送处理中消息
        state["message_stream"] = [
            self.create_message("正在分析你的解答...", msg_type="thinking")
        ]

        # 执行诊断
        image_path = attachments[0] if attachments else None
        diagnosis = await self.diagnose(
            problem=problem,
            student_answer=message,
            image_path=image_path,
        )

        # 生成反馈
        feedback = await self.generate_feedback(diagnosis, problem)

        # 更新状态
        state["last_diagnosis"] = {
            "has_error": diagnosis.has_error,
            "error_step_index": diagnosis.error_step_index,
            "error_type": diagnosis.error_type.value if diagnosis.error_type else None,
            "severity": diagnosis.severity,
            "explanation": diagnosis.explanation,
        }

        # 更新连续错误计数
        if diagnosis.has_error:
            state["consecutive_errors"] = state.get("consecutive_errors", 0) + 1
            error_types = state.get("error_types", [])
            if diagnosis.error_type:
                error_types.append(diagnosis.error_type.value)
            state["error_types"] = error_types
        else:
            state["consecutive_errors"] = 0

        # 构建响应消息
        if diagnosis.has_error:
            content = f"**诊断结果**\n\n{feedback}"
            if diagnosis.error_type:
                content += f"\n\n*错误类型: {ERROR_TYPE_DESCRIPTIONS.get(diagnosis.error_type, '未知')}*"
        else:
            content = "✅ **解答正确！**\n\n" + feedback

        state["message_stream"] = [
            self.create_message(
                content,
                msg_type="diagnosis",
                has_error=diagnosis.has_error,
                error_type=diagnosis.error_type.value if diagnosis.error_type else None,
            )
        ]

        # 更新智能体输出
        state["agent_outputs"] = {
            "diagnostician": {
                "has_error": diagnosis.has_error,
                "error_step_index": diagnosis.error_step_index,
                "error_type": diagnosis.error_type.value if diagnosis.error_type else None,
                "severity": diagnosis.severity,
            }
        }

        # 写入追踪数据（新增）
        state["tracking_data"] = {
            "interaction_type": "diagnose",
            "concepts_involved": diagnosis.related_concepts,
            "is_correct": not diagnosis.has_error,
            "error_type": diagnosis.error_type.value if diagnosis.error_type else None,
            "difficulty_level": estimate_difficulty(problem),
        }

        return state

    async def stream_process(
        self, state: StreamingState
    ) -> AsyncIterator[dict[str, Any]]:
        """
        流式处理诊断请求

        Args:
            state: 当前状态

        Yields:
            流式输出的内容块
        """
        message = state.get("last_message", "")
        problem = state.get("current_problem", "")
        attachments = state.get("attachments", [])

        # 如果没有问题上下文，尝试从消息中提取
        if not problem:
            problem = message

        # 提取图片附件
        images = [att for att in attachments if isinstance(att, str) and (
            att.startswith("/uploads/") or att.startswith("data:image/") or
            att.startswith("http://") or att.startswith("https://")
        )]

        # 如果有图片，使用多模态分析
        if images:
            yield {
                "type": "chunk",
                "content": "正在分析图片内容...\n\n",
                "agent": self.agent_type.value,
                "metadata": {"msg_type": "thinking"},
            }

            # 使用多模态 LLM 分析图片
            prompt = IMAGE_ANALYSIS_PROMPT.format(message=message)

            try:
                async for chunk in self.llm.stream_generate_with_images(
                    prompt=prompt,
                    images=images,
                    temperature=0.7,
                ):
                    yield {
                        "type": "chunk",
                        "content": chunk,
                        "agent": self.agent_type.value,
                        "metadata": {"msg_type": "diagnosis"},
                    }
                return
            except Exception as e:
                logger.error(f"图片分析失败: {e}")
                yield {
                    "type": "chunk",
                    "content": f"抱歉，图片分析时遇到问题: {str(e)}",
                    "agent": self.agent_type.value,
                    "metadata": {"msg_type": "error"},
                }
                return

        # 发送处理中消息
        yield {
            "type": "chunk",
            "content": "正在分析你的解答...\n\n",
            "agent": self.agent_type.value,
            "metadata": {"msg_type": "thinking"},
        }

        # 执行诊断（这部分无法流式）
        image_path = attachments[0] if attachments else None
        diagnosis = await self.diagnose(
            problem=problem,
            student_answer=message,
            image_path=image_path,
        )

        # 流式生成反馈
        if diagnosis.has_error:
            yield {
                "type": "chunk",
                "content": "**诊断结果**\n\n",
                "agent": self.agent_type.value,
                "metadata": {"msg_type": "diagnosis"},
            }

            # 流式生成反馈内容
            async for chunk in self._stream_generate_feedback(diagnosis, problem):
                yield {
                    "type": "chunk",
                    "content": chunk,
                    "agent": self.agent_type.value,
                    "metadata": {"msg_type": "diagnosis"},
                }

            if diagnosis.error_type:
                yield {
                    "type": "chunk",
                    "content": f"\n\n*错误类型: {ERROR_TYPE_DESCRIPTIONS.get(diagnosis.error_type, '未知')}*",
                    "agent": self.agent_type.value,
                    "metadata": {"msg_type": "diagnosis"},
                }
        else:
            yield {
                "type": "chunk",
                "content": "✅ **解答正确！**\n\n",
                "agent": self.agent_type.value,
                "metadata": {"msg_type": "diagnosis"},
            }

            # 流式生成正确反馈
            async for chunk in self._stream_generate_feedback(diagnosis, problem):
                yield {
                    "type": "chunk",
                    "content": chunk,
                    "agent": self.agent_type.value,
                    "metadata": {"msg_type": "diagnosis"},
                }

    async def _stream_generate_feedback(
        self,
        diagnosis: DiagnosisResult,
        problem: str = "",
    ) -> AsyncIterator[str]:
        """
        流式生成反馈提示

        Args:
            diagnosis: 诊断结果
            problem: 问题描述

        Yields:
            反馈内容的文本片段
        """
        if not diagnosis.has_error:
            yield "解答正确！做得很好！"
            return

        error_type_desc = "未知错误"
        if diagnosis.error_type is not None:
            error_type_desc = ERROR_TYPE_DESCRIPTIONS.get(diagnosis.error_type, "未知错误")

        prompt = FEEDBACK_GENERATION_PROMPT.format(
            problem=problem,
            step_num=diagnosis.error_step_index + 1 if diagnosis.error_step_index is not None else "?",
            error_type=error_type_desc,
            error_description=diagnosis.explanation,
        )

        try:
            async for chunk in self.llm.stream_generate(
                prompt=prompt,
                temperature=0.7,
            ):
                yield chunk

        except Exception as e:
            logger.error(f"流式反馈生成失败: {e}")
            if diagnosis.error_step_index is not None:
                yield f"注意检查第 {diagnosis.error_step_index + 1} 步的计算。你能回顾一下这一步的思路吗？"
            else:
                yield "解答中有一些小问题，让我们一起来看看。"
