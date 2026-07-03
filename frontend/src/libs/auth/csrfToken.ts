const CSRF_COOKIE_KEY = 'csrf_token';
const MAX_CSRF_TOKEN_LENGTH = 4096;

export function getCsrfToken(): string | null {
  if (typeof document === 'undefined') {
    return null;
  }
  const cookies = document.cookie ? document.cookie.split(';') : [];
  for (const cookie of cookies) {
    const [rawName, ...rawValue] = cookie.split('=');
    if (rawName.trim() === CSRF_COOKIE_KEY) {
      const encodedValue = rawValue.join('=');
      if (!encodedValue || encodedValue.length > MAX_CSRF_TOKEN_LENGTH) {
        return null;
      }
      try {
        const token = decodeURIComponent(encodedValue);
        return token.length <= MAX_CSRF_TOKEN_LENGTH ? token : null;
      } catch {
        return null;
      }
    }
  }
  return null;
}

export function csrfHeader(): Record<string, string> {
  const token = getCsrfToken();
  return token ? { 'X-CSRF-Token': token } : {};
}
