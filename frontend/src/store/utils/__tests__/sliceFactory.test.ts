import { describe, it, expect } from 'vitest';
import { createSlice, configureStore } from '@reduxjs/toolkit';
import {
  createLoadingReducers,
  createNamedLoadingReducer,
  createLoadingSelectors,
  createFieldSelector,
  createFieldSelectors,
  type WithLoadingState,
} from '@/store/utils/sliceFactory';
import type { LoadingState } from '@/types/common';

// 测试用的 Slice 状态类型
interface TestState extends WithLoadingState {
  loadingState: LoadingState;
  error: string | null;
  data: string[];
  count: number;
  sendingState: LoadingState;
}

const initialState: TestState = {
  loadingState: 'idle',
  error: null,
  data: [],
  count: 0,
  sendingState: 'idle',
};

// 创建测试用 Slice
const testSlice = createSlice({
  name: 'test',
  initialState,
  reducers: {
    ...createLoadingReducers<TestState>(),
    ...createNamedLoadingReducer<TestState, 'setSendingState', 'sendingState'>(
      'setSendingState',
      'sendingState'
    ),
  },
});

const { setLoadingState, setError, clearError, setSendingState } = testSlice.actions;

// 创建测试用 Store
function makeStore() {
  return configureStore({ reducer: { test: testSlice.reducer } });
}

// ─── createLoadingReducers ───────────────────────────────────────────────────

describe('createLoadingReducers', () => {
  it('setLoadingState 正确设置加载状态', () => {
    const store = makeStore();
    store.dispatch(setLoadingState('loading'));
    expect(store.getState().test.loadingState).toBe('loading');
  });

  it("setLoadingState('loading') 清除 error", () => {
    const store = makeStore();
    // 先设置一个错误
    store.dispatch(setError('some error'));
    expect(store.getState().test.error).toBe('some error');
    // 切换到 loading 应清除 error
    store.dispatch(setLoadingState('loading'));
    expect(store.getState().test.error).toBeNull();
  });

  it("setLoadingState('success') 不清除 error", () => {
    const store = makeStore();
    store.dispatch(setError('some error'));
    store.dispatch(setLoadingState('success'));
    // success 不清除 error
    expect(store.getState().test.error).toBe('some error');
    expect(store.getState().test.loadingState).toBe('success');
  });

  it('setError 设置错误消息并将 loadingState 置为 error', () => {
    const store = makeStore();
    store.dispatch(setError('请求失败'));
    expect(store.getState().test.error).toBe('请求失败');
    expect(store.getState().test.loadingState).toBe('error');
  });

  it('clearError 将 error 置为 null', () => {
    const store = makeStore();
    store.dispatch(setError('some error'));
    store.dispatch(clearError());
    expect(store.getState().test.error).toBeNull();
  });

  it('clearError 不改变 loadingState', () => {
    const store = makeStore();
    store.dispatch(setError('some error'));
    // loadingState 此时为 'error'
    store.dispatch(clearError());
    expect(store.getState().test.loadingState).toBe('error');
  });
});

// ─── createNamedLoadingReducer ───────────────────────────────────────────────

describe('createNamedLoadingReducer', () => {
  it('使用指定的 actionName 创建 reducer', () => {
    // setSendingState action 应该存在
    expect(typeof setSendingState).toBe('function');
  });

  it('正确设置命名的状态键', () => {
    const store = makeStore();
    store.dispatch(setSendingState('loading'));
    expect(store.getState().test.sendingState).toBe('loading');
  });

  it("设置为 'loading' 时清除 error", () => {
    const store = makeStore();
    store.dispatch(setError('some error'));
    store.dispatch(setSendingState('loading'));
    expect(store.getState().test.error).toBeNull();
  });

  it("设置为非 'loading' 时不清除 error", () => {
    const store = makeStore();
    store.dispatch(setError('some error'));
    store.dispatch(setSendingState('success'));
    expect(store.getState().test.error).toBe('some error');
    expect(store.getState().test.sendingState).toBe('success');
  });
});

