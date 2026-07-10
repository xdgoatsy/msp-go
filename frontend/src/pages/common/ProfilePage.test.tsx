import { MemoryRouter } from 'react-router-dom';
import { render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ProfilePage } from './ProfilePage';

const mocks = vi.hoisted(() => ({
  getBindingStatus: vi.fn(),
  user: {
    id: 'user-1',
    name: 'Alice',
    email: 'alice@example.com',
    role: 'student' as const,
  },
}));

vi.mock('@/store', () => ({
  useAppSelector: () => mocks.user,
}));

vi.mock('@/modules/auth/store/authSlice', () => ({
  selectCurrentUser: vi.fn(),
}));

vi.mock('@/modules/xidian/services/xidianService', () => ({
  xidianService: {
    getBindingStatus: mocks.getBindingStatus,
  },
}));

vi.mock('@/modules/xidian', () => ({
  clearCredential: vi.fn(),
}));

describe('ProfilePage account boundaries', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.getBindingStatus.mockResolvedValue({ is_bound: false });
  });

  it('shows the registered email without unsupported binding controls', async () => {
    render(
      <MemoryRouter>
        <ProfilePage />
      </MemoryRouter>,
    );

    await waitFor(() => expect(mocks.getBindingStatus).toHaveBeenCalledTimes(1));
    const emailSection = screen.getByLabelText('注册邮箱');
    expect(within(emailSection).getByText('alice@example.com')).toBeInTheDocument();
    expect(within(emailSection).queryByRole('button')).not.toBeInTheDocument();
    expect(screen.queryByText('未验证')).not.toBeInTheDocument();
    expect(screen.queryByText('手机号码')).not.toBeInTheDocument();
  });
});
