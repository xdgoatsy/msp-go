import { lazy } from 'react';
import type { RouteConfig } from './index';

// 教师页面懒加载
const TeacherDashboardPage = lazy(() => import('@/pages/teacher/TeacherDashboardPage').then(m => ({ default: m.TeacherDashboardPage })));
const ClassManagementPage = lazy(() => import('@/pages/teacher/ClassManagementPage').then(m => ({ default: m.ClassManagementPage })));
const QuestionBankPage = lazy(() => import('@/pages/teacher/QuestionBankPage').then(m => ({ default: m.QuestionBankPage })));
const QuestionEditPage = lazy(() => import('@/pages/teacher/QuestionEditPage').then(m => ({ default: m.QuestionEditPage })));
const ClassDetailPage = lazy(() => import('@/pages/teacher/ClassDetailPage').then(m => ({ default: m.ClassDetailPage })));
const StudentDetailPage = lazy(() => import('@/pages/teacher/StudentDetailPage').then(m => ({ default: m.StudentDetailPage })));
const StudentsPage = lazy(() => import('@/pages/teacher/StudentsPage').then(m => ({ default: m.StudentsPage })));
const TeacherResourcesPage = lazy(() => import('@/pages/teacher/TeacherResourcesPage').then(m => ({ default: m.default })));
const ProfilePage = lazy(() => import('@/pages/common/ProfilePage').then(m => ({ default: m.ProfilePage })));

/**
 * 教师路由 - 需要登录 + teacher 角色
 */
export const teacherRoutes: RouteConfig[] = [
  { path: '/teacher/dashboard', component: TeacherDashboardPage, title: '教学概览', protected: true, requiredRole: 'teacher' },
  { path: '/teacher/classes', component: ClassManagementPage, title: '班级管理', protected: true, requiredRole: 'teacher' },
  { path: '/teacher/students', component: StudentsPage, title: '学生管理', protected: true, requiredRole: 'teacher' },
  { path: '/teacher/question-bank', component: QuestionBankPage, title: '题库管理', protected: true, requiredRole: 'teacher' },
  { path: '/teacher/question/new', component: QuestionEditPage, title: '新建题目', protected: true, requiredRole: 'teacher' },
  { path: '/teacher/question/:id/edit', component: QuestionEditPage, title: '编辑题目', protected: true, requiredRole: 'teacher' },
  { path: '/teacher/resources', component: TeacherResourcesPage, title: '教学资源', protected: true, requiredRole: 'teacher' },
  { path: '/teacher/class/:id', component: ClassDetailPage, title: '班级详情', protected: true, requiredRole: 'teacher' },
  { path: '/teacher/student/:id', component: StudentDetailPage, title: '学生详情', protected: true, requiredRole: 'teacher' },
  { path: '/teacher/profile', component: ProfilePage, title: '个人资料', protected: true, requiredRole: 'teacher' },
];
