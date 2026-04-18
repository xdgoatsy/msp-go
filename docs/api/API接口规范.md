# API 接口规范

本文档定义了前端需要的所有后端 API 接口，包括请求参数、响应格式、错误处理等。

**基础信息**：
- **Base URL**：`http://localhost:8000/api/v1`
- **认证方式**：JWT Token（通过 `Authorization: Bearer <token>` 请求头传递）
- **内容类型**：`application/json`
- **字符编码**：`UTF-8`

---

## 📋 目录

1. [通用规范](#通用规范)
2. [认证模块](#认证模块)
3. [练习模块](#练习模块)
4. [学习会话模块](#学习会话模块)
5. [错题本模块](#错题本模块)
6. [诊断报告模块](#诊断报告模块)
7. [学习路径模块](#学习路径模块)
8. [知识图谱模块](#知识图谱模块)
9. [课程模块](#课程模块)
10. [作业模块](#作业模块)
11. [班级模块](#班级模块)
12. [用户模块](#用户模块)
13. [学习分析模块](#学习分析模块)

---

## 通用规范

### 统一响应格式

所有 API 响应均遵循以下格式：

#### 成功响应
```json
{
  "success": true,
  "data": {
    // 实际数据
  },
  "message": "操作成功"
}
```

#### 错误响应
```json
{
  "success": false,
  "message": "错误描述",
  "code": "ERROR_CODE",
  "details": {
    // 可选的详细错误信息
  }
}
```

### 分页响应格式

```json
{
  "success": true,
  "data": {
    "items": [],
    "total": 100,
    "page": 1,
    "pageSize": 20,
    "totalPages": 5
  }
}
```

### 通用错误码

| 错误码 | HTTP 状态码 | 说明 |
|--------|------------|------|
| `UNAUTHORIZED` | 401 | 未授权，需要登录 |
| `FORBIDDEN` | 403 | 无权限访问 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `VALIDATION_ERROR` | 400 | 请求参数验证失败 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |

---

## 认证模块

### 1. 用户登录

**接口**：`POST /auth/login`

**请求参数**：
```json
{
  "username": "string",
  "password": "string"
}
```

**响应数据**：
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "string",
      "username": "string",
      "email": "string",
      "role": "student | teacher",
      "avatar": "string?",
      "createdAt": "2026-01-21T10:00:00Z",
      "updatedAt": "2026-01-21T10:00:00Z"
    },
    "token": "string",
    "refreshToken": "string"
  }
}
```

**错误码**：
- `INVALID_CREDENTIALS` - 用户名或密码错误
- `ACCOUNT_DISABLED` - 账户已被禁用

---

### 2. 用户注册

**接口**：`POST /auth/register`

**请求参数**：
```json
{
  "username": "string",
  "email": "string",
  "password": "string",
  "role": "student | teacher"
}
```

**响应数据**：同登录接口

**错误码**：
- `USERNAME_EXISTS` - 用户名已存在
- `EMAIL_EXISTS` - 邮箱已被注册
- `WEAK_PASSWORD` - 密码强度不足

---

### 3. 刷新 Token

**接口**：`POST /auth/refresh`

**请求参数**：
```json
{
  "refreshToken": "string"
}
```

**响应数据**：
```json
{
  "success": true,
  "data": {
    "token": "string",
    "refreshToken": "string"
  }
}
```

---

### 4. 登出

**接口**：`POST /auth/logout`

**请求头**：需要 `Authorization: Bearer <token>`

**响应数据**：
```json
{
  "success": true,
  "message": "登出成功"
}
```

---

### 5. 获取当前用户信息

**接口**：`GET /auth/me`

**请求头**：需要 `Authorization: Bearer <token>`

**响应数据**：
```json
{
  "success": true,
  "data": {
    "id": "string",
    "username": "string",
    "email": "string",
    "role": "student | teacher",
    "avatar": "string?",
    "createdAt": "2026-01-21T10:00:00Z",
    "updatedAt": "2026-01-21T10:00:00Z"
  }
}
```

---

## 练习模块

### 1. 获取练习题列表

**接口**：`GET /exercise/list`

**请求参数**（Query）：
```
page: number (默认 1)
pageSize: number (默认 20)
difficulty?: "easy" | "medium" | "hard"
knowledgeNodeId?: string
search?: string
```

**响应数据**：
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "string",
        "title": "string",
        "content": "string (LaTeX)",
        "difficulty": "easy | medium | hard",
        "knowledgeNodeIds": ["string"],
        "solution": "string?",
        "hints": ["string"],
        "createdAt": "2026-01-21T10:00:00Z",
        "updatedAt": "2026-01-21T10:00:00Z"
      }
    ],
    "total": 100,
    "page": 1,
    "pageSize": 20,
    "totalPages": 5
  }
}
```

---

### 2. 获取下一道练习题

**接口**：`GET /exercise/next`

**请求参数**（Query）：
```
difficulty?: "easy" | "medium" | "hard"
knowledgeNodeId?: string
```

**响应数据**：
```json
{
  "success": true,
  "data": {
    "id": "string",
    "title": "string",
    "content": "string (LaTeX)",
    "difficulty": "easy | medium | hard",
    "knowledgeNodeIds": ["string"],
    "hints": ["string"],
    "createdAt": "2026-01-21T10:00:00Z"
  }
}
```

---

### 3. 提交练习题答案

**接口**：`POST /exercise/submit`

**请求参数**：
```json
{
  "exerciseId": "string",
  "answer": "string"
}
```

**响应数据**：
```json
{
  "success": true,
  "data": {
    "correct": true,
    "feedback": "string",
    "solution": "string?",
    "diagnosisReportId": "string?",
    "hints": ["string"],
    "relatedConcepts": ["string"]
  }
}
```

---

### 4. 获取练习题详情

**接口**：`GET /exercise/{exerciseId}`

**响应数据**：
```json
{
  "success": true,
  "data": {
    "id": "string",
    "title": "string",
    "content": "string (LaTeX)",
    "difficulty": "easy | medium | hard",
    "knowledgeNodeIds": ["string"],
    "solution": "string",
    "hints": ["string"],
    "createdAt": "2026-01-21T10:00:00Z",
    "updatedAt": "2026-01-21T10:00:00Z"
  }
}
```

---

## 学习会话模块

### 1. 创建学习会话

**接口**：`POST /session/create`

**请求参数**：
```json
{
  "title": "string?",
  "initialMessage": "string?"
}
```

**响应数据**：
```json
{
  "success": true,
  "data": {
    "id": "string",
    "studentId": "string",
    "title": "string",
    "status": "active",
    "startedAt": "2026-01-21T10:00:00Z",
    "messageCount": 0
  }
}
```

---

### 2. 获取会话列表

**接口**：`GET /session/list`

**请求参数**（Query）：
```
page: number (默认 1)
pageSize: number (默认 20)
status?: "active" | "completed" | "paused"
```

**响应数据**：
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "string",
        "studentId": "string",
        "title": "string",
        "status": "active | completed | paused",
        "startedAt": "2026-01-21T10:00:00Z",
        "endedAt": "2026-01-21T11:00:00Z?",
        "messageCount": 10
      }
    ],
    "total": 50,
    "page": 1,
    "pageSize": 20,
    "totalPages": 3
  }
}
```

---

### 3. 获取会话详情

**接口**：`GET /session/{sessionId}`

**响应数据**：
```json
{
  "success": true,
  "data": {
    "id": "string",
    "studentId": "string",
    "title": "string",
    "status": "active | completed | paused",
    "startedAt": "2026-01-21T10:00:00Z",
    "endedAt": "2026-01-21T11:00:00Z?",
    "messageCount": 10
  }
}
```

---

### 4. 发送消息

**接口**：`POST /session/{sessionId}/message`

**请求参数**：
```json
{
  "content": "string",
  "metadata": {
    // 可选的元数据
  }
}
```

**响应数据**：
```json
{
  "success": true,
  "data": {
    "id": "string",
    "sessionId": "string",
    "role": "assistant",
    "content": "string",
    "timestamp": "2026-01-21T10:00:00Z",
    "metadata": {}
  }
}
```

---

### 5. 获取会话消息列表

**接口**：`GET /session/{sessionId}/messages`

**请求参数**（Query）：
```
page: number (默认 1)
pageSize: number (默认 50)
```

**响应数据**：
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "string",
        "sessionId": "string",
        "role": "user | assistant | system",
        "content": "string",
        "timestamp": "2026-01-21T10:00:00Z",
        "metadata": {}
      }
    ],
    "total": 100,
    "page": 1,
    "pageSize": 50,
    "totalPages": 2
  }
}
```

---

### 6. 结束会话

**接口**：`POST /session/{sessionId}/end`

**响应数据**：
```json
{
  "success": true,
  "message": "会话已结束"
}
```

---

## 错题本模块

### 1. 获取错题列表

**接口**：`GET /mistake-book/list`

**请求参数**（Query）：
```
page: number (默认 1)
pageSize: number (默认 20)
masteredOnly?: boolean
knowledgeNodeId?: string
```

**响应数据**：
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "string",
        "studentId": "string",
        "exerciseId": "string",
        "exercise": {
          "id": "string",
          "title": "string",
          "content": "string",
          "difficulty": "easy | medium | hard"
        },
        "userAnswer": "string",
        "correctAnswer": "string",
        "diagnosis": "string?",
        "createdAt": "2026-01-21T10:00:00Z",
        "reviewedAt": "2026-01-21T11:00:00Z?",
        "masteredAt": "2026-01-21T12:00:00Z?"
      }
    ],
    "total": 30,
    "page": 1,
    "pageSize": 20,
    "totalPages": 2
  }
}
```

---

### 2. 标记错题为已掌握

**接口**：`POST /mistake-book/{mistakeId}/master`

**响应数据**：
```json
{
  "success": true,
  "message": "已标记为掌握"
}
```

---

### 3. 删除错题记录

**接口**：`DELETE /mistake-book/{mistakeId}`

**响应数据**：
```json
{
  "success": true,
  "message": "删除成功"
}
```

---

## 诊断报告模块

### 1. 获取诊断报告详情

**接口**：`GET /diagnosis/{reportId}`

**响应数据**：
```json
{
  "success": true,
  "data": {
    "id": "string",
    "studentId": "string",
    "exerciseId": "string",
    "errorType": "string",
    "errorDescription": "string",
    "suggestions": ["string"],
    "relatedConcepts": ["string"],
    "createdAt": "2026-01-21T10:00:00Z"
  }
}
```

---

### 2. 获取诊断报告列表

**接口**：`GET /diagnosis/list`

**请求参数**（Query）：
```
page: number (默认 1)
pageSize: number (默认 20)
```

**响应数据**：
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "string",
        "studentId": "string",
        "exerciseId": "string",
        "errorType": "string",
        "errorDescription": "string",
        "suggestions": ["string"],
        "relatedConcepts": ["string"],
        "createdAt": "2026-01-21T10:00:00Z"
      }
    ],
    "total": 15,
    "page": 1,
    "pageSize": 20,
    "totalPages": 1
  }
}
```

---

## 学习路径模块

### 1. 获取学习路径

**接口**：`GET /learning-path/current`

**响应数据**：
```json
{
  "success": true,
  "data": {
    "id": "string",
    "studentId": "string",
    "name": "string",
    "description": "string?",
    "nodes": [
      {
        "id": "string",
        "knowledgeNodeId": "string",
        "knowledgeNode": {
          "id": "string",
          "name": "string",
          "description": "string?",
          "level": 1,
          "order": 1
        },
        "order": 1,
        "status": "locked | available | in_progress | completed",
        "progress": 0.5
      }
    ],
    "progress": 0.3,
    "createdAt": "2026-01-21T10:00:00Z",
    "updatedAt": "2026-01-21T10:00:00Z"
  }
}
```

---

### 2. 更新学习路径节点状态

**接口**：`POST /learning-path/node/{nodeId}/update`

**请求参数**：
```json
{
  "status": "in_progress | completed",
  "progress": 0.8
}
```

**响应数据**：
```json
{
  "success": true,
  "message": "更新成功"
}
```

---

## 知识图谱模块

### 1. 获取知识图谱

**接口**：`GET /knowledge-graph`

**响应数据**：
```json
{
  "success": true,
  "data": {
    "nodes": [
      {
        "id": "string",
        "name": "string",
        "description": "string?",
        "parentId": "string?",
        "level": 1,
        "order": 1
      }
    ],
    "edges": [
      {
        "source": "string",
        "target": "string",
        "type": "prerequisite | related"
      }
    ]
  }
}
```

---

### 2. 获取知识节点详情

**接口**：`GET /knowledge-graph/node/{nodeId}`

**响应数据**：
```json
{
  "success": true,
  "data": {
    "id": "string",
    "name": "string",
    "description": "string?",
    "parentId": "string?",
    "level": 1,
    "order": 1,
    "prerequisites": ["string"],
    "relatedNodes": ["string"],
    "exercises": [
      {
        "id": "string",
        "title": "string",
        "difficulty": "easy | medium | hard"
      }
    ]
  }
}
```

---

## 课程模块

### 1. 获取课程列表

**接口**：`GET /course/list`

**请求参数**（Query）：
```
page: number (默认 1)
pageSize: number (默认 20)
```

**响应数据**：
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "string",
        "name": "string",
        "description": "string?",
        "teacherId": "string",
        "teacher": {
          "id": "string",
          "username": "string",
          "email": "string"
        },
        "coverImage": "string?",
        "startDate": "2026-01-21?",
        "endDate": "2026-06-21?",
        "studentCount": 30
      }
    ],
    "total": 10,
    "page": 1,
    "pageSize": 20,
    "totalPages": 1
  }
}
```

---

### 2. 获取课程详情

**接口**：`GET /course/{courseId}`

**响应数据**：
```json
{
  "success": true,
  "data": {
    "id": "string",
    "name": "string",
    "description": "string?",
    "teacherId": "string",
    "teacher": {
      "id": "string",
      "username": "string",
      "email": "string"
    },
    "coverImage": "string?",
    "startDate": "2026-01-21?",
    "endDate": "2026-06-21?",
    "studentCount": 30
  }
}
```

---

## 作业模块

### 1. 获取作业列表

**接口**：`GET /assignment/list`

**请求参数**（Query）：
```
page: number (默认 1)
pageSize: number (默认 20)
courseId?: string
```

**响应数据**：
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "string",
        "courseId": "string",
        "title": "string",
        "description": "string?",
        "exerciseIds": ["string"],
        "dueDate": "2026-01-28T23:59:59Z?",
        "createdAt": "2026-01-21T10:00:00Z",
        "updatedAt": "2026-01-21T10:00:00Z"
      }
    ],
    "total": 5,
    "page": 1,
    "pageSize": 20,
    "totalPages": 1
  }
}
```

