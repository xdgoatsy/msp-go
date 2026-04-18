import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAppSelector } from '@/store';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/Button';
import { ThemeToggle } from '@/components/ui/ThemeToggle';
import { cn } from '@/libs/utils/cn';
import { LogOut, User, Users } from 'lucide-react';
import { selectIsAuthenticated, selectCurrentUser } from '@/modules/auth/store/authSlice';
import { getNavItemsByRole } from '@/modules/auth/constants/navigationConfig';
import { useAuth } from '@/modules/auth/hooks/useAuth';
import { animationCombos, navIndicatorVariants } from '@/libs/animations';

interface HeaderProps {
  variant?: 'default' | 'transparent' | 'dark';
  onLoginClick?: () => void;
  onRegisterClick?: () => void;
}

/**
 * Header - 应用头部组件
 *
 * 设计原则：
 * - 单一职责: 只负责展示头部 UI，业务逻辑通过 hooks 获取
 * - DRY: 导航配置和认证逻辑已提取到独立模块
 * - SOLID: 依赖抽象（hooks），而非具体实现
 */
export const Header: React.FC<HeaderProps> = ({ variant = 'default', onLoginClick, onRegisterClick }) => {
  const location = useLocation();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const user = useAppSelector(selectCurrentUser);
  const { handleLogin, handleRegister, handleLogout } = useAuth();

  // 真正的登录状态：token 存在且 user 信息已加载
  const isLoggedIn = isAuthenticated && user !== null;

  // 获取导航菜单配置
  const navItems = getNavItemsByRole(user?.role);
  const isTeacher = user?.role === 'teacher';

  const isDark = variant === 'dark' || variant === 'transparent';

  return (
    <header className={cn(
      "top-0 z-50 w-full border-b",
      animationCombos.buttonHover,
      variant === 'default' && "sticky border-surface-200/60 bg-white/80 backdrop-blur-md supports-backdrop-filter:bg-white/60 dark:border-surface-700/60 dark:bg-surface-900/80 dark:supports-backdrop-filter:bg-surface-900/60",
      variant === 'transparent' && "fixed border-transparent bg-transparent backdrop-blur-sm",
      variant === 'dark' && "sticky border-surface-800 bg-surface-950/80 backdrop-blur-md"
    )}>
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link to={isLoggedIn ? (isTeacher ? '/teacher/dashboard' : '/course/overview') : '/'} className="flex items-center space-x-2 group">
          <div className={cn(
            "h-8 w-8 rounded-lg flex items-center justify-center text-white shadow-lg",
            animationCombos.buttonHover,
            isTeacher
              ? "bg-linear-to-br from-emerald-500 to-teal-600 group-hover:shadow-emerald-500/30"
              : "bg-linear-to-br from-primary-500 to-secondary-600 group-hover:shadow-primary-500/30"
          )}>
            <span className="font-bold text-lg">M</span>
          </div>
          <span className={cn(
            "font-bold text-xl bg-clip-text text-transparent bg-linear-to-r",
            isDark ? "from-white to-surface-400" : "from-surface-900 to-surface-600 dark:from-white dark:to-surface-400"
          )}>
            高数智学
          </span>
          {/* 角色标识 */}
          {isLoggedIn && (
            <span className={cn(
              "ml-1 px-2 py-0.5 text-xs font-medium rounded-full",
              isTeacher
                ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-400"
                : "bg-primary-100 text-primary-700 dark:bg-primary-900/50 dark:text-primary-400"
            )}>
              {isTeacher ? '教师端' : '学生端'}
            </span>
          )}
        </Link>

        {/* Desktop Navigation - Only show when authenticated */}
        {isLoggedIn && (
          <nav className="hidden md:flex items-center space-x-1">
            {navItems.map((item) => {
              const isActive = location.pathname.startsWith(item.href);
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  to={item.href}
                  className={cn(
                    "relative flex items-center px-3 py-2 rounded-md text-sm font-medium",
                    animationCombos.navItemHover,
                    isActive
                      ? isTeacher
                        ? "text-emerald-600 bg-emerald-50 dark:text-emerald-400 dark:bg-emerald-950/50"
                        : "text-primary-600 bg-primary-50 dark:text-primary-400 dark:bg-primary-950/50"
                      : "text-surface-600 hover:text-primary-600 hover:bg-surface-50 dark:text-surface-400 dark:hover:text-primary-400 dark:hover:bg-surface-800"
                  )}
                >
                  <Icon className={cn("w-4 h-4 mr-2 transition-transform duration-200", isActive && "scale-110")} />
                  {item.label}
                  {/* 激活指示器 - 下划线 */}
                  <motion.span
                    className={cn(
                      "absolute bottom-0 left-0 right-0 h-0.5 rounded-full",
                      isTeacher
                        ? "bg-emerald-600 dark:bg-emerald-400"
                        : "bg-primary-600 dark:bg-primary-400"
                    )}
                    initial="inactive"
                    animate={isActive ? "active" : "inactive"}
                    variants={navIndicatorVariants}
                  />
                </Link>
              );
            })}
          </nav>
        )}

        {/* User Actions */}
        <div className="flex items-center space-x-3">
          {/* 主题切换按钮 */}
          <ThemeToggle variant="ghost" />

          {isLoggedIn ? (
            <div className="flex items-center space-x-3">
              <span className={cn("hidden sm:inline-block text-sm font-medium", isDark ? "text-surface-300" : "text-surface-700 dark:text-surface-300")}>
                你好，{user?.name || (isTeacher ? '老师' : '同学')}
              </span>
              <div className={cn(
                "h-9 w-9 rounded-full border shadow-sm flex items-center justify-center font-bold text-sm cursor-pointer transition-all group relative",
                isTeacher
                  ? "bg-linear-to-tr from-emerald-100 to-teal-100 dark:from-emerald-900 dark:to-teal-900 border-white dark:border-surface-700 text-emerald-700 dark:text-emerald-300 hover:ring-2 hover:ring-emerald-200 dark:hover:ring-emerald-700"
                  : "bg-linear-to-tr from-primary-100 to-secondary-100 dark:from-primary-900 dark:to-secondary-900 border-white dark:border-surface-700 text-primary-700 dark:text-primary-300 hover:ring-2 hover:ring-primary-200 dark:hover:ring-primary-700"
              )}>
                <User className="w-5 h-5" />
                {/* Quick Logout Dropdown (Simulated) */}
                <div className="absolute top-full right-0 mt-2 w-36 py-2 bg-white dark:bg-surface-800 rounded-lg shadow-lg border border-surface-100 dark:border-surface-700 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 transform origin-top-right">
                  {!isTeacher && (
                    <Link
                      to="/my-class"
                      className="w-full px-4 py-2 text-left text-sm text-surface-700 dark:text-surface-300 hover:bg-surface-50 dark:hover:bg-surface-700 flex items-center"
                    >
                      <Users className="w-4 h-4 mr-2" />
                      我的班级
                    </Link>
                  )}
                  <Link
                    to={isTeacher ? "/teacher/profile" : "/profile"}
                    className="w-full px-4 py-2 text-left text-sm text-surface-700 dark:text-surface-300 hover:bg-surface-50 dark:hover:bg-surface-700 flex items-center"
                  >
                    <User className="w-4 h-4 mr-2" />
                    个人中心
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="w-full px-4 py-2 text-left text-sm text-surface-700 dark:text-surface-300 hover:bg-surface-50 dark:hover:bg-surface-700 flex items-center"
                  >
                    <LogOut className="w-4 h-4 mr-2" />
                    退出登录
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center space-x-2">
              <Button variant="ghost" size="sm" onClick={() => handleLogin(onLoginClick)} className={cn(isDark && "text-surface-300 hover:bg-white/10 hover:text-white")}>登录</Button>
              <Button variant="primary" size="sm" onClick={() => handleRegister(onRegisterClick, onLoginClick)}>注册</Button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};