import { createSlice, type PayloadAction } from '@reduxjs/toolkit';

interface UiState {
  isLoading: boolean;
  theme: 'light' | 'dark';
  sidebarOpen: boolean;
}

// 从 localStorage 获取保存的主题，默认为 'light'
const getInitialTheme = (): 'light' | 'dark' => {
  if (typeof window !== 'undefined') {
    const savedTheme = localStorage.getItem('theme') as 'light' | 'dark' | null;
    if (savedTheme) {
      return savedTheme;
    }
    // 检测系统偏好
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
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
        localStorage.setItem('theme', state.theme);
      }
    },
    setTheme(state, action: PayloadAction<'light' | 'dark'>) {
      state.theme = action.payload;
      if (typeof window !== 'undefined') {
        localStorage.setItem('theme', state.theme);
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