/**
 * 视频管理状态管理
 */
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { Video } from '../../types';

interface VideoState {
  videos: Video[];
  selectedVideos: Video[];
  currentVideo: Video | null;
  loading: boolean;
  error: string | null;
  searchQuery: string;
  selectedCategory: string;
  pagination: {
    page: number;
    totalPages: number;
    totalCount: number;
  };
}

const initialState: VideoState = {
  videos: [],
  selectedVideos: [],
  currentVideo: null,
  loading: false,
  error: null,
  searchQuery: '',
  selectedCategory: '',
  pagination: {
    page: 1,
    totalPages: 1,
    totalCount: 0,
  },
};

const videoSlice = createSlice({
  name: 'video',
  initialState,
  reducers: {
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload;
    },
    setVideos: (state, action: PayloadAction<Video[]>) => {
      state.videos = action.payload;
      state.loading = false;
    },
    setError: (state, action: PayloadAction<string>) => {
      state.error = action.payload;
      state.loading = false;
    },
    clearError: (state) => {
      state.error = null;
    },
    setCurrentVideo: (state, action: PayloadAction<Video | null>) => {
      state.currentVideo = action.payload;
    },
    addSelectedVideo: (state, action: PayloadAction<Video>) => {
      const exists = state.selectedVideos.find(v => v.id === action.payload.id);
      if (!exists) {
        state.selectedVideos.push(action.payload);
      }
    },
    removeSelectedVideo: (state, action: PayloadAction<number>) => {
      state.selectedVideos = state.selectedVideos.filter(v => v.id !== action.payload);
    },
    clearSelectedVideos: (state) => {
      state.selectedVideos = [];
    },
    reorderSelectedVideos: (state, action: PayloadAction<Video[]>) => {
      state.selectedVideos = action.payload;
    },
    setSearchQuery: (state, action: PayloadAction<string>) => {
      state.searchQuery = action.payload;
    },
    setSelectedCategory: (state, action: PayloadAction<string>) => {
      state.selectedCategory = action.payload;
    },
    setPagination: (state, action: PayloadAction<{ page: number; totalPages: number; totalCount: number }>) => {
      state.pagination = action.payload;
    },
  },
});

export const {
  setLoading,
  setVideos,
  setError,
  clearError,
  setCurrentVideo,
  addSelectedVideo,
  removeSelectedVideo,
  clearSelectedVideos,
  reorderSelectedVideos,
  setSearchQuery,
  setSelectedCategory,
  setPagination,
} = videoSlice.actions;

export default videoSlice.reducer;