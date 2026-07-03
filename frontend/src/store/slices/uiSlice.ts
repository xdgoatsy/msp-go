import { createSlice, type PayloadAction } from '@reduxjs/toolkit';

interface UiState {
  isLoading: boolean;
  theme: 'light' | 'dark';
  sidebarOpen: boolean;
}

type Theme = UiState['theme'];

function isTheme(value: unknown): value is Theme {
  return value === 'light' || value === 'dark';
}

function clearStoredTheme(): void {
  try {
    localStorage.removeItem('theme');
  } catch {
    // 存储不可用时忽略
  }
}

function persistTheme(theme: Theme): void {
  try {
    localStorage.setItem('theme', theme);
  } catch {
    // 存储不可用时忽略
  }
}

// 从 localStorage 获取保存的主题，默认为 'light'
const getInitialTheme = (): Theme => {
  if (typeof window !== 'undefined') {
    const savedTheme = (() => {
      try {
        return localStorage.getItem('theme');
      } catch {
        return null;
      }
    })();
    if (isTheme(savedTheme)) {
      return savedTheme;
    }
    if (savedTheme) {
      clearStoredTheme();
    }
    // 检测系统偏好
    if (window.matchMedia?.('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
  }
  return 'light';
};

const initialState: UiState = {
  isLoading: false,
  theme: getInitialTheme(),
  sidebarOpen: true,
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    setLoading(state, action: PayloadAction<boolean>) {
      state.isLoading = action.payload;
    },
    toggleTheme(state) {
      state.theme = state.theme === 'light' ? 'dark' : 'light';
      // 持久化到 localStorage
      if (typeof window !== 'undefined') {
        persistTheme(state.theme);
      }
    },
    setTheme(state, action: PayloadAction<Theme>) {
      state.theme = action.payload;
      if (typeof window !== 'undefined') {
        persistTheme(state.theme);
      }
    },
    toggleSidebar(state) {
      state.sidebarOpen = !state.sidebarOpen;
    },
  },
});

export const { setLoading, toggleTheme, setTheme, toggleSidebar } = uiSlice.actions;

// Selector
export const selectTheme = (state: { ui: UiState }) => state.ui.theme;

export default uiSlice.reducer;
