# 向量检索(VectorChord)+图数据库方案（单校/公开检索/老师写权限）

> 适用场景：题库/讲义等内容在发布后对所有登录用户公开可检索；但需要做到“老师只能管理自己名下内容”（增删改、上下线）。题库会周期性大批量改动/增量导入；自建 PostgreSQL。

## 1. 目标与非目标

### 目标

- 公开检索：任意已登录用户可检索并查看 `published` 内容（不按班级/老师做可见性隔离）。
- 写权限：老师仅能创建/编辑/删除自己名下内容（可扩展协作编辑）。
- 批量导入：支持“时不时大量改动/增量导入”，可回放、可审计、可重试。
- 向量检索：在 PostgreSQL 内完成向量 TopK，减少多系统一致性成本。
- 图谱能力：用图数据库表达知识结构与先修关系，为推荐/路径/诊断提供支撑。

### 非目标

- Milvus 等独立向量库的多租户隔离与分区管理。
- 对未登录用户开放检索。
- 视频转录与视频语义检索（本方案仅管理视频附件元数据）。

## 2. 总体架构与职责边界

### 组件

- PostgreSQL（主事实库）
  - 业务：内容、发布状态、权限、审计
  - 向量：VectorChord 扩展（兼容 pgvector 的 SQL 体验）
  - 导入：批量导入任务、变更事件（outbox）
- 图数据库（知识图谱）
  - 知识点/章节/课程节点与关系边
  - 不参与“是否可见”的最终判断（可见性以 Postgres 为准）
- 后端服务（唯一对外入口）
  - 认证鉴权；写权限校验；统一 DAO/Repository；检索与回源

### 数据原则（关键）

- “是否对外可见”必须由 Postgres 的 `status/deleted_at` 决定；检索永远以此二次过滤。
- 向量召回只负责“相关性候选”；不承担权限与可见性隔离。
- 图数据库用于“结构推理/路径推荐/知识诊断”；图同步延迟不应导致越权或泄漏。

## 3. 数据模型（Postgres）

下面给出推荐的最小集合。表名可按项目规范调整。

### 3.1 用户与内容

- `users(id, role, ...)`
  - `role`: `student | teacher | admin`

- `contents(
    id,
    type,
    owner_teacher_id,
    status,
    title,
    body,
    difficulty,
    created_at,
    updated_at,
    published_at,
    deleted_at
  )`
  - `type`: `problem | note | video | ...`
  - `status`: `draft | published | archived`
  - 约束：对外展示/检索必须满足 `status='published' AND deleted_at IS NULL`

- `content_assets(id, content_id, kind, url, meta_jsonb, created_at)`
  - `kind`: `video | image | pdf | ...`
  - 视频只作为附件：`url` 指向对象存储；`meta_jsonb` 可存时长、封面等

### 3.2 权限（owner + 可选协作）

最简：只用 `contents.owner_teacher_id`。

若需要“协作编辑/共享归属”，增加：

- `content_acl(content_id, teacher_id, permission, created_at)`
  - `permission`: `editor | admin`

建议索引：

- `contents(owner_teacher_id)`（老师管理列表）
- `content_acl(teacher_id, content_id)`

### 3.3 向量（VectorChord）

核心建议：**把“向量维度不确定”当作“模型版本演进问题”处理**。

原因：Postgres 的 `vector(n)`（以及 VectorChord 的兼容用法）要求维度固定；混用不同维度会直接不可用。

推荐做法：

- `embedding_models(name, dim, distance, is_active, created_at)`
  - `distance`: `cosine | l2 | ip`（取决于你是否做归一化、以及检索距离定义）
  - 只允许同时存在一个 `is_active=true` 的模型用于在线写入

- 向量表按模型分离（推荐）
  - `content_embeddings_<model>(content_id PK, embedding vector(<dim>), updated_at)`
  - 模型升级：新建表 + 回填 + 切换读写

替代做法（不推荐但可应急）：同一张表用多个向量列（`embedding_v1`, `embedding_v2`），用 `active_model` 决定查询列；迁移完成后删旧列。

