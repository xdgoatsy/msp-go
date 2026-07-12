# 前端架构文档

> 归档说明：本文记录旧版前端架构约定，仅用于追溯。当前说明见 [系统架构](../../technical/architecture.md) 和 [开发指南](../../technical/development.md)。

## 概述

MathStudyPlatform 前端采用 **Feature-First 模块化架构**，基于 React 19 + TypeScript 5.9 + Vite 7.2 构建。
架构核心理念：按业务功能模块组织代码，每个模块自包含其 services、store、types、hooks 和 components。

## 技术栈

| 类别 | 技术 | 版本 |
|------|------|------|
| UI 框架 | React | 19.x |
| 类型系统 | TypeScript | 5.9 |
| 构建工具 | Vite | 7.x |
| 状态管理 | Redux Toolkit | 2.x |
| 路由 | React Router | 7.x |
| 样式 | TailwindCSS | 4.x |
| 动画 | Framer Motion | 12.x |
| 表单 | React Hook Form + Zod | 7.x / 4.x |
| HTTP | Axios | 1.x |
| 图表 | ECharts + AntV G6 | 6.x / 5.x |
| 数学渲染 | KaTeX | 0.16 |

## 目录结构

```
src/
├── app/                          # 🏗️ 应用层
│   ├── providers/                # 全局 Provider 组件
│   │   ├── AppProviders.tsx      # Provider 组合（入口）
│   │   ├── ThemeProvider.tsx     # 主题切换
│   │   └── AuthProvider.tsx      # 认证初始化
│   └── routes/                   # 路由配置
│       ├── index.ts              # 路由类型 + 合并导出
│       ├── AppRoutes.tsx         # 路由渲染组件
│       ├── publicRoutes.ts       # 公共路由
│       ├── studentRoutes.ts      # 学生路由
│       ├── teacherRoutes.ts      # 教师路由
│       └── adminRoutes.ts        # 管理员路由
│
├── modules/                      # 📦 业务模块层
│   ├── auth/                     # 认证模块
│   ├── session/                  # 学习会话模块
│   ├── exercise/                 # 练习题模块
│   ├── mistake/                  # 错题本模块
│   ├── knowledge/                # 知识图谱模块
│   ├── analytics/                # 学习分析模块
│   ├── resource/                 # 资源模块
│   ├── classroom/                # 班级模块
│   ├── teacher/                  # 教师模块
│   ├── student/                  # 学生模块
│   ├── admin/                    # 管理员模块
│   ├── ai-config/                # AI 配置模块
│   ├── question/                 # 题目模块
│   ├── upload/                   # 上传模块
│   ├── xidian/                   # 西电集成模块
│   └── password-reset/           # 密码重置模块
│
├── components/                   # 🎨 共享 UI 组件
│   ├── ui/                       # 基础组件 (Button, Card, Modal...)
│   ├── layout/                   # 布局组件 (MainLayout, Footer)
│   ├── chat/                     # 聊天组件 (MessageItem, Markdown)
│   └── charts/                   # 图表组件
│
├── hooks/                        # 🪝 共享 Hooks
│   ├── useDebounce.ts
│   └── useLocalStorage.ts
│
├── libs/                         # 🔧 工具库
│   ├── http/                     # HTTP 客户端 (apiClient, sseClient)
│   ├── auth/                     # 认证事件
│   ├── form/                     # 表单组件库
│   ├── graph/                    # 图表配置
│   ├── math/                     # 数学渲染
│   ├── parsers/                  # 文档解析
│   ├── validation/               # Zod 验证规则
│   ├── animations/               # Framer Motion 配置
│   ├── export/                   # 导出工具
│   ├── styles/                   # 样式工具
│   └── utils/                    # 通用工具 (logger, cn)
│
├── types/                        # 📝 共享类型（仅跨模块类型）
│   ├── common.ts                 # 通用类型 (Theme, UserRole, LoadingState)
│   ├── models.ts                 # 数据模型 (User, Student, Teacher)
│   ├── api.ts                    # API 通用类型
│   └── index.ts                  # 统一导出
│
├── pages/                        # 📄 页面层（薄壳组件）
│   ├── student/                  # 学生页面
│   ├── teacher/                  # 教师页面
│   ├── admin/                    # 管理员页面
│   └── common/                   # 公共页面
│
├── store/                        # 🗃️ Redux Store 配置
│   ├── index.ts                  # Store 入口 + typed hooks
│   └── slices/                   # 兼容层（重导出到 modules）
│
├── App.tsx                       # 根组件（极简）
├── main.tsx                      # 应用入口
└── index.css                     # 全局样式
```

## 分层架构

```
┌─────────────────────────────────────────┐
│              pages/ (页面层)              │  薄壳组件，组合模块功能
├─────────────────────────────────────────┤
│            modules/ (业务模块层)          │  自包含的业务功能单元
├─────────────────────────────────────────┤
│  components/ │ hooks/ │ libs/ │ types/  │  共享基础设施
├─────────────────────────────────────────┤
│              app/ (应用层)               │  Provider、路由、全局配置
├─────────────────────────────────────────┤
│           store/ (状态管理入口)           │  Redux Store 配置
└─────────────────────────────────────────┘
```

### 层级职责

| 层级 | 职责 | 可依赖 |
|------|------|--------|
| `app/` | Provider 组合、路由配置 | modules, components, store |
| `pages/` | 页面布局、组合模块组件 | modules, components, hooks, libs |
| `modules/` | 业务逻辑、领域组件、API 调用 | components, hooks, libs, types, 其他 modules (通过 barrel export) |
| `components/` | 通用 UI 组件（无业务逻辑） | hooks, libs |
| `hooks/` | 通用自定义 Hooks | libs |
| `libs/` | 纯工具函数、第三方库封装 | 无 |
| `types/` | 跨模块共享的类型定义 | 无 |

### 依赖规则
- ✅ 上层可以依赖下层
- ✅ 同层模块间通过 barrel export (index.ts) 交互
- ❌ 下层不可依赖上层
- ❌ 禁止跨模块深层导入（如 `@/modules/auth/store/authSlice`）

## 模块规范

### 标准模块结构

```
modules/<name>/
├── components/     # 模块专属 UI 组件
├── hooks/          # 业务逻辑 Hooks
├── services/       # API 服务层
├── store/          # Redux Slice
├── types/          # 模块类型定义
├── constants/      # 模块常量
└── index.ts        # Barrel Export（公共 API）
```

### Barrel Export 规范

每个模块的 `index.ts` 定义了该模块的公共 API。外部消费者只能通过 barrel export 导入：

```typescript
// ✅ 正确：通过 barrel export 导入
import { authService, ProtectedRoute, useAuth } from '@/modules/auth';

// ❌ 错误：深层导入
import { authService } from '@/modules/auth/services/authService';
```

### 新建模块步骤

1. 在 `modules/` 下创建模块目录
2. 按需创建 `services/`、`store/`、`hooks/`、`components/`、`types/` 子目录
3. 创建 `index.ts` barrel export
4. 如有 Redux slice，在 `store/index.ts` 中注册 reducer
5. 如有路由，在 `app/routes/` 对应文件中添加

## 页面开发规范

### 页面职责
页面组件应该是**薄壳组件**，只负责：
- 布局和组合
- 调用模块提供的 hooks 获取数据和操作
- 渲染 UI

### 业务逻辑抽取模式

```tsx
// ❌ 反模式：页面内混杂业务逻辑
const MyPage = () => {
  const [data, setData] = useState([]);
  const dispatch = useAppDispatch();
  useEffect(() => { fetchData(); }, []);
  const handleSubmit = async () => { /* 复杂逻辑 */ };
  return <div>...</div>;
};

// ✅ 推荐：业务逻辑抽取到模块 hook
const MyPage = () => {
  const { data, loading, handleSubmit } = useMyFeature();
  return <div>...</div>;
};
```

## 状态管理

### Redux Store 结构

Store 配置在 `store/index.ts`，各 reducer 从对应模块导入：

```typescript
import authReducer from '@/modules/auth/store/authSlice';
import sessionReducer from '@/modules/session/store/sessionSlice';
// ...
```

### 类型安全 Hooks

始终使用类型安全的 hooks：

```typescript
import { useAppDispatch, useAppSelector } from '@/store';
```

## API 层

### HTTP 客户端
- `libs/http/apiClient.ts` — Axios 实例，自动 token 注入、401 重试
- `libs/http/sseClient.ts` — SSE 流式连接
- `libs/http/serviceFactory.ts` — 服务方法工厂（统一错误处理、重试）

### Service 规范
每个模块的 service 文件封装该模块的所有 API 调用：

```typescript
// modules/auth/services/authService.ts
export const authService = {
  login: (data: LoginRequest) => apiClient.post('/auth/login', data),
  register: (data: RegisterRequest) => apiClient.post('/auth/register', data),
};
```

## 路由

路由按角色拆分为独立文件，在 `app/routes/` 下管理：
- `publicRoutes.ts` — 无需登录
- `studentRoutes.ts` — 学生角色
- `teacherRoutes.ts` — 教师角色
- `adminRoutes.ts` — 管理员角色

所有页面使用 `React.lazy()` 实现代码分割。

## 命名约定

| 类型 | 命名规则 | 示例 |
|------|----------|------|
| 组件文件 | PascalCase | `LoginForm.tsx` |
| Hook 文件 | camelCase，use 前缀 | `useAuth.ts` |
| Service 文件 | camelCase，Service 后缀 | `authService.ts` |
| Store 文件 | camelCase，Slice 后缀 | `authSlice.ts` |
| 类型文件 | camelCase | `aiConfig.ts` |
| 常量文件 | camelCase | `providerPresets.ts` |
| 模块目录 | kebab-case | `ai-config/` |
| 页面目录 | camelCase | `student/` |

## 兼容层（现状）

历史兼容层已基本清理：

- `services/*.ts`、`types/*.ts` 旧路径兼容文件已删除
- `features/*` 兼容层已移除

当前仅保留少量 `store/slices/*` 迁移入口（如仍存在）。
新代码必须直接从 `modules/*` 导入，不再新增兼容重导出。
