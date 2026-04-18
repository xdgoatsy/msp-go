import { describe, it, expect } from 'vitest';
import { configureStore, createSlice } from '@reduxjs/toolkit';
import {
  createSafeThunk,
  createSafeThunkWithState,
} from '@/store/utils/thunkFactory';

// 测试用的简单 Store 状态
interface TestRootState {
  counter: { value: number };
}

const counterSlice = createSlice({
  name: 'counter',
  initialState: { value: 42 },
  reducers: {},
});

function makeStore() {
  return configureStore<TestRootState>({
    reducer: { counter: counterSlice.reducer },
  });
}

// ─── createSafeThunk ─────────────────────────────────────────────────────────

describe('createSafeThunk', () => {
  it('成功时返回结果', async () => {
    const fetchData = createSafeThunk('test/fetchData', async () => {
      return { id: 1, name: '测试' };
    });

    const store = makeStore();
    const result = await store.dispatch(fetchData());

    expect(result.type).toBe('test/fetchData/fulfilled');
    expect((result as { payload: unknown }).payload).toEqual({ id: 1, name: '测试' });
  });

  it('抛出 Error 时使用 error.message 拒绝', async () => {
    const failThunk = createSafeThunk('test/fail', async () => {
      throw new Error('网络请求失败');
    });

    const store = makeStore();
    const result = await store.dispatch(failThunk());

    expect(result.type).toBe('test/fail/rejected');
    expect((result as { payload: unknown }).payload).toBe('网络请求失败');
  });

  it('抛出非 Error 对象时使用默认错误消息', async () => {
    const failThunk = createSafeThunk('test/failNonError', async () => {
      throw '字符串错误';
    });

    const store = makeStore();
    const result = await store.dispatch(failThunk());

    expect(result.type).toBe('test/failNonError/rejected');
    // 默认消息为 '操作失败'
    expect((result as { payload: unknown }).payload).toBe('操作失败');
  });

  it('使用自定义默认错误消息', async () => {
    const failThunk = createSafeThunk(
      'test/failCustomMsg',
      async () => {
        throw 42; // 非 Error 对象
      },
      '自定义错误消息'
    );

    const store = makeStore();
    const result = await store.dispatch(failThunk());

    expect(result.type).toBe('test/failCustomMsg/rejected');
    expect((result as { payload: unknown }).payload).toBe('自定义错误消息');
  });

  it('带参数时正确传递 arg', async () => {
    const fetchById = createSafeThunk<string, number>(
      'test/fetchById',
      async (id) => `item-${id}`
    );

    const store = makeStore();
    const result = await store.dispatch(fetchById(99));

    expect(result.type).toBe('test/fetchById/fulfilled');
    expect((result as { payload: unknown }).payload).toBe('item-99');
  });
});

// ─── createSafeThunkWithState ────────────────────────────────────────────────

describe('createSafeThunkWithState', () => {
  it('成功时返回结果', async () => {
    const fetchWithState = createSafeThunkWithState<string, void, TestRootState>(
      'test/fetchWithState',
      async () => '成功结果'
    );

    const store = makeStore();
    const result = await store.dispatch(fetchWithState());

    expect(result.type).toBe('test/fetchWithState/fulfilled');
    expect((result as { payload: unknown }).payload).toBe('成功结果');
  });

  it('向 payloadCreator 提供 getState 函数', async () => {
    let capturedValue: number | undefined;

    const readStateThunk = createSafeThunkWithState<void, void, TestRootState>(
      'test/readState',
      async (_arg, getState) => {
        capturedValue = getState().counter.value;
      }
    );

    const store = makeStore();
    await store.dispatch(readStateThunk());

    // store 中 counter.value 初始为 42
    expect(capturedValue).toBe(42);
  });

  it('失败时使用 error.message 拒绝', async () => {
    const failThunk = createSafeThunkWithState<string, void, TestRootState>(
      'test/failWithState',
      async () => {
        throw new Error('状态相关操作失败');
      }
    );

    const store = makeStore();
    const result = await store.dispatch(failThunk());

    expect(result.type).toBe('test/failWithState/rejected');
    expect((result as { payload: unknown }).payload).toBe('状态相关操作失败');
  });

  it('抛出非 Error 时使用自定义默认消息', async () => {
    const failThunk = createSafeThunkWithState<string, void, TestRootState>(
      'test/failWithStateCustom',
      async () => {
        throw null;
      },
      '自定义状态错误'
    );

    const store = makeStore();
    const result = await store.dispatch(failThunk());

    expect(result.type).toBe('test/failWithStateCustom/rejected');
    expect((result as { payload: unknown }).payload).toBe('自定义状态错误');
  });
});
