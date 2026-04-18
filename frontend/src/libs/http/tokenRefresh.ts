/**
 * Token 刷新服务
 *
 * 处理 access token 刷新逻辑，包括并发请求的竞态处理
 */

import axios from 'axios';
import { logger } from '../utils/logger';

const refreshLogger = logger.createContextLogger('TokenRefresh');

// 刷新状态
let isRefreshing = false;
let refreshSubscribers: Array<(token: string) => void> = [];

/**
 * 订阅 token 刷新完成事件
 */
function subscribeTokenRefresh(callback: (token: string) => void): void {
  refreshSubscribers.push(callback);
}

/**
 * 通知所有订阅者刷新完成
 */
function onTokenRefreshed(token: string): void {
  refreshSubscribers.forEach((callback) => callback(token));
  refreshSubscribers = [];
}

/**
 * 通知所有订阅者刷新失败
 */
function onRefreshFailed(): void {
  refreshSubscribers = [];
}

/**
 * 刷新 access token
 *
 * @returns 新的 access token，如果刷新失败返回 null
 */
export async function refreshAccessToken(): Promise<string | null> {
  try {
    // 使用独立的 axios 实例避免触发拦截器循环
    const response = await axios.post<{ access_token: string }>(
      '/api/v1/auth/refresh',
      {},
      {
        withCredentials: true, // 发送 HttpOnly Cookie
      }
    );

    const newToken = response.data.access_token;
    refreshLogger.info('Token 刷新成功');
    return newToken;
  } catch (error) {
    refreshLogger.error('Token 刷新失败', error);
    return null;
  }
}

/**
 * 处理 401 错误，尝试刷新 token
 *
 * @param retryRequest 重试原始请求的函数
 * @returns 是否成功刷新并重试
 */
export async function handle401Error<T>(
  retryRequest: (newToken: string) => Promise<T>
): Promise<{ success: boolean; data?: T }> {
  // 如果已经在刷新中，等待刷新完成
  if (isRefreshing) {
    return new Promise((resolve) => {
      subscribeTokenRefresh(async (newToken) => {
        try {
          const data = await retryRequest(newToken);
          resolve({ success: true, data });
        } catch {
          resolve({ success: false });
        }
      });
    });
  }

  // 开始刷新
  isRefreshing = true;

  try {
    const newToken = await refreshAccessToken();

    if (newToken) {
      // 更新本地存储
      localStorage.setItem('auth_token', newToken);

      // 通知所有等待的请求
      onTokenRefreshed(newToken);

      // 重试原始请求
      const data = await retryRequest(newToken);
      return { success: true, data };
    } else {
      // 刷新失败
      onRefreshFailed();
      return { success: false };
    }
  } finally {
    isRefreshing = false;
  }
}

/**
 * 检查是否正在刷新 token
 */
export function isTokenRefreshing(): boolean {
  return isRefreshing;
}
