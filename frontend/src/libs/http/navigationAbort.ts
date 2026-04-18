/**
 * 导航级请求取消管理器
 *
 * 当用户在页面间快速切换时，自动取消上一个页面的未完成请求，
 * 避免无效请求消耗服务端限流配额。
 *
 * 设计原则：
 * - KISS: 基于 AbortController 的简单实现
 * - 单一职责: 只负责按页面维度管理请求取消
 */

class NavigationAbortManager {
  // 当前活跃的 AbortController（按页面路径）
  private controllers = new Map<string, AbortController>();

  /**
   * 获取当前页面的 AbortSignal
   *
   * 如果该页面已有未完成的 controller，先取消它再创建新的
   *
   * @param pageKey - 页面标识（通常是路由路径）
   * @returns AbortSignal 用于传递给 axios 请求
   *
   * @example
   * ```ts
   * const signal = navigationAbort.getSignal('/analytics');
   * apiClient.get('/progress/overview', { signal });
   * ```
   */
  getSignal(pageKey: string): AbortSignal {
    // 取消该页面之前的请求
    this.abort(pageKey);

    const controller = new AbortController();
    this.controllers.set(pageKey, controller);
    return controller.signal;
  }

  /**
   * 取消指定页面的所有未完成请求
   */
  abort(pageKey: string): void {
    const existing = this.controllers.get(pageKey);
    if (existing) {
      existing.abort();
      this.controllers.delete(pageKey);
    }
  }

  /**
   * 取消所有页面的未完成请求
   */
  abortAll(): void {
    for (const [key, controller] of this.controllers) {
      controller.abort();
      this.controllers.delete(key);
    }
  }
}

/**
 * 全局导航请求取消管理器实例
 */
export const navigationAbort = new NavigationAbortManager();
