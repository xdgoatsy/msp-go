# 代码示例与快速开始

> **文档**: 智能体系统设计 - 第5部分
> **版本**: v1.0
> **日期**: 2026-01-22

[← 返回主文档](../智能体系统设计文档.md) | [文档索引](./README.md)

---

## 📋 目录

- [1. 快速开始](#1-快速开始)
- [2. 完整示例](#2-完整示例)
- [3. 测试用例](#3-测试用例)
- [4. 常见问题](#4-常见问题)

---

## 1. 快速开始

### 1.1 环境准备

```bash
# 1. 克隆项目
git clone https://github.com/your-org/MathStudyPlatform.git
cd MathStudyPlatform/backend

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. 安装依赖
pip install -e ".[dev,ai]"

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入 API 密钥

# 5. 启动数据库
docker-compose up -d postgres redis neo4j qdrant

# 6. 运行数据库迁移
alembic upgrade head

# 7. 启动服务
uvicorn app.main:app --reload
```

### 1.2 第一个智能体调用

```python
# examples/hello_agent.py

import asyncio
from app.agents.solver import SymPySolver
from langchain_openai import ChatOpenAI

async def main():
    # 初始化 LLM
    llm = ChatOpenAI(
        api_key="your_api_key",
        base_url="https://api.deepseek.com",
        model="deepseek-chat"
    )

    # 创建求解器
    solver = SymPySolver(llm)

    # 求解问题
    problem = "计算 ∫x²dx"
    result = await solver.solve(problem)

    print(f"答案: {result['answer']}")
    print(f"步骤: {result['steps']}")

if __name__ == "__main__":
    asyncio.run(main())
```

运行：
```bash
python examples/hello_agent.py
```

---

## 2. 完整示例

### 2.1 完整的 LangGraph 工作流

```python
# examples/complete_workflow.py

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict, Annotated
import operator

# ========== 1. 定义状态 ==========
class MathLearningState(TypedDict):
    session_id: str
    student_id: str
    message_stream: Annotated[list[dict], operator.add]
    current_problem: str | None
    intent: str | None
    should_continue: bool

# ========== 2. 定义节点 ==========
async def entry_node(state: MathLearningState) -> MathLearningState:
    """入口节点"""
    state["message_stream"] = [{
        "role": "assistant",
        "content": "你好！我是你的数学学习助手。"
    }]
    return state

async def intent_classifier_node(state: MathLearningState) -> MathLearningState:
    """意图分类节点"""
    # 简化版：基于关键词
    message = state.get("last_message", "")

    if "计算" in message or "求" in message:
        state["intent"] = "solve_problem"
    elif "什么是" in message or "解释" in message:
        state["intent"] = "ask_concept"
    else:
        state["intent"] = "general_chat"

    return state

async def solver_node(state: MathLearningState) -> MathLearningState:
    """求解节点"""
    problem = state["current_problem"]

    # 调用求解器
    from app.agents.solver import SymPySolver
    solver = SymPySolver()
    result = await solver.solve(problem)

    if result["success"]:
        state["message_stream"] = [{
            "role": "assistant",
            "content": f"答案是：{result['answer']}"
        }]
    else:
        state["message_stream"] = [{
            "role": "assistant",
            "content": "抱歉，我无法求解这个问题。"
        }]

    state["should_continue"] = False
    return state

async def tutor_node(state: MathLearningState) -> MathLearningState:
    """导师节点"""
    state["message_stream"] = [{
        "role": "assistant",
        "content": "让我来解释一下这个概念..."
    }]
    state["should_continue"] = False
    return state

# ========== 3. 构建工作流 ==========
def create_workflow():
    workflow = StateGraph(MathLearningState)

    # 添加节点
    workflow.add_node("entry", entry_node)
    workflow.add_node("intent_classifier", intent_classifier_node)
    workflow.add_node("solver", solver_node)
    workflow.add_node("tutor", tutor_node)

    # 设置入口
    workflow.set_entry_point("entry")

    # 添加边
    workflow.add_edge("entry", "intent_classifier")

    # 条件路由
    workflow.add_conditional_edges(
        "intent_classifier",
        lambda state: state["intent"],
        {
            "solve_problem": "solver",
            "ask_concept": "tutor",
            "general_chat": "tutor",
        }
    )

    # 结束
    workflow.add_edge("solver", END)
    workflow.add_edge("tutor", END)

    # 编译
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)

# ========== 4. 运行工作流 ==========
async def main():
    app = create_workflow()

    # 初始状态
    initial_state = {
        "session_id": "test-session-1",
        "student_id": "student-123",
        "message_stream": [],
        "current_problem": "计算 ∫x²dx",
        "last_message": "计算 ∫x²dx",
        "intent": None,
        "should_continue": True
    }

    # 运行
    result = await app.ainvoke(
        initial_state,
        config={"configurable": {"thread_id": "test-session-1"}}
    )

    # 打印结果
    print("=== 对话历史 ===")
    for msg in result["message_stream"]:
        print(f"{msg['role']}: {msg['content']}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### 2.2 FastAPI 集成

```python
# app/api/v1/session.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.agents.workflow import create_workflow

router = APIRouter()

# 创建全局工作流实例
app = create_workflow()

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket 端点：流式学习会话

    客户端发送：
    {
        "action": "send_message",
        "content": "计算 ∫x²dx"
    }

    服务端推送：
    {
        "type": "message",
        "role": "assistant",
        "content": "答案是：x³/3 + C"
    }
    """
    await websocket.accept()

    try:
        while True:
            # 接收用户消息
            data = await websocket.receive_json()

            if data["action"] == "send_message":
                # 构建状态
                state = {
                    "session_id": session_id,
                    "student_id": data.get("student_id", "unknown"),
                    "message_stream": [],
                    "last_message": data["content"],
                    "current_problem": data["content"],
                    "intent": None,
                    "should_continue": True
                }

                # 流式执行工作流
                async for chunk in app.astream(
                    state,
                    config={"configurable": {"thread_id": session_id}}
                ):
                    # 推送消息
                    if "message_stream" in chunk:
                        for message in chunk["message_stream"]:
                            await websocket.send_json({
                                "type": "message",
                                "role": message["role"],
                                "content": message["content"]
                            })

    except WebSocketDisconnect:
        print(f"Client disconnected: {session_id}")
```

### 2.3 前端集成示例

```typescript
// frontend/src/services/websocket.ts

class MathLearningWebSocket {
  private ws: WebSocket | null = null;
  private sessionId: string;

  constructor(sessionId: string) {
    this.sessionId = sessionId;
  }

  connect(onMessage: (message: any) => void) {
    this.ws = new WebSocket(
      `ws://localhost:8000/api/v1/session/ws/${this.sessionId}`
    );

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      onMessage(data);
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  sendMessage(content: string) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        action: 'send_message',
        content: content,
        student_id: 'student-123'
      }));
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

// 使用示例
const ws = new MathLearningWebSocket('session-123');

ws.connect((message) => {
  if (message.type === 'message') {
    console.log(`${message.role}: ${message.content}`);
    // 更新 UI
  }
});

ws.sendMessage('计算 ∫x²dx');
```

---

## 3. 测试用例

### 3.1 单元测试

```python
# tests/agents/test_solver.py

import pytest
from app.agents.solver import SymPySolver

@pytest.mark.asyncio
async def test_solver_basic_integration():
    """测试基础积分求解"""
    solver = SymPySolver()

    result = await solver.solve("计算 ∫x²dx")

    assert result["success"] is True
    assert "x**3/3" in result["answer"] or "x³/3" in result["answer"]

@pytest.mark.asyncio
async def test_solver_derivative():
    """测试导数求解"""
    solver = SymPySolver()

    result = await solver.solve("求 f(x) = x³ 的导数")

    assert result["success"] is True
    assert "3*x**2" in result["answer"] or "3x²" in result["answer"]

@pytest.mark.asyncio
async def test_solver_error_handling():
    """测试错误处理"""
    solver = SymPySolver()

    result = await solver.solve("这不是一个数学问题")

    assert result["success"] is False
    assert "error" in result
```

### 3.2 集成测试

```python
# tests/integration/test_workflow.py

import pytest
from app.agents.workflow import create_workflow

@pytest.mark.asyncio
async def test_complete_workflow():
    """测试完整工作流"""
    app = create_workflow()

    initial_state = {
        "session_id": "test-1",
        "student_id": "student-1",
        "message_stream": [],
        "last_message": "计算 ∫x²dx",
        "current_problem": "计算 ∫x²dx",
        "intent": None,
        "should_continue": True
    }

    result = await app.ainvoke(
        initial_state,
        config={"configurable": {"thread_id": "test-1"}}
    )

    # 验证结果
    assert len(result["message_stream"]) > 0
    assert result["intent"] == "solve_problem"
    assert result["should_continue"] is False

@pytest.mark.asyncio
async def test_workflow_persistence():
    """测试工作流持久化"""
    app = create_workflow()

    # 第一次调用
    state1 = {
        "session_id": "test-2",
        "student_id": "student-1",
        "message_stream": [],
        "last_message": "什么是导数？",
        "intent": None,
        "should_continue": True
    }

    result1 = await app.ainvoke(
        state1,
        config={"configurable": {"thread_id": "test-2"}}
    )

    # 第二次调用（恢复会话）
    state2 = {
        "last_message": "继续",
        "should_continue": True
    }

    result2 = await app.ainvoke(
        state2,
        config={"configurable": {"thread_id": "test-2"}}
    )

    # 验证会话持久化
    assert len(result2["message_stream"]) > len(result1["message_stream"])
```

### 3.3 性能测试

```python
# tests/performance/test_caching.py

import pytest
import time
from app.agents.solver import CachedSolver

@pytest.mark.asyncio
async def test_cache_performance():
    """测试缓存性能"""
    solver = CachedSolver()

    problem = "计算 ∫x²dx"

    # 第一次调用（无缓存）
    start1 = time.time()
    result1 = await solver.solve(problem)
    duration1 = time.time() - start1

    # 第二次调用（有缓存）
    start2 = time.time()
    result2 = await solver.solve(problem)
    duration2 = time.time() - start2

    # 验证缓存加速
    assert duration2 < duration1 * 0.1  # 缓存应该快 10 倍以上
    assert result1["answer"] == result2["answer"]

@pytest.mark.asyncio
async def test_concurrent_requests():
    """测试并发性能"""
    import asyncio

    solver = CachedSolver()
    problems = [f"计算 ∫x^{i}dx" for i in range(10)]

    # 并发执行
    start = time.time()
    results = await asyncio.gather(*[
        solver.solve(problem) for problem in problems
    ])
    duration = time.time() - start

    # 验证所有请求都成功
    assert all(r["success"] for r in results)

    # 验证并发性能
    assert duration < 10  # 10 个请求应在 10 秒内完成
```

---

## 4. 常见问题

### 4.1 如何调试 LangGraph 工作流？

```python
# 启用调试模式
import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "your_langsmith_key"

# 或者使用本地日志
from langgraph.graph import StateGraph

workflow = StateGraph(State)
# ... 添加节点和边 ...

# 编译时启用调试
app = workflow.compile(debug=True)

# 运行时查看状态
async for chunk in app.astream(initial_state):
    print(f"Current state: {chunk}")
```

### 4.2 如何处理 LLM 超时？

```python
import asyncio

async def llm_with_timeout(prompt: str, timeout: int = 30):
    """带超时的 LLM 调用"""
    try:
        return await asyncio.wait_for(
            llm.ainvoke(prompt),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        return {"error": "LLM 调用超时"}
```

### 4.3 如何优化内存使用？

```python
# 1. 限制对话历史长度
def truncate_history(history: list, max_length: int = 10):
    """截断对话历史"""
    if len(history) > max_length:
        return history[-max_length:]
    return history

# 2. 使用生成器而非列表
async def stream_messages(state):
    """流式生成消息（节省内存）"""
    for message in generate_messages(state):
        yield message
        # 不保存在内存中

# 3. 定期清理缓存
async def cleanup_cache():
    """清理过期缓存"""
    await redis.execute_command("MEMORY PURGE")
```

### 4.4 如何监控智能体性能？

```python
# 使用 Prometheus 监控
from prometheus_client import start_http_server, Counter, Histogram

# 启动 Prometheus 服务器
start_http_server(8001)

# 定义指标
solver_requests = Counter('solver_requests_total', 'Total solver requests')
solver_duration = Histogram('solver_duration_seconds', 'Solver duration')

# 在智能体中使用
async def monitored_solve(problem: str):
    solver_requests.inc()

    with solver_duration.time():
        result = await solver.solve(problem)

    return result
```

---

## 📚 相关文档

- [← 返回主文档](../智能体系统设计文档.md)
- [← 性能优化方案](./performance-optimization.md)
- [← 智能体详细设计](./agents-detail.md)
- [← LangGraph 工作流设计](./langgraph-workflow.md)

---

## 🎉 完成

恭喜！你已经完成了智能体系统的学习。

**下一步**：
1. 阅读 [实施路线图](./performance-optimization.md#2-实施路线图)
2. 开始实现第一个智能体（Solver）
3. 加入开发团队，贡献代码

**需要帮助？**
- 查看 [常见问题](#4-常见问题)
- 提交 Issue: https://github.com/your-org/MathStudyPlatform/issues
- 加入讨论: https://discord.gg/your-server
