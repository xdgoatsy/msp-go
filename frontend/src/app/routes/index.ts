import { lazy } from 'react';
import { publicRoutes } from './publicRoutes';
import { studentRoutes } from './studentRoutes';
import { teacherRoutes } from './teacherRoutes';
import { adminRoutes } from './adminRoutes';

/**
 * 路由配置类型定义
 */
export interface RouteConfig {
  path: string;
  component: React.LazyExoticComponent<React.FC>;
  title: string;
  protected?: boolean;
  requiredRole?: 'student' | 'teacher' | 'admin';
  exact?: boolean;
}

/** 合并所有路由配置 */
export const routes: RouteConfig[] = [
  ...publicRoutes,
  ...studentRoutes,
  ...teacherRoutes,
  ...adminRoutes,
];

// 404 页面
const NotFoundPage = lazy(() =>
  import('@/pages/NotFoundPage').then(m => ({ default: m.NotFoundPage }))
);

export const notFoundRoute: RouteConfig = {
  path: '*',
  component: NotFoundPage,
  title: '页面未找到',
  protected: false,
};
