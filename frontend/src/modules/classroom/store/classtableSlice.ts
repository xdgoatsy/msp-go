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

/**
 * 从 localStorage 加载缓存
 */
function loadCacheFromStorage(): ClasstableCache | null {
  try {
    const cached = localStorage.getItem(CACHE_KEY);
    if (!cached) return null;
    const parsed = JSON.parse(cached) as ClasstableCache;
    if (parsed.data && parsed.lastSyncAt && parsed.cachedAt) {
      return parsed;
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * 保存缓存到 localStorage
 */
function saveCacheToStorage(data: ClasstableData, lastSyncAt: string): void {
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
  localStorage.removeItem(CACHE_KEY);
}

/**
 * 从后端同步课表（强制刷新）
 */
export const syncClasstable = createAsyncThunk(
  'classtable/sync',
  async (_, { rejectWithValue }) => {
    try {
      const response = await xidianService.syncClasstable();
      const data = response.data as unknown as ClasstableData;
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
