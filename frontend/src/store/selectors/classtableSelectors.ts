/**
 * 课表 Selectors
 *
 * 简单字段访问使用普通函数，无需 createSelector
 */

import type { RootState } from '@/store';

// ========== 字段 Selectors ==========

export const selectClasstableData = (state: RootState) => state.classtable.data;

export const selectClasstableLoading = (state: RootState) => state.classtable.loading;

export const selectClasstableError = (state: RootState) => state.classtable.error;

export const selectClasstableIsFromCache = (state: RootState) => state.classtable.isFromCache;

export const selectClasstableLastSyncAt = (state: RootState) => state.classtable.lastSyncAt;

export const selectClasstableCachedAt = (state: RootState) => state.classtable.cachedAt;
