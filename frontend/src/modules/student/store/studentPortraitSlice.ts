/**
 * 学生画像 Redux Slice
 *
 * 管理学生画像的状态
 */

import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { studentPortraitService } from '@/modules/student/services/studentPortraitService';
import type { StudentPortrait } from '@/modules/student/types/studentPortrait';

// =============================================================================
// 状态类型
// =============================================================================

interface StudentPortraitState {
  portrait: StudentPortrait | null;
  loadingState: 'idle' | 'loading' | 'success' | 'error';
  generating: boolean;
  clearing: boolean;
  error: string | null;
}

// =============================================================================
// 初始状态
// =============================================================================

const initialState: StudentPortraitState = {
  portrait: null,
  loadingState: 'idle',
  generating: false,
  clearing: false,
  error: null,
};

// =============================================================================
// 异步 Thunks
// =============================================================================

export const fetchPortrait = createAsyncThunk(
  'studentPortrait/fetch',
  async (_, { rejectWithValue }) => {
    try {
      return await studentPortraitService.getPortrait();
    } catch (error) {
      return rejectWithValue(
        error instanceof Error ? error.message : '获取画像失败'
      );
    }
  }
);

export const generatePortrait = createAsyncThunk(
  'studentPortrait/generate',
  async (_, { rejectWithValue }) => {
    try {
      return await studentPortraitService.generatePortrait();
    } catch (error) {
      return rejectWithValue(
        error instanceof Error ? error.message : '生成画像失败'
      );
    }
  }
);

export const clearPortrait = createAsyncThunk(
  'studentPortrait/clear',
  async (_, { rejectWithValue }) => {
    try {
      return await studentPortraitService.clearPortrait();
    } catch (error) {
      return rejectWithValue(
        error instanceof Error ? error.message : '清除画像失败'
      );
    }
  }
);

// =============================================================================
// Slice
// =============================================================================

const studentPortraitSlice = createSlice({
  name: 'studentPortrait',
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    // fetchPortrait
    builder
      .addCase(fetchPortrait.pending, (state) => {
        state.loadingState = 'loading';
        state.error = null;
      })
      .addCase(fetchPortrait.fulfilled, (state, action) => {
        state.loadingState = 'success';
        state.portrait = action.payload;
      })
      .addCase(fetchPortrait.rejected, (state, action) => {
        state.loadingState = 'error';
        state.error = action.payload as string;
      });

    // generatePortrait
    builder
      .addCase(generatePortrait.pending, (state) => {
        state.generating = true;
        state.error = null;
      })
      .addCase(generatePortrait.fulfilled, (state, action) => {
        state.generating = false;
        if (state.portrait) {
          state.portrait.portrait_content = action.payload.portrait_content;
          state.portrait.portrait_generated_at =
            action.payload.portrait_generated_at;
          state.portrait.portrait_version = action.payload.portrait_version;
          state.portrait.has_content = true;
        }
      })
      .addCase(generatePortrait.rejected, (state, action) => {
        state.generating = false;
        state.error = action.payload as string;
      });

    // clearPortrait
    builder
      .addCase(clearPortrait.pending, (state) => {
        state.clearing = true;
        state.error = null;
      })
      .addCase(clearPortrait.fulfilled, (state) => {
        state.clearing = false;
        if (state.portrait) {
          state.portrait.portrait_content = null;
          state.portrait.portrait_generated_at = null;
          state.portrait.portrait_version = 0;
          state.portrait.has_content = false;
        }
      })
      .addCase(clearPortrait.rejected, (state, action) => {
        state.clearing = false;
        state.error = action.payload as string;
      });
  },
});

export default studentPortraitSlice.reducer;
