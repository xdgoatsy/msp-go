import { describe, expect, it } from 'vitest';
import type { RootState } from '@/store';
import type { LLMModel, LLMProvider } from '@/modules/ai-config/types/aiConfig';
import {
  selectActiveModels,
  selectActiveProviders,
  selectDefaultModel,
  selectModelsByProvider,
  selectSelectedModel,
  selectSelectedProvider,
} from './aiConfigSelectors';

function provider(id: string, isActive: boolean): LLMProvider {
  return {
    id,
    name: `Provider ${id}`,
    code: id,
    base_url: `https://${id}.example.com`,
    is_active: isActive,
    description: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  };
}

function model(
  id: string,
  providerId: string,
  options: { isActive?: boolean; isDefault?: boolean } = {}
): LLMModel {
  return {
    id,
    provider_id: providerId,
    name: `Model ${id}`,
    model_id: id,
    default_temperature: 0.7,
    default_max_tokens: null,
    default_top_p: null,
    default_timeout: 60,
    default_max_retries: 2,
    is_active: options.isActive ?? true,
    is_default: options.isDefault ?? false,
    capabilities: {},
    description: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    provider_name: null,
    provider_code: null,
  };
}

function stateWith(overrides: Partial<RootState['aiConfig']> = {}): RootState {
  return {
    aiConfig: {
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
      ...overrides,
    },
  } as RootState;
}

describe('AI config selectors', () => {
  it('filters active providers and preserves the memoized result reference', () => {
    const state = stateWith({
      providers: [provider('active', true), provider('inactive', false)],
    });

    const first = selectActiveProviders(state);

    expect(first).toEqual([state.aiConfig.providers[0]]);
    expect(selectActiveProviders(state)).toBe(first);
  });

  it('returns the selected provider or null when the selection is missing', () => {
    const selectedState = stateWith({
      providers: [provider('provider-1', true)],
      selectedProviderId: 'provider-1',
    });

    expect(selectSelectedProvider(selectedState)).toBe(selectedState.aiConfig.providers[0]);
    expect(selectSelectedProvider(stateWith({ selectedProviderId: 'missing' }))).toBeNull();
  });

  it('filters active models and preserves the memoized result reference', () => {
    const state = stateWith({
      models: [model('active', 'provider-1'), model('inactive', 'provider-1', { isActive: false })],
    });

    const first = selectActiveModels(state);

    expect(first).toEqual([state.aiConfig.models[0]]);
    expect(selectActiveModels(state)).toBe(first);
  });

  it('filters models by provider and memoizes each parameterized result', () => {
    const state = stateWith({
      models: [model('model-1', 'provider-1'), model('model-2', 'provider-2')],
    });

    const first = selectModelsByProvider(state, 'provider-1');

    expect(first).toEqual([state.aiConfig.models[0]]);
    expect(selectModelsByProvider(state, 'provider-1')).toBe(first);
    expect(selectModelsByProvider(state, 'missing')).toEqual([]);
  });

  it('returns the selected and default models with null fallbacks', () => {
    const state = stateWith({
      models: [model('model-1', 'provider-1', { isDefault: true })],
      selectedModelId: 'model-1',
    });

    expect(selectSelectedModel(state)).toBe(state.aiConfig.models[0]);
    expect(selectDefaultModel(state)).toBe(state.aiConfig.models[0]);
    expect(selectSelectedModel(stateWith({ selectedModelId: 'missing' }))).toBeNull();
    expect(selectDefaultModel(stateWith())).toBeNull();
  });
});
