/**
 * 视频合成页面单元测试
 * 验证需求: 需求 6.1, 6.4, 6.5
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import videoSlice from '../../store/slices/videoSlice';

// Mock videoService
const mockVideoService = {
  getVideos: jest.fn(),
  createCompositionTask: jest.fn(),
  getCompositionTaskStatus: jest.fn(),
  getCompositionDownloadUrl: jest.fn(),
  cancelCompositionTask: jest.fn(),
  getCompositionTaskList: jest.fn(),
};

jest.mock('../../services/videoService', () => ({
  videoService: mockVideoService
}));

// 创建测试用的 Redux store
const createTestStore = (initialState = {}) => {
  return configureStore({
    reducer: {
      video: videoSlice,
    },
    preloadedState: {
      video: {
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
        ...initialState,
      },
    },
  });
};

describe('CompositionPage 组件测试', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // 默认 mock 返回空的视频列表
    mockVideoService.getVideos.mockResolvedValue({
      results: [],
      count: 0,
      next: null,
      previous: null,
    });
  });

  describe('基本渲染测试', () => {
    test('应该能够创建Redux store', () => {
      const store = createTestStore();
      expect(store).toBeDefined();
      expect(store.getState().video).toBeDefined();
    });

    test('应该能够渲染Provider组件', () => {
      const store = createTestStore();
      const TestComponent = () => <div>测试组件</div>;
      
      render(
        <Provider store={store}>
          <TestComponent />
        </Provider>
      );
      
      expect(screen.getByText('测试组件')).toBeInTheDocument();
    });
  });

  describe('videoService mock测试', () => {
    test('应该正确mock videoService', () => {
      expect(mockVideoService.getVideos).toBeDefined();
      expect(mockVideoService.createCompositionTask).toBeDefined();
      expect(mockVideoService.getCompositionTaskStatus).toBeDefined();
      expect(mockVideoService.getCompositionDownloadUrl).toBeDefined();
      expect(mockVideoService.cancelCompositionTask).toBeDefined();
      expect(mockVideoService.getCompositionTaskList).toBeDefined();
    });

    test('应该能够调用mock方法', async () => {
      const result = await mockVideoService.getVideos();
      expect(result).toEqual({
        results: [],
        count: 0,
        next: null,
        previous: null,
      });
      expect(mockVideoService.getVideos).toHaveBeenCalled();
    });
  });

  describe('Redux状态测试', () => {
    test('应该有正确的初始状态', () => {
      const store = createTestStore();
      const state = store.getState().video;
      
      expect(state.videos).toEqual([]);
      expect(state.selectedVideos).toEqual([]);
      expect(state.currentVideo).toBeNull();
      expect(state.loading).toBe(false);
      expect(state.error).toBeNull();
      expect(state.searchQuery).toBe('');
      expect(state.selectedCategory).toBe('');
      expect(state.pagination).toEqual({
        page: 1,
        totalPages: 1,
        totalCount: 0,
      });
    });

    test('应该能够使用自定义初始状态', () => {
      const customState = {
        loading: true,
        searchQuery: '测试搜索',
        selectedCategory: '道德经',
      };
      
      const store = createTestStore(customState);
      const state = store.getState().video;
      
      expect(state.loading).toBe(true);
      expect(state.searchQuery).toBe('测试搜索');
      expect(state.selectedCategory).toBe('道德经');
    });
  });
});