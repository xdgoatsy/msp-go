import { describe, it, expect } from 'vitest';
import {
  usernameSchema,
  emailSchema,
  passwordSchema,
  strongPasswordSchema,
  loginSchema,
  registerSchema,
  passwordChangeSchema,
  questionSchema,
  databaseSettingsSchema,
  securitySettingsSchema,
} from '@/libs/validation/schemas';

// ============================================
// usernameSchema 测试
// ============================================
describe('usernameSchema', () => {
  it('接受合法用户名（字母数字）', () => {
    expect(usernameSchema.safeParse('alice123').success).toBe(true);
  });

  it('接受含下划线的用户名', () => {
    expect(usernameSchema.safeParse('user_name').success).toBe(true);
  });

  it('接受中文用户名', () => {
    // 中文字符每个计 1 个字符，需至少 3 个
    expect(usernameSchema.safeParse('张三丰').success).toBe(true);
  });

  it('接受 3 个字符（最小长度）', () => {
    expect(usernameSchema.safeParse('abc').success).toBe(true);
  });

  it('接受 20 个字符（最大长度）', () => {
    expect(usernameSchema.safeParse('a'.repeat(20)).success).toBe(true);
  });

  it('拒绝少于 3 个字符', () => {
    expect(usernameSchema.safeParse('ab').success).toBe(false);
  });

  it('拒绝超过 20 个字符', () => {
    expect(usernameSchema.safeParse('a'.repeat(21)).success).toBe(false);
  });

  it('拒绝含特殊字符（@）', () => {
    expect(usernameSchema.safeParse('user@name').success).toBe(false);
  });

  it('拒绝含空格', () => {
    expect(usernameSchema.safeParse('user name').success).toBe(false);
  });
});

// ============================================
// emailSchema 测试
// ============================================
describe('emailSchema', () => {
  it('接受合法邮箱', () => {
    expect(emailSchema.safeParse('user@example.com').success).toBe(true);
  });

  it('接受带子域名的邮箱', () => {
    expect(emailSchema.safeParse('user@mail.example.com').success).toBe(true);
  });

  it('拒绝缺少 @ 的邮箱', () => {
    expect(emailSchema.safeParse('userexample.com').success).toBe(false);
  });

  it('拒绝缺少域名的邮箱', () => {
    expect(emailSchema.safeParse('user@').success).toBe(false);
  });

  it('拒绝空字符串', () => {
    expect(emailSchema.safeParse('').success).toBe(false);
  });
});

// ============================================
// passwordSchema 测试
// ============================================
describe('passwordSchema', () => {
  it('接受 6 个字符（最小长度）', () => {
    expect(passwordSchema.safeParse('abc123').success).toBe(true);
  });

  it('接受长密码', () => {
    expect(passwordSchema.safeParse('a'.repeat(50)).success).toBe(true);
  });

  it('拒绝少于 6 个字符', () => {
    expect(passwordSchema.safeParse('abc').success).toBe(false);
  });

  it('拒绝超过 50 个字符', () => {
    expect(passwordSchema.safeParse('a'.repeat(51)).success).toBe(false);
  });
});

// ============================================
// strongPasswordSchema 测试
// ============================================
describe('strongPasswordSchema', () => {
  it('接受包含大小写和数字的密码', () => {
    expect(strongPasswordSchema.safeParse('Abcdef1!').success).toBe(true);
  });

  it('拒绝少于 8 个字符', () => {
    expect(strongPasswordSchema.safeParse('Abc1').success).toBe(false);
  });

  it('拒绝缺少大写字母', () => {
    expect(strongPasswordSchema.safeParse('abcdef12').success).toBe(false);
  });

  it('拒绝缺少小写字母', () => {
    expect(strongPasswordSchema.safeParse('ABCDEF12').success).toBe(false);
  });

  it('拒绝缺少数字', () => {
    expect(strongPasswordSchema.safeParse('Abcdefgh').success).toBe(false);
  });
});

