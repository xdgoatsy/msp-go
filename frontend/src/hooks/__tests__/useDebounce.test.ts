import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useDebounce } from '@/hooks/useDebounce';

describe('useDebounce', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('立即返回初始值', () => {
    const { result } = renderHook(() => useDebounce('初始值', 300));
    expect(result.current).toBe('初始值');
  });

  it('延迟后更新为新值', () => {
    const { result, rerender } = renderHook(
      ({ value, delay }: { value: string; delay: number }) => useDebounce(value, delay),
      { initialProps: { value: '初始', delay: 300 } }
    );

    // 更新 value
    rerender({ value: '更新后', delay: 300 });

    // 延迟未到，值不变
    expect(result.current).toBe('初始');

    // 推进时间超过延迟
    act(() => {
      vi.advanceTimersByTime(300);
    });

    expect(result.current).toBe('更新后');
  });

  it('快速连续变化时重置计时器（只取最后一次值）', () => {
    const { result, rerender } = renderHook(
      ({ value }: { value: string }) => useDebounce(value, 300),
      { initialProps: { value: '第一次' } }
    );

    rerender({ value: '第二次' });
    act(() => { vi.advanceTimersByTime(100); });

    rerender({ value: '第三次' });
    act(() => { vi.advanceTimersByTime(100); });

    rerender({ value: '最终值' });
    // 此时距最后一次变化只过了 0ms，值仍为初始
    expect(result.current).toBe('第一次');

    // 推进到最后一次变化的延迟结束
    act(() => {
      vi.advanceTimersByTime(300);
    });

    expect(result.current).toBe('最终值');
  });

  it('使用默认 500ms 延迟', () => {
    const { result, rerender } = renderHook(
      ({ value }: { value: string }) => useDebounce(value),
      { initialProps: { value: '原始' } }
    );

    rerender({ value: '新值' });

    // 499ms 时值未更新
    act(() => { vi.advanceTimersByTime(499); });
    expect(result.current).toBe('原始');

    // 500ms 时值更新
    act(() => { vi.advanceTimersByTime(1); });
    expect(result.current).toBe('新值');
  });

  it('处理数字类型', () => {
    const { result, rerender } = renderHook(
      ({ value }: { value: number }) => useDebounce(value, 200),
      { initialProps: { value: 0 } }
    );

    rerender({ value: 42 });
    act(() => { vi.advanceTimersByTime(200); });

    expect(result.current).toBe(42);
  });

  it('处理对象类型', () => {
    const obj1 = { name: '张三', score: 90 };
    const obj2 = { name: '李四', score: 95 };

    const { result, rerender } = renderHook(
      ({ value }: { value: typeof obj1 }) => useDebounce(value, 200),
      { initialProps: { value: obj1 } }
    );

    rerender({ value: obj2 });
    act(() => { vi.advanceTimersByTime(200); });

    expect(result.current).toEqual({ name: '李四', score: 95 });
  });

  it('延迟时间变化时重新计时', () => {
    const { result, rerender } = renderHook(
      ({ value, delay }: { value: string; delay: number }) => useDebounce(value, delay),
      { initialProps: { value: '原始', delay: 300 } }
    );

    // 改变 delay
    rerender({ value: '新值', delay: 600 });

    // 300ms 时不应更新（新 delay 是 600ms）
    act(() => { vi.advanceTimersByTime(300); });
    expect(result.current).toBe('原始');

    // 再过 300ms（共 600ms）才更新
    act(() => { vi.advanceTimersByTime(300); });
    expect(result.current).toBe('新值');
  });
});
