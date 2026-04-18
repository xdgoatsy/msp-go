# 数学学习平台文档中心

欢迎来到数学学习平台的文档中心。本文档提供了项目的完整技术文档，包括 API 规范、架构设计、开发规范和部署指南。

---

## 📚 文档导航

### 1. [API 接口规范](./api/)
- **[API接口规范.md](./api/API接口规范.md)** - 完整的后端 API 接口定义
  - 认证与授权接口
  - 学生端功能接口
  - 教师端功能接口
  - 管理员端功能接口
  - 请求/响应格式说明

### 2. [架构设计](./architecture/)
- **[数据模型定义.md](./architecture/数据模型定义.md)** - 前后端数据模型定义
- **[状态管理说明.md](./architecture/状态管理说明.md)** - Redux 状态管理架构
- **[智能体系统设计文档.md](./architecture/智能体系统设计文档.md)** - AI 智能体系统架构
- **[向量检索+图数据库方案.md](./architecture/向量检索(VectorChord)+图数据库方案.md)** - 知识图谱存储方案

### 3. [设计提案](./design/)
- **[README.md](./design/README.md)** - 设计提案索引
- **[agents-detail.md](./design/agents-detail.md)** - 智能体详细设计
- **[langgraph-workflow.md](./design/langgraph-workflow.md)** - LangGraph 工作流设计
- **[code-examples.md](./design/code-examples.md)** - 代码示例
- **[performance-optimization.md](./design/performance-optimization.md)** - 性能优化方案

### 4. [部署运维](./deployment/)
- **[DEPLOYMENT.md](./deployment/DEPLOYMENT.md)** - Docker 生产环境部署指南
- **[API_PROXY_GUIDE.md](./deployment/API_PROXY_GUIDE.md)** - API 代理配置指南

### 5. [开发规范](./development/)
- **[开发规范文档](./development/README.md)** - 通用开发规范和最佳实践
- **[后端 Python 到 Go 重构迁移文档](./development/backend-python-to-go-refactor.md)** - 后端 Go 重写阶段计划、验收规则和进度记录
- **[数据库迁移指南](./development/MIGRATION_GUIDE.md)** - Alembic 迁移管理指南
- **[动画系统文档](./development/animation-system.md)** - 前端动画系统使用指南
- **[日志系统文档](./development/logger-system.md)** - 前端日志管理系统使用指南

---

## 🚀 快速开始

### 对于新加入的开发者

**后端开发者**：
1. 阅读 [API接口规范](./api/API接口规范.md) 了解接口需求
2. 阅读 [数据模型定义](./architecture/数据模型定义.md) 了解数据结构
3. 阅读 [智能体系统设计文档](./architecture/智能体系统设计文档.md) 了解 AI 功能

**前端开发者**：
1. 阅读 [API接口规范](./api/API接口规范.md) 了解可用接口
2. 阅读 [状态管理说明](./architecture/状态管理说明.md) 了解状态管理
3. 阅读 [数据模型定义](./architecture/数据模型定义.md) 了解数据结构

**运维人员**：
1. 阅读 [DEPLOYMENT.md](./deployment/DEPLOYMENT.md) 了解部署流程
2. 阅读 [API_PROXY_GUIDE.md](./deployment/API_PROXY_GUIDE.md) 了解代理配置

**AI 工程师**：
1. 阅读 [智能体系统设计文档](./architecture/智能体系统设计文档.md) 了解整体架构
2. 阅读 [设计提案](./design/) 了解详细实现方案
3. 参考 [code-examples.md](./design/code-examples.md) 快速上手

---

## 📋 项目概述

### 技术栈

**前端**：
- React 18 + TypeScript
- Redux Toolkit (状态管理)
- Ant Design (UI 组件库)
- Vite (构建工具)

**后端**：
- FastAPI (Python Web 框架)
- PostgreSQL (关系数据库)
- Redis (缓存)
- LangGraph (AI 工作流)
- DeepSeek API (大语言模型)

**部署**：
- Docker + Docker Compose
- Nginx (反向代理)

### 核心功能

1. **学生端**
   - 智能练习系统
   - AI 对话辅导
   - 错题本管理
   - 知识图谱可视化

2. **教师端**
   - 题库管理
   - 班级管理
   - 学生画像分析
   - 资源管理

3. **管理员端**
   - 用户管理
   - 系统配置
   - AI 模型配置
   - 知识图谱管理

---

## 🔄 文档更新记录

### 2026-04-18
- 新增后端 Python 到 Go 重构迁移文档
- 更新开发规范文档索引

### 2026-02-19
- 整理散落文档到 docs/development/ 目录
- 迁入数据库迁移指南、动画系统文档、日志系统文档
- 更新文档索引和引用链接

### 2026-02-15
- 整合 backend/docs 和 frontend/docs 到根目录
- 创建分层文档结构
- 添加文档导航和索引

### 2026-02-12
- 添加部署文档

### 2026-01-26
- 添加向量检索和图数据库方案

### 2026-01-23
- 添加智能体系统设计文档
- 添加设计提案文档

### 2026-01-21
- 创建前端开发文档
- 添加 API 接口规范
- 添加数据模型定义

---

## 💡 贡献指南

### 文档规范

1. **文件命名**：使用中文或英文，保持一致性
2. **Markdown 格式**：遵循标准 Markdown 语法
3. **目录结构**：每个文档都应包含目录导航
4. **代码示例**：提供完整可运行的代码示例
5. **更新记录**：在文档末尾记录更新历史

### 如何贡献

1. 发现文档错误或需要补充时，直接修改对应文件
2. 添加新文档时，更新相应目录的 README.md
3. 重大更新需要在本文档的更新记录中添加条目
4. 确保文档格式清晰、内容准确

---

## 📞 联系方式

如有疑问或建议，请：
- 提交 Issue
- 联系项目维护者
- 查看项目主 README

---

## 🔗 相关链接

- **项目主页**：[../README.md](../README.md)
- **前端 README**：[../frontend/README.md](../frontend/README.md)
- **后端 README**：[../backend/README.md](../backend/README.md)
- **前端 CLAUDE.md**：[../frontend/CLAUDE.md](../frontend/CLAUDE.md)
- **后端 CLAUDE.md**：[../backend/CLAUDE.md](../backend/CLAUDE.md)
