# 日志管理系统使用指南

## 概述

前端项目现在使用统一的日志管理系统，替代原有的 `console.log/error/warn` 调用。该系统提供了更强大的功能，包括日志级别控制、环境区分、敏感信息过滤和远程日志上报。

## 核心特性

- ✅ **统一接口**：提供一致的日志记录 API
- ✅ **环境区分**：开发环境显示详细日志，生产环境只显示警告和错误
- ✅ **日志级别**：DEBUG、INFO、WARN、ERROR 四个级别
- ✅ **安全保护**：自动过滤敏感信息（密码、token 等）
- ✅ **上下文日志**：支持创建带上下文的日志记录器
- ✅ **远程上报**：生产环境自动上报警告和错误到服务器
- ✅ **性能监控**：内置性能日志记录功能
- ✅ **安全审计**：专门的安全事件日志

## 快速开始

### 1. 基本使用

```typescript
import { logger } from '@/libs/utils/logger';

// 调试日志（仅开发环境）
logger.debug('User data loaded', { userId: '123', count: 10 });

// 信息日志
logger.info('User logged in successfully', { userId: '123' });

// 警告日志
logger.warn('API response slow', { duration: 3000 });

// 错误日志
logger.error('Failed to fetch data', error);
```

### 2. 创建上下文日志记录器

推荐为每个模块创建专用的日志记录器：

```typescript
import { logger } from '@/libs/utils/logger';

// 创建带上下文的日志记录器
const authLogger = logger.createContextLogger('Auth');

// 使用上下文日志记录器
authLogger.info('Login attempt', { username: 'user123' });
// 输出: [INFO] [Auth] Login attempt { username: 'user123' }

authLogger.error('Login failed', error);
// 输出: [ERROR] [Auth] Login failed { name: 'Error', message: '...' }
```

### 3. 安全事件日志

用于记录安全相关的事件（登录失败、未授权访问等）：

```typescript
const authLogger = logger.createContextLogger('Auth');

// 记录安全事件
authLogger.security('Login failed', {
  username: 'user123',
  ipAddress: '192.168.1.1',
  reason: 'Invalid password'
});

// 安全事件会自动上报到服务器（即使在开发环境）
```

### 4. 性能监控

```typescript
const apiLogger = logger.createContextLogger('API');

const startTime = performance.now();
// ... 执行操作
const duration = performance.now() - startTime;

apiLogger.performance('API request', duration, 'ms');
// 输出: [INFO] [API] [PERFORMANCE] API request: 150ms
```

## 日志级别说明

| 级别 | 用途 | 开发环境 | 生产环境 |
|------|------|----------|----------|
| DEBUG | 调试信息，详细的执行流程 | ✅ 显示 | ❌ 不显示 |
| INFO | 一般信息，重要的业务事件 | ✅ 显示 | ❌ 不显示 |
| WARN | 警告信息，潜在问题 | ✅ 显示 | ✅ 显示并上报 |
| ERROR | 错误信息，需要关注的问题 | ✅ 显示 | ✅ 显示并上报 |

## 敏感信息保护

日志系统会自动过滤以下敏感字段：
- `password`
- `token`
- `secret`
- `apiKey`
- `authorization`
- `cookie`

```typescript
logger.info('User data', {
  username: 'user123',
  password: 'secret123',  // 会被替换为 [REDACTED]
  token: 'abc123'         // 会被替换为 [REDACTED]
});

// 实际输出:
// { username: 'user123', password: '[REDACTED]', token: '[REDACTED]' }
```

## 实际使用示例

### 示例 1: API 客户端

```typescript
// src/libs/http/apiClient.ts
import { logger } from '../utils/logger';

const apiLogger = logger.createContextLogger('API');

apiClient.interceptors.request.use(
  (config) => {
    apiLogger.debug('Request sent', {
      method: config.method,
      url: config.url
    });
    return config;
  },
  (error) => {
    apiLogger.error('Request error', error);
    return Promise.reject(error);
  }
);

apiClient.interceptors.response.use(
  (response) => {
    apiLogger.debug('Response received', {
      status: response.status,
      url: response.config.url
    });
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      apiLogger.security('Unauthorized access', {
        url: error.config?.url
      });
    } else {
      apiLogger.error('API error', {
        status: error.response?.status,
        message: error.message
      });
    }
    return Promise.reject(error);
  }
);
```

### 示例 2: 认证组件

```typescript
// src/modules/auth/components/LoginForm.tsx
import { logger } from '@/libs/utils/logger';

const authLogger = logger.createContextLogger('Auth');

const handleLogin = async () => {
  try {
    const response = await authService.login(credentials);

    authLogger.info('Login successful', {
      userId: response.user.id,
      role: response.user.role
    });

    navigate('/dashboard');
  } catch (error) {
    authLogger.security('Login failed', {
      username: credentials.username,
      error: error instanceof Error ? error.message : 'Unknown error'
    });

    setError('登录失败');
  }
};
```

