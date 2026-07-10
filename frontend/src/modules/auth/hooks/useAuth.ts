import { useCallback, useRef, useState } from 'react';
import { useDispatch } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { logout } from '@/modules/auth/store/authSlice';
import { authService } from '@/modules/auth/services/authService';

/**
 * useAuth Hook
 *
 * 封装认证相关的业务逻辑
 *
 * 设计原则：
 * - 单一职责: 只处理认证相关逻辑
 * - DRY: 避免在多个组件中重复认证逻辑
 */
export const useAuth = (logoutRedirect = '/welcome') => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const logoutInProgress = useRef(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  /**
   * 处理登录
   *
   * @param onLoginClick - 可选的自定义登录回调
   */
  const handleLogin = useCallback((onLoginClick?: () => void) => {
    if (onLoginClick) {
      onLoginClick();
    }
  }, []);

  /**
   * 处理注册
   *
   * @param onRegisterClick - 可选的自定义注册回调
   * @param onLoginClick - 可选的登录回调（作为注册的回退）
   */
  const handleRegister = useCallback((onRegisterClick?: () => void, onLoginClick?: () => void) => {
    if (onRegisterClick) {
      onRegisterClick();
    } else if (onLoginClick) {
      // 如果没有专门的注册回调，使用登录回调
      onLoginClick();
    }
  }, []);

  /**
   * 处理登出
   */
  const handleLogout = useCallback(async () => {
    if (logoutInProgress.current) return;

    logoutInProgress.current = true;
    setIsLoggingOut(true);

    try {
      // 先撤销服务端 refresh session 并清除 HttpOnly Cookie，再落定本地退出状态。
      await authService.logout();
    } catch {
      // 服务端不可用时仍必须完成本地退出，避免界面滞留在认证态。
    } finally {
      dispatch(logout());
      logoutInProgress.current = false;
      setIsLoggingOut(false);
      navigate(logoutRedirect, { replace: true });
    }
  }, [dispatch, logoutRedirect, navigate]);

  return {
    handleLogin,
    handleRegister,
    handleLogout,
    isLoggingOut,
  };
};
