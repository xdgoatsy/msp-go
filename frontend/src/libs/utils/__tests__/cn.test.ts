import { describe, it, expect } from 'vitest';
import { cn } from '@/libs/utils/cn';

describe('cn 工具函数', () => {
  it('合并多个类名', () => {
    expect(cn('foo', 'bar')).toBe('foo bar');
  });

  it('处理条件类名 - 真值条件', () => {
    const isActive = true;

    expect(cn('base', isActive && 'active')).toBe('base active');
  });

  it('处理条件类名 - 假值条件', () => {
    const isActive = false;

    expect(cn('base', isActive && 'active')).toBe('base');
  });

  it('解决 Tailwind 冲突 - p-4 vs p-2 后者优先', () => {
    expect(cn('p-4', 'p-2')).toBe('p-2');
  });

  it('解决 Tailwind 冲突 - text-red-500 vs text-blue-500', () => {
    expect(cn('text-red-500', 'text-blue-500')).toBe('text-blue-500');
  });

  it('处理空字符串输入', () => {
    expect(cn('')).toBe('');
  });

  it('处理 undefined 输入', () => {
    expect(cn(undefined)).toBe('');
  });

  it('处理 null 输入', () => {
    expect(cn(null)).toBe('');
  });

  it('处理无参数调用', () => {
    expect(cn()).toBe('');
  });

  it('处理数组输入', () => {
    expect(cn(['foo', 'bar'])).toBe('foo bar');
  });

  it('处理对象输入 - 真值键', () => {
    expect(cn({ foo: true, bar: false })).toBe('foo');
  });

  it('处理对象输入 - 多个真值键', () => {
    expect(cn({ foo: true, bar: true })).toBe('foo bar');
  });

  it('混合字符串、数组和对象', () => {
    const result = cn('base', ['extra'], { active: true, disabled: false });
    expect(result).toBe('base extra active');
  });

  it('混合 undefined 和有效类名', () => {
    expect(cn('foo', undefined, 'bar')).toBe('foo bar');
  });
});