### 示例 3: Redux Slice

```typescript
// src/modules/exercise/store/exerciseSlice.ts
import { logger } from '@/libs/utils/logger';

const exerciseLogger = logger.createContextLogger('Exercise');

const exerciseSlice = createSlice({
  name: 'exercise',
  initialState,
  reducers: {
    setCurrentExercise(state, action) {
      exerciseLogger.debug('Exercise loaded', {
        exerciseId: action.payload.id,
        difficulty: action.payload.difficulty
      });
      state.currentExercise = action.payload;
    },
    submitAnswer(state, action) {
      exerciseLogger.info('Answer submitted', {
        exerciseId: state.currentExercise?.id,
        answerLength: action.payload.length
      });
    }
  }
});
```

### 示例 4: 错误边界

```typescript
// src/components/ErrorBoundary.tsx
import { logger } from '@/libs/utils/logger';

const errorLogger = logger.createContextLogger('ErrorBoundary');

class ErrorBoundary extends React.Component {
  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    errorLogger.error('React error boundary caught error', {
      error: error.message,
      componentStack: errorInfo.componentStack
    });
  }
}
```

## 配置选项

可以在应用启动时配置日志系统：

```typescript
// src/main.tsx
import { logger, LogLevel } from '@/libs/utils/logger';

// 配置日志系统
logger.configure({
  level: LogLevel.DEBUG,           // 设置日志级别
  enableConsole: true,             // 启用控制台输出
  enableRemote: false,             // 禁用远程上报（开发环境）
  remoteEndpoint: '/api/v1/logs'   // 远程日志端点
});
```

## 最佳实践

### ✅ 推荐做法

1. **为每个模块创建专用日志记录器**
   ```typescript
   const moduleLogger = logger.createContextLogger('ModuleName');
   ```

2. **使用合适的日志级别**
   - DEBUG: 详细的调试信息
   - INFO: 重要的业务事件
   - WARN: 潜在问题
   - ERROR: 错误和异常

3. **提供有意义的上下文信息**
   ```typescript
   logger.info('User action', {
     action: 'click',
     target: 'submit-button',
     userId: user.id
   });
   ```

4. **使用安全日志记录敏感操作**
   ```typescript
   authLogger.security('Password reset requested', {
     userId: user.id,
     email: user.email
   });
   ```

### ❌ 避免的做法

1. **不要直接使用 console.log**
   ```typescript
   // ❌ 不推荐
   console.log('User logged in');

   // ✅ 推荐
   logger.info('User logged in', { userId: user.id });
   ```

2. **不要记录敏感信息**
   ```typescript
   // ❌ 不推荐
   logger.info('Login', { password: user.password });

   // ✅ 推荐（系统会自动过滤，但最好不要记录）
   logger.info('Login', { username: user.username });
   ```

3. **不要在循环中记录大量日志**
   ```typescript
   // ❌ 不推荐
   items.forEach(item => {
     logger.debug('Processing item', item);
   });

   // ✅ 推荐
   logger.debug('Processing items', { count: items.length });
   ```

## 远程日志上报

生产环境中，WARN 和 ERROR 级别的日志会自动上报到服务器。

### 后端接口要求

```typescript
// POST /api/v1/logs
{
  "type": "log" | "security",
  "message": "Error message",
  "data": {
    "timestamp": "2026-01-22T10:00:00.000Z",
    "level": "ERROR",
    "message": "API request failed",
    "data": { ... }
  },
  "timestamp": "2026-01-22T10:00:00.000Z"
}
```

## 故障排查

### 问题：日志没有显示

**解决方案**：
1. 检查日志级别配置
2. 确认是否在生产环境（生产环境只显示 WARN 和 ERROR）
3. 检查浏览器控制台过滤器设置

### 问题：敏感信息被过滤

**解决方案**：
这是预期行为。如果需要记录某些字段，请使用不包含敏感关键词的字段名。

### 问题：远程日志上报失败

**解决方案**：
1. 检查后端日志接口是否正常
2. 检查网络连接
3. 远程日志上报失败不会影响应用运行

## 迁移指南

### 从 console.log 迁移

```typescript
// 旧代码
console.log('User data:', userData);
console.error('Error:', error);
console.warn('Warning:', message);

// 新代码
import { logger } from '@/libs/utils/logger';

const moduleLogger = logger.createContextLogger('ModuleName');

moduleLogger.debug('User data', userData);
moduleLogger.error('Error occurred', error);
moduleLogger.warn('Warning', { message });
```

## 相关文件

- 日志系统实现: `src/libs/utils/logger.ts`
- CSRF 工具: `src/libs/utils/csrf.ts`（已创建，待后端支持后启用）
- API 客户端: `src/libs/http/apiClient.ts`（已集成日志系统）

## 总结

统一的日志管理系统提供了更好的可维护性、安全性和可观测性。请在新代码中使用日志系统，并逐步迁移旧代码。
