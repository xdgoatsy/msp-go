# LangGraph 工作流详细设计

> **文档**: 智能体系统设计 - 第2部分
> **版本**: v1.0
> **日期**: 2026-01-22

[← 返回主文档](../智能体系统设计文档.md) | [文档索引](./README.md)

---

## 📋 目录

- [1. 状态定义](#1-状态定义)
- [2. 节点设计](#2-节点设计)
- [3. 边与路由](#3-边与路由)
- [4. 工作流编排](#4-工作流编排)
- [5. 持久化策略](#5-持久化策略)
- [6. 错误处理](#6-错误处理)

---

## 1. 状态定义

### 1.1 核心状态结构

```python
from typing import TypedDict, Annotated, Any
from langgraph.graph import add_messages
import operator

class StreamingState(TypedDict):
    """
    LangGraph 全局状态

    设计原则：
    1. 不可变性 - 每次更新返回新状态
    2. 类型安全 - 使用 TypedDict 强类型
    3. 可序列化 - 支持持久化到数据库
    """

    # ========== 会话标识 ==========
    session_id: str
    student_id: str

    # ========== 消息流（流式推送） ==========
    # 使用 Annotated 支持增量更新
    message_stream: Annotated[list[dict], operator.add]

    # ========== 智能体协作状态 ==========
    active_agents: set[str]  # 当前活跃的智能体
    agent_outputs: dict[str, Any]  # 各智能体的输出缓存
    current_agent: str | None  # 当前执行的智能体

    # ========== 学生认知状态 ==========
    cognitive_state: dict[str, float]  # {concept_id: mastery_probability}
    attention_span: float  # 注意力衰减系数 (0-1)
    frustration_level: float  # 挫败感指数 (0-1)
    confidence_level: float  # 自信度 (0-1)

    # ========== 教学上下文 ==========
    current_concept: str | None  # 当前学习的知识点
    current_problem: str | None  # 当前问题
    learning_path: list[str]  # 学习路径（知识点 ID 列表）
    path_index: int  # 当前路径位置

    # ========== 交互历史 ==========
    interaction_history: list[dict]  # 完整的交互记录
    last_message: str  # 最后一条用户消息
    last_response_time: float  # 最后响应时间（秒）

    # ========== 错误与诊断 ==========
    consecutive_errors: int  # 连续错误次数
    error_types: list[str]  # 错误类型历史
    last_diagnosis: dict | None  # 最后一次诊断结果

    # ========== 控制流 ==========
    should_continue: bool  # 是否继续学习循环
    intent: str | None  # 用户意图
    next_action: str | None  # 下一步动作

    # ========== 元数据 ==========
    session_start_time: float  # 会话开始时间
    total_interactions: int  # 总交互次数
    teaching_strategy: str  # 当前教学策略
```

### 1.2 状态更新策略

```python
# 使用 Annotated 实现增量更新
from typing import Annotated
import operator

# 消息流：追加模式
message_stream: Annotated[list[dict], operator.add]

# 示例：
state["message_stream"] = [{"role": "assistant", "content": "新消息"}]
# LangGraph 会自动追加到现有列表，而非覆盖

# 认知状态：合并模式
cognitive_state: Annotated[dict[str, float], merge_dicts]

def merge_dicts(a: dict, b: dict) -> dict:
    """合并字典，b 覆盖 a"""
    return {**a, **b}
```

---

## 2. 节点设计

### 2.1 节点类型分类

| 节点类型 | 职责 | 示例 |
|---------|------|------|
| **入口节点** | 接收用户输入，初始化状态 | `entry_node` |
| **路由节点** | 意图识别，决定下一步 | `intent_classifier` |
| **执行节点** | 调用智能体执行任务 | `solver_node`, `tutor_node` |
| **检测节点** | 监控状态，触发干预 | `emotion_detector`, `reflection_node` |
| **决策节点** | 条件判断，分支路由 | `should_continue_node` |
| **出口节点** | 清理状态，返回结果 | `exit_node` |

### 2.2 核心节点实现

#### 2.2.1 入口节点（Entry Node）

```python
async def entry_node(state: StreamingState) -> StreamingState:
    """
    入口节点：初始化会话状态

    职责：
    1. 验证会话 ID
    2. 加载学生画像
    3. 初始化认知状态
    """
    # 加载学生画像
    student_profile = await db.get_student_profile(state["student_id"])

    # 初始化认知状态
    state["cognitive_state"] = student_profile.mastery_vector
    state["attention_span"] = 1.0  # 初始注意力满值
    state["frustration_level"] = 0.0
    state["confidence_level"] = 0.5

    # 加载学习路径
    state["learning_path"] = await planner.get_learning_path(
        state["student_id"],
        state.get("target_concept")
    )
    state["path_index"] = 0

    # 初始化元数据
    state["session_start_time"] = time.time()
    state["total_interactions"] = 0
    state["teaching_strategy"] = "adaptive"  # 默认策略

    # 欢迎消息
    state["message_stream"] = [{
        "role": "assistant",
        "content": f"你好！我是你的数学学习助手。今天我们来学习「{state['current_concept']}」。",
        "metadata": {"type": "greeting"}
    }]

    return state
```

#### 2.2.2 意图分类节点（Intent Classifier）

```python
async def intent_classifier_node(state: StreamingState) -> StreamingState:
    """
    意图分类节点

    使用 LLM 识别用户意图
    """
    last_message = state["last_message"]

    # 检查是否有图片附件
    if state.get("attachments"):
        state["intent"] = "upload_image"
        return state

    # 使用 LLM 分类意图
    prompt = f"""
    分析用户消息的意图，从以下类别中选择一个：
    - ask_concept: 询问概念解释
    - solve_problem: 请求求解问题
    - submit_answer: 提交答案等待批改
    - request_exercise: 请求练习题
    - request_hint: 请求提示
    - general_chat: 一般对话

    用户消息：{last_message}

    只返回意图类别，不要解释。
    """

    intent = await llm.generate(prompt)
    state["intent"] = intent.strip()

    # 更新交互计数
    state["total_interactions"] += 1

    return state
```

#### 2.2.3 并行求解节点（Parallel Solver）

```python
async def parallel_solver_node(state: StreamingState) -> StreamingState:
    """
    并行求解节点（创新）

    同时启动多个求解策略，竞速机制
    """
    problem = state["current_problem"]

    # 流式推送：开始求解
    state["message_stream"] = [{
        "role": "assistant",
        "content": "正在求解中...",
        "metadata": {"type": "thinking", "agent": "solver"}
    }]

    # 并行启动多个求解器
    tasks = [
        solver_sympy.solve(problem),      # SymPy 符号求解
        solver_numerical.solve(problem),  # 数值方法
        solver_llm.solve(problem),        # LLM 推理（备选）
    ]

    # 竞速：谁先返回正确结果谁胜出
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 选择最优解
    best_result = None
    for result in results:
        if isinstance(result, Exception):
            continue
        if result.success and result.answer:
            best_result = result
            break

    if best_result:
        state["agent_outputs"]["solver"] = best_result
        state["message_stream"] = [{
            "role": "assistant",
            "content": f"答案是：{best_result.answer}",
            "metadata": {"type": "solution", "steps": best_result.steps}
        }]
    else:
        state["message_stream"] = [{
            "role": "assistant",
            "content": "抱歉，我暂时无法求解这个问题。",
            "metadata": {"type": "error"}
        }]

    return state
```

#### 2.2.4 情感检测节点（Emotion Detector）

```python
async def emotion_detector_node(state: StreamingState) -> StreamingState:
    """
    情感检测节点（创新）

    分析学生情绪，触发干预
    """
    # 收集情感信号
    signals = {
        "text_sentiment": await analyze_text_sentiment(state["last_message"]),
        "response_time": state["last_response_time"],
        "consecutive_errors": state["consecutive_errors"],
        "help_requests": state.get("help_count", 0),
        "time_on_task": time.time() - state["session_start_time"],
    }

    # 综合判断情绪
    emotion = classify_emotion(signals)

    # 更新状态
    state["frustration_level"] = emotion["frustration"]
    state["confidence_level"] = emotion["confidence"]

    # 判断是否需要干预
    intervention_needed = (
        emotion["frustration"] > 0.7 or
        emotion["confusion"] > 0.6 or
        emotion["boredom"] > 0.5
    )

    state["agent_outputs"]["emotion"] = {
        "emotion": emotion,
        "intervention_needed": intervention_needed,
        "suggested_action": suggest_intervention(emotion)
    }

    return state
```

#### 2.2.5 反思节点（Reflection Node）

```python
async def reflection_node(state: StreamingState) -> StreamingState:
    """
    反思节点（创新 - 元认知）

    评估学生理解深度
    """
    # 分析最近的交互
    recent_interactions = state["interaction_history"][-5:]

    # 评估理解深度
    understanding_depth = await assess_understanding(
        recent_interactions,
        state["current_concept"]
    )

    # 如果理解深度不足，触发深度提问
    if understanding_depth < 0.5:
        deep_question = await generate_deep_question(
            state["current_concept"],
            state["cognitive_state"]
        )

        state["message_stream"] = [{
            "role": "assistant",
            "content": deep_question,
            "metadata": {"type": "deep_question"}
        }]

        state["should_continue"] = True  # 继续对话
    else:
        # 理解充分，可以继续下一个知识点
        state["path_index"] += 1
        state["should_continue"] = state["path_index"] < len(state["learning_path"])

    return state
```

---

## 3. 边与路由

### 3.1 条件边（Conditional Edges）

```python
# 意图路由
workflow.add_conditional_edges(
    "intent_classifier",
    lambda state: state["intent"],
    {
        "ask_concept": "tutor_node",
        "solve_problem": "parallel_solver_node",
        "submit_answer": "diagnostician_node",
        "request_exercise": "planner_node",
        "request_hint": "tutor_node",
        "upload_image": "diagnostician_node",
        "general_chat": "tutor_node",
    }
)

# 情感干预路由
workflow.add_conditional_edges(
    "emotion_detector",
    lambda state: state["agent_outputs"]["emotion"]["intervention_needed"],
    {
        True: "intervention_node",   # 需要干预
        False: "reflection_node"     # 继续正常流程
    }
)

# 学习循环控制
workflow.add_conditional_edges(
    "planner_node",
    lambda state: state["should_continue"],
    {
        True: "intent_classifier",  # 继续学习
        False: "exit_node"          # 结束会话
    }
)
```

### 3.2 固定边（Normal Edges）

```python
# 求解后 → 导师讲解
workflow.add_edge("parallel_solver_node", "tutor_node")

# 诊断后 → 情感检测
workflow.add_edge("diagnostician_node", "emotion_detector")

# 导师讲解后 → 反思
workflow.add_edge("tutor_node", "reflection_node")

# 反思后 → 路径规划
workflow.add_edge("reflection_node", "planner_node")
```

---

## 4. 工作流编排

### 4.1 完整工作流定义

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# 创建状态图
workflow = StateGraph(StreamingState)

# ========== 添加节点 ==========
workflow.add_node("entry", entry_node)
workflow.add_node("intent_classifier", intent_classifier_node)
workflow.add_node("parallel_solver", parallel_solver_node)
workflow.add_node("diagnostician", diagnostician_node)
workflow.add_node("emotion_detector", emotion_detector_node)
workflow.add_node("tutor", tutor_node)
workflow.add_node("planner", planner_node)
workflow.add_node("reflection", reflection_node)
workflow.add_node("intervention", intervention_node)
workflow.add_node("exit", exit_node)

# ========== 设置入口 ==========
workflow.set_entry_point("entry")

# ========== 添加边 ==========
# 入口 → 意图分类
workflow.add_edge("entry", "intent_classifier")

# 意图分类 → 条件路由
workflow.add_conditional_edges(
    "intent_classifier",
    lambda state: state["intent"],
    {
        "ask_concept": "tutor",
        "solve_problem": "parallel_solver",
        "submit_answer": "diagnostician",
        "request_exercise": "planner",
        "upload_image": "diagnostician",
        "general_chat": "tutor",
    }
)

# 求解 → 导师
workflow.add_edge("parallel_solver", "tutor")

# 诊断 → 情感检测
workflow.add_edge("diagnostician", "emotion_detector")

# 情感检测 → 条件分支
workflow.add_conditional_edges(
    "emotion_detector",
    lambda state: state["agent_outputs"]["emotion"]["intervention_needed"],
    {
        True: "intervention",
        False: "reflection"
    }
)

# 干预 → 反思
workflow.add_edge("intervention", "reflection")

# 导师 → 反思
workflow.add_edge("tutor", "reflection")

# 反思 → 规划
workflow.add_edge("reflection", "planner")

# 规划 → 循环或结束
workflow.add_conditional_edges(
    "planner",
    lambda state: state["should_continue"],
    {
        True: "intent_classifier",
        False: "exit"
    }
)

# 出口 → END
workflow.add_edge("exit", END)

# ========== 编译工作流 ==========
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)
```

### 4.2 工作流可视化

```mermaid
graph TD
    Start([开始]) --> Entry[入口节点]
    Entry --> Intent[意图分类]

    Intent -->|询问概念| Tutor[导师节点]
    Intent -->|求解问题| Solver[并行求解]
    Intent -->|提交答案| Diag[诊断节点]
    Intent -->|请求练习| Planner[规划节点]

    Solver --> Tutor
    Diag --> Emotion[情感检测]

    Emotion -->|需要干预| Intervention[干预节点]
    Emotion -->|无需干预| Reflection[反思节点]

    Intervention --> Reflection
    Tutor --> Reflection

    Reflection --> Planner

    Planner -->|继续学习| Intent
    Planner -->|结束会话| Exit[出口节点]

    Exit --> End([结束])
```

---

## 5. 持久化策略

### 5.1 检查点（Checkpointing）

```python
from langgraph.checkpoint.postgres import PostgresSaver

# 使用 PostgreSQL 持久化状态
checkpointer = PostgresSaver(
    connection_string="postgresql://user:pass@localhost/db"
)

app = workflow.compile(checkpointer=checkpointer)

# 运行工作流（自动保存检查点）
result = await app.ainvoke(
    initial_state,
    config={"configurable": {"thread_id": session_id}}
)

# 恢复会话（从检查点继续）
resumed_result = await app.ainvoke(
    {"last_message": "继续"},
    config={"configurable": {"thread_id": session_id}}
)
```

### 5.2 状态快照

```python
# 获取当前状态快照
snapshot = await app.aget_state(
    config={"configurable": {"thread_id": session_id}}
)

print(snapshot.values)  # 当前状态
print(snapshot.next)    # 下一个节点
```

---

## 6. 错误处理

### 6.1 节点级错误处理

```python
async def safe_node_wrapper(node_func):
    """节点错误处理包装器"""
    async def wrapper(state: StreamingState) -> StreamingState:
        try:
            return await node_func(state)
        except Exception as e:
            # 记录错误
            logger.error(f"Node {node_func.__name__} failed: {e}")

            # 添加错误消息
            state["message_stream"] = [{
                "role": "assistant",
                "content": "抱歉，系统遇到了一些问题，请稍后再试。",
                "metadata": {"type": "error", "error": str(e)}
            }]

            # 标记需要人工介入
            state["should_continue"] = False

            return state

    return wrapper

# 应用包装器
workflow.add_node("solver", safe_node_wrapper(parallel_solver_node))
```

### 6.2 超时处理

```python
import asyncio

async def timeout_wrapper(node_func, timeout_seconds=30):
    """超时处理包装器"""
    async def wrapper(state: StreamingState) -> StreamingState:
        try:
            return await asyncio.wait_for(
                node_func(state),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            state["message_stream"] = [{
                "role": "assistant",
                "content": "处理超时，请简化问题后重试。",
                "metadata": {"type": "timeout"}
            }]
            return state

    return wrapper
```

---

## 📚 相关文档

- [← 返回主文档](../智能体系统设计文档.md)
- [智能体详细设计 →](./agents-detail.md)
- [性能优化方案](./performance-optimization.md)

---

**下一步**：查看 [智能体详细设计](./agents-detail.md) 了解各智能体的具体实现。
