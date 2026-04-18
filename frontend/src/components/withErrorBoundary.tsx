import React, { type ReactNode } from 'react';
import { ErrorBoundary } from './ErrorBoundary';

/**
 * 用于函数组件的错误边界 HOC 包装器
 *
 * 将此 HOC 分离到单独文件以支持 React Fast Refresh
 * (Fast Refresh 要求文件只导出组件)
 */
export function withErrorBoundary<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  fallback?: ReactNode
): React.FC<P> {
  const WithErrorBoundary: React.FC<P> = (props) => (
    <ErrorBoundary fallback={fallback}>
      <WrappedComponent {...props} />
    </ErrorBoundary>
  );

  WithErrorBoundary.displayName = `WithErrorBoundary(${WrappedComponent.displayName || WrappedComponent.name || 'Component'})`;

  return WithErrorBoundary;
}

export default withErrorBoundary;
