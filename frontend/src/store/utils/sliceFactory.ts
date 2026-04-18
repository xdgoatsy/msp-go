import type { PayloadAction, Draft } from '@reduxjs/toolkit';
import { createSelector } from '@reduxjs/toolkit';
import type { LoadingState } from '../../types';

/**
 * 基础加载状态接口
 * 所有需要加载状态管理的 Slice 都应该实现此接口
 */
export interface WithLoadingState {
  loadingState: LoadingState;
  error: string | null;
}

type LoadingStateKeyOf<T> = {
  [K in keyof T]: T[K] extends LoadingState ? K : never;
}[keyof T];

/**
 * 创建通用的加载状态 Reducers
 *
 * @description 生成 setLoadingState、setError、clearError 三个通用 reducer
 * 遵循 DRY 原则，消除各 Slice 中重复的加载状态管理代码
 *
 * 兼容 Redux Toolkit 的 createSlice
 *
 * @example
 * ```typescript
 * const slice = createSlice({
 *   name: 'example',
 *   initialState,
 *   reducers: {
 *     ...createLoadingReducers<ExampleState>(),
 *     // 其他 reducers
 *   },
 * });
 * ```
 */
export function createLoadingReducers<T extends WithLoadingState>() {
  return {
    setLoadingState: (state: Draft<T>, action: PayloadAction<LoadingState>) => {
      state.loadingState = action.payload as Draft<T>['loadingState'];
      if (action.payload === 'loading') {
        state.error = null;
      }
    },
    setError: (state: Draft<T>, action: PayloadAction<string>) => {
      state.error = action.payload as Draft<T>['error'];
      state.loadingState = 'error' as Draft<T>['loadingState'];
    },
    clearError: (state: Draft<T>) => {
      state.error = null;
    },
  };
}

/**
 * 创建命名的加载状态 Reducer
 *
 * @description 用于创建如 sendingState、submitState 等额外的加载状态管理
 * 返回一个带有指定名称的 reducer
 *
 * @param actionName - action 名称（如 'setSendingState', 'setSubmitState'）
 * @param stateKey - 状态键名（如 'sendingState', 'submitState'）
 *
 * @example
 * ```typescript
 * const slice = createSlice({
 *   name: 'session',
 *   initialState,
 *   reducers: {
 *     ...createLoadingReducers<SessionState>(),
 *     ...createNamedLoadingReducer<SessionState>('setSendingState', 'sendingState'),
 *     // 其他 reducers
 *   },
 * });
 * ```
 */
export function createNamedLoadingReducer<
  T extends WithLoadingState,
  ActionName extends string = string,
  StateKey extends LoadingStateKeyOf<T> = LoadingStateKeyOf<T>
>(
  actionName: ActionName,
  stateKey: StateKey
): Record<ActionName, (state: Draft<T>, action: PayloadAction<LoadingState>) => void> {
  const reducer = (state: Draft<T>, action: PayloadAction<LoadingState>) => {
    (state as unknown as Record<string, LoadingState>)[stateKey as string] = action.payload;
    if (action.payload === 'loading') {
      state.error = null;
    }
  };

  return {
    [actionName]: reducer,
  } as Record<ActionName, typeof reducer>;
}

/**
 * Selector 工厂函数配置
 */
interface SelectorFactoryConfig<SliceName extends string> {
  /** Slice 名称，用于生成 selector 名称和访问 state */
  sliceName: SliceName;
  /** 额外的加载状态键名列表 */
  extraLoadingStates?: string[];
}

/**
 * 创建通用的加载状态 Selectors
 *
 * @description 生成标准的加载状态相关 selectors
 * 遵循 DRY 原则，消除各 Slice 中重复的 selector 定义
 *
 * @param config - 配置对象
 *
 * @example
 * ```typescript
 * const {
 *   selectSessionLoadingState,
 *   selectSessionError,
 *   selectIsSessionLoading,
 * } = createLoadingSelectors<'session', SessionState>({
 *   sliceName: 'session',
 * });
 * ```
 */
