import { useEffect, useRef } from 'react';
import { useAppSelector, useAppDispatch } from '@/store';
import { selectIsAuthenticated, selectCurrentUser, selectAuthLoadingState, fetchCurrentUser, logout } from '@/modules/auth/store/authSlice';
import { subscribeAuthExpired } from '@/libs/auth/authEvents';
import LoadingFallback from '@/components/LoadingFallback';

/**
 * 认证初始化组件
 * 在应用启动时检查 token 并恢复用户信息
 * 优化：有缓存用户时直接渲染，后台静默刷新用户信息
 */
export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const dispatch = useAppDispatch();
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const user = useAppSelector(selectCurrentUser);
  const loadingState = useAppSelector(selectAuthLoadingState);
  const fetchStarted = useRef(false);

  useEffect(() => {
    // 有 token 时始终后台刷新用户信息（无论是否有缓存）
    // 有缓存时不阻塞渲染，静默更新；无缓存时会触发 LoadingFallback
    if (isAuthenticated && !fetchStarted.current) {
      fetchStarted.current = true;
      dispatch(fetchCurrentUser());
    }
  }, [dispatch, isAuthenticated]);

  useEffect(() => {
    const unsubscribe = subscribeAuthExpired(() => {
      dispatch(logout());
    });

    return unsubscribe;
  }, [dispatch]);

  // 有 token 但没有用户信息（无缓存），且正在加载或即将加载，显示加载状态
  if (isAuthenticated && !user && loadingState !== 'error') {
    return <LoadingFallback />;
  }

  return <>{children}</>;
};
