import { beforeEach, describe, expect, it, vi } from 'vitest';

const USER_CACHE_KEY = 'auth_user_cache';
const TOKEN_KEY = 'auth_token';

async function loadAuthSlice() {
  vi.resetModules();
  return import('./authSlice');
}

describe('authSlice cached user boundary', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  it('restores a valid cached user when a session token exists', async () => {
    sessionStorage.setItem(TOKEN_KEY, 'access-token');
    localStorage.setItem(
      USER_CACHE_KEY,
      JSON.stringify({
        id: 'user-1',
        name: 'Alice',
        email: 'alice@example.com',
        email_verified: true,
        role: 'teacher',
        avatar: '/uploads/images/avatar.png',
        ignored: 'extra',
      })
    );

    const { default: reducer } = await loadAuthSlice();
    const state = reducer(undefined, { type: '@@INIT' });

    expect(state.user).toEqual({
      id: 'user-1',
      name: 'Alice',
      email: 'alice@example.com',
      email_verified: true,
      role: 'teacher',
      avatar: '/uploads/images/avatar.png',
    });
    expect(state.isAuthenticated).toBe(true);
  });

  it('clears a cached user with a forged role', async () => {
    sessionStorage.setItem(TOKEN_KEY, 'access-token');
    localStorage.setItem(
      USER_CACHE_KEY,
      JSON.stringify({
        id: 'user-1',
        name: 'Mallory',
        role: 'superadmin',
      })
    );

    const { default: reducer } = await loadAuthSlice();
    const state = reducer(undefined, { type: '@@INIT' });

    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(true);
    expect(localStorage.getItem(USER_CACHE_KEY)).toBeNull();
  });

  it('clears malformed cached users', async () => {
    sessionStorage.setItem(TOKEN_KEY, 'access-token');
    localStorage.setItem(USER_CACHE_KEY, JSON.stringify({ id: 'user-1', role: 'student' }));

    const { default: reducer } = await loadAuthSlice();
    const state = reducer(undefined, { type: '@@INIT' });

    expect(state.user).toBeNull();
    expect(localStorage.getItem(USER_CACHE_KEY)).toBeNull();
  });
});