export function createLoadingSelectors<
  SliceName extends string,
  State extends WithLoadingState
>(config: SelectorFactoryConfig<SliceName>) {
  const { sliceName, extraLoadingStates = [] } = config;
  const capitalizedName = sliceName.charAt(0).toUpperCase() + sliceName.slice(1);

  type RootState = { [K in SliceName]: State };

  // 基础 selector - 获取整个 slice 状态
  const selectSliceState = (state: RootState) => state[sliceName];

  // 使用 createSelector 实现记忆化的基础 selectors
  const baseSelectors = {
    [`select${capitalizedName}LoadingState`]: createSelector(
      [selectSliceState],
      (sliceState) => sliceState.loadingState
    ),
    [`select${capitalizedName}Error`]: createSelector(
      [selectSliceState],
      (sliceState) => sliceState.error
    ),
    [`selectIs${capitalizedName}Loading`]: createSelector(
      [selectSliceState],
      (sliceState) => sliceState.loadingState === 'loading'
    ),
  };

  // 额外加载状态的记忆化 selectors
  const extraSelectors: Record<string, ReturnType<typeof createSelector>> = {};

  for (const stateKey of extraLoadingStates) {
    const capitalizedKey = stateKey.charAt(0).toUpperCase() + stateKey.slice(1);
    // 移除 'State' 后缀以生成更简洁的名称
    const cleanKey = stateKey.replace(/State$/, '');
    const capitalizedCleanKey = cleanKey.charAt(0).toUpperCase() + cleanKey.slice(1);

    extraSelectors[`select${capitalizedName}${capitalizedKey}`] = createSelector(
      [selectSliceState],
      (sliceState) => (sliceState as Record<string, unknown>)[stateKey]
    );

    extraSelectors[`selectIs${capitalizedCleanKey}`] = createSelector(
      [selectSliceState],
      (sliceState) => (sliceState as Record<string, unknown>)[stateKey] === 'loading'
    );
  }

  return { ...baseSelectors, ...extraSelectors };
}

/**
 * 创建简单的字段 Selector
 *
 * @description 快速生成访问 slice 中某个字段的 selector
 *
 * @param sliceName - Slice 名称
 * @param fieldName - 字段名称
 *
 * @example
 * ```typescript
 * export const selectCurrentSession = createFieldSelector<SessionState, 'session'>('session', 'currentSession');
 * ```
 */
export function createFieldSelector<
  State,
  SliceName extends string,
  Field extends keyof State
>(sliceName: SliceName, fieldName: Field) {
  type RootState = { [K in SliceName]: State };
  return (state: RootState): State[Field] => state[sliceName][fieldName];
}

/**
 * 批量创建字段 Selectors
 *
 * @description 一次性为多个字段创建 selectors
 *
 * @param sliceName - Slice 名称
 * @param fieldNames - 字段名称数组
 *
 * @example
 * ```typescript
 * const selectors = createFieldSelectors<SessionState, 'session'>('session', [
 *   'currentSession',
 *   'messages',
 *   'mode',
 * ] as const);
 * // 使用: selectors.selectCurrentSession(state)
 * ```
 */
export function createFieldSelectors<
  State,
  SliceName extends string,
  Fields extends readonly (keyof State)[]
>(sliceName: SliceName, fieldNames: Fields) {
  type RootState = { [K in SliceName]: State };

  // 基础 selector - 获取整个 slice 状态
  const selectSliceState = (state: RootState) => state[sliceName];

  const selectors = {} as {
    [K in Fields[number] as `select${Capitalize<string & K>}`]: ReturnType<typeof createSelector>;
  };

  for (const fieldName of fieldNames) {
    const capitalizedField = String(fieldName).charAt(0).toUpperCase() + String(fieldName).slice(1);
    const selectorName = `select${capitalizedField}` as keyof typeof selectors;
    // 使用 createSelector 实现记忆化
    (selectors as Record<string, unknown>)[selectorName] = createSelector(
      [selectSliceState],
      (sliceState) => sliceState[fieldName]
    );
  }

  return selectors;
}