// ============================================
// loginSchema 测试
// ============================================
describe('loginSchema', () => {
  it('接受合法登录数据', () => {
    const result = loginSchema.safeParse({
      username: 'alice',
      password: 'secret',
      role: 'student',
    });
    expect(result.success).toBe(true);
  });

  it('接受 teacher 角色', () => {
    const result = loginSchema.safeParse({
      username: 'teacher01',
      password: 'pass123',
      role: 'teacher',
    });
    expect(result.success).toBe(true);
  });

  it('拒绝缺少 username', () => {
    const result = loginSchema.safeParse({
      password: 'secret',
      role: 'student',
    });
    expect(result.success).toBe(false);
  });

  it('拒绝缺少 password', () => {
    const result = loginSchema.safeParse({
      username: 'alice',
      role: 'student',
    });
    expect(result.success).toBe(false);
  });

  it('拒绝无效角色', () => {
    const result = loginSchema.safeParse({
      username: 'alice',
      password: 'secret',
      role: 'admin',
    });
    expect(result.success).toBe(false);
  });
});

// ============================================
// registerSchema 测试
// ============================================
describe('registerSchema', () => {
  it('接受合法注册数据', () => {
    const result = registerSchema.safeParse({
      username: 'newuser',
      email: 'new@example.com',
      password: 'pass123',
      confirmPassword: 'pass123',
      role: 'student',
    });
    expect(result.success).toBe(true);
  });

  it('拒绝密码不一致', () => {
    const result = registerSchema.safeParse({
      username: 'newuser',
      email: 'new@example.com',
      password: 'pass123',
      confirmPassword: 'different',
      role: 'student',
    });
    expect(result.success).toBe(false);
  });

  it('拒绝缺少 email', () => {
    const result = registerSchema.safeParse({
      username: 'newuser',
      password: 'pass123',
      confirmPassword: 'pass123',
      role: 'student',
    });
    expect(result.success).toBe(false);
  });
});

// ============================================
// passwordChangeSchema 测试
// ============================================
describe('passwordChangeSchema', () => {
  it('接受合法密码修改数据', () => {
    const result = passwordChangeSchema.safeParse({
      currentPassword: 'oldpass',
      newPassword: 'newpass1',
      confirmNewPassword: 'newpass1',
    });
    expect(result.success).toBe(true);
  });

  it('拒绝新密码与当前密码相同', () => {
    const result = passwordChangeSchema.safeParse({
      currentPassword: 'samepass',
      newPassword: 'samepass',
      confirmNewPassword: 'samepass',
    });
    expect(result.success).toBe(false);
  });

  it('拒绝两次新密码不一致', () => {
    const result = passwordChangeSchema.safeParse({
      currentPassword: 'oldpass',
      newPassword: 'newpass1',
      confirmNewPassword: 'newpass2',
    });
    expect(result.success).toBe(false);
  });

  it('拒绝缺少当前密码', () => {
    const result = passwordChangeSchema.safeParse({
      newPassword: 'newpass1',
      confirmNewPassword: 'newpass1',
    });
    expect(result.success).toBe(false);
  });
});

// ============================================
// questionSchema 测试
// ============================================
describe('questionSchema', () => {
  it('接受合法题目数据', () => {
    const result = questionSchema.safeParse({
      title: '求导数',
      content: '求 f(x) = x^2 的导数',
      difficulty: 'easy',
      type: 'short_answer',
      knowledgeNodeIds: ['node-1'],
    });
    expect(result.success).toBe(true);
  });

  it('接受带可选字段的题目', () => {
    const result = questionSchema.safeParse({
      title: '证明题',
      content: '证明...',
      difficulty: 'hard',
      type: 'proof',
      knowledgeNodeIds: ['node-1', 'node-2'],
      solution: '解题过程',
      hints: ['提示1', '提示2'],
    });
    expect(result.success).toBe(true);
  });

  it('拒绝缺少 title', () => {
    const result = questionSchema.safeParse({
      content: '内容',
      difficulty: 'easy',
      type: 'fill',
      knowledgeNodeIds: ['node-1'],
    });
    expect(result.success).toBe(false);
  });

  it('拒绝空 knowledgeNodeIds', () => {
    const result = questionSchema.safeParse({
      title: '题目',
      content: '内容',
      difficulty: 'medium',
      type: 'choice',
      knowledgeNodeIds: [],
    });
    expect(result.success).toBe(false);
  });

  it('拒绝无效 difficulty', () => {
    const result = questionSchema.safeParse({
      title: '题目',
      content: '内容',
      difficulty: 'very_hard',
      type: 'choice',
      knowledgeNodeIds: ['node-1'],
    });
    expect(result.success).toBe(false);
  });
});

