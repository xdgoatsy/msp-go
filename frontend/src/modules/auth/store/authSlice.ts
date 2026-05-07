import { createSlice, createAsyncThunk, type PayloadAction } from '@reduxjs/toolkit';
import type { LoadingState } from '@/types';
import { createFieldSelector } from '@/store/utils/sliceFactory';
import { authService } from '@/modules/auth/services/authService';
import { authTokenStorage } from '@/libs/auth/tokenStorage';

/**
 * 认证状态
 */
export interface AuthState {
  token: string | null;
  user: {
    id: string;
    name: string;
    email?: string;
    email_verified?: boolean;
    role: 'student' | 'teacher' | 'admin';
    avatar?: string;
  } | null;
  isAuthenticated: boolean;
  loadingState: LoadingState;
  error: string | null;
}

const USER_CACHE_KEY = 'auth_user_cache';

function loadUserFromCache(): AuthState['user'] {
  try {
    const cached = localStorage.getItem(USER_CACHE_KEY);
    if (!cached) return null;
    return JSON.parse(cached) as AuthState['user'];
  } catch {
    return null;
  }
}

function saveUserToCache(user: AuthState['user']): void {
  try {
    if (user) {
      localStorage.setItem(USER_CACHE_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(USER_CACHE_KEY);
    }
  } catch {
    // 存储失败时静默处理
  }
}

const cachedUser = loadUserFromCache();
const token = authTokenStorage.get();

const initialState: AuthState = {
  token,
  // 有 token 且有缓存用户时直接恢复，避免首次加载阻塞
  user: token ? cachedUser : null,
  isAuthenticated: !!token,
  loadingState: 'idle',
  error: null,
};

// 异步 thunk：获取当前用户信息
export const fetchCurrentUser = createAsyncThunk(
  'auth/fetchCurrentUser',
  async (_, { rejectWithValue }) => {
    try {
      const userInfo = await authService.getCurrentUser();
      return {
        id: userInfo.id,
        name: userInfo.username,
        email: userInfo.email,
        email_verified: userInfo.email_verified,
        role: userInfo.role,
      };
    } catch {
      // 获取用户信息失败，清除 token
      authTokenStorage.clear();
      return rejectWithValue('获取用户信息失败');
    }
  }
);

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    // 设置凭证
    setCredentials(
      state,
      action: PayloadAction<{
        token: string;
        user: AuthState['user'];
      }>
    ) {
      const { token, user } = action.payload;
      state.token = token;
      state.user = user;
      state.isAuthenticated = true;
      state.loadingState = 'success';
      state.error = null;
      authTokenStorage.set(token);
      saveUserToCache(user);
    },

    // 登出
    logout(state) {
      state.token = null;
      state.user = null;
      state.isAuthenticated = false;
      state.loadingState = 'idle';
      state.error = null;
      authTokenStorage.clear();
      saveUserToCache(null);
    },

    // 更新用户信息
    updateUser(state, action: PayloadAction<Partial<AuthState['user']>>) {
      if (state.user) {
        state.user = {
          ...state.user,
          ...action.payload,
        };
      }
    },

    // 设置加载状态
    setLoadingState(state, action: PayloadAction<LoadingState>) {
      state.loadingState = action.payload;
      if (action.payload === 'loading') {
        state.error = null;
      }
    },

    // 设置错误信息
    setError(state, action: PayloadAction<string>) {
      state.error = action.payload;
      state.loadingState = 'error';
    },

    // 清除错误
    clearError(state) {
      state.error = null;
    },

    // 刷新 token
    refreshToken(state, action: PayloadAction<string>) {
      state.token = action.payload;
      state.isAuthenticated = true;
      authTokenStorage.set(action.payload);
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchCurrentUser.pending, (state) => {
        state.loadingState = 'loading';
      })
      .addCase(fetchCurrentUser.fulfilled, (state, action) => {
        state.user = action.payload;
        state.isAuthenticated = true;
        state.loadingState = 'success';
        state.error = null;
        saveUserToCache(action.payload);
      })
      .addCase(fetchCurrentUser.rejected, (state) => {
        state.token = null;
        state.user = null;
        state.isAuthenticated = false;
        state.loadingState = 'error';
        state.error = null;
        saveUserToCache(null);
      });
  },
});

export const {
  setCredentials,
  logout,
  updateUser,
  setLoadingState,
  setError,
  clearError,
  refreshToken,
} = authSlice.actions;

// ============ Selectors ============
// 使用工厂函数生成字段 selectors
export const selectCurrentUser = createFieldSelector<AuthState, 'auth', 'user'>('auth', 'user');
export const selectIsAuthenticated = createFieldSelector<AuthState, 'auth', 'isAuthenticated'>('auth', 'isAuthenticated');
export const selectAuthToken = createFieldSelector<AuthState, 'auth', 'token'>('auth', 'token');
export const selectAuthLoadingState = createFieldSelector<AuthState, 'auth', 'loadingState'>('auth', 'loadingState');
export const selectAuthError = createFieldSelector<AuthState, 'auth', 'error'>('auth', 'error');

// 派生 selector
export const selectIsAuthLoading = (state: { auth: AuthState }) =>
  state.auth.loadingState === 'loading';

export default authSlice.reducer;
