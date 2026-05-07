const CSRF_COOKIE_KEY = 'csrf_token';

export function getCsrfToken(): string | null {
  if (typeof document === 'undefined') {
    return null;
  }
  const cookies = document.cookie ? document.cookie.split(';') : [];
  for (const cookie of cookies) {
    const [rawName, ...rawValue] = cookie.split('=');
    if (rawName.trim() === CSRF_COOKIE_KEY) {
      return decodeURIComponent(rawValue.join('='));
    }
  }
  return null;
}

export function csrfHeader(): Record<string, string> {
  const token = getCsrfToken();
  return token ? { 'X-CSRF-Token': token } : {};
}
