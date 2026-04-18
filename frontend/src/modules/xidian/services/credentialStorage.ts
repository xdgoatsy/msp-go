/**
 * 西电账号凭证安全存储工具
 * 使用 Base64 + 简单位移混淆，防止明文暴露
 */

const CREDENTIAL_KEY = 'xidian_cred';
const reverseString = (value: string) => value.split('').reverse().join('');

export interface XidianCredential {
  username: string;
  password: string;
}

/**
 * 保存凭证到 localStorage
 */
export function saveCredential(username: string, password: string): void {
  const data = JSON.stringify({ u: username, p: password });
  const encoded = reverseString(btoa(unescape(encodeURIComponent(data))));
  localStorage.setItem(CREDENTIAL_KEY, encoded);
}

/**
 * 从 localStorage 读取凭证
 */
export function loadCredential(): XidianCredential | null {
  const encoded = localStorage.getItem(CREDENTIAL_KEY);
  if (!encoded) return null;
  try {
    const data = decodeURIComponent(escape(atob(reverseString(encoded))));
    const { u, p } = JSON.parse(data);
    if (typeof u === 'string' && typeof p === 'string') {
      return { username: u, password: p };
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * 清除保存的凭证
 */
export function clearCredential(): void {
  localStorage.removeItem(CREDENTIAL_KEY);
}

/**
 * 检查是否有保存的凭证
 */
export function hasCredential(): boolean {
  return localStorage.getItem(CREDENTIAL_KEY) !== null;
}
