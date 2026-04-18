import { lazy } from 'react';
import type { RouteConfig } from './index';

// 公共页面懒加载
const WelcomePage = lazy(() => import('@/pages/common/WelcomePage').then(m => ({ default: m.WelcomePage })));
const ProfilePage = lazy(() => import('@/pages/common/ProfilePage').then(m => ({ default: m.ProfilePage })));
const PrivacyPolicyPage = lazy(() => import('@/pages/common/PrivacyPolicyPage').then(m => ({ default: m.PrivacyPolicyPage })));
const TermsOfServicePage = lazy(() => import('@/pages/common/TermsOfServicePage').then(m => ({ default: m.TermsOfServicePage })));
const GuidePage = lazy(() => import('@/pages/common/GuidePage').then(m => ({ default: m.GuidePage })));
const FAQPage = lazy(() => import('@/pages/common/FAQPage').then(m => ({ default: m.FAQPage })));
const AboutPage = lazy(() => import('@/pages/common/AboutPage').then(m => ({ default: m.AboutPage })));
const ContactPage = lazy(() => import('@/pages/common/ContactPage').then(m => ({ default: m.ContactPage })));
/**
 * 公共路由 - 无需登录即可访问
 */
export const publicRoutes: RouteConfig[] = [
  { path: '/welcome', component: WelcomePage, title: '欢迎', protected: false },
  { path: '/privacy-policy', component: PrivacyPolicyPage, title: '隐私政策', protected: false },
  { path: '/terms-of-service', component: TermsOfServicePage, title: '服务条款', protected: false },
  { path: '/guide', component: GuidePage, title: '使用指南', protected: false },
  { path: '/faq', component: FAQPage, title: '常见问题', protected: false },
  { path: '/about', component: AboutPage, title: '团队介绍', protected: false },
  { path: '/contact', component: ContactPage, title: '联系我们', protected: false },
  { path: '/profile', component: ProfilePage, title: '个人资料', protected: true },
];
