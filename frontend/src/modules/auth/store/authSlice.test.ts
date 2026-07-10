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

describe('authSlice logout boundary', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  it('clears credentials and cached user data', async () => {
    const { default: reducer, logout, setCredentials } = await loadAuthSlice();
    let state = reducer(undefined, { type: '@@INIT' });

    state = reducer(state, setCredentials({
      token: 'access-token',
      user: { id: 'user-1', name: 'Alice', role: 'student' },
    }));
    state = reducer(state, logout());

    expect(state).toMatchObject({
      token: null,
      user: null,
      isAuthenticated: false,
      loadingState: 'idle',
      currentUserRequestId: null,
    });
    expect(sessionStorage.getItem(TOKEN_KEY)).toBeNull();
    expect(localStorage.getItem(USER_CACHE_KEY)).toBeNull();
  });

  it('ignores a current-user response that arrives after logout', async () => {
    const { default: reducer, fetchCurrentUser, logout, setCredentials } = await loadAuthSlice();
    let state = reducer(undefined, { type: '@@INIT' });

    state = reducer(state, setCredentials({
      token: 'access-token',
      user: { id: 'user-1', name: 'Alice', role: 'student' },
    }));
    state = reducer(state, fetchCurrentUser.pending('request-1', undefined));
    state = reducer(state, logout());
    state = reducer(state, fetchCurrentUser.fulfilled(
      { id: 'user-1', name: 'Alice', email: 'alice@example.com', role: 'student' },
      'request-1',
      undefined
    ));

    expect(state.token).toBeNull();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
  });

  it('ignores an old current-user failure after a new login', async () => {
    const { default: reducer, fetchCurrentUser, setCredentials } = await loadAuthSlice();
    let state = reducer(undefined, { type: '@@INIT' });

    state = reducer(state, setCredentials({
      token: 'old-token',
      user: { id: 'user-1', name: 'Alice', role: 'student' },
    }));
    state = reducer(state, fetchCurrentUser.pending('request-1', undefined));
    state = reducer(state, setCredentials({
      token: 'new-token',
      user: { id: 'user-2', name: 'Bob', role: 'teacher' },
    }));
    state = reducer(state, fetchCurrentUser.rejected(
      new Error('stale request failed'),
      'request-1',
      undefined
    ));

    expect(state.token).toBe('new-token');
    expect(state.user?.id).toBe('user-2');
    expect(state.isAuthenticated).toBe(true);
    expect(sessionStorage.getItem(TOKEN_KEY)).toBe('new-token');
  });
});
