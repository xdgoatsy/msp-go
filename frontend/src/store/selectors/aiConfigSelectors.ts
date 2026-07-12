/**
 * AI 配置 Selectors（记忆化）
 *
 * 对会产生新数组的 .filter() 和需要派生查找的 .find() 使用 createSelector
 * 简单字段访问保持原有 selector 不变
 */

import { createSelector } from '@reduxjs/toolkit';
import type { RootState } from '@/store';

// ========== 基础 Selector ==========

const selectAIConfigState = (state: RootState) => state.aiConfig;

// ========== 派生 Selectors（记忆化） ==========

/** 活跃的提供商列表（.filter 产生新引用） */
export const selectActiveProviders = createSelector(
  [selectAIConfigState],
  (state) => state.providers.filter((p) => p.is_active)
);

/** 当前选中的提供商（避免重复线性查找） */
export const selectSelectedProvider = createSelector(
  [selectAIConfigState],
  (state) => state.providers.find((p) => p.id === state.selectedProviderId) || null
);

/** 活跃的模型列表（.filter 产生新引用） */
export const selectActiveModels = createSelector(
  [selectAIConfigState],
  (state) => state.models.filter((m) => m.is_active)
);

/** 按提供商筛选模型（参数化 selector） */
export const selectModelsByProvider = createSelector(
  [selectAIConfigState, (_: RootState, providerId: string) => providerId],
  (state, providerId) => state.models.filter((m) => m.provider_id === providerId)
);

/** 当前选中的模型（避免重复线性查找） */
export const selectSelectedModel = createSelector(
  [selectAIConfigState],
  (state) => state.models.find((m) => m.id === state.selectedModelId) || null
);

/** 默认模型（避免重复线性查找） */
export const selectDefaultModel = createSelector(
  [selectAIConfigState],
  (state) => state.models.find((m) => m.is_default) || null
);
