import { configureStore } from '@reduxjs/toolkit';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ClasstableData } from '@/modules/classroom/types/classtable';
import { xidianService } from '@/modules/xidian/services/xidianService';
import reducer, { clearClasstable, loadFromCache, syncClasstable } from './classtableSlice';

vi.mock('@/modules/xidian/services/xidianService', () => ({
  xidianService: {
    syncClasstable: vi.fn(),
  },
}));

const CACHE_KEY = 'xidian_classtable_cache';

const validClasstableData: ClasstableData = {
  semester_code: '2026-spring',
  term_start_day: '2026-02-23',
  semester_length: 20,
  class_detail: [
    {
      name: '高等数学',
      code: 'MATH101',
      number: '01',
    },
  ],
  time_arrangement: [
    {
      source: 'MATH101',
      index: 0,
      start: 1,
      stop: 2,
      day: 1,
      week_list: [true, false, 1],
      teacher: 'Teacher',
      classroom: 'A101',
    },
  ],
  not_arranged: [],
  class_changes: [],
};

function createStore() {
  return configureStore({
    reducer,
  });
}

describe('classtableSlice cache boundary', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it('loads a valid cache from localStorage', () => {
    localStorage.setItem(
      CACHE_KEY,
      JSON.stringify({
        data: validClasstableData,
        lastSyncAt: '2026-03-01T00:00:00Z',
        cachedAt: '2026-03-01T00:01:00Z',
      })
    );

    const state = reducer(undefined, loadFromCache());

    expect(state.data).toEqual(validClasstableData);
    expect(state.lastSyncAt).toBe('2026-03-01T00:00:00Z');
    expect(state.cachedAt).toBe('2026-03-01T00:01:00Z');
    expect(state.isFromCache).toBe(true);
  });

  it('clears malformed cached data', () => {
    localStorage.setItem(
      CACHE_KEY,
      JSON.stringify({
        data: {
          ...validClasstableData,
          time_arrangement: [{ ...validClasstableData.time_arrangement[0], day: 9 }],
        },
        lastSyncAt: '2026-03-01T00:00:00Z',
        cachedAt: '2026-03-01T00:01:00Z',
      })
    );

    const state = reducer(undefined, loadFromCache());

    expect(state.data).toBeNull();
    expect(state.isFromCache).toBe(false);
    expect(localStorage.getItem(CACHE_KEY)).toBeNull();
  });

  it('does not throw when clearing cache fails', () => {
    vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {
      throw new Error('storage blocked');
    });

    expect(() => reducer(undefined, clearClasstable())).not.toThrow();
  });

  it('rejects malformed sync responses before storing them', async () => {
    vi.mocked(xidianService.syncClasstable).mockResolvedValue({
      data: {
        ...validClasstableData,
        semester_length: 99,
      },
      fetched_at: '2026-03-01T00:00:00Z',
      is_cached: false,
    });
    const store = createStore();

    await store.dispatch(syncClasstable());

    expect(store.getState().data).toBeNull();
    expect(store.getState().error).toBe('课表数据格式异常');
    expect(localStorage.getItem(CACHE_KEY)).toBeNull();
  });
});
