/**
 * AI 配置状态管理
 *
 * 管理 AI 模型配置的全局状态
 */

import { createSlice, createAsyncThunk, type PayloadAction } from '@reduxjs/toolkit';
import type { RootState } from '@/store';
import { aiConfigService } from '@/modules/ai-config/services/aiConfigService';
import type {
  LLMProvider,
  LLMModel,
  AgentModelConfig,
  AgentTypeInfo,
  CreateProviderRequest,
  CreateProviderWithModelsRequest,
  ProviderWithModelsResponse,
  UpdateProviderRequest,
  CreateModelRequest,
  UpdateModelRequest,
  UpdateAgentConfigRequest,
  ProviderTestResult,
  FetchModelsResponse,
  ModelsUpdateRequest,
  ModelsUpdateResponse,
} from '@/modules/ai-config/types/aiConfig';
import type { LoadingState } from '@/types';

/**
 * AI 配置状态
 */
interface AIConfigState {
  // 提供商
  providers: LLMProvider[];
  providersLoading: LoadingState;
  providersError: string | null;

  // 模型
  models: LLMModel[];
  modelsLoading: LoadingState;
  modelsError: string | null;

  // 智能体配置
  agentConfigs: AgentModelConfig[];
  agentTypes: AgentTypeInfo[];
  agentConfigsLoading: LoadingState;
  agentConfigsError: string | null;

  // 当前选中
  selectedProviderId: string | null;
  selectedModelId: string | null;
  selectedAgentType: string | null;

  // 连接测试
  testResult: ProviderTestResult | null;
  testLoading: boolean;
}

const initialState: AIConfigState = {
  providers: [],
  providersLoading: 'idle',
  providersError: null,

  models: [],
  modelsLoading: 'idle',
  modelsError: null,

  agentConfigs: [],
  agentTypes: [],
  agentConfigsLoading: 'idle',
  agentConfigsError: null,

  selectedProviderId: null,
  selectedModelId: null,
  selectedAgentType: null,

  testResult: null,
  testLoading: false,
};

// ========== 异步 Thunks ==========

// 提供商相关
export const fetchProviders = createAsyncThunk(
  'aiConfig/fetchProviders',
  async (includeInactive: boolean = false, { rejectWithValue }) => {
    try {
      const response = await aiConfigService.listProviders(includeInactive);
      return response.items;
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '获取提供商列表失败';
      return rejectWithValue(message);
    }
  },
  {
    condition: (_, { getState }) => {
      const { providersLoading } = (getState() as RootState).aiConfig;
      return providersLoading !== 'loading';
    },
  }
);

export const createProvider = createAsyncThunk(
  'aiConfig/createProvider',
  async (data: CreateProviderRequest, { rejectWithValue }) => {
    try {
      return await aiConfigService.createProvider(data);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '创建提供商失败';
      return rejectWithValue(message);
    }
  }
);

export const updateProvider = createAsyncThunk(
  'aiConfig/updateProvider',
  async ({ id, data }: { id: string; data: UpdateProviderRequest }, { rejectWithValue }) => {
    try {
      return await aiConfigService.updateProvider(id, data);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '更新提供商失败';
      return rejectWithValue(message);
    }
  }
);

export const deleteProvider = createAsyncThunk(
  'aiConfig/deleteProvider',
  async (id: string, { rejectWithValue }) => {
    try {
      await aiConfigService.deleteProvider(id);
      return id;
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '删除提供商失败';
      return rejectWithValue(message);
    }
  }
);

export const testProviderConnection = createAsyncThunk(
  'aiConfig/testProviderConnection',
  async (
    { id, modelId }: { id: string; modelId?: string },
    { rejectWithValue }
  ) => {
    try {
      return await aiConfigService.testProvider(id, modelId);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '测试连接失败';
      return rejectWithValue(message);
    }
  }
);

export const createProviderWithModels = createAsyncThunk<
  ProviderWithModelsResponse,
  CreateProviderWithModelsRequest,
  { rejectValue: string }
>(
  'aiConfig/createProviderWithModels',
  async (data: CreateProviderWithModelsRequest, { rejectWithValue }) => {
    try {
      return await aiConfigService.createProviderWithModels(data);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '创建渠道失败';
      return rejectWithValue(message);
    }
  }
);

