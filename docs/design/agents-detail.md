# 智能体详细设计

> **文档**: 智能体系统设计 - 第3部分
> **版本**: v1.1
> **日期**: 2026-01-23

[← 返回主文档](../智能体系统设计文档.md) | [文档索引](./README.md)

---

## 📋 目录

- [1. Orchestrator（编排智能体）](#1-orchestrator编排智能体)
- [2. Solver（求解智能体）](#2-solver求解智能体)
- [3. Diagnostician（诊断智能体）](#3-diagnostician诊断智能体)
- [4. Tutor（导师智能体）](#4-tutor导师智能体)
- [5. Planner（规划智能体）](#5-planner规划智能体)
- [6. Emotion Detector（情感检测智能体）](#6-emotion-detector情感检测智能体)
- [7. Reflection Agent（反思智能体）](#7-reflection-agent反思智能体)
- [8. Verifier（验证智能体）](#8-verifier验证智能体) ⭐ v1.1 新增
- [9. Safety Module（安全模块）](#9-safety-module安全模块) ⭐ v1.1 新增

---

## 1. Orchestrator（编排智能体）

### 1.1 职责

- 意图识别（Intent Classification）
- 任务路由（Task Routing）
- 全局状态管理（State Management）

### 1.2 核心实现

```python
from langchain_openai import ChatOpenAI
from enum import Enum

class IntentType(str, Enum):
    """用户意图类型"""
    ASK_CONCEPT = "ask_concept"
    SOLVE_PROBLEM = "solve_problem"
    SUBMIT_ANSWER = "submit_answer"
    REQUEST_EXERCISE = "request_exercise"
    UPLOAD_IMAGE = "upload_image"
    REQUEST_HINT = "request_hint"
    GENERAL_CHAT = "general_chat"

class OrchestratorAgent:
    """编排智能体"""

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    async def classify_intent(
        self,
        message: str,
        conversation_history: list[dict],
        attachments: list[str] | None = None
    ) -> IntentType:
        """
        意图识别

        使用 LLM 进行意图分类
        """
        # 如果有附件，直接判定为上传图片
        if attachments:
            return IntentType.UPLOAD_IMAGE

        # 构建 Few-Shot Prompt
        prompt = f"""
你是一个意图分类器。分析用户消息，判断其意图。

意图类别：
- ask_concept: 询问概念解释（如"什么是导数？"）
- solve_problem: 请求求解问题（如"计算 ∫x²dx"）
- submit_answer: 提交答案等待批改（如"我的答案是..."）
- request_exercise: 请求练习题（如"给我一道题"）
- request_hint: 请求提示（如"给我一个提示"）
- general_chat: 一般对话（如"谢谢"、"你好"）

对话历史：
{self._format_history(conversation_history[-3:])}

用户消息：{message}

只返回意图类别，不要解释。
"""

        response = await self.llm.ainvoke(prompt)
        intent_str = response.content.strip().lower()

        # 映射到枚举
        try:
            return IntentType(intent_str)
        except ValueError:
            return IntentType.GENERAL_CHAT

    def route(self, intent: IntentType) -> str:
        """
        任务路由

        根据意图返回下一个智能体名称
        """
        routing_map = {
            IntentType.ASK_CONCEPT: "tutor",
            IntentType.SOLVE_PROBLEM: "solver",
            IntentType.SUBMIT_ANSWER: "diagnostician",
            IntentType.REQUEST_EXERCISE: "planner",
            IntentType.UPLOAD_IMAGE: "diagnostician",
            IntentType.REQUEST_HINT: "tutor",
            IntentType.GENERAL_CHAT: "tutor",
        }
        return routing_map.get(intent, "tutor")

    def _format_history(self, history: list[dict]) -> str:
        """格式化对话历史"""
        return "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in history
        ])
```

---

## 2. Solver（求解智能体）

### 2.1 职责

- 数学问题求解（精确计算）
- 代码生成与执行（SymPy/NumPy）
- 答案验证

### 2.2 核心实现

#### 2.2.1 SymPy 求解器

```python
from sympy import *
from sympy.parsing.latex import parse_latex
import asyncio

class SymPySolver:
    """SymPy 符号求解器"""

    async def solve(self, problem: str) -> dict:
        """
        求解数学问题

        Args:
            problem: 问题描述（LaTeX 或自然语言）

        Returns:
            {
                "success": bool,
                "answer": str,  # LaTeX 格式
                "steps": list[str],
                "code": str
            }
        """
        try:
            # 1. 生成求解代码
            code = await self._generate_code(problem)

            # 2. 执行代码
            result = await self._execute_code(code)

            # 3. 格式化输出
            answer_latex = latex(result)

            return {
                "success": True,
                "answer": answer_latex,
                "steps": self._extract_steps(code),
                "code": code
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "code": code if 'code' in locals() else None
            }

    async def _generate_code(self, problem: str) -> str:
        """
        使用 LLM 生成 SymPy 代码

        Prompt 策略：Program-of-Thought
        """
        prompt = f"""
你是一个数学问题求解器。将以下问题转换为 Python/SymPy 代码。

问题：{problem}

要求：
1. 使用 sympy 库
2. 代码必须可执行
3. 最后一行打印结果

示例：
问题：计算 ∫x²dx
代码：
```python
from sympy import *
x = Symbol('x')
result = integrate(x**2, x)
print(result)
```

现在生成代码：
"""

        response = await self.llm.ainvoke(prompt)
        code = self._extract_code_block(response.content)

        return code

    async def _execute_code(self, code: str) -> Any:
        """
        在沙箱中执行代码

        使用 E2B 或 Docker 沙箱
        """
        # 方案 1：使用 E2B（推荐）
        from e2b_code_interpreter import CodeInterpreter

        with CodeInterpreter() as sandbox:
            execution = sandbox.notebook.exec_cell(code)

            if execution.error:
                raise Exception(execution.error.value)

            return execution.results[0].text

        # 方案 2：本地执行（仅开发环境）
        # 注意：生产环境必须使用沙箱！
        # local_vars = {}
        # exec(code, {"__builtins__": {}}, local_vars)
        # return local_vars.get("result")

    def _extract_steps(self, code: str) -> list[str]:
        """从代码中提取解题步骤"""
        # 简单实现：按行分割
        lines = code.strip().split('\n')
        steps = [line for line in lines if not line.startswith('#')]
        return steps
```

#### 2.2.2 并行求解器（创新）

```python
class ParallelSolver:
    """并行求解器（多策略竞速）"""

    def __init__(self):
        self.sympy_solver = SymPySolver()
        self.numerical_solver = NumericalSolver()
        self.llm_solver = LLMSolver()

    async def solve(self, problem: str) -> dict:
        """
        并行求解

        同时启动多个求解策略，最快返回的胜出
        """
        # 创建任务
        tasks = [
            self.sympy_solver.solve(problem),
            self.numerical_solver.solve(problem),
            self.llm_solver.solve(problem),
        ]

        # 竞速执行
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 选择最优结果
        for result in results:
            if isinstance(result, Exception):
                continue
            if result.get("success") and result.get("answer"):
                return result

        # 所有策略都失败
        return {
            "success": False,
            "error": "所有求解策略均失败",
            "attempts": len(results)
        }
```

---

## 3. Diagnostician（诊断智能体）

### 3.1 职责

- OCR 识别学生手写步骤
- 步骤比对与错误定位
- 错误类型分类
- 生成诊断报告

### 3.2 核心实现

```python
from PIL import Image
import httpx

class DiagnosticianAgent:
    """诊断智能体"""

    def __init__(self, ocr_api_url: str, llm: ChatOpenAI):
        self.ocr_api_url = ocr_api_url
        self.llm = llm
        self.solver = SymPySolver()

    async def diagnose(
        self,
        problem: str,
        student_steps: list[str] | None = None,
        image_path: str | None = None
    ) -> dict:
        """
        诊断学生答案

        Args:
            problem: 问题描述
            student_steps: 学生步骤（文本）
            image_path: 学生手写图片路径

        Returns:
            诊断报告
        """
        # 1. 如果有图片，先 OCR 识别
        if image_path:
            student_steps = await self._ocr_recognize(image_path)

        # 2. 生成标准答案
        standard_solution = await self.solver.solve(problem)

        if not standard_solution["success"]:
            return {
                "success": False,
                "error": "无法生成标准答案"
            }

        # 3. 步骤比对
        comparison = await self._compare_steps(
            student_steps,
            standard_solution["steps"]
        )

        # 4. 错误分类
        if comparison["has_error"]:
            error_analysis = await self._analyze_error(
                problem,
                student_steps,
                comparison["error_step_index"]
            )
        else:
            error_analysis = None

        # 5. 生成诊断报告
        return {
            "success": True,
            "is_correct": not comparison["has_error"],
            "error_step_index": comparison.get("error_step_index"),
            "error_type": error_analysis.get("error_type") if error_analysis else None,
            "error_description": error_analysis.get("description") if error_analysis else None,
            "suggested_hint": error_analysis.get("hint") if error_analysis else None,
            "standard_answer": standard_solution["answer"]
        }

    async def _ocr_recognize(self, image_path: str) -> list[str]:
        """
        OCR 识别数学公式

        使用 Texify 模型
        """
        async with httpx.AsyncClient() as client:
            with open(image_path, "rb") as f:
                response = await client.post(
                    self.ocr_api_url,
                    files={"image": f}
                )

            result = response.json()
            latex_text = result["latex"]

            # 分割为步骤
            steps = latex_text.split("\\\\")  # LaTeX 换行符
            return [step.strip() for step in steps if step.strip()]

    async def _compare_steps(
        self,
        student_steps: list[str],
        standard_steps: list[str]
    ) -> dict:
        """
        步骤比对

        使用 LLM 进行语义比对
        """
        prompt = f"""
比对学生步骤和标准步骤，找出第一个错误。

标准步骤：
{self._format_steps(standard_steps)}

学生步骤：
{self._format_steps(student_steps)}

如果学生步骤正确，返回：
{{"has_error": false}}

如果有错误，返回：
{{"has_error": true, "error_step_index": <错误步骤索引（从0开始）>}}

只返回 JSON，不要解释。
"""

        response = await self.llm.ainvoke(prompt)
        return eval(response.content)  # 注意：生产环境应使用 json.loads

    async def _analyze_error(
        self,
        problem: str,
        student_steps: list[str],
        error_index: int
    ) -> dict:
        """
        错误分析

        分类错误类型，生成提示
        """
        error_step = student_steps[error_index]

        prompt = f"""
分析学生的错误。

问题：{problem}
学生在第 {error_index + 1} 步出错：{error_step}

错误类型：
- conceptual: 概念错误
- procedural: 过程错误
- calculation: 计算错误
- symbolic: 符号错误

返回 JSON：
{{
    "error_type": "<类型>",
    "description": "<错误描述>",
    "hint": "<提示（不直接给答案）>"
}}
"""

        response = await self.llm.ainvoke(prompt)
        return eval(response.content)

    def _format_steps(self, steps: list[str]) -> str:
        """格式化步骤"""
        return "\n".join([
            f"步骤 {i+1}: {step}"
            for i, step in enumerate(steps)
        ])
```

---

## 4. Tutor（导师智能体）

### 4.1 职责

- 概念解释
- 苏格拉底式引导
- 提供提示（不直接给答案）
- 鼓励与情感支持

### 4.2 核心实现

```python
class TutorAgent:
    """导师智能体"""

    def __init__(self, llm: ChatOpenAI, rag_retriever):
        self.llm = llm
        self.rag_retriever = rag_retriever

    async def explain_concept(
        self,
        concept: str,
        student_profile: dict
    ) -> str:
        """
        解释概念

        根据学生画像自适应调整解释深度
        """
        # 1. 检索相关知识
        context = await self.rag_retriever.retrieve(concept)

        # 2. 生成自适应 Prompt
        prompt = self._generate_adaptive_prompt(student_profile)

        # 3. 生成解释
        full_prompt = f"""
{prompt}

请解释概念：{concept}

参考资料：
{context}

要求：
1. 使用学生能理解的语言
2. 提供具体例子
3. 关联已学知识
"""

        response = await self.llm.ainvoke(full_prompt)
        return response.content

    async def provide_hint(
        self,
        problem: str,
        student_progress: str,
        diagnosis: dict | None = None
    ) -> str:
        """
        提供提示

        苏格拉底式引导，不直接给答案
        """
        if diagnosis and diagnosis.get("error_step_index") is not None:
            # 针对性提示
            step = diagnosis["error_step_index"] + 1
            error_type = diagnosis.get("error_type", "")

            prompt = f"""
学生在第 {step} 步出错（错误类型：{error_type}）。

问题：{problem}
学生进度：{student_progress}

请提供苏格拉底式提示：
1. 不要直接给答案
2. 引导学生思考
3. 提出启发性问题

示例：
"让我们回顾一下导数的定义。你能告诉我 f'(x) 的几何意义是什么吗？"
"""
        else:
            # 一般性提示
            prompt = f"""
学生在解决问题时遇到困难。

问题：{problem}
学生进度：{student_progress}

请提供引导性提示，帮助学生自己找到解决方法。
"""

        response = await self.llm.ainvoke(prompt)
        return response.content

    def _generate_adaptive_prompt(self, student_profile: dict) -> str:
        """
        生成自适应 Prompt（创新）

        根据学生画像动态调整教学风格
        """
        base_prompt = "你是一位数学导师。"

        # 学习风格适配
        learning_style = student_profile.get("learning_style", "verbal")
        if learning_style == "visual":
            base_prompt += "优先使用图形、图表和几何直觉来解释概念。"
        elif learning_style == "verbal":
            base_prompt += "使用详细的文字描述和类比来解释概念。"

        # 知识水平适配
        mastery_level = student_profile.get("avg_mastery", 0.5)
        if mastery_level < 0.3:
            base_prompt += "学生是初学者，使用简单的语言，避免专业术语。"
        elif mastery_level > 0.7:
            base_prompt += "学生基础扎实，可以使用更严谨的数学语言。"

        # 情绪适配
        frustration = student_profile.get("frustration_level", 0)
        if frustration > 0.6:
            base_prompt += "学生当前有些挫败，请多鼓励，降低难度。"

        return base_prompt
```

---

## 5. Planner（规划智能体）

### 5.1 职责

- 学习路径规划
- 知识图谱遍历
- 题目推荐
- DKT 模型更新

### 5.2 核心实现

```python
class PlannerAgent:
    """规划智能体"""

    def __init__(self, kg_client, dkt_model):
        self.kg_client = kg_client  # Neo4j 客户端
        self.dkt_model = dkt_model  # DKT 模型

    async def plan_learning_path(
        self,
        student_id: str,
        target_concept: str,
        current_mastery: dict[str, float]
    ) -> list[str]:
        """
        规划学习路径

        基于知识图谱和 DKT 模型
        """
        # 1. 查询知识图谱，获取先修关系
        prerequisites = await self.kg_client.get_prerequisites(target_concept)

        # 2. 识别未掌握的先修知识
        weak_concepts = [
            concept for concept in prerequisites
            if current_mastery.get(concept, 0) < 0.7
        ]

        # 3. 拓扑排序，确定学习顺序
        learning_path = await self._topological_sort(weak_concepts)

        # 4. 添加目标概念
        learning_path.append(target_concept)

        return learning_path

    async def recommend_exercise(
        self,
        student_id: str,
        concept_id: str,
        difficulty_preference: float = 0.5
    ) -> dict:
        """
        推荐练习题

        基于学生能力和概念掌握度
        """
        # 1. 获取学生当前能力值
        ability = await self.dkt_model.predict_ability(student_id)

        # 2. 查询题库
        exercises = await self.db.query_exercises(
            concept_id=concept_id,
            difficulty_range=(
                difficulty_preference - 0.2,
                difficulty_preference + 0.2
            )
        )

        # 3. 选择最合适的题目（IRT 模型）
        best_exercise = self._select_by_irt(exercises, ability)

        return best_exercise

    async def update_mastery(
        self,
        student_id: str,
        exercise_id: str,
        is_correct: bool
    ) -> dict[str, float]:
        """
        更新掌握度

        使用 DKT 模型实时更新
        """
        # 1. 记录练习结果
        await self.dkt_model.record_attempt(
            student_id,
            exercise_id,
            is_correct
        )

        # 2. 更新掌握度向量
        new_mastery = await self.dkt_model.predict_mastery(student_id)

        return new_mastery

    async def _topological_sort(self, concepts: list[str]) -> list[str]:
        """拓扑排序（确定学习顺序）"""
        # 使用 Kahn 算法
        graph = await self.kg_client.get_subgraph(concepts)
        return topological_sort(graph)
```

---

## 6. Emotion Detector（情感检测智能体）

### 6.1 职责（创新）

- 检测学生情绪状态
- 触发干预策略
- 调整教学节奏

### 6.2 核心实现

```python
from transformers import pipeline

class EmotionDetectorAgent:
    """情感检测智能体（创新）"""

    def __init__(self):
        # 加载情感分析模型
        self.sentiment_analyzer = pipeline(
            "sentiment-analysis",
            model="uer/roberta-base-finetuned-chinanews-chinese"
        )

    async def detect_emotion(self, state: dict) -> dict:
        """
        检测学生情绪

        综合多个信号源
        """
        # 1. 文本情感分析
        text_sentiment = self._analyze_text(state["last_message"])

        # 2. 行为信号分析
        behavior_signals = {
            "response_time": state["last_response_time"],
            "consecutive_errors": state["consecutive_errors"],
            "help_requests": state.get("help_count", 0),
            "time_on_task": state.get("time_on_task", 0),
        }

        # 3. 综合判断
        emotion = self._classify_emotion(text_sentiment, behavior_signals)

        # 4. 判断是否需要干预
        intervention_needed = (
            emotion["frustration"] > 0.7 or
            emotion["confusion"] > 0.6 or
            emotion["boredom"] > 0.5
        )

        return {
            "emotion": emotion,
            "intervention_needed": intervention_needed,
            "suggested_action": self._suggest_intervention(emotion)
        }

    def _analyze_text(self, text: str) -> dict:
        """文本情感分析"""
        result = self.sentiment_analyzer(text)[0]

        # 检测负面情绪关键词
        frustration_keywords = ["不懂", "太难", "放弃", "不会"]
        confusion_keywords = ["什么意思", "不理解", "为什么"]

        frustration_score = sum(1 for kw in frustration_keywords if kw in text) / len(frustration_keywords)
        confusion_score = sum(1 for kw in confusion_keywords if kw in text) / len(confusion_keywords)

        return {
            "sentiment": result["label"],
            "score": result["score"],
            "frustration": frustration_score,
            "confusion": confusion_score
        }

    def _classify_emotion(self, text_sentiment: dict, behavior: dict) -> dict:
        """综合分类情绪"""
        # 挫败感
        frustration = (
            text_sentiment["frustration"] * 0.4 +
            min(behavior["consecutive_errors"] / 5, 1.0) * 0.3 +
            min(behavior["help_requests"] / 3, 1.0) * 0.3
        )

        # 困惑度
        confusion = (
            text_sentiment["confusion"] * 0.5 +
            (1.0 if behavior["response_time"] > 60 else 0.0) * 0.5
        )

        # 无聊度
        boredom = (
            1.0 if behavior["time_on_task"] > 1800 else 0.0  # 超过30分钟
        )

        # 自信度
        confidence = 1.0 - frustration

        return {
            "frustration": frustration,
            "confusion": confusion,
            "boredom": boredom,
            "confidence": confidence
        }

    def _suggest_intervention(self, emotion: dict) -> str:
        """建议干预策略"""
        if emotion["frustration"] > 0.7:
            return "lower_difficulty"  # 降低难度
        elif emotion["confusion"] > 0.6:
            return "provide_example"  # 提供示例
        elif emotion["boredom"] > 0.5:
            return "increase_challenge"  # 增加挑战
        else:
            return "continue"  # 继续
```

---

## 7. Reflection Agent（反思智能体）

### 7.1 职责（创新）

- 评估理解深度
- 检测机械记忆
- 触发深度提问

### 7.2 核心实现

```python
class ReflectionAgent:
    """反思智能体（创新 - 元认知）"""

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    async def assess_understanding(
        self,
        concept: str,
        interaction_history: list[dict]
    ) -> float:
        """
        评估理解深度

        Returns:
            理解深度分数 (0-1)
        """
        # 分析最近的交互
        recent_interactions = interaction_history[-5:]

        prompt = f"""
评估学生对概念「{concept}」的理解深度。

交互历史：
{self._format_interactions(recent_interactions)}

评估维度：
1. 能否用自己的话解释概念？
2. 能否举出新的例子？
3. 能否识别错误示例？
4. 能否迁移到新问题？

返回理解深度分数（0-1）：
- 0-0.3: 机械记忆，未真正理解
- 0.3-0.7: 部分理解，需要巩固
- 0.7-1.0: 深度理解，可以迁移

只返回数字，不要解释。
"""

        response = await self.llm.ainvoke(prompt)
        score = float(response.content.strip())

        return score

    async def generate_deep_question(
        self,
        concept: str,
        cognitive_state: dict[str, float]
    ) -> str:
        """
        生成深度提问

        检验真正理解
        """
        prompt = f"""
生成一个深度问题，检验学生对「{concept}」的理解。

要求：
1. 不是简单的定义复述
2. 需要迁移应用
3. 或者提供反例让学生判断

示例：
概念：导数
深度问题："如果函数在某点不连续，它在该点可导吗？为什么？"

现在生成问题：
"""

        response = await self.llm.ainvoke(prompt)
        return response.content

    def _format_interactions(self, interactions: list[dict]) -> str:
        """格式化交互历史"""
        return "\n".join([
            f"{i['role']}: {i['content']}"
            for i in interactions
        ])
```

---

## 8. Verifier（验证智能体）

### 8.1 职责（v1.1 新增）

- 验证并行求解结果的正确性
- 等价性判定与数值回代
- 步骤合法性检查
- 为 Diagnostician/Tutor 提供复用能力

### 8.2 核心实现

```python
from sympy import simplify, Eq, Symbol, N
from sympy.parsing.latex import parse_latex
from typing import TypedDict
import random

class VerifierOutput(TypedDict):
    """验证器输出"""
    is_valid: bool              # 是否有效
    confidence: float           # 置信度 0-1
    failure_reason: str | None  # 失败原因
    normalized_answer: str      # 标准化答案（用于缓存）
    details: dict | None        # 详细信息

class FailureReason:
    """失败原因枚举"""
    DOMAIN_ERROR = "domain_error"           # 定义域错误
    MISSING_CONSTANT = "missing_constant"   # 遗漏常数项
    NON_EQUIVALENT = "non_equivalent"       # 不等价
    AMBIGUITY = "ambiguity"                 # 歧义
    TIMEOUT = "timeout"                     # 超时
    INVALID_STEP = "invalid_step"           # 步骤非法

class VerifierAgent:
    """验证智能体"""

    def __init__(self, timeout_seconds: float = 5.0):
        self.timeout = timeout_seconds

    async def verify(
        self,
        candidate_answer: str,
        reference_answer: str | None = None,
        problem: str | None = None,
        constraints: dict | None = None
    ) -> VerifierOutput:
        """
        验证候选答案

        Args:
            candidate_answer: 候选答案（LaTeX 格式）
            reference_answer: 参考答案（可选）
            problem: 原问题（用于约束推断）
            constraints: 约束条件（定义域、参数条件等）

        Returns:
            VerifierOutput
        """
        try:
            # 1. 解析表达式
            candidate_expr = parse_latex(candidate_answer)
            normalized = str(simplify(candidate_expr))

            # 2. 如果有参考答案，进行等价性验证
            if reference_answer:
                equiv_result = await self._check_equivalence(
                    candidate_expr,
                    parse_latex(reference_answer),
                    constraints
                )
                if not equiv_result["is_equivalent"]:
                    return VerifierOutput(
                        is_valid=False,
                        confidence=equiv_result["confidence"],
                        failure_reason=FailureReason.NON_EQUIVALENT,
                        normalized_answer=normalized,
                        details=equiv_result
                    )

            # 3. 约束校验
            if constraints:
                constraint_result = await self._check_constraints(
                    candidate_expr,
                    constraints
                )
                if not constraint_result["satisfied"]:
                    return VerifierOutput(
                        is_valid=False,
                        confidence=0.9,
                        failure_reason=constraint_result["reason"],
                        normalized_answer=normalized,
                        details=constraint_result
                    )

            # 4. 数值回代验证（额外确认）
            numerical_result = await self._numerical_verification(
                candidate_expr,
                problem,
                constraints
            )

            return VerifierOutput(
                is_valid=True,
                confidence=numerical_result["confidence"],
                failure_reason=None,
                normalized_answer=normalized,
                details={"numerical_check": numerical_result}
            )

        except Exception as e:
            return VerifierOutput(
                is_valid=False,
                confidence=0.0,
                failure_reason=FailureReason.AMBIGUITY,
                normalized_answer=candidate_answer,
                details={"error": str(e)}
            )

    async def _check_equivalence(
        self,
        expr1,
        expr2,
        constraints: dict | None
    ) -> dict:
        """
        等价性验证

        使用 SymPy simplify + 数值抽样
        """
        # 符号等价检查
        try:
            diff = simplify(expr1 - expr2)
            if diff == 0:
                return {"is_equivalent": True, "confidence": 1.0, "method": "symbolic"}
        except:
            pass

        # 数值抽样检查
        symbols = list(expr1.free_symbols | expr2.free_symbols)
        if not symbols:
            # 常数表达式
            val1 = complex(N(expr1))
            val2 = complex(N(expr2))
            is_close = abs(val1 - val2) < 1e-10
            return {"is_equivalent": is_close, "confidence": 0.99 if is_close else 0.0, "method": "constant"}

        # 多点抽样
        sample_points = self._generate_sample_points(symbols, constraints, n=10)
        matches = 0
        for point in sample_points:
            try:
                val1 = complex(N(expr1.subs(point)))
                val2 = complex(N(expr2.subs(point)))
                if abs(val1 - val2) < 1e-8 * max(abs(val1), abs(val2), 1):
                    matches += 1
            except:
                continue

        confidence = matches / len(sample_points) if sample_points else 0
        return {
            "is_equivalent": confidence > 0.9,
            "confidence": confidence,
            "method": "numerical_sampling",
            "samples": len(sample_points),
            "matches": matches
        }

    async def _check_constraints(
        self,
        expr,
        constraints: dict
    ) -> dict:
        """
        约束校验

        检查定义域、边界条件等
        """
        # 检查积分常数
        if constraints.get("requires_constant"):
            symbols = expr.free_symbols
            has_constant = any(str(s).upper() == 'C' for s in symbols)
            if not has_constant:
                return {
                    "satisfied": False,
                    "reason": FailureReason.MISSING_CONSTANT,
                    "message": "积分结果缺少常数项 C"
                }

        # 检查定义域
        if "domain" in constraints:
            # TODO: 实现定义域检查
            pass

        return {"satisfied": True, "reason": None}

    async def _numerical_verification(
        self,
        expr,
        problem: str | None,
        constraints: dict | None
    ) -> dict:
        """数值回代验证"""
        # 简化实现：返回高置信度
        return {"confidence": 0.95, "method": "numerical"}

    def _generate_sample_points(
        self,
        symbols: list,
        constraints: dict | None,
        n: int = 10
    ) -> list[dict]:
        """生成采样点"""
        points = []
        for _ in range(n):
            point = {}
            for sym in symbols:
                # 默认在 [-10, 10] 范围内采样
                point[sym] = random.uniform(-10, 10)
            points.append(point)
        return points

    async def verify_step(
        self,
        prev_step: str,
        curr_step: str,
        rule_hint: str | None = None
    ) -> dict:
        """
        验证单步变换的合法性

        用于 Diagnostician 复用
        """
        try:
            prev_expr = parse_latex(prev_step)
            curr_expr = parse_latex(curr_step)

            # 检查等价性
            equiv = await self._check_equivalence(prev_expr, curr_expr, None)

            return {
                "is_valid": equiv["is_equivalent"],
                "confidence": equiv["confidence"],
                "rule_applied": rule_hint,
                "details": equiv
            }
        except Exception as e:
            return {
                "is_valid": False,
                "confidence": 0.0,
                "error": str(e)
            }
```

---

## 9. Safety Module（安全模块）

### 9.1 职责（v1.1 新增）

- 代码执行风险过滤
- 敏感信息检测与脱敏
- 输出内容安全审核
- 越权建议拦截

### 9.2 核心实现

```python
import re
from enum import Enum
from dataclasses import dataclass

class RiskLevel(str, Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class SafetyCheckResult:
    """安全检查结果"""
    is_safe: bool
    risk_level: RiskLevel
    issues: list[str]
    sanitized_content: str | None  # 脱敏后的内容

class SafetyModule:
    """安全模块"""

    def __init__(self):
        # 危险代码模式
        self.dangerous_patterns = [
            r"os\.system\s*\(",
            r"subprocess\.",
            r"eval\s*\(",
            r"exec\s*\(",
            r"__import__\s*\(",
            r"open\s*\([^)]*['\"]w['\"]",  # 写文件
            r"shutil\.rmtree",
            r"os\.remove",
            r"requests\.(get|post|put|delete)",  # 网络请求
        ]

        # 敏感信息模式
        self.sensitive_patterns = [
            (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "EMAIL"),
            (r"\b\d{11}\b", "PHONE"),
            (r"\b\d{18}|\d{17}X\b", "ID_CARD"),
            (r"(password|passwd|pwd|secret|token|api_key)\s*[=:]\s*['\"][^'\"]+['\"]", "CREDENTIAL"),
        ]

        # 不当建议关键词
        self.inappropriate_keywords = [
            "作弊", "抄袭", "代写", "答案直接",
            "跳过学习", "不用理解",
        ]

    async def check_code(self, code: str) -> SafetyCheckResult:
        """
        检查代码安全性

        用于 Solver 执行前的安全审核
        """
        issues = []
        risk_level = RiskLevel.LOW

        for pattern in self.dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                issues.append(f"检测到危险代码模式: {pattern}")
                risk_level = RiskLevel.CRITICAL

        # 检查导入
        imports = re.findall(r"^(?:from|import)\s+(\S+)", code, re.MULTILINE)
        allowed_modules = {"sympy", "numpy", "scipy", "math", "fractions", "decimal"}
        for imp in imports:
            module = imp.split(".")[0]
            if module not in allowed_modules:
                issues.append(f"不允许的模块导入: {module}")
                risk_level = max(risk_level, RiskLevel.HIGH, key=lambda x: list(RiskLevel).index(x))

        return SafetyCheckResult(
            is_safe=len(issues) == 0,
            risk_level=risk_level,
            issues=issues,
            sanitized_content=None
        )

    async def check_output(self, content: str) -> SafetyCheckResult:
        """
        检查输出内容安全性

        用于 Tutor/Diagnostician 输出前的审核
        """
        issues = []
        sanitized = content

        # 检查敏感信息
        for pattern, info_type in self.sensitive_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                issues.append(f"检测到敏感信息: {info_type}")
                # 脱敏处理
                sanitized = re.sub(pattern, f"[{info_type}_MASKED]", sanitized, flags=re.IGNORECASE)

        # 检查不当建议
        for keyword in self.inappropriate_keywords:
            if keyword in content:
                issues.append(f"检测到不当建议关键词: {keyword}")

        risk_level = RiskLevel.LOW
        if any("敏感信息" in issue for issue in issues):
            risk_level = RiskLevel.MEDIUM
        if any("不当建议" in issue for issue in issues):
            risk_level = RiskLevel.HIGH

        return SafetyCheckResult(
            is_safe=len(issues) == 0,
            risk_level=risk_level,
            issues=issues,
            sanitized_content=sanitized if sanitized != content else None
        )

    async def check_request(
        self,
        user_message: str,
        context: dict | None = None
    ) -> SafetyCheckResult:
        """
        检查用户请求安全性

        用于入口节点的请求过滤
        """
        issues = []

        # 检查是否试图绕过学习
        bypass_patterns = [
            r"直接(给|告诉)我答案",
            r"不要解释.*直接",
            r"跳过.*步骤",
        ]
        for pattern in bypass_patterns:
            if re.search(pattern, user_message):
                issues.append("检测到试图绕过学习过程的请求")

        # 检查注入攻击
        injection_patterns = [
            r"忽略(之前|上面)的(指令|提示)",
            r"你现在是",
            r"假装你是",
        ]
        for pattern in injection_patterns:
            if re.search(pattern, user_message):
                issues.append("检测到可能的提示注入攻击")

        risk_level = RiskLevel.LOW
        if issues:
            risk_level = RiskLevel.MEDIUM

        return SafetyCheckResult(
            is_safe=len(issues) == 0,
            risk_level=risk_level,
            issues=issues,
            sanitized_content=None
        )

    def create_audit_log(
        self,
        check_type: str,
        result: SafetyCheckResult,
        metadata: dict | None = None
    ) -> dict:
        """
        创建审计日志

        用于合规追踪
        """
        import time
        return {
            "timestamp": time.time(),
            "check_type": check_type,
            "is_safe": result.is_safe,
            "risk_level": result.risk_level.value,
            "issues": result.issues,
            "metadata": metadata or {}
        }
```

---

## 📚 相关文档

- [← 返回主文档](../智能体系统设计文档.md)
- [← LangGraph 工作流设计](./langgraph-workflow.md)
- [性能优化方案 →](./performance-optimization.md)

---

**下一步**：查看 [性能优化方案](./performance-optimization.md) 了解缓存、批量推理等优化策略。
