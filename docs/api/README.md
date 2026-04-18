# API 接口规范

本目录包含数学学习平台的完整 API 接口规范文档。

---

## 📄 文档列表

### [API接口规范.md](./API接口规范.md)

完整的后端 API 接口定义，包括：

#### 1. 认证与授权
- 用户登录/注册
- 密码重置
- Token 刷新
- 西电统一认证集成

#### 2. 学生端接口
- **练习系统**：获取练习题、提交答案、查看解析
- **会话管理**：创建/删除会话、发送消息、流式响应
- **错题本**：查看错题、标记掌握、统计分析
- **知识图谱**：获取知识节点、查看学习路径
- **课程资源**：浏览资源、下载文件

#### 3. 教师端接口
- **题库管理**：CRUD 操作、批量导入/导出
- **班级管理**：创建班级、管理学生、查看统计
- **学生画像**：学习数据分析、知识掌握度
- **资源管理**：上传/管理教学资源

#### 4. 管理员端接口
- **用户管理**：用户 CRUD、权限管理
- **系统配置**：系统参数、AI 模型配置
- **知识图谱管理**：节点/关系 CRUD、图谱编辑
- **统计分析**：用户增长、系统使用情况

---

## 🔑 接口规范说明

### 基础信息

- **Base URL**: `http://your-domain.com/api`
- **认证方式**: JWT Bearer Token
- **请求格式**: JSON
- **响应格式**: JSON
- **字符编码**: UTF-8

### 通用响应格式

#### 成功响应
```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

#### 错误响应
```json
{
  "code": 400,
  "message": "错误描述",
  "detail": "详细错误信息"
}
```

### HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未授权（未登录或 Token 失效） |
| 403 | 无权限访问 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

### 认证说明

大部分接口需要在请求头中携带 JWT Token：

```http
Authorization: Bearer <your_token_here>
```

获取 Token 的方式：
1. 调用登录接口 `/auth/login`
2. 从响应中获取 `access_token`
3. 在后续请求中携带该 Token

---

## 📝 使用示例

### 登录示例

```bash
curl -X POST http://your-domain.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "student001",
    "password": "password123"
  }'
```

### 获取练习题示例

```bash
curl -X GET http://your-domain.com/api/exercises?difficulty=medium&count=5 \
  -H "Authorization: Bearer <your_token>"
```

### 提交答案示例

```bash
curl -X POST http://your-domain.com/api/exercises/submit \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "exercise_id": 123,
    "answer": "x = 5"
  }'
```

---

## 🔄 更新记录

### 2026-02-15
- 迁移到统一文档目录
- 添加 API 目录 README

### 2026-01-21
- 初始版本，完整的 API 接口规范

---

## 🔗 相关文档

- [数据模型定义](../architecture/数据模型定义.md) - 了解数据结构
- [部署指南](../deployment/DEPLOYMENT.md) - 了解如何部署 API 服务
- [文档中心](../README.md) - 返回文档首页