export const fetchAvailableModels = createAsyncThunk<
  FetchModelsResponse,
  string,
  { rejectValue: string }
>(
  'aiConfig/fetchAvailableModels',
  async (providerId: string, { rejectWithValue }) => {
    try {
      return await aiConfigService.fetchAvailableModels(providerId);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '获取可用模型列表失败';
      return rejectWithValue(message);
    }
  }
);

export const updateProviderModels = createAsyncThunk<
  ModelsUpdateResponse,
  { providerId: string; data: ModelsUpdateRequest },
  { rejectValue: string }
>(
  'aiConfig/updateProviderModels',
  async ({ providerId, data }, { rejectWithValue }) => {
    try {
      return await aiConfigService.updateProviderModels(providerId, data);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '更新模型列表失败';
      return rejectWithValue(message);
    }
  }
);

// 模型相关
export const fetchModels = createAsyncThunk(
  'aiConfig/fetchModels',
  async (
    { providerId, includeInactive }: { providerId?: string; includeInactive?: boolean } = {},
    { rejectWithValue }
  ) => {
    try {
      const response = await aiConfigService.listModels(providerId, includeInactive);
      return response.items;
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '获取模型列表失败';
      return rejectWithValue(message);
    }
  },
  {
    condition: (_, { getState }) => {
      const { modelsLoading } = (getState() as RootState).aiConfig;
      return modelsLoading !== 'loading';
    },
  }
);

export const createModel = createAsyncThunk(
  'aiConfig/createModel',
  async (data: CreateModelRequest, { rejectWithValue }) => {
    try {
      return await aiConfigService.createModel(data);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '创建模型失败';
      return rejectWithValue(message);
    }
  }
);

export const updateModel = createAsyncThunk(
  'aiConfig/updateModel',
  async ({ id, data }: { id: string; data: UpdateModelRequest }, { rejectWithValue }) => {
    try {
      return await aiConfigService.updateModel(id, data);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '更新模型失败';
      return rejectWithValue(message);
    }
  }
);

export const deleteModel = createAsyncThunk(
  'aiConfig/deleteModel',
  async (id: string, { rejectWithValue }) => {
    try {
      await aiConfigService.deleteModel(id);
      return id;
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '删除模型失败';
      return rejectWithValue(message);
    }
  }
);

export const setDefaultModel = createAsyncThunk(
  'aiConfig/setDefaultModel',
  async (id: string, { rejectWithValue }) => {
    try {
      await aiConfigService.setDefaultModel(id);
      return id;
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '设置默认模型失败';
      return rejectWithValue(message);
    }
  }
);

// 智能体配置相关
export const fetchAgentConfigs = createAsyncThunk(
  'aiConfig/fetchAgentConfigs',
  async (_, { rejectWithValue }) => {
    try {
      const response = await aiConfigService.listAgentConfigs();
      return response.items;
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '获取智能体配置失败';
      return rejectWithValue(message);
    }
  }
);

export const fetchAgentTypes = createAsyncThunk(
  'aiConfig/fetchAgentTypes',
  async (_, { rejectWithValue }) => {
    try {
      const response = await aiConfigService.listAgentTypes();
      return response.items;
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '获取智能体类型失败';
      return rejectWithValue(message);
    }
  }
);

export const updateAgentConfig = createAsyncThunk(
  'aiConfig/updateAgentConfig',
  async (
    { agentType, data }: { agentType: string; data: UpdateAgentConfigRequest },
    { rejectWithValue }
  ) => {
    try {
      return await aiConfigService.updateAgentConfig(agentType, data);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '更新智能体配置失败';
      return rejectWithValue(message);
    }
  }
);

export const deleteAgentConfig = createAsyncThunk(
  'aiConfig/deleteAgentConfig',
  async (agentType: string, { rejectWithValue }) => {
    try {
      await aiConfigService.deleteAgentConfig(agentType);
      return agentType;
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '删除智能体配置失败';
      return rejectWithValue(message);
    }
  }
);

// ========== Slice ==========

