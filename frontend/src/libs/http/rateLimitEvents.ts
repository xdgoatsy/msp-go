/**
 * 限流事件
 *
 * 用于在 apiClient 拦截器（React 外部）与 UI 组件之间通信
 * 遵循 authEvents.ts 的事件模式
 */

export const RATE_LIMIT_EVENT = 'api:rate-limited';

interface RateLimitDetail {
  retryAfter: number;
  url?: string;
}

export function emitRateLimited(detail: RateLimitDetail): void {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent(RATE_LIMIT_EVENT, { detail }));
}

export function subscribeRateLimited(
  callback: (detail: RateLimitDetail) => void
): () => void {
  if (typeof window === 'undefined') return () => undefined;
  const handler = (e: Event) => callback((e as CustomEvent<RateLimitDetail>).detail);
  window.addEventListener(RATE_LIMIT_EVENT, handler);
  return () => window.removeEventListener(RATE_LIMIT_EVENT, handler);
}
