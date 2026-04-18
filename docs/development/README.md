# 开发规范文档

本目录包含数学学习平台的开发规范和最佳实践。

---

## 📄 文档列表

### 工具与系统文档
- **[后端 Python 到 Go 重构迁移文档](./backend-python-to-go-refactor.md)** - 后端整体迁移到 Go 的阶段计划、验收规则和进度跟踪
- **[数据库迁移指南](./MIGRATION_GUIDE.md)** - Alembic 迁移管理、回滚、最佳实践
- **[动画系统文档](./animation-system.md)** - Tailwind CSS + Framer Motion 动画系统使用指南
- **[日志系统文档](./logger-system.md)** - 统一日志管理系统（级别控制、敏感信息过滤、远程上报）

### 前端开发规范（待完善）
- 代码风格规范
- 组件开发规范
- 状态管理规范
- API 调用规范
- 测试规范

### 后端开发规范（待完善）
- 代码风格规范
- API 设计规范
- 数据库设计规范
- 错误处理规范
- 测试规范

---

## 🎯 通用开发规范

### 代码风格

#### 命名规范

**变量命名**：
- 使用有意义的名称
- 驼峰命名法（camelCase）用于变量和函数
- 帕斯卡命名法（PascalCase）用于类和组件
- 全大写下划线分隔（UPPER_CASE）用于常量

```typescript
// ✅ 好的命名
const userProfile = getUserProfile();
const MAX_RETRY_COUNT = 3;
class UserService {}

// ❌ 不好的命名
const data = getData();
const x = 3;
class service {}
```

**文件命名**：
- 组件文件使用 PascalCase：`UserProfile.tsx`
- 工具函数文件使用 camelCase：`formatDate.ts`
- 常量文件使用 camelCase：`apiConstants.ts`

#### 代码格式

- 使用 2 空格缩进
- 每行最大长度 100 字符
- 使用分号结尾
- 使用单引号（字符串）
- 使用 Prettier 自动格式化

### Git 提交规范

使用 Conventional Commits 规范：

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type 类型**：
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具相关

**示例**：
```bash
feat(auth): 添加西电统一认证登录功能

- 集成西电统一认证 API
- 添加自动登录逻辑
- 更新登录页面 UI

Closes #123
```

### 分支管理

- `main`: 主分支，保护分支
- `develop`: 开发分支
- `feature/*`: 功能分支
- `bugfix/*`: 修复分支
- `hotfix/*`: 紧急修复分支

**工作流程**：
1. 从 `develop` 创建 `feature/xxx` 分支
2. 开发完成后提交 PR 到 `develop`
3. Code Review 通过后合并
4. 定期从 `develop` 合并到 `main`

---

## 🔍 代码审查清单

### 功能性
- [ ] 功能是否按需求实现
- [ ] 边界条件是否处理
- [ ] 错误处理是否完善
- [ ] 是否有单元测试

### 代码质量
- [ ] 代码是否易读易懂
- [ ] 是否有重复代码
- [ ] 函数是否过长（建议 < 50 行）
- [ ] 是否有魔法数字（应使用常量）

### 性能
- [ ] 是否有性能问题
- [ ] 是否有不必要的重复计算
- [ ] 是否有内存泄漏风险
- [ ] 数据库查询是否优化

### 安全性
- [ ] 是否有 SQL 注入风险
- [ ] 是否有 XSS 风险
- [ ] 敏感信息是否加密
- [ ] 权限检查是否完善

---

## 📝 注释规范

### 何时写注释

**需要注释的情况**：
- 复杂的业务逻辑
- 非显而易见的算法
- 临时解决方案（TODO/FIXME）
- 公共 API 和函数

**不需要注释的情况**：
- 显而易见的代码
- 变量名已经说明用途
- 简单的 getter/setter

### 注释格式

**函数注释**（JSDoc）：
```typescript
/**
 * 计算两个数的和
 * @param a - 第一个数
 * @param b - 第二个数
 * @returns 两数之和
 */
function add(a: number, b: number): number {
  return a + b;
}
```

**TODO 注释**：
```typescript
// TODO: 优化查询性能
// FIXME: 修复边界条件 bug
// HACK: 临时解决方案，需要重构
```

---

## 🧪 测试规范

### 测试覆盖率目标

- 核心业务逻辑：> 80%
- 工具函数：> 90%
- UI 组件：> 60%

### 测试类型

1. **单元测试**：测试单个函数/组件
2. **集成测试**：测试模块间交互
3. **端到端测试**：测试完整用户流程

### 测试命名

```typescript
describe('UserService', () => {
  describe('getUserById', () => {
    it('should return user when id exists', () => {
      // 测试代码
    });

    it('should throw error when id not found', () => {
      // 测试代码
    });
  });
});
```

---

## 🔄 更新记录

### 2026-04-18
- 添加后端 Python 到 Go 重构迁移文档入口

### 2026-02-15
- 创建开发规范文档目录
- 添加通用开发规范

---

## 🔗 相关文档

- [API 接口规范](../api/API接口规范.md) - API 设计规范
- [架构设计](../architecture/) - 了解系统架构
- [文档中心](../README.md) - 返回文档首页
