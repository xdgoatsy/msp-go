import { beforeEach, describe, expect, it } from 'vitest';
import { csrfHeader, getCsrfToken } from './csrfToken';

function clearCookie(name: string) {
  document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
}

describe('csrfToken', () => {
  beforeEach(() => {
    clearCookie('csrf_token');
    clearCookie('other');
  });

  it('reads and decodes the csrf token cookie', () => {
    document.cookie = 'other=value; path=/';
    document.cookie = `csrf_token=${encodeURIComponent('token=value+space token')}; path=/`;

    expect(getCsrfToken()).toBe('token=value+space token');
    expect(csrfHeader()).toEqual({ 'X-CSRF-Token': 'token=value+space token' });
  });

  it('returns an empty header for malformed encoded cookies', () => {
    document.cookie = 'csrf_token=%E0%A4%A; path=/';

    expect(getCsrfToken()).toBeNull();
    expect(csrfHeader()).toEqual({});
  });

  it('returns an empty header for oversized cookies', () => {
    document.cookie = `csrf_token=${'a'.repeat(4097)}; path=/`;

    expect(getCsrfToken()).toBeNull();
    expect(csrfHeader()).toEqual({});
  });
});