---

### 2. 创建作业（教师）

**接口**：`POST /assignment/create`

**请求参数**：
```json
{
  "courseId": "string",
  "title": "string",
  "description": "string?",
  "exerciseIds": ["string"],
  "dueDate": "2026-01-28T23:59:59Z?"
}
```

**响应数据**：
```json
{
  "success": true,
  "data": {
    "id": "string",
    "courseId": "string",
    "title": "string",
    "description": "string?",
    "exerciseIds": ["string"],
    "dueDate": "2026-01-28T23:59:59Z?",
    "createdAt": "2026-01-21T10:00:00Z",
    "updatedAt": "2026-01-21T10:00:00Z"
  }
}
```

---

## 班级模块

### 1. 获取班级列表（教师）

**接口**：`GET /class/list`

**请求参数**（Query）：
```
page: number (默认 1)
pageSize: number (默认 20)
```

**响应数据**：
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "string",
        "name": "string",
        "teacherId": "string",
        "teacher": {
          "id": "string",
          "username": "string"
        },
        "studentIds": ["string"],
        "students": [
          {
            "id": "string",
            "username": "string",
            "email": "string"
          }
        ],
        "courseId": "string?",
        "createdAt": "2026-01-21T10:00:00Z"
      }
    ],
    "total": 3,
    "page": 1,
    "pageSize": 20,
    "totalPages": 1
  }
}
```

---

### 2. 获取班级详情（教师）

**接口**：`GET /class/{classId}`

**响应数据**：
```json
{
  "success": true,
  "data": {
    "id": "string",
    "name": "string",
    "teacherId": "string",
    "teacher": {
      "id": "string",
      "username": "string",
      "email": "string"
    },
    "studentIds": ["string"],
    "students": [
      {
        "id": "string",
        "username": "string",
        "email": "string",
        "role": "student"
      }
    ],
    "courseId": "string?",
    "course": {
      "id": "string",
      "name": "string"
    },
    "createdAt": "2026-01-21T10:00:00Z"
  }
}
```

---

## 用户模块

### 1. 获取学生列表（教师）

**接口**：`GET /user/students`

**请求参数**（Query）：
```
page: number (默认 1)
pageSize: number (默认 20)
classId?: string
search?: string
```

**响应数据**：
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "string",
        "username": "string",
        "email": "string",
        "role": "student",
        "avatar": "string?",
        "grade": "string?",
        "school": "string?",
        "createdAt": "2026-01-21T10:00:00Z"
      }
    ],
    "total": 50,
    "page": 1,
    "pageSize": 20,
    "totalPages": 3
  }
}
```

