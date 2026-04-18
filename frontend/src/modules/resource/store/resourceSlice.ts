/**
 * 资源状态管理
 *
 * 管理资源中心的状态：资源列表、统计、收藏、筛选等
 */

import { createSlice, createAsyncThunk, type PayloadAction } from '@reduxjs/toolkit';
import { resourceService } from '@/modules/resource/services/resourceService';
import type {
  Resource,
  ResourceFilter,
  ResourceStats,
  ResourceCreateRequest,
  ResourceUpdateRequest,
} from '@/modules/resource/types/resource';

// =============================================================================
// 状态类型
// =============================================================================

interface ResourceState {
  // 资源列表
  resources: Resource[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;

  // 统计数据
  stats: ResourceStats | null;

  // 筛选条件
  filter: ResourceFilter;

  // 加载状态
  loading: boolean;
  statsLoading: boolean;
  actionLoading: boolean;

  // 错误信息
  error: string | null;
}

// =============================================================================
// 初始状态
// =============================================================================

const initialState: ResourceState = {
  resources: [],
  total: 0,
  page: 1,
  pageSize: 20,
  hasMore: false,

  stats: null,

  filter: {},

  loading: false,
  statsLoading: false,
  actionLoading: false,

  error: null,
};

// =============================================================================
// 异步 Thunks
// =============================================================================

/**
 * 获取资源列表
 */
export const fetchResources = createAsyncThunk(
  'resource/fetchResources',
  async (filter: ResourceFilter | undefined, { rejectWithValue }) => {
    try {
      const response = await resourceService.getResources(filter);
      return { response, filter };
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '获取资源列表失败';
      return rejectWithValue(message);
    }
  }
);

/**
 * 获取资源统计
 */
export const fetchResourceStats = createAsyncThunk(
  'resource/fetchStats',
  async (_, { rejectWithValue }) => {
    try {
      return await resourceService.getStats();
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '获取资源统计失败';
      return rejectWithValue(message);
    }
  }
);

/**
 * 切换收藏状态
 */
export const toggleFavorite = createAsyncThunk(
  'resource/toggleFavorite',
  async (resourceId: string, { rejectWithValue }) => {
    try {
      const response = await resourceService.toggleFavorite(resourceId);
      return response;
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '操作失败';
      return rejectWithValue(message);
    }
  }
);

/**
 * 创建资源
 */
export const createResource = createAsyncThunk(
  'resource/create',
  async (data: ResourceCreateRequest, { rejectWithValue }) => {
    try {
      return await resourceService.createResource(data);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '创建资源失败';
      return rejectWithValue(message);
    }
  }
);

/**
 * 更新资源
 */
export const updateResource = createAsyncThunk(
  'resource/update',
  async ({ id, data }: { id: string; data: ResourceUpdateRequest }, { rejectWithValue }) => {
    try {
      return await resourceService.updateResource(id, data);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '更新资源失败';
      return rejectWithValue(message);
    }
  }
);

/**
 * 删除资源
 */
export const deleteResource = createAsyncThunk(
  'resource/delete',
  async (id: string, { rejectWithValue }) => {
    try {
      await resourceService.deleteResource(id);
      return id;
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '删除资源失败';
      return rejectWithValue(message);
    }
  }
);

// =============================================================================
// Slice
// =============================================================================

const resourceSlice = createSlice({
  name: 'resource',
  initialState,
  reducers: {
    /**
     * 设置筛选条件
     */
    setFilter: (state, action: PayloadAction<ResourceFilter>) => {
      state.filter = action.payload;
    },

    /**
     * 重置筛选条件
     */
    resetFilter: (state) => {
      state.filter = {};
    },

    /**
     * 清除错误
     */
    clearError: (state) => {
      state.error = null;
    },

    /**
     * 重置状态
     */
    resetState: () => initialState,
  },
  extraReducers: (builder) => {
    // 获取资源列表
    builder
      .addCase(fetchResources.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchResources.fulfilled, (state, action) => {
        state.loading = false;
        state.resources = action.payload.response.items;
        state.total = action.payload.response.total;
        state.page = action.payload.response.page;
        state.pageSize = action.payload.response.page_size;
        state.hasMore = action.payload.response.has_more;
        if (action.payload.filter) {
          state.filter = action.payload.filter;
        }
      })
      .addCase(fetchResources.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });

    // 获取资源统计
    builder
      .addCase(fetchResourceStats.pending, (state) => {
        state.statsLoading = true;
      })
      .addCase(fetchResourceStats.fulfilled, (state, action) => {
        state.statsLoading = false;
        state.stats = action.payload;
      })
      .addCase(fetchResourceStats.rejected, (state, action) => {
        state.statsLoading = false;
        state.error = action.payload as string;
      });

    // 切换收藏
    builder
      .addCase(toggleFavorite.pending, (state) => {
        state.actionLoading = true;
      })
      .addCase(toggleFavorite.fulfilled, (state, action) => {
        state.actionLoading = false;
        // 更新资源列表中的收藏状态
        const resource = state.resources.find((r) => r.id === action.payload.resource_id);
        if (resource) {
          resource.is_favorite = action.payload.is_favorite;
        }
        // 更新统计中的收藏数
        if (state.stats) {
          state.stats.favorites += action.payload.is_favorite ? 1 : -1;
        }
      })
      .addCase(toggleFavorite.rejected, (state, action) => {
        state.actionLoading = false;
        state.error = action.payload as string;
      });

    // 创建资源
    builder
      .addCase(createResource.pending, (state) => {
        state.actionLoading = true;
      })
      .addCase(createResource.fulfilled, (state, action) => {
        state.actionLoading = false;
        state.resources.unshift(action.payload);
        state.total += 1;
        // 更新统计
        if (state.stats) {
          state.stats.total += 1;
          if (action.payload.type === 'video') state.stats.videos += 1;
          else if (action.payload.type === 'document') state.stats.documents += 1;
        }
      })
      .addCase(createResource.rejected, (state, action) => {
        state.actionLoading = false;
        state.error = action.payload as string;
      });

    // 更新资源
    builder
      .addCase(updateResource.pending, (state) => {
        state.actionLoading = true;
      })
      .addCase(updateResource.fulfilled, (state, action) => {
        state.actionLoading = false;
        const index = state.resources.findIndex((r) => r.id === action.payload.id);
        if (index !== -1) {
          state.resources[index] = action.payload;
        }
      })
      .addCase(updateResource.rejected, (state, action) => {
        state.actionLoading = false;
        state.error = action.payload as string;
      });

    // 删除资源
    builder
      .addCase(deleteResource.pending, (state) => {
        state.actionLoading = true;
      })
      .addCase(deleteResource.fulfilled, (state, action) => {
        state.actionLoading = false;
        const deletedResource = state.resources.find((r) => r.id === action.payload);
        state.resources = state.resources.filter((r) => r.id !== action.payload);
        state.total -= 1;
        // 更新统计
        if (state.stats && deletedResource) {
          state.stats.total -= 1;
          if (deletedResource.type === 'video') state.stats.videos -= 1;
          else if (deletedResource.type === 'document') state.stats.documents -= 1;
          if (deletedResource.is_favorite) state.stats.favorites -= 1;
        }
      })
      .addCase(deleteResource.rejected, (state, action) => {
        state.actionLoading = false;
        state.error = action.payload as string;
      });
  },
});

// =============================================================================
// 导出
// =============================================================================

export const { setFilter, resetFilter, clearError, resetState } = resourceSlice.actions;

export default resourceSlice.reducer;
