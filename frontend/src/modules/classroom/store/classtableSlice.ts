import { createSlice, createAsyncThunk, type PayloadAction } from '@reduxjs/toolkit';
import { xidianService } from '@/modules/xidian/services/xidianService';
import type { ClasstableData } from '@/modules/classroom/types/classtable';

const CACHE_KEY = 'xidian_classtable_cache';

interface ClasstableCache {
  data: ClasstableData;
  lastSyncAt: string;
  cachedAt: string;
}

interface ClasstableState {
  data: ClasstableData | null;
  loading: boolean;
  error: string | null;
  lastSyncAt: string | null;
  cachedAt: string | null;
  isFromCache: boolean;
}

const initialState: ClasstableState = {
  data: null,
  loading: false,
  error: null,
  lastSyncAt: null,
  cachedAt: null,
  isFromCache: false,
};

const MAX_CACHE_ARRAY_ITEMS = 2000;
const MAX_WEEK_LIST_ITEMS = 64;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isString(value: unknown): value is string {
  return typeof value === 'string';
}

function isIntegerInRange(value: unknown, min: number, max: number): value is number {
  return typeof value === 'number' && Number.isInteger(value) && value >= min && value <= max;
}

function isBoundedArray(value: unknown, maxItems: number): value is unknown[] {
  return Array.isArray(value) && value.length <= maxItems;
}

function isWeekFlag(value: unknown): boolean {
  return typeof value === 'boolean' || Number.isInteger(value);
}

function isClassDetail(value: unknown): boolean {
  return isRecord(value) && isString(value.name) && isString(value.code) && isString(value.number);
}

function isTimeArrangement(value: unknown): boolean {
  if (!isRecord(value)) return false;
  if (!isString(value.source)) return false;
  if (!isIntegerInRange(value.index, 0, MAX_CACHE_ARRAY_ITEMS)) return false;
  if (!isIntegerInRange(value.start, 1, 20)) return false;
  if (!isIntegerInRange(value.stop, 1, 20) || value.stop < value.start) return false;
  if (!isIntegerInRange(value.day, 1, 7)) return false;
  if (!isBoundedArray(value.week_list, MAX_WEEK_LIST_ITEMS) || !value.week_list.every(isWeekFlag)) return false;
  return isString(value.teacher) && isString(value.classroom);
}

function isClasstableData(value: unknown): value is ClasstableData {
  if (!isRecord(value)) return false;
  if (!isString(value.semester_code) || !isString(value.term_start_day)) return false;
  if (!isIntegerInRange(value.semester_length, 1, 60)) return false;
  if (!isBoundedArray(value.class_detail, MAX_CACHE_ARRAY_ITEMS) || !value.class_detail.every(isClassDetail)) return false;
  if (!isBoundedArray(value.time_arrangement, MAX_CACHE_ARRAY_ITEMS) || !value.time_arrangement.every(isTimeArrangement)) return false;
  if (!isBoundedArray(value.not_arranged, MAX_CACHE_ARRAY_ITEMS)) return false;
  if (!isBoundedArray(value.class_changes, MAX_CACHE_ARRAY_ITEMS)) return false;
  return true;
}

function isClasstableCache(value: unknown): value is ClasstableCache {
  return isRecord(value) && isClasstableData(value.data) && isString(value.lastSyncAt) && isString(value.cachedAt);
}

/**
 * 从 localStorage 加载缓存
 */
function loadCacheFromStorage(): ClasstableCache | null {
  try {
    const cached = localStorage.getItem(CACHE_KEY);
    if (!cached) return null;
    const parsed = JSON.parse(cached);
    if (isClasstableCache(parsed)) {
      return parsed;
    }
    clearClasstableCache();
    return null;
  } catch {
    clearClasstableCache();
    return null;
  }
}

/**
 * 保存缓存到 localStorage
 */
function saveCacheToStorage(data: ClasstableData, lastSyncAt: string): void {
  if (!isClasstableData(data) || !isString(lastSyncAt)) {
    clearClasstableCache();
    return;
  }
  const cache: ClasstableCache = {
    data,
    lastSyncAt,
    cachedAt: new Date().toISOString(),
  };
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(cache));
  } catch {
    // 存储失败时静默处理
  }
}

/**
 * 清除 localStorage 缓存
 */
export function clearClasstableCache(): void {
  try {
    localStorage.removeItem(CACHE_KEY);
  } catch {
    // 存储不可用时忽略
  }
}

/**
 * 从后端同步课表（强制刷新）
 */
export const syncClasstable = createAsyncThunk(
  'classtable/sync',
  async (_, { rejectWithValue }) => {
    try {
      const response = await xidianService.syncClasstable();
      const data = response.data;
      if (!isClasstableData(data)) {
        clearClasstableCache();
        return rejectWithValue('课表数据格式异常');
      }
      const fetchedAt = response.fetched_at;
      const isCached = response.is_cached ?? false;

      // 同步成功后保存到缓存
      saveCacheToStorage(data, fetchedAt);

      return {
        data,
        fetchedAt,
        isCached,
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : '获取课表失败';
      return rejectWithValue(message);
    }
  }
);

/**
 * 兼容旧的 fetchClasstable（等同于 syncClasstable）
 */
export const fetchClasstable = syncClasstable;

const classtableSlice = createSlice({
  name: 'classtable',
  initialState,
  reducers: {
    /**
     * 从本地缓存加载课表数据
     */
    loadFromCache: (state) => {
      const cached = loadCacheFromStorage();
      if (cached) {
        state.data = cached.data;
        state.lastSyncAt = cached.lastSyncAt;
        state.cachedAt = cached.cachedAt;
        state.isFromCache = true;
        state.error = null;
      }
    },
    /**
     * 清除课表数据和缓存
     */
    clearClasstable: (state) => {
      state.data = null;
      state.error = null;
      state.lastSyncAt = null;
      state.cachedAt = null;
      state.isFromCache = false;
      clearClasstableCache();
    },
    /**
     * 设置错误信息
     */
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(syncClasstable.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(syncClasstable.fulfilled, (state, action) => {
        state.loading = false;
        state.data = action.payload.data;
        state.lastSyncAt = action.payload.fetchedAt;
        state.cachedAt = new Date().toISOString();
        state.isFromCache = action.payload.isCached;
      })
      .addCase(syncClasstable.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });
  },
});

export const { loadFromCache, clearClasstable, setError } = classtableSlice.actions;

export default classtableSlice.reducer;
