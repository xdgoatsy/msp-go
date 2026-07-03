import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useLocalStorage } from '@/hooks/useLocalStorage';

describe('useLocalStorage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
    vi.spyOn(console, 'debug').mockImplementation(() => undefined);
    vi.spyOn(console, 'warn').mockImplementation(() => undefined);
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns the initial value when no cached value exists', () => {
    const { result } = renderHook(() => useLocalStorage('counter', 0));

    expect(result.current[0]).toBe(0);
  });

  it('restores stored JSON and persists updates', () => {
    localStorage.setItem('counter', '1');

    const { result } = renderHook(() => useLocalStorage('counter', 0));

    expect(result.current[0]).toBe(1);

    act(() => {
      result.current[1]((value) => value + 1);
    });

    expect(result.current[0]).toBe(2);
    expect(localStorage.getItem('counter')).toBe('2');
  });

  it('clears malformed cached JSON and falls back to the initial value', () => {
    localStorage.setItem('settings', '{bad json');

    const { result } = renderHook(() => useLocalStorage('settings', { theme: 'light' }));

    expect(result.current[0]).toEqual({ theme: 'light' });
    expect(localStorage.getItem('settings')).toBeNull();
  });

  it('clears cached values rejected by the optional validator', () => {
    localStorage.setItem('settings', JSON.stringify({ theme: 'solarized' }));

    const { result } = renderHook(() =>
      useLocalStorage(
        'settings',
        { theme: 'light' },
        {
          validate: (value): value is { theme: 'light' | 'dark' } =>
            typeof value === 'object' &&
            value !== null &&
            'theme' in value &&
            (value.theme === 'light' || value.theme === 'dark'),
        }
      )
    );

    expect(result.current[0]).toEqual({ theme: 'light' });
    expect(localStorage.getItem('settings')).toBeNull();
  });

  it('does not throw when browser storage reads are blocked', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('storage blocked');
    });

    const { result } = renderHook(() => useLocalStorage('auth_token', 'fallback-token'));

    expect(result.current[0]).toBe('fallback-token');
  });

  it('keeps state usable when browser storage writes or removals fail', () => {
    const { result } = renderHook(() => useLocalStorage('auth_token', 'initial-token'));

    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('storage blocked');
    });

    expect(() => {
      act(() => {
        result.current[1]('next-token');
      });
    }).not.toThrow();
    expect(result.current[0]).toBe('next-token');

    setItemSpy.mockRestore();
    vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {
      throw new Error('storage blocked');
    });

    expect(() => {
      act(() => {
        result.current[2]();
      });
    }).not.toThrow();
    expect(result.current[0]).toBe('initial-token');
  });
});
