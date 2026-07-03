import { beforeEach, describe, expect, it, vi } from 'vitest';

async function loadUiSlice() {
  vi.resetModules();
  return import('./uiSlice');
}

function setSystemTheme(matchesDark: boolean): void {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: vi.fn().mockReturnValue({ matches: matchesDark }),
  });
}

describe('uiSlice theme persistence boundary', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
    setSystemTheme(false);
  });

  it('restores a valid stored theme', async () => {
    localStorage.setItem('theme', 'dark');

    const { default: reducer } = await loadUiSlice();
    const state = reducer(undefined, { type: '@@INIT' });

    expect(state.theme).toBe('dark');
  });

  it('clears invalid stored themes and falls back to system preference', async () => {
    localStorage.setItem('theme', 'solarized');
    setSystemTheme(true);

    const { default: reducer } = await loadUiSlice();
    const state = reducer(undefined, { type: '@@INIT' });

    expect(state.theme).toBe('dark');
    expect(localStorage.getItem('theme')).toBeNull();
  });

  it('falls back to light when localStorage reads fail', async () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('storage blocked');
    });

    const { default: reducer } = await loadUiSlice();
    const state = reducer(undefined, { type: '@@INIT' });

    expect(state.theme).toBe('light');
  });

  it('does not throw when persisting a theme fails', async () => {
    const { default: reducer, toggleTheme } = await loadUiSlice();
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('storage blocked');
    });

    expect(() => reducer(undefined, toggleTheme())).not.toThrow();
  });
});
