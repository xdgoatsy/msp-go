/**
 * AI 配置管理 Hook
 *
 * 封装 Redux 操作和业务逻辑
 */

import { useCallback, useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '@/store';
import {
  // Thunks
  fetchProviders,
  fetchModels,
  fetchAgentConfigs,
  fetchAgentTypes,
  createProvider,
  updateProvider,
  deleteProvider,
  testProviderConnection,
  createModel,
  updateModel,
  deleteModel,
  setDefaultModel,
  updateAgentConfig,
  deleteAgentConfig,
  // Actions
  setSelectedProvider,
  setSelectedModel,
  setSelectedAgentType,
  clearTestResult,
  clearProvidersError,
  clearModelsError,
  clearAgentConfigsError,
  // Selectors
  selectProviders,
  selectProvidersLoading,
  selectProvidersError,
  selectSelectedProviderId,
  selectModels,
  selectModelsLoading,
  selectModelsError,
  selectSelectedModelId,
  selectAgentConfigs,
  selectAgentTypes,
  selectAgentConfigsLoading,
  selectAgentConfigsError,
  selectSelectedAgentType,
  selectTestResult,
  selectTestLoading,
} from '@/modules/ai-config/store/aiConfigSlice';
import {
  selectActiveModels,
  selectActiveProviders,
  selectDefaultModel,
  selectSelectedModel,
  selectSelectedProvider,
} from '@/store/selectors/aiConfigSelectors';
import { aiConfigService } from '@/modules/ai-config/services/aiConfigService';
import type {
  CreateProviderRequest,
  UpdateProviderRequest,
  CreateProviderWithModelsRequest,
  CreateModelRequest,
  UpdateModelRequest,
  UpdateAgentConfigRequest,
  ProviderWithModelsResponse,
  FetchModelsResponse,
} from '@/modules/ai-config/types/aiConfig';

/**
 * 提供商管理 Hook
 */
export function useProviders() {
  const dispatch = useAppDispatch();
  const providers = useAppSelector(selectProviders);
  const activeProviders = useAppSelector(selectActiveProviders);
  const loading = useAppSelector(selectProvidersLoading);
  const error = useAppSelector(selectProvidersError);
  const selectedId = useAppSelector(selectSelectedProviderId);
  const selectedProvider = useAppSelector(selectSelectedProvider);

  // 加载提供商列表
  const loadProviders = useCallback(
    (includeInactive = false) => {
      return dispatch(fetchProviders(includeInactive));
    },
    [dispatch]
  );

  // 创建提供商
  const create = useCallback(
    (data: CreateProviderRequest) => {
      return dispatch(createProvider(data));
    },
    [dispatch]
  );

  // 创建提供商并同时创建模型
  const createWithModels = useCallback(
    async (data: CreateProviderWithModelsRequest): Promise<ProviderWithModelsResponse> => {
      const result = await aiConfigService.createProviderWithModels(data);
      // 刷新列表
      dispatch(fetchProviders(true));
      dispatch(fetchModels({}));
      return result;
    },
    [dispatch]
  );

  // 更新提供商
  const update = useCallback(
    (id: string, data: UpdateProviderRequest) => {
      return dispatch(updateProvider({ id, data }));
    },
    [dispatch]
  );

  // 删除提供商
  const remove = useCallback(
    (id: string) => {
      return dispatch(deleteProvider(id));
    },
    [dispatch]
  );

  // 测试连接
  const testConnection = useCallback(
    (id: string, modelId?: string) => {
      // 使用服务直接调用，支持指定模型
      return aiConfigService.testProvider(id, modelId);
    },
    []
  );

  // 获取可用模型列表
  const fetchAvailableModels = useCallback(
    async (providerId: string): Promise<FetchModelsResponse> => {
      return aiConfigService.fetchAvailableModels(providerId);
    },
    []
  );

  // 选择提供商
  const select = useCallback(
    (id: string | null) => {
      dispatch(setSelectedProvider(id));
    },
    [dispatch]
  );

  // 清除错误
  const clearError = useCallback(() => {
    dispatch(clearProvidersError());
  }, [dispatch]);

  return {
    providers,
    activeProviders,
    loading,
    error,
    selectedId,
    selectedProvider,
    loadProviders,
    create,
    createWithModels,
    update,
    remove,
    testConnection,
    fetchAvailableModels,
    select,
    clearError,
  };
}

/**
 * 模型管理 Hook
 */
export function useModels() {
  const dispatch = useAppDispatch();
  const models = useAppSelector(selectModels);
  const activeModels = useAppSelector(selectActiveModels);
  const loading = useAppSelector(selectModelsLoading);
  const error = useAppSelector(selectModelsError);
  const selectedId = useAppSelector(selectSelectedModelId);
  const selectedModel = useAppSelector(selectSelectedModel);
  const defaultModel = useAppSelector(selectDefaultModel);

  // 加载模型列表
  const loadModels = useCallback(
    (providerId?: string, includeInactive = false) => {
      return dispatch(fetchModels({ providerId, includeInactive }));
    },
    [dispatch]
  );

  // 根据提供商获取模型（基于已加载的 models 数据过滤）
  const getModelsByProvider = useCallback(
    (providerId: string) => {
      return models.filter((m) => m.provider_id === providerId);
    },
    [models]
  );

  // 创建模型
  const create = useCallback(
    (data: CreateModelRequest) => {
      return dispatch(createModel(data));
    },
    [dispatch]
  );

  // 更新模型
  const update = useCallback(
    (id: string, data: UpdateModelRequest) => {
      return dispatch(updateModel({ id, data }));
    },
    [dispatch]
  );

  // 删除模型
  const remove = useCallback(
    (id: string) => {
      return dispatch(deleteModel(id));
    },
    [dispatch]
  );

  // 设置默认模型
  const setDefault = useCallback(
    (id: string) => {
      return dispatch(setDefaultModel(id));
    },
    [dispatch]
  );

  // 选择模型
  const select = useCallback(
    (id: string | null) => {
      dispatch(setSelectedModel(id));
    },
    [dispatch]
  );

  // 清除错误
  const clearError = useCallback(() => {
    dispatch(clearModelsError());
  }, [dispatch]);

  return {
    models,
    activeModels,
    loading,
    error,
    selectedId,
    selectedModel,
    defaultModel,
    loadModels,
    getModelsByProvider,
    create,
    update,
    remove,
    setDefault,
    select,
    clearError,
  };
}

/**
 * 智能体配置管理 Hook
 */
export function useAgentConfigs() {
  const dispatch = useAppDispatch();
  const configs = useAppSelector(selectAgentConfigs);
  const agentTypes = useAppSelector(selectAgentTypes);
  const loading = useAppSelector(selectAgentConfigsLoading);
  const error = useAppSelector(selectAgentConfigsError);
  const selectedType = useAppSelector(selectSelectedAgentType);

  // 加载智能体配置
  const loadConfigs = useCallback(() => {
    return dispatch(fetchAgentConfigs());
  }, [dispatch]);

  // 加载智能体类型
  const loadTypes = useCallback(() => {
    return dispatch(fetchAgentTypes());
  }, [dispatch]);

  // 根据类型获取配置（基于已加载的 configs 数据查找）
  const getConfigByType = useCallback(
    (agentType: string) => {
      return configs.find((c) => c.agent_type === agentType) || null;
    },
    [configs]
  );

  // 更新配置
  const update = useCallback(
    (agentType: string, data: UpdateAgentConfigRequest) => {
      return dispatch(updateAgentConfig({ agentType, data }));
    },
    [dispatch]
  );

  // 删除配置
  const remove = useCallback(
    (agentType: string) => {
      return dispatch(deleteAgentConfig(agentType));
    },
    [dispatch]
  );

  // 选择智能体类型
  const select = useCallback(
    (type: string | null) => {
      dispatch(setSelectedAgentType(type));
    },
    [dispatch]
  );

  // 清除错误
  const clearError = useCallback(() => {
    dispatch(clearAgentConfigsError());
  }, [dispatch]);

  return {
    configs,
    agentTypes,
    loading,
    error,
    selectedType,
    loadConfigs,
    loadTypes,
    getConfigByType,
    update,
    remove,
    select,
    clearError,
  };
}

/**
 * 测试连接 Hook
 */
export function useTestConnection() {
  const dispatch = useAppDispatch();
  const result = useAppSelector(selectTestResult);
  const loading = useAppSelector(selectTestLoading);

  // 测试连接（使用 Redux）
  const test = useCallback(
    (providerId: string, modelId?: string) => {
      return dispatch(testProviderConnection({ id: providerId, modelId }));
    },
    [dispatch]
  );

  // 清除结果
  const clear = useCallback(() => {
    dispatch(clearTestResult());
  }, [dispatch]);

  return {
    result,
    loading,
    test,
    clear,
  };
}

/**
 * AI 配置综合 Hook
 *
 * 组合所有配置管理功能
 */
export function useAIConfig() {
  const providers = useProviders();
  const models = useModels();
  const agentConfigs = useAgentConfigs();
  const testConnection = useTestConnection();

  // 初始化加载所有数据
  const loadAll = useCallback(
    (includeInactive = false) => {
      providers.loadProviders(includeInactive);
      models.loadModels(undefined, includeInactive);
      agentConfigs.loadConfigs();
      agentConfigs.loadTypes();
    },
    [providers, models, agentConfigs]
  );

  // 初始化时自动加载（仅在组件挂载时执行一次）
  useEffect(() => {
    loadAll(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    providers,
    models,
    agentConfigs,
    testConnection,
    loadAll,
  };
}

export default useAIConfig;