### 3.4 审计与导入

- `content_audit(id, content_id, actor_user_id, action, at, diff_jsonb)`
  - `action`: `create | update | publish | archive | delete | bulk_import | ...`

- `import_jobs(id, kind, status, created_by, created_at, params_jsonb, stats_jsonb)`
  - `kind`: `problems_bulk_upsert | problems_bulk_delete | ...`
  - `status`: `pending | running | succeeded | failed | cancelled`

- `outbox_events(id, type, payload_jsonb, created_at, processed_at, retry_count, last_error)`
  - `type`: `content_changed | content_deleted | content_published | content_knowledge_linked | ...`
  - 通过 outbox 实现：可重试、可回放、可观测

## 4. 写权限落地（应用层 RBAC + owner/assignment）

### 4.1 写操作必须“单条 SQL 带权限条件”

不要做：先 `SELECT` 判断归属，再 `UPDATE/DELETE`。

要做：

- 仅 owner：
  - `UPDATE ... WHERE id=$1 AND owner_teacher_id=$me`
  - `DELETE/soft-delete ... WHERE id=$1 AND owner_teacher_id=$me`

- owner + 协作（若有 `content_acl`）：
  - `... WHERE id=$1 AND (owner_teacher_id=$me OR EXISTS (SELECT 1 FROM content_acl WHERE content_id=$1 AND teacher_id=$me AND permission IN ('editor','admin')))`

### 4.2 读操作（公开）仍要强制状态过滤

- 详情、列表、检索统一加：`status='published' AND deleted_at IS NULL`

说明：这是避免“草稿/已下线内容被公开”的最后一道闸。

### 4.3 是否需要 RLS

默认建议：先不上 RLS，用应用层 RBAC + 统一 DAO + 越权回归测试把风险压住。

考虑启用 RLS 的触发条件：

- 存在 BI/脚本/多服务可能绕过应用层直接连库
- 团队规模变大，担心“漏写 WHERE owner 条件”导致事故

若启用 RLS：务必制定“普通角色测试、避免复杂 policy、性能基准”的规范；并明确 superuser/owner 绕过等行为对测试的影响。

## 5. VectorChord 检索设计

### 5.1 安装与启用（自建）

1) 在 `postgresql.conf` 设置：

```conf
shared_preload_libraries = 'vchord'
```

2) 重启 PostgreSQL。

3) 在数据库内执行：

```sql
CREATE EXTENSION IF NOT EXISTS vchord CASCADE;
```

### 5.2 索引与参数选择（适配“周期性大批量改动”）

总体原则：

- 小规模/快速落地：优先选择默认图索引（实现简单）
- 批量导入频繁、更新多：优先选择更易控的 IVF 路线（构建/更新吞吐更容易被运维窗口化）

建议按你的真实数据做 3 组基准（见第 9 节），再拍板最终索引类型与参数。

### 5.3 检索 SQL 模板（必须固定）

检索只返回候选 + distance，最终可见性在 `contents` 二次过滤：

```sql
SELECT
  c.id,
  c.title,
  c.type,
  c.difficulty,
  (e.embedding <=> $1) AS distance
FROM content_embeddings_modelX e
JOIN contents c ON c.id = e.content_id
WHERE c.status = 'published'
  AND c.deleted_at IS NULL
ORDER BY e.embedding <=> $1
LIMIT $2;
```

注意：

- 距离操作符、索引 operator class、向量是否归一化要统一，否则容易“索引不命中/召回质量不稳”。

### 5.4 删除/下线一致性

推荐：内容软删 + 检索二次过滤兜底。

- 对外可见：只由 `contents.status/deleted_at` 决定（同步生效）
- embedding 清理：可以异步（不影响权限/可见性，只影响候选集规模与质量）

## 6. 批量导入与大改动（关键流水线）

### 6.1 导入总体流程（可回放、可重试）