// ─── createLoadingSelectors ──────────────────────────────────────────────────

describe('createLoadingSelectors', () => {
  const selectors = createLoadingSelectors<'test', TestState>({ sliceName: 'test' });

  it('生成正确命名的 selectors', () => {
    expect(typeof selectors.selectTestLoadingState).toBe('function');
    expect(typeof selectors.selectTestError).toBe('function');
    expect(typeof selectors.selectIsTestLoading).toBe('function');
  });

  it('selectTestLoadingState 返回正确的 loadingState', () => {
    const store = makeStore();
    store.dispatch(setLoadingState('success'));
    const state = store.getState();
    expect(selectors.selectTestLoadingState(state)).toBe('success');
  });

  it('selectTestError 返回正确的 error', () => {
    const store = makeStore();
    store.dispatch(setError('测试错误'));
    const state = store.getState();
    expect(selectors.selectTestError(state)).toBe('测试错误');
  });

  it("selectIsTestLoading 在 loadingState 为 'loading' 时返回 true", () => {
    const store = makeStore();
    store.dispatch(setLoadingState('loading'));
    expect(selectors.selectIsTestLoading(store.getState())).toBe(true);
  });

  it("selectIsTestLoading 在 loadingState 非 'loading' 时返回 false", () => {
    const store = makeStore();
    store.dispatch(setLoadingState('idle'));
    expect(selectors.selectIsTestLoading(store.getState())).toBe(false);

    store.dispatch(setLoadingState('success'));
    expect(selectors.selectIsTestLoading(store.getState())).toBe(false);

    store.dispatch(setLoadingState('error'));
    expect(selectors.selectIsTestLoading(store.getState())).toBe(false);
  });

  it('支持 extraLoadingStates 生成额外 selectors', () => {
    const extSelectors = createLoadingSelectors<'test', TestState>({
      sliceName: 'test',
      extraLoadingStates: ['sendingState'],
    });
    expect(typeof extSelectors.selectTestSendingState).toBe('function');
    expect(typeof extSelectors.selectIsSending).toBe('function');

    const store = makeStore();
    store.dispatch(setSendingState('loading'));
    expect(extSelectors.selectTestSendingState(store.getState())).toBe('loading');
    expect(extSelectors.selectIsSending(store.getState())).toBe(true);
  });
});

// ─── createFieldSelector ─────────────────────────────────────────────────────

describe('createFieldSelector', () => {
  it('返回指定字段的正确值', () => {
    const selectCount = createFieldSelector<TestState, 'test', 'count'>('test', 'count');
    const store = makeStore();
    // 初始值为 0
    expect(selectCount(store.getState())).toBe(0);
  });

  it('返回 data 字段的正确值', () => {
    const selectData = createFieldSelector<TestState, 'test', 'data'>('test', 'data');
    const store = makeStore();
    expect(selectData(store.getState())).toEqual([]);
  });
});

// ─── createFieldSelectors ────────────────────────────────────────────────────

describe('createFieldSelectors', () => {
  const fields = ['data', 'count', 'sendingState'] as const;
  const fieldSelectors = createFieldSelectors<TestState, 'test', typeof fields>('test', fields);

  it('为所有指定字段创建 selectors', () => {
    expect(typeof fieldSelectors.selectData).toBe('function');
    expect(typeof fieldSelectors.selectCount).toBe('function');
    expect(typeof fieldSelectors.selectSendingState).toBe('function');
  });

  it('每个 selector 返回正确的字段值', () => {
    const store = makeStore();
    const state = store.getState();
    expect(fieldSelectors.selectData(state)).toEqual([]);
    expect(fieldSelectors.selectCount(state)).toBe(0);
    expect(fieldSelectors.selectSendingState(state)).toBe('idle');
  });
});
