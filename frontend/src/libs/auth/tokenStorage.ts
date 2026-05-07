const TOKEN_KEY = 'auth_token';

export const authTokenStorage = {
  get(): string | null {
    return sessionStorage.getItem(TOKEN_KEY);
  },

  set(token: string): void {
    sessionStorage.setItem(TOKEN_KEY, token);
  },

  clear(): void {
    sessionStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(TOKEN_KEY);
  },
};