---

### 2. 获取学生详情（教师）

**接口**：`GET /user/student/{studentId}`

**响应数据**：
```json
{
  "success": true,
  "data": {
    "id": "string",
    "username": "string",
    "email": "string",
    "role": "student",
    "avatar": "string?",
    "grade": "string?",
    "school": "string?",
    "createdAt": "2026-01-21T10:00:00Z",
    "updatedAt": "2026-01-21T10:00:00Z"
  }
}
```

---

### 3. 更新用户信息

**接口**：`PUT /user/profile`

**请求参数**：
```json
{
  "username": "string?",
  "email": "string?",
  "avatar": "string?",
  "grade": "string?",
  "school": "string?"
}
```

**响应数据**：
```json
{
  "success": true,
  "data": {
    "id": "string",
    "username": "string",
    "email": "string",
    "role": "student | teacher",
    "avatar": "string?",
    "updatedAt": "2026-01-21T10:00:00Z"
  }
}
```

---

## 学习分析模块

### 1. 获取学习统计数据

**接口**：`GET /analytics/stats`

**响应数据**：
```json
{
  "success": true,
  "data": {
    "totalExercises": 150,
    "correctRate": 0.85,
    "totalStudyTime": 7200,
    "currentStreak": 7,
    "masteredConcepts": 25,
    "weakConcepts": ["微积分", "线性代数"]
  }
}
```

