"""
题目 AI 识别服务

调用 LLM 从原始文本中结构化提取题目信息
"""

import json
import logging
import re
from typing import Any

from app.agents.core.llm_client import get_agent_llm_client

logger = logging.getLogger(__name__)

# AI 识别的系统提示词
PARSE_SYSTEM_PROMPT = """你是一个高等数学题目结构化提取专家。你的任务是从给定的原始文本中提取题目信息，并以严格的 JSON 格式返回。

## 输出格式要求

返回一个 JSON 数组，每个元素代表一道题目，包含以下字段：
- title: 题目标题（简短描述，不超过 50 字）
- body: 题目完整内容（保留原始 LaTeX 公式格式，如 $...$ 或 $$...$$）
- type: 题型，取值为 "short_answer"（简答/计算/填空）、"multiple_choice"（选择题）、"proof"（证明题）
- difficulty: 难度系数 0-1（0.15=简单, 0.5=中等, 0.85=困难）
- answer: 标准答案（保留 LaTeX 格式）
- answer_type: 答案类型，取值为 "expression"（数学表达式）、"numeric"（数值）、"text"（文本）
- options: 选择题选项数组（仅选择题需要，其他题型为 null）
- hints: 提示列表（如果文本中有提示信息则提取，否则为空数组）
- solution_steps: 解题步骤列表（如果文本中有解题过程则提取，否则为空数组）
- tags: 标签列表（根据题目内容推断，如"极限"、"微分"、"积分"等）

## 注意事项

1. 保留所有 LaTeX 数学公式的原始格式
2. 如果无法确定某个字段的值，使用合理的默认值
3. 如果文本中包含多道题目，请全部提取
4. 只返回 JSON 数组，不要包含其他文字说明
5. 确保 JSON 格式严格正确"""


class QuestionAIService:
    """题目 AI 识别服务"""

    def __init__(self) -> None:
        # 复用 tutor 智能体的 LLM 配置
        self.llm_client = get_agent_llm_client("tutor")

    async def parse_questions(self, raw_texts: list[str]) -> list[dict[str, Any]]:
        """
        调用 LLM 从原始文本中提取结构化题目数据

        Args:
            raw_texts: 原始文本数组

        Returns:
            提取出的题目列表
        """
        all_questions: list[dict[str, Any]] = []

        for text in raw_texts:
            # 截断过长的文本
            truncated = text[:3000]

            try:
                response = await self.llm_client.generate(
                    prompt=f"请从以下文本中提取题目结构，返回 JSON 数组：\n\n{truncated}",
                    system_prompt=PARSE_SYSTEM_PROMPT,
                    temperature=0.1,  # 低温度确保稳定输出
                    max_tokens=4000,
                )

                parsed = self._extract_json(response)
                all_questions.extend(parsed)

            except Exception as e:
                logger.error(f"AI 题目识别失败: {e}, text_preview={text[:100]}...")
                # 单段失败不影响其他段的处理
                continue

        return all_questions

    @staticmethod
    def _extract_json(response: str) -> list[dict[str, Any]]:
        """
        从 LLM 响应中提取 JSON 数组

        LLM 可能返回带有 markdown 代码块的 JSON，需要清理

        Args:
            response: LLM 原始响应文本

        Returns:
            解析出的字典列表
        """
        text = response.strip()

        # 尝试提取 markdown 代码块中的 JSON
        code_block_match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", text)
        if code_block_match:
            text = code_block_match.group(1).strip()

        # 尝试找到 JSON 数组
        array_match = re.search(r"\[[\s\S]*\]", text)
        if array_match:
            text = array_match.group(0)

        try:
            result = json.loads(text)
            if isinstance(result, list):
                return result
            elif isinstance(result, dict):
                # 如果返回的是单个对象，包装为数组
                return [result]
            else:
                logger.warning(f"AI 返回了非预期的 JSON 类型: {type(result)}")
                return []
        except json.JSONDecodeError as e:
            logger.error(f"AI 响应 JSON 解析失败: {e}, response_preview={response[:200]}...")
            return []
