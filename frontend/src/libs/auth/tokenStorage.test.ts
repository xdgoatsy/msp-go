import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { authTokenStorage } from './tokenStorage';

const TOKEN_KEY = 'auth_token';

describe('authTokenStorage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    sessionStorage.clear();
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('stores reads and clears the session token', () => {
    authTokenStorage.set('access-token');

    expect(authTokenStorage.get()).toBe('access-token');

    authTokenStorage.clear();

    expect(authTokenStorage.get()).toBeNull();
  });

  it('removes legacy localStorage tokens when clearing', () => {
    localStorage.setItem(TOKEN_KEY, 'legacy-token');

    authTokenStorage.clear();

    expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
  });

  it('returns null when sessionStorage reads are blocked', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('storage blocked');
    });

    expect(authTokenStorage.get()).toBeNull();
  });

  it('does not throw when browser storage writes or removals fail', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('storage blocked');
    });
    expect(() => authTokenStorage.set('access-token')).not.toThrow();

    vi.restoreAllMocks();
    vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {
      throw new Error('storage blocked');
    });
    expect(() => authTokenStorage.clear()).not.toThrow();
  });
});