// ============================================
// databaseSettingsSchema 测试
// ============================================
describe('databaseSettingsSchema', () => {
  it('接受合法数据库配置', () => {
    const result = databaseSettingsSchema.safeParse({
      host: 'localhost',
      port: 5432,
      database: 'mydb',
      username: 'admin',
    });
    expect(result.success).toBe(true);
  });

  it('接受字符串端口（coerce）', () => {
    const result = databaseSettingsSchema.safeParse({
      host: 'localhost',
      port: '3306',
      database: 'mydb',
      username: 'root',
    });
    expect(result.success).toBe(true);
  });

  it('拒绝端口 0', () => {
    const result = databaseSettingsSchema.safeParse({
      host: 'localhost',
      port: 0,
      database: 'mydb',
      username: 'admin',
    });
    expect(result.success).toBe(false);
  });

  it('拒绝端口超过 65535', () => {
    const result = databaseSettingsSchema.safeParse({
      host: 'localhost',
      port: 65536,
      database: 'mydb',
      username: 'admin',
    });
    expect(result.success).toBe(false);
  });

  it('拒绝缺少 host', () => {
    const result = databaseSettingsSchema.safeParse({
      port: 5432,
      database: 'mydb',
      username: 'admin',
    });
    expect(result.success).toBe(false);
  });
});

// ============================================
// securitySettingsSchema 测试
// ============================================
describe('securitySettingsSchema', () => {
  it('接受合法安全配置', () => {
    const result = securitySettingsSchema.safeParse({
      minPasswordLength: 8,
      passwordExpiryDays: 90,
      requireSpecialChar: false,
      sessionTimeoutMinutes: 30,
      maxConcurrentSessions: 3,
    });
    expect(result.success).toBe(true);
  });

  it('接受边界值 - 最小密码长度 6', () => {
    const result = securitySettingsSchema.safeParse({
      minPasswordLength: 6,
      passwordExpiryDays: 0,
      requireSpecialChar: true,
      sessionTimeoutMinutes: 5,
      maxConcurrentSessions: 1,
    });
    expect(result.success).toBe(true);
  });

  it('接受边界值 - 最大密码长度 32', () => {
    const result = securitySettingsSchema.safeParse({
      minPasswordLength: 32,
      passwordExpiryDays: 365,
      requireSpecialChar: false,
      sessionTimeoutMinutes: 1440,
      maxConcurrentSessions: 10,
    });
    expect(result.success).toBe(true);
  });

  it('拒绝 minPasswordLength 小于 6', () => {
    const result = securitySettingsSchema.safeParse({
      minPasswordLength: 5,
      passwordExpiryDays: 90,
      requireSpecialChar: false,
      sessionTimeoutMinutes: 30,
      maxConcurrentSessions: 3,
    });
    expect(result.success).toBe(false);
  });

  it('拒绝 sessionTimeoutMinutes 小于 5', () => {
    const result = securitySettingsSchema.safeParse({
      minPasswordLength: 8,
      passwordExpiryDays: 90,
      requireSpecialChar: false,
      sessionTimeoutMinutes: 4,
      maxConcurrentSessions: 3,
    });
    expect(result.success).toBe(false);
  });

  it('拒绝 maxConcurrentSessions 超过 10', () => {
    const result = securitySettingsSchema.safeParse({
      minPasswordLength: 8,
      passwordExpiryDays: 90,
      requireSpecialChar: false,
      sessionTimeoutMinutes: 30,
      maxConcurrentSessions: 11,
    });
    expect(result.success).toBe(false);
  });

  it('拒绝 passwordExpiryDays 超过 365', () => {
    const result = securitySettingsSchema.safeParse({
      minPasswordLength: 8,
      passwordExpiryDays: 366,
      requireSpecialChar: false,
      sessionTimeoutMinutes: 30,
      maxConcurrentSessions: 3,
    });
    expect(result.success).toBe(false);
  });
});
