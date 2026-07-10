import { beforeEach, describe, expect, it, vi } from 'vitest';
import { authService } from './authService';

const apiClientMock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
}));

vi.mock('@/libs/http/apiClient', () => ({
  apiClient: apiClientMock,
}));

vi.mock('@/libs/auth/tokenStorage', () => ({
  authTokenStorage: {
    clear: vi.fn(),
  },
}));

describe('authService account profile', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns the registered email from the current-user response', async () => {
    const account = {
      id: 'user-1',
      username: 'alice',
      email: 'alice@example.com',
      role: 'student' as const,
    };
    apiClientMock.get.mockResolvedValue({ data: account });

    await expect(authService.getCurrentUser()).resolves.toEqual(account);
    expect(apiClientMock.get).toHaveBeenCalledWith('/auth/me');
  });
});
