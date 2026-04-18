# 数据库迁移管理指南

## 当前迁移状态

项目当前有 **12 个迁移文件**，总计约 1556 行代码：

| 迁移文件 | 大小 | 描述 |
|---------|------|------|
| 0001_initial_merged.py | 30K | 初始数据库结构（已合并） |
| 0002_system_settings.py | 1.4K | 系统设置表 |
| 0003_security_logs.py | 3.5K | 安全日志系统 |
| 0004_user_favorites.py | 1.8K | 用户收藏功能 |
| 0005_performance_indexes.py | 3.0K | 性能索引优化 |
| 0006_xidian_integration.py | 2.6K | 西电教务集成 |
| 0007_xidian_cookie_persist.py | 931B | 西电 Cookie 持久化 |
| 0008_additional_indexes.py | 1.3K | 额外索引 |
| 0009_student_portrait_fields.py | 1.2K | 学生画像字段 |
| 0010_nullable_max_tokens_top_p.py | 1.8K | AI 配置字段调整 |
| 0011_class_management.py | 2.6K | 班级管理系统 |
| 0012_knowledge_graph_seed_data.py | 5.4K | 知识图谱种子数据 |

## 是否需要合并迁移？

### ❌ 不建议合并的原因

1. **生产环境风险**：如果已有生产数据库运行了这些迁移，合并会导致迁移历史不一致
2. **开发历史清晰**：当前迁移文件清晰记录了功能演进过程
3. **回滚灵活性**：独立的迁移文件便于精确回滚到特定版本
4. **团队协作**：其他开发者可能已经应用了部分迁移

### ✅ 可以合并的场景

**仅在以下情况下考虑合并：**
- 项目尚未部署到生产环境
- 所有开发环境都可以重置数据库
- 需要清理开发阶段的实验性迁移

## 迁移管理最佳实践

### 1. 生产环境迁移流程

```bash
# 1. 备份数据库
docker exec msp_postgres pg_dump -U postgres math_platform > backup_$(date +%Y%m%d).sql

# 2. 查看待执行的迁移
docker exec msp_backend alembic current
docker exec msp_backend alembic history

# 3. 执行迁移（推荐逐个执行）
docker exec msp_backend alembic upgrade +1  # 升级一个版本
docker exec msp_backend alembic upgrade head # 或直接升级到最新

# 4. 验证迁移结果
docker exec msp_backend alembic current
```

### 2. 回滚迁移

```bash
# 回滚到上一个版本
docker exec msp_backend alembic downgrade -1

# 回滚到特定版本
docker exec msp_backend alembic downgrade <revision_id>

# 查看迁移历史
docker exec msp_backend alembic history --verbose
```

### 3. 创建新迁移

```bash
# 自动生成迁移（基于模型变更）
docker exec msp_backend alembic revision --autogenerate -m "描述变更内容"

# 手动创建空迁移
docker exec msp_backend alembic revision -m "描述变更内容"

# 检查生成的迁移文件
# 位置: backend/alembic/versions/
```

### 4. 迁移文件命名规范

```
<序号>_<功能描述>.py

示例:
0013_add_user_preferences.py
0014_optimize_query_performance.py
```

## 生产环境注意事项

### ⚠️ 危险操作

以下操作在生产环境中需要特别谨慎：

1. **删除列/表**：可能导致数据丢失
2. **修改列类型**：可能导致数据转换失败
3. **添加 NOT NULL 约束**：需要先填充默认值
4. **大表添加索引**：可能锁表较长时间

### ✅ 安全操作流程

```python
# 示例：安全地添加 NOT NULL 列

# 步骤 1：添加可空列
op.add_column('users', sa.Column('new_field', sa.String(), nullable=True))

# 步骤 2：填充默认值
op.execute("UPDATE users SET new_field = 'default_value' WHERE new_field IS NULL")

# 步骤 3：添加 NOT NULL 约束
op.alter_column('users', 'new_field', nullable=False)
```

## 监控和日志

### 查看迁移日志

```bash
# 查看 Alembic 版本表
docker exec msp_postgres psql -U postgres -d math_platform -c "SELECT * FROM alembic_version;"

# 查看迁移执行日志
docker logs msp_backend | grep alembic
```

### 迁移性能监控

```bash
# 在迁移前后检查表大小
docker exec msp_postgres psql -U postgres -d math_platform -c "
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

## 常见问题排查

### 问题 1：迁移冲突

```bash
# 症状：多个分支创建了相同序号的迁移
# 解决：重新生成迁移序号
docker exec msp_backend alembic revision --autogenerate -m "merge migrations"
```

### 问题 2：迁移失败

```bash
# 1. 查看错误日志
docker logs msp_backend

# 2. 检查当前版本
docker exec msp_backend alembic current

# 3. 手动修复数据库
docker exec -it msp_postgres psql -U postgres -d math_platform

# 4. 标记迁移为已执行（谨慎使用）
docker exec msp_backend alembic stamp head
```

### 问题 3：pgvector 扩展未安装

```bash
# 手动安装 pgvector
docker exec msp_postgres psql -U postgres -d math_platform -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

## 建议

### 当前项目建议

**不需要合并迁移**，原因：
1. 迁移文件数量合理（12 个）
2. 每个迁移职责清晰
3. 便于追踪功能演进
4. 方便问题定位和回滚

### 未来迁移策略

1. **定期审查**：每季度审查迁移文件，清理无用的实验性迁移
2. **版本里程碑**：在大版本发布时可以考虑合并迁移
3. **文档同步**：每次迁移都更新此文档
4. **测试覆盖**：为关键迁移编写测试用例

## 相关命令速查

```bash
# 查看当前版本
alembic current

# 查看迁移历史
alembic history

# 升级到最新
alembic upgrade head

# 升级一个版本
alembic upgrade +1

# 降级一个版本
alembic downgrade -1

# 降级到特定版本
alembic downgrade <revision>

# 查看 SQL（不执行）
alembic upgrade head --sql

# 生成迁移
alembic revision --autogenerate -m "message"
```
