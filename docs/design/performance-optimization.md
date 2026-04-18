# 性能优化与实施指南

> **文档**: 智能体系统设计 - 第4部分
> **版本**: v1.0
> **日期**: 2026-01-22

[← 返回主文档](../智能体系统设计文档.md) | [文档索引](./README.md)

---

## 📋 目录

- [1. 性能优化策略](#1-性能优化策略)
- [2. 实施路线图](#2-实施路线图)
- [3. 技术栈与依赖](#3-技术栈与依赖)
- [4. 部署架构](#4-部署架构)
- [5. 监控与调优](#5-监控与调优)

---

## 1. 性能优化策略

### 1.1 智能缓存（Smart Caching）

#### 1.1.1 求解结果缓存

```python
import hashlib
from redis import asyncio as aioredis

class CachedSolver:
    """带缓存的求解器"""

    def __init__(self, solver, redis_client: aioredis.Redis):
        self.solver = solver
        self.redis = redis_client

    async def solve(self, problem: str) -> dict:
        """
        求解问题（带缓存）

        缓存策略：
        - Key: problem 的 MD5 哈希
        - TTL: 24 小时
        - 命中率目标: > 80%
        """
        # 生成缓存键
        cache_key = f"solution:{self._hash_problem(problem)}"

        # 检查缓存
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)

        # 实际求解
        result = await self.solver.solve(problem)

        # 缓存结果（仅缓存成功的结果）
        if result.get("success"):
            await self.redis.setex(
                cache_key,
                86400,  # 24 小时
                json.dumps(result)
            )

        return result

    def _hash_problem(self, problem: str) -> str:
        """生成问题指纹"""
        # 标准化问题文本（去除空格、统一大小写）
        normalized = problem.strip().lower()
        return hashlib.md5(normalized.encode()).hexdigest()
```

#### 1.1.2 学生画像缓存

```python
class CachedProfileService:
    """学生画像缓存"""

    async def get_student_profile(self, student_id: str) -> dict:
        """
        获取学生画像（带缓存）

        缓存策略：
        - 热数据：Redis（5分钟）
        - 冷数据：PostgreSQL
        - 更新策略：Write-Through
        """
        cache_key = f"profile:{student_id}"

        # 1. 尝试从 Redis 获取
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)

        # 2. 从数据库加载
        profile = await self.db.query_profile(student_id)

        # 3. 写入缓存
        await self.redis.setex(
            cache_key,
            300,  # 5 分钟
            json.dumps(profile)
        )

        return profile

    async def update_profile(self, student_id: str, updates: dict):
        """
        更新学生画像（Write-Through）

        同时更新数据库和缓存
        """
        # 1. 更新数据库
        await self.db.update_profile(student_id, updates)

        # 2. 更新缓存
        cache_key = f"profile:{student_id}"
        profile = await self.db.query_profile(student_id)
        await self.redis.setex(cache_key, 300, json.dumps(profile))
```

---

### 1.2 批量推理（Batch Inference）

#### 1.2.1 LLM 批量调用

```python
import asyncio
from collections import deque

class BatchedLLMClient:
    """批量 LLM 推理客户端"""

    def __init__(
        self,
        llm_client,
        batch_size: int = 5,
        max_wait_ms: int = 100
    ):
        self.llm_client = llm_client
        self.batch_size = batch_size
        self.max_wait_ms = max_wait_ms
        self.pending_requests = deque()
        self.lock = asyncio.Lock()

    async def generate(self, prompt: str) -> str:
        """
        生成响应（自动批量）

        优势：
        - vLLM 支持批量推理，吞吐量提升 3-5 倍
        - 降低 API 调用成本
        """
        # 创建 Future 用于接收结果
        future = asyncio.Future()

        async with self.lock:
            self.pending_requests.append((prompt, future))

            # 达到批量大小，立即执行
            if len(self.pending_requests) >= self.batch_size:
                asyncio.create_task(self._flush_batch())
            else:
                # 否则等待超时后执行
                asyncio.create_task(self._wait_and_flush())

        # 等待结果
        return await future

    async def _flush_batch(self):
        """执行批量推理"""
        async with self.lock:
            if not self.pending_requests:
                return

            # 取出当前批次
            batch = []
            futures = []
            while self.pending_requests and len(batch) < self.batch_size:
                prompt, future = self.pending_requests.popleft()
                batch.append(prompt)
                futures.append(future)

        # 批量调用 LLM
        try:
            results = await self.llm_client.batch_generate(batch)

            # 分发结果
            for future, result in zip(futures, results):
                future.set_result(result)

        except Exception as e:
            # 错误处理
            for future in futures:
                future.set_exception(e)

    async def _wait_and_flush(self):
        """等待超时后执行"""
        await asyncio.sleep(self.max_wait_ms / 1000)
        await self._flush_batch()
```

---

### 1.3 预测性预加载（Predictive Preloading）

```python
class PredictiveLoader:
    """预测性资源加载"""

    async def preload_next_concepts(self, state: dict):
        """
        预加载下一个知识点

        策略：
        - 在学生学习当前知识点时，后台预加载下一个
        - 预加载内容：概念解释、示例题目、相关资源
        """
        learning_path = state["learning_path"]
        current_index = state["path_index"]

        # 预测下一个知识点
        if current_index < len(learning_path) - 1:
            next_concept = learning_path[current_index + 1]

            # 后台任务：预加载
            asyncio.create_task(self._load_concept(next_concept))

    async def _load_concept(self, concept_id: str):
        """加载知识点资源"""
        # 1. 预加载概念解释
        explanation = await self.rag_retriever.retrieve(concept_id)
        await self.redis.setex(
            f"concept:{concept_id}:explanation",
            600,  # 10 分钟
            json.dumps(explanation)
        )

        # 2. 预加载示例题目
        exercises = await self.db.query_exercises(concept_id, limit=5)
        await self.redis.setex(
            f"concept:{concept_id}:exercises",
            600,
            json.dumps(exercises)
        )
```

---

### 1.4 流式响应优化

```python
from fastapi import WebSocket

class StreamingResponseHandler:
    """流式响应处理器"""

    async def stream_agent_output(
        self,
        websocket: WebSocket,
        state: dict
    ):
        """
        流式推送智能体输出

        优势：
        - 降低首字节时间（TTFB）
        - 提升用户体验
        - 支持中断
        """
        async for message in self._generate_messages(state):
            # 推送消息
            await websocket.send_json({
                "type": "message",
                "content": message["content"],
                "metadata": message.get("metadata", {})
            })

            # 检查是否被中断
            if await self._check_interrupt(websocket):
                break

    async def _generate_messages(self, state: dict):
        """生成消息流"""
        # 使用 LangGraph 的流式 API
        async for chunk in app.astream(state):
            if "message_stream" in chunk:
                for message in chunk["message_stream"]:
                    yield message

    async def _check_interrupt(self, websocket: WebSocket) -> bool:
        """检查用户是否中断"""
        try:
            data = await asyncio.wait_for(
                websocket.receive_json(),
                timeout=0.01
            )
            return data.get("action") == "interrupt"
        except asyncio.TimeoutError:
            return False
```

---

## 2. 实施路线图

### 阶段 1：核心智能体（2周）

#### Week 1: Solver + Orchestrator

**任务清单**：
- [ ] 实现 SymPy 求解器
  - [ ] 代码生成（LLM）
  - [ ] 代码执行（E2B 沙箱）
  - [ ] 结果验证
- [ ] 实现 Orchestrator
  - [ ] 意图分类（LLM）
  - [ ] 任务路由
  - [ ] 状态管理
- [ ] 集成 LangGraph
  - [ ] 定义状态结构
  - [ ] 创建基础工作流
  - [ ] 测试端到端流程

**验收标准**：
- ✅ 能够正确求解基础微积分问题（积分、导数）
- ✅ 意图分类准确率 > 90%
- ✅ 端到端延迟 < 3s

#### Week 2: Tutor + Diagnostician

**任务清单**：
- [ ] 实现 Tutor Agent
  - [ ] HybridRAG 集成
  - [ ] 自适应 Prompt 生成
  - [ ] 苏格拉底式引导
- [ ] 实现 Diagnostician
  - [ ] OCR 集成（Texify）
  - [ ] 步骤比对
  - [ ] 错误分类
- [ ] 前后端集成
  - [ ] WebSocket 流式推送
  - [ ] 前端消息渲染

**验收标准**：
- ✅ 能够解释基础概念（导数、积分）
- ✅ OCR 识别准确率 > 85%
- ✅ 错误诊断准确率 > 80%

---

### 阶段 2：创新功能（2周）

#### Week 3: Emotion + Reflection

**任务清单**：
- [ ] 实现 Emotion Detector
  - [ ] 文本情感分析
  - [ ] 行为信号分析
  - [ ] 干预策略
- [ ] 实现 Reflection Agent
  - [ ] 理解深度评估
  - [ ] 深度提问生成
  - [ ] 元认知检测
- [ ] 集成到工作流
  - [ ] 添加情感检测节点
  - [ ] 添加反思节点
  - [ ] 条件路由

**验收标准**：
- ✅ 情感检测准确率 > 75%
- ✅ 能够识别机械记忆 vs 真正理解
- ✅ 干预策略有效性 > 70%

#### Week 4: 并行求解 + Planner

**任务清单**：
- [ ] 实现并行求解
  - [ ] 多策略并行
  - [ ] 竞速机制
  - [ ] 结果选择
- [ ] 实现 Planner Agent
  - [ ] 知识图谱集成（Neo4j）
  - [ ] 学习路径规划
  - [ ] DKT 模型集成
- [ ] 性能优化
  - [ ] Redis 缓存
  - [ ] 批量推理

**验收标准**：
- ✅ 并行求解成功率 > 95%
- ✅ 求解延迟降低 30%
- ✅ 学习路径合理性 > 85%

---

### 阶段 3：优化与集成（1周）

#### Week 5: 性能优化 + 测试

**任务清单**：
- [ ] 性能优化
  - [ ] 缓存命中率优化
  - [ ] 批量推理集成
  - [ ] 预测性预加载
- [ ] 测试与调优
  - [ ] 单元测试（覆盖率 > 80%）
  - [ ] 集成测试
  - [ ] 压力测试（1000 并发）
- [ ] 文档完善
  - [ ] API 文档
  - [ ] 部署文档
  - [ ] 运维手册

**验收标准**：
- ✅ TTFB < 500ms
- ✅ 缓存命中率 > 80%
- ✅ 并发支持 > 1000
- ✅ 测试覆盖率 > 80%

---

## 3. 技术栈与依赖

### 3.1 核心依赖

```toml
# pyproject.toml

[project]
name = "math-study-platform-agents"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    # LangGraph 核心
    "langgraph>=0.2.0",
    "langchain>=0.3.0",
    "langchain-openai>=0.2.0",

    # 数学计算
    "sympy>=1.13.0",
    "numpy>=1.26.0",
    "scipy>=1.11.0",

    # 代码执行
    "e2b-code-interpreter>=0.0.10",

    # 向量检索
    "qdrant-client>=1.11.0",
    "sentence-transformers>=3.0.0",

    # 情感分析
    "transformers>=4.45.0",
    "torch>=2.0.0",

    # 数据库
    "asyncpg>=0.30.0",
    "redis[hiredis]>=5.2.0",
    "neo4j>=5.25.0",

    # Web 框架
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "websockets>=13.0",

    # 工具
    "httpx>=0.28.0",
    "pillow>=10.0.0",
    "pydantic>=2.10.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "ruff>=0.8.0",
    "mypy>=1.13.0",
]
```

### 3.2 环境变量配置

```bash
# .env

# LLM 配置
LLM_API_BASE=https://api.deepseek.com
LLM_API_KEY=your_api_key
LLM_MODEL_NAME=deepseek-chat

# 代码执行
E2B_API_KEY=your_e2b_key

# 数据库
POSTGRES_URL=postgresql://user:pass@localhost/db
REDIS_URL=redis://localhost:6379/0
NEO4J_URL=bolt://localhost:7687

# 向量检索
QDRANT_URL=http://localhost:6333
EMBEDDING_MODEL=BAAI/bge-m3

# OCR
TEXIFY_API_URL=http://localhost:8080/ocr

# 性能配置
BATCH_SIZE=5
BATCH_WAIT_MS=100
CACHE_TTL_SECONDS=86400
```

---

## 4. 部署架构

### 4.1 容器化部署

```yaml
# docker-compose.yml

version: '3.8'

services:
  # FastAPI 后端
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - LLM_API_KEY=${LLM_API_KEY}
      - POSTGRES_URL=postgresql://postgres:password@postgres:5432/mathplatform
      - REDIS_URL=redis://redis:6379/0
      - NEO4J_URL=bolt://neo4j:7687
    depends_on:
      - postgres
      - redis
      - neo4j
      - qdrant

  # PostgreSQL
  postgres:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: password
      POSTGRES_DB: mathplatform
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # Redis
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  # Neo4j
  neo4j:
    image: neo4j:5
    environment:
      NEO4J_AUTH: neo4j/password
    volumes:
      - neo4j_data:/data

  # Qdrant
  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - qdrant_data:/qdrant/storage

volumes:
  postgres_data:
  redis_data:
  neo4j_data:
  qdrant_data:
```

### 4.2 Kubernetes 部署（生产环境）

```yaml
# k8s/deployment.yaml

apiVersion: apps/v1
kind: Deployment
metadata:
  name: math-platform-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: mathplatform/backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: LLM_API_KEY
          valueFrom:
            secretKeyRef:
              name: llm-secret
              key: api-key
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
```

---

## 5. 监控与调优

### 5.1 性能监控

```python
from prometheus_client import Counter, Histogram, Gauge

# 定义指标
request_count = Counter(
    'agent_requests_total',
    'Total agent requests',
    ['agent_type', 'status']
)

request_duration = Histogram(
    'agent_request_duration_seconds',
    'Agent request duration',
    ['agent_type']
)

cache_hit_rate = Gauge(
    'cache_hit_rate',
    'Cache hit rate',
    ['cache_type']
)

# 使用示例
async def monitored_solve(problem: str):
    with request_duration.labels(agent_type='solver').time():
        try:
            result = await solver.solve(problem)
            request_count.labels(
                agent_type='solver',
                status='success'
            ).inc()
            return result
        except Exception as e:
            request_count.labels(
                agent_type='solver',
                status='error'
            ).inc()
            raise
```

### 5.2 日志记录

```python
import structlog

logger = structlog.get_logger()

async def solve_with_logging(problem: str):
    logger.info(
        "solver.start",
        problem_hash=hash_problem(problem),
        problem_length=len(problem)
    )

    try:
        result = await solver.solve(problem)

        logger.info(
            "solver.success",
            problem_hash=hash_problem(problem),
            execution_time=result.get("execution_time")
        )

        return result

    except Exception as e:
        logger.error(
            "solver.error",
            problem_hash=hash_problem(problem),
            error=str(e),
            exc_info=True
        )
        raise
```

---

## 📚 相关文档

- [← 返回主文档](../智能体系统设计文档.md)
- [← 智能体详细设计](./agents-detail.md)
- [← LangGraph 工作流设计](./langgraph-workflow.md)

---

**完成**：智能体系统设计文档已全部完成！