const aiConfigSlice = createSlice({
  name: 'aiConfig',
  initialState,
  reducers: {
    // 选择提供商
    setSelectedProvider(state, action: PayloadAction<string | null>) {
      state.selectedProviderId = action.payload;
    },

    // 选择模型
    setSelectedModel(state, action: PayloadAction<string | null>) {
      state.selectedModelId = action.payload;
    },

    // 选择智能体类型
    setSelectedAgentType(state, action: PayloadAction<string | null>) {
      state.selectedAgentType = action.payload;
    },

    // 清除测试结果
    clearTestResult(state) {
      state.testResult = null;
    },

    // 清除错误
    clearProvidersError(state) {
      state.providersError = null;
    },

    clearModelsError(state) {
      state.modelsError = null;
    },

    clearAgentConfigsError(state) {
      state.agentConfigsError = null;
    },

    // 重置状态
    resetAIConfigState() {
      return initialState;
    },
  },
  extraReducers: (builder) => {
    // ========== 提供商 ==========
    builder
      .addCase(fetchProviders.pending, (state) => {
        state.providersLoading = 'loading';
        state.providersError = null;
      })
      .addCase(fetchProviders.fulfilled, (state, action) => {
        state.providersLoading = 'success';
        state.providers = action.payload;
      })
      .addCase(fetchProviders.rejected, (state, action) => {
        state.providersLoading = 'error';
        state.providersError = action.payload as string;
      })

      .addCase(createProvider.fulfilled, (state, action) => {
        state.providers.unshift(action.payload);
      })

      .addCase(updateProvider.fulfilled, (state, action) => {
        const index = state.providers.findIndex((p) => p.id === action.payload.id);
        if (index !== -1) {
          state.providers[index] = action.payload;
        }
      })

      .addCase(deleteProvider.fulfilled, (state, action) => {
        state.providers = state.providers.filter((p) => p.id !== action.payload);
        // 同时删除关联的模型
        state.models = state.models.filter((m) => m.provider_id !== action.payload);
      })

      .addCase(testProviderConnection.pending, (state) => {
        state.testLoading = true;
        state.testResult = null;
      })
      .addCase(testProviderConnection.fulfilled, (state, action) => {
        state.testLoading = false;
        state.testResult = action.payload;
      })
      .addCase(testProviderConnection.rejected, (state) => {
        state.testLoading = false;
      })

      .addCase(createProviderWithModels.fulfilled, (state, action) => {
        // 新增 provider
        state.providers.unshift(action.payload.provider);
        // 合并新增 models（按 id 去重）
        const existing = new Set(state.models.map((m) => m.id));
        for (const m of action.payload.models) {
          if (!existing.has(m.id)) {
            state.models.unshift(m);
            existing.add(m.id);
          }
        }
      })

      .addCase(updateProviderModels.fulfilled, (state, action) => {
        // 获取更新的提供商 ID（从返回的模型中获取）
        const providerId = action.payload.models[0]?.provider_id;
        if (providerId) {
          // 移除该提供商的旧模型
          state.models = state.models.filter((m) => m.provider_id !== providerId);
          // 添加新模型
          state.models.push(...action.payload.models);
        }
      })

      // ========== 模型 ==========
      .addCase(fetchModels.pending, (state) => {
        state.modelsLoading = 'loading';
        state.modelsError = null;
      })
      .addCase(fetchModels.fulfilled, (state, action) => {
        state.modelsLoading = 'success';
        state.models = action.payload;
      })
      .addCase(fetchModels.rejected, (state, action) => {
        state.modelsLoading = 'error';
        state.modelsError = action.payload as string;
      })

      .addCase(createModel.fulfilled, (state, action) => {
        state.models.unshift(action.payload);
      })

      .addCase(updateModel.fulfilled, (state, action) => {
        const index = state.models.findIndex((m) => m.id === action.payload.id);
        if (index !== -1) {
          state.models[index] = action.payload;
        }
      })

      .addCase(deleteModel.fulfilled, (state, action) => {
        state.models = state.models.filter((m) => m.id !== action.payload);
      })

      .addCase(setDefaultModel.fulfilled, (state, action) => {
        // 更新所有模型的 is_default 状态
        state.models = state.models.map((m) => ({
          ...m,
          is_default: m.id === action.payload,
        }));
      })

      // ========== 智能体配置 ==========
      .addCase(fetchAgentConfigs.pending, (state) => {
        state.agentConfigsLoading = 'loading';
        state.agentConfigsError = null;
      })
      .addCase(fetchAgentConfigs.fulfilled, (state, action) => {
        state.agentConfigsLoading = 'success';
        state.agentConfigs = action.payload;
      })
      .addCase(fetchAgentConfigs.rejected, (state, action) => {
        state.agentConfigsLoading = 'error';
        state.agentConfigsError = action.payload as string;
      })

      .addCase(fetchAgentTypes.fulfilled, (state, action) => {
        state.agentTypes = action.payload;
      })

      .addCase(updateAgentConfig.fulfilled, (state, action) => {
        const index = state.agentConfigs.findIndex(
          (c) => c.agent_type === action.payload.agent_type
        );
        if (index !== -1) {
          state.agentConfigs[index] = action.payload;
        } else {
          state.agentConfigs.push(action.payload);
        }
        // 更新 agentTypes 中的 configured 状态
        const typeIndex = state.agentTypes.findIndex(
          (t) => t.type === action.payload.agent_type
        );
        if (typeIndex !== -1) {
          state.agentTypes[typeIndex].configured = true;
        }
      })

      .addCase(deleteAgentConfig.fulfilled, (state, action) => {
        state.agentConfigs = state.agentConfigs.filter(
          (c) => c.agent_type !== action.payload
        );
        // 更新 agentTypes 中的 configured 状态
        const typeIndex = state.agentTypes.findIndex((t) => t.type === action.payload);
        if (typeIndex !== -1) {
          state.agentTypes[typeIndex].configured = false;
        }
      });
  },
});

