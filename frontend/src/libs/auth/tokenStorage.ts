const TOKEN_KEY = 'auth_token';

export const authTokenStorage = {
  get(): string | null {
    try {
      return sessionStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },

  set(token: string): void {
    try {
      sessionStorage.setItem(TOKEN_KEY, token);
    } catch {
      // 存储不可用时仅保留内存态认证
    }
  },

  clear(): void {
    try {
      sessionStorage.removeItem(TOKEN_KEY);
    } catch {
      // 存储不可用时忽略
    }
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch {
      // 清理旧 localStorage token 失败时忽略
    }
  },
};
