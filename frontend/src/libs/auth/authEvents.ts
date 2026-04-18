export const AUTH_EXPIRED_EVENT = 'auth:expired';

export function emitAuthExpired(): void {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
}

export function subscribeAuthExpired(callback: () => void): () => void {
  if (typeof window === 'undefined') return () => undefined;
  const handler = () => callback();
  window.addEventListener(AUTH_EXPIRED_EVENT, handler);
  return () => window.removeEventListener(AUTH_EXPIRED_EVENT, handler);
}
