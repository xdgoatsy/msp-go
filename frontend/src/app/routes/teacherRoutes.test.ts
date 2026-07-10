import { describe, expect, it } from 'vitest';
import { teacherNavItems } from '@/modules/auth/constants/navigationConfig';
import { teacherRoutes } from './teacherRoutes';

describe('teacher route availability', () => {
  it('does not expose assignment management without backend support', () => {
    expect(teacherRoutes.map((route) => route.path)).not.toContain('/teacher/assignments');
    expect(teacherNavItems.map((item) => item.href)).not.toContain('/teacher/assignments');
  });
});
