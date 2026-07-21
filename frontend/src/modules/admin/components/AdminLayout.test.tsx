import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AdminLayout } from './AdminLayout';

const mocks = vi.hoisted(() => ({
  logout: vi.fn(),
}));

vi.mock('@/store', () => ({
  useAppSelector: () => ({ name: 'Admin', email: 'admin@example.com' }),
}));

vi.mock('@/modules/auth/store/authSlice', () => ({
  selectCurrentUser: vi.fn(),
}));

vi.mock('@/modules/auth/hooks/useAuth', () => ({
  useAuth: () => ({ handleLogout: mocks.logout, isLoggingOut: false }),
}));

vi.mock('@/modules/password-reset/services/passwordResetService', () => ({
  passwordResetService: {
    getPendingCount: vi.fn().mockResolvedValue({ pending_count: 0 }),
  },
}));

vi.mock('@/hooks/useSerialPolling', () => ({
  useSerialPolling: vi.fn(),
}));

vi.mock('@/components/ui/ThemeToggle', () => ({
  ThemeToggle: () => <button type="button">切换主题</button>,
}));

describe('AdminLayout', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 390 });
  });

  it('uses a dismissible navigation drawer on small screens', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={['/admin/risk-control']}>
        <AdminLayout><div>页面内容</div></AdminLayout>
      </MemoryRouter>
    );

    const sidebar = screen.getByRole('complementary', { hidden: true });
    expect(sidebar).toHaveClass('-translate-x-full');
    expect(sidebar).toHaveAttribute('aria-hidden', 'true');
    expect(sidebar).toHaveAttribute('inert');
    expect(screen.getByText('页面内容')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '打开管理导航' }));
    expect(sidebar).toHaveClass('translate-x-0');
    expect(sidebar).toHaveAttribute('aria-hidden', 'false');
    expect(sidebar).not.toHaveAttribute('inert');
    expect(screen.getByRole('button', { name: '风控中心' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '关闭管理导航' }));
    expect(sidebar).toHaveClass('-translate-x-full');

    await user.click(screen.getByRole('button', { name: '打开管理导航' }));
    await user.click(screen.getByRole('button', { name: '风控中心' }));
    expect(sidebar).toHaveClass('-translate-x-full');
  });
});
