/**
 * 西电账号重新验证事件
 * 从 xidian 业务模块抽离到 libs/auth，避免 libs/http 反向依赖业务模块层
 */

export const XIDIAN_REAUTH_EVENT = 'xidian:reauth';

/**
 * 触发全局重新验证事件
 */
export function emitXidianReauth(): void {
  window.dispatchEvent(new CustomEvent(XIDIAN_REAUTH_EVENT));
}

/**
 * 订阅西电重新验证事件
 */
export function subscribeXidianReauth(callback: () => void): () => void {
  const handler = () => callback();
  window.addEventListener(XIDIAN_REAUTH_EVENT, handler);
  return () => window.removeEventListener(XIDIAN_REAUTH_EVENT, handler);
}
