import { Suspense } from 'react';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import { store } from '@/store';
import { ToastProvider } from '@/components/ui/Toast';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { XidianReauthProvider } from '@/modules/xidian';
import ScrollToTop from '@/components/ScrollToTop';
import LoadingFallback from '@/components/LoadingFallback';
import { ThemeProvider } from './ThemeProvider';
import { AuthProvider } from './AuthProvider';
import { useRateLimitToast } from '@/hooks/useRateLimitToast';

/** 全局事件监听桥接（需要在 ToastProvider 内部） */
const GlobalEventListeners: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  useRateLimitToast();
  return <>{children}</>;
};

/**
 * 应用级 Provider 组合组件
 * 统一管理所有全局 Provider 的嵌套顺序
 *
 * 嵌套顺序（从外到内）：
 * ErrorBoundary → Redux Provider → Theme → Toast → Router → Xidian → Auth
 */
export const AppProviders: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <ErrorBoundary>
      <Provider store={store}>
        <ThemeProvider>
          <ToastProvider>
            <BrowserRouter>
              <GlobalEventListeners>
                <XidianReauthProvider>
                  <AuthProvider>
                    <ScrollToTop />
                    <Suspense fallback={<LoadingFallback />}>
                      {children}
                    </Suspense>
                  </AuthProvider>
                </XidianReauthProvider>
              </GlobalEventListeners>
            </BrowserRouter>
          </ToastProvider>
        </ThemeProvider>
      </Provider>
    </ErrorBoundary>
  );
};