1) 导入文件/数据进入 staging（例如 `staging_contents_<job_id>`）并校验
2) 单事务 upsert 到 `contents`（或 `content_versions`）
3) 同事务写 `content_audit` 与 `outbox_events`
4) 异步消费者处理 outbox：生成/更新 embedding、同步知识图谱边
5) 大批量场景触发“索引窗口化策略”（6.2）

### 6.2 索引窗口化策略（避免拖垮主库）

根据导入规模分级：

- 小批量（例如 <1 万条）：直接增量更新 embedding + 索引
- 中批量：限制并发、分批提交、监控写放大
- 大批量（例如 >=10 万条，按你们机器能力调整）：
  - 方案 A：影子表/影子索引
    - 新建 `content_embeddings_modelX_shadow`
    - 批量回填
    - 构建索引
    - 原子切换（视图/同义对象/路由配置）
  - 方案 B：导入窗口
    - 在低峰期暂停/降级向量检索
    - 批量回填后集中构建/重建索引
    - 恢复服务

建议优先方案 A（对线上影响小），但实现复杂度更高。

## 7. 图数据库（知识图谱）

### 7.1 推荐用途

- 课程/章节/知识点结构化表达
- 先修关系推理（PREREQ）
- 学习路径生成与推荐
- 内容-知识点覆盖（COVERS）用于：按知识路径检索内容、错误诊断回溯

### 7.2 图模型建议

- 节点：
  - `Course{id, name}`
  - `Chapter{id, course_id, name}`
  - `KnowledgeNode{id, name, domain, difficulty}`
  - `Content{id}`（可选；也可只在 Postgres 存 content 与 knowledge 的关联）
- 边：
  - `(:Chapter)-[:PART_OF]->(:Course)`
  - `(:KnowledgeNode)-[:PREREQ]->(:KnowledgeNode)`
  - `(:Content)-[:COVERS {weight}]->(:KnowledgeNode)`

### 7.3 同步策略（outbox）

- Postgres 作为事实源
- outbox 消费者写图数据库
- 失败重试、支持从 offset 重放
- 图数据库不用于“可见性最终判定”，避免同步延迟造成串/漏

## 8. 运维与监控（自建）

### 8.1 角色与权限

- `app_rw`：业务表读写（无 DDL）
- `app_ro`：只读（可用于检索服务只读连接）
- `migration`：仅迁移时使用

### 8.2 备份恢复

- 每周演练一次：全量备份 -> 异机恢复 -> 冒烟（含向量检索 + 图查询）

### 8.3 监控指标

- Postgres：CPU/IO、连接数、慢查询、autovacuum、表膨胀、索引大小
- 向量：p50/p95 延迟、错误率、索引构建时间、embedding 覆盖率
- 导入：job 成功率、outbox 堆积长度、重试次数、回填速率

## 9. 基准与验收

### 9.1 最小基准（三组）

- 构建：同等数据量下索引构建时间、构建峰值内存
- 查询：TopK=20/50 的 p95 延迟（热/冷缓存各测一次）
- 更新：每秒 upsert 吞吐（小批量与大批量两种）

### 9.2 验收清单

- 权限：老师 A 不能更新/删除老师 B 的内容（含批量接口）
- 公开：任意登录用户只能看到 `published & not deleted` 内容（检索/详情一致）
- 导入：批量导入后 embedding 覆盖率达到阈值（例如 >=99%）
- 可恢复：备份恢复后向量检索与图谱查询均可用

## 10. 常见坑（务必提前规避）

- 维度变更无预案：`vector(n)` 维度固定，模型升级必须“新表/新列 + 回填 + 切换”。
- 大批量更新直接在线重建索引：拖垮主库；必须窗口化或影子索引切换。
- 权限漏写：缺少统一 DAO/缺少越权回归测试，“老师越权改删”迟早发生。
- 检索漏过滤 `status/deleted_at`：草稿/下线内容被公开。
- outbox 不可重放：消费者失败后图谱/embedding 状态不可恢复，必须设计幂等键与重试。
