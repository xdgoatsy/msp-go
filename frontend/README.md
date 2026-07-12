# MathStudyPlatform Frontend

React 19 + TypeScript 5.9 + Vite 7 前端应用，按学生、教师、管理员和公共页面划分路由，业务能力集中在 `src/modules/`。

## 常用命令

```bash
npm install
npm run dev
npm test
npm run test:coverage
npm run lint
npm run build
npm run preview
```

本地开发服务器默认为 `http://localhost:5173`，API 请求通过 Vite 或 Nginx 配置转发到 Go 后端。

## 目录约定

```text
src/
├── app/          # Provider 和路由装配
├── pages/        # 按角色分组的薄页面组件
├── modules/      # 业务模块、服务、Hooks、状态和组件
├── components/   # 跨业务通用组件
├── store/        # Redux Toolkit 根 Store
├── libs/         # HTTP、数学渲染、验证和导出等基础能力
├── hooks/        # 跨模块 Hooks
└── types/        # 公共类型
```

模块对外接口由各自 `index.ts` 暴露；页面负责组合和布局，业务逻辑放在模块 Hook 或 Service 中；新增代码不再添加旧路径兼容重导出。

## 相关文档

- [系统架构](../docs/technical/architecture.md)
- [开发指南](../docs/technical/development.md)
- [项目待办](../docs/TODO.md)
- [历史前端架构说明](../docs/archive/architecture/frontend-architecture.md)