---

### 2. 获取每周学习数据

**接口**：`GET /analytics/weekly`

**响应数据**：
```json
{
  "success": true,
  "data": [
    {
      "date": "2026-01-15",
      "exerciseCount": 10,
      "correctCount": 8,
      "studyTime": 3600
    },
    {
      "date": "2026-01-16",
      "exerciseCount": 12,
      "correctCount": 10,
      "studyTime": 4200
    }
  ]
}
```

---

### 3. 获取知识点掌握度

**接口**：`GET /analytics/topic-mastery`

**响应数据**：
```json
{
  "success": true,
  "data": [
    {
      "topicId": "string",
      "topicName": "微积分",
      "mastery": 0.85,
      "exerciseCount": 50,
      "correctCount": 42
    },
    {
      "topicId": "string",
      "topicName": "线性代数",
      "mastery": 0.65,
      "exerciseCount": 30,
      "correctCount": 19
    }
  ]
}
```

---

### 4. 获取错误分布

**接口**：`GET /analytics/error-distribution`

**响应数据**：
```json
{
  "success": true,
  "data": [
    {
      "errorType": "计算错误",
      "count": 15,
      "percentage": 0.3
    },
    {
      "errorType": "概念理解错误",
      "count": 20,
      "percentage": 0.4
    },
    {
      "errorType": "步骤遗漏",
      "count": 10,
      "percentage": 0.2
    }
  ]
}
```

---

### 5. 获取排名信息

**接口**：`GET /analytics/ranking`

**响应数据**：
```json
{
  "success": true,
  "data": {
    "rank": 15,
    "totalUsers": 100,
    "percentile": 0.85,
    "score": 850
  }
}
```

---

## 附录

### 日期时间格式

所有日期时间字段均使用 ISO 8601 格式：`YYYY-MM-DDTHH:mm:ssZ`

示例：`2026-01-21T10:30:00Z`

### 文件上传

文件上传接口使用 `multipart/form-data` 格式，具体接口待补充。

### WebSocket 接口

实时消息推送使用 WebSocket，具体协议待补充。

---

**文档版本**：v1.0
**最后更新**：2026-01-21
**维护者**：前端团队