// 导出 actions
export const {
  setSelectedProvider,
  setSelectedModel,
  setSelectedAgentType,
  clearTestResult,
  clearProvidersError,
  clearModelsError,
  clearAgentConfigsError,
  resetAIConfigState,
} = aiConfigSlice.actions;

// ========== Selectors ==========

// 类型定义
type StateWithAIConfig = { aiConfig?: AIConfigState };

// 提供商
export const selectProviders = (state: StateWithAIConfig) =>
  state.aiConfig?.providers ?? [];
export const selectProvidersLoading = (state: StateWithAIConfig) =>
  state.aiConfig?.providersLoading ?? 'idle';
export const selectProvidersError = (state: StateWithAIConfig) =>
  state.aiConfig?.providersError ?? null;
export const selectSelectedProviderId = (state: StateWithAIConfig) =>
  state.aiConfig?.selectedProviderId ?? null;

// 模型
export const selectModels = (state: StateWithAIConfig) =>
  state.aiConfig?.models ?? [];
export const selectModelsLoading = (state: StateWithAIConfig) =>
  state.aiConfig?.modelsLoading ?? 'idle';
export const selectModelsError = (state: StateWithAIConfig) =>
  state.aiConfig?.modelsError ?? null;
export const selectSelectedModelId = (state: StateWithAIConfig) =>
  state.aiConfig?.selectedModelId ?? null;

// 智能体配置
export const selectAgentConfigs = (state: StateWithAIConfig) =>
  state.aiConfig?.agentConfigs ?? [];
export const selectAgentTypes = (state: StateWithAIConfig) =>
  state.aiConfig?.agentTypes ?? [];
export const selectAgentConfigsLoading = (state: StateWithAIConfig) =>
  state.aiConfig?.agentConfigsLoading ?? 'idle';
export const selectAgentConfigsError = (state: StateWithAIConfig) =>
  state.aiConfig?.agentConfigsError ?? null;
export const selectSelectedAgentType = (state: StateWithAIConfig) =>
  state.aiConfig?.selectedAgentType ?? null;
export const selectAgentConfigByType = (agentType: string) => (state: StateWithAIConfig) =>
  (state.aiConfig?.agentConfigs ?? []).find((c) => c.agent_type === agentType) || null;

// 测试结果
export const selectTestResult = (state: StateWithAIConfig) =>
  state.aiConfig?.testResult ?? null;
export const selectTestLoading = (state: StateWithAIConfig) =>
  state.aiConfig?.testLoading ?? false;

export default aiConfigSlice.reducer;
