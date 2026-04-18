import { createSlice, createAsyncThunk, type PayloadAction } from '@reduxjs/toolkit';
import type {
  KnowledgeNode,
  KnowledgeEdge,
  KnowledgeGraphStatistics,
  KnowledgeGraphFilters,
} from '@/modules/knowledge/types/knowledge';
import { knowledgeService } from '@/modules/knowledge/services/knowledgeService';
import { createLoadingReducers, type WithLoadingState } from '@/store/utils/sliceFactory';

/**
 * 知识图谱状态
 */
export interface KnowledgeState extends WithLoadingState {
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
  statistics: KnowledgeGraphStatistics | null;
  filters: KnowledgeGraphFilters;
  selectedNodeId: string | null;
}

const initialState: KnowledgeState = {
  nodes: [],
  edges: [],
  statistics: null,
  filters: {},
  selectedNodeId: null,
  loadingState: 'idle',
  error: null,
};

/**
 * 异步获取知识图谱数据
 */
export const fetchKnowledgeGraph = createAsyncThunk(
  'knowledge/fetchKnowledgeGraph',
  async (filters?: KnowledgeGraphFilters) => {
    const data = await knowledgeService.getKnowledgeGraph(filters);
    return data;
  }
);

const knowledgeSlice = createSlice({
  name: 'knowledge',
  initialState,
  reducers: {
    // 使用工厂函数创建通用加载状态 reducers (DRY 原则)
    ...createLoadingReducers<KnowledgeState>(),

    // 设置筛选条件
    setFilters(state, action: PayloadAction<KnowledgeGraphFilters>) {
      state.filters = action.payload;
    },

    // 更新单个筛选条件
    updateFilter<K extends keyof KnowledgeGraphFilters>(
      state: KnowledgeState,
      action: PayloadAction<{ key: K; value: KnowledgeGraphFilters[K] }>
    ) {
      const { key, value } = action.payload;
      if (value === undefined || value === '') {
        delete state.filters[key];
      } else {
        state.filters[key] = value;
      }
    },

    // 清除筛选条件
    clearFilters(state) {
      state.filters = {};
    },

    // 选中节点
    selectNode(state, action: PayloadAction<string | null>) {
      state.selectedNodeId = action.payload;
    },

    // 清除数据
    clearKnowledgeGraph(state) {
      state.nodes = [];
      state.edges = [];
      state.statistics = null;
      state.selectedNodeId = null;
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // 获取知识图谱数据 - pending
      .addCase(fetchKnowledgeGraph.pending, (state) => {
        state.loadingState = 'loading';
        state.error = null;
      })
      // 获取知识图谱数据 - fulfilled
      .addCase(fetchKnowledgeGraph.fulfilled, (state, action) => {
        state.loadingState = 'success';
        state.nodes = action.payload.nodes;
        state.edges = action.payload.edges;
        state.statistics = action.payload.statistics;
        state.error = null;
      })
      // 获取知识图谱数据 - rejected
      .addCase(fetchKnowledgeGraph.rejected, (state, action) => {
        state.loadingState = 'error';
        state.error = action.error.message || '获取知识图谱数据失败';
      });
  },
});

export const {
  setLoadingState,
  setError,
  clearError,
  setFilters,
  updateFilter,
  clearFilters,
  selectNode,
  clearKnowledgeGraph,
} = knowledgeSlice.actions;

export default knowledgeSlice.reducer;
