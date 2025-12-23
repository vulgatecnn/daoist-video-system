/**
 * 视频选择功能属性测试
 * 验证需求: 需求 5.1, 5.2, 5.3, 5.5
 * 
 * 属性 9: 视频选择状态一致性
 * 对于任何视频选择操作序列，选中视频的数量、预览列表内容和复选框状态应该始终保持一致
 */
import { configureStore } from '@reduxjs/toolkit';
const fc = require('fast-check');
import videoReducer, {
  addSelectedVideo,
  removeSelectedVideo,
  clearSelectedVideos,
  reorderSelectedVideos,
} from '../../store/slices/videoSlice';
import authReducer from '../../store/slices/authSlice';
import { Video } from '../../types';

// 生成测试视频数据的生成器
const videoGenerator = fc.record({
  id: fc.integer({ min: 1, max: 1000 }),
  title: fc.string({ minLength: 1, maxLength: 100 }),
  description: fc.string({ minLength: 0, maxLength: 200 }),
  file_path: fc.string({ minLength: 1 }),
  thumbnail: fc.string({ minLength: 1 }),
  duration: fc.oneof(
    fc.constant('00:30'),
    fc.constant('01:45'),
    fc.constant('02:30'),
    fc.constant('05:00')
  ),
  file_size: fc.integer({ min: 1000000, max: 100000000 }),
  category: fc.oneof(
    fc.constant('道德经'),
    fc.constant('太上感应篇'),
    fc.constant('清静经'),
    fc.constant('黄庭经'),
    fc.constant('阴符经'),
    fc.constant('其他经文')
  ),
  upload_time: fc.date().map(d => d.toISOString()),
  uploader: fc.integer({ min: 1, max: 100 }),
  view_count: fc.integer({ min: 0, max: 10000 }),
  is_active: fc.constant(true)
});

// 视频选择操作生成器
const videoSelectionOperation = fc.oneof(
  fc.record({ type: fc.constant('select'), videoId: fc.integer({ min: 1, max: 1000 }) }),
  fc.record({ type: fc.constant('deselect'), videoId: fc.integer({ min: 1, max: 1000 }) }),
  fc.record({ type: fc.constant('clear') })
);

// 创建测试store
const createTestStore = (initialVideos: Video[] = []) => {
  return configureStore({
    reducer: {
      video: videoReducer,
      auth: authReducer,
    },
    preloadedState: {
      video: {
        videos: initialVideos,
        selectedVideos: [],
        currentVideo: null,
        loading: false,
        error: null,
        searchQuery: '',
        selectedCategory: '',
        pagination: {
          page: 1,
          totalPages: 1,
          totalCount: initialVideos.length,
        },
      },
      auth: {
        user: { id: 1, username: 'testuser', email: 'test@example.com', role: 'user' },
        accessToken: 'mock-token',
        refreshToken: 'mock-refresh-token',
        isAuthenticated: true,
        loading: false,
        error: null,
      },
    },
  });
};

describe('视频选择状态管理属性测试', () => {
  /**
   * 属性 9: 视频选择状态一致性
   * 验证需求: 需求 5.1, 5.2, 5.3, 5.5
   */
  test('属性 9: 视频选择状态一致性 - 选中视频的数量、预览列表内容和复选框状态应该始终保持一致', () => {
    fc.assert(
      fc.property(
        fc.array(videoGenerator, { minLength: 1, maxLength: 10 }),
        fc.array(videoSelectionOperation, { minLength: 1, maxLength: 20 }),
        (videos: Video[], operations) => {
          // 确保视频ID唯一
          const uniqueVideos = videos.map((video, index) => ({
            ...video,
            id: index + 1,
          }));

          const store = createTestStore(uniqueVideos);
          
          // 跟踪预期的选中状态
          const expectedSelectedIds = new Set<number>();

          // 执行操作序列
          for (const operation of operations) {
            if (operation.type === 'select') {
              const videoExists = uniqueVideos.some(v => v.id === operation.videoId);
              if (videoExists && !expectedSelectedIds.has(operation.videoId)) {
                expectedSelectedIds.add(operation.videoId);
                const video = uniqueVideos.find(v => v.id === operation.videoId)!;
                store.dispatch(addSelectedVideo(video));
              }
            } else if (operation.type === 'deselect') {
              if (expectedSelectedIds.has(operation.videoId)) {
                expectedSelectedIds.delete(operation.videoId);
                store.dispatch(removeSelectedVideo(operation.videoId));
              }
            } else if (operation.type === 'clear') {
              expectedSelectedIds.clear();
              store.dispatch(clearSelectedVideos());
            }
          }

          // 验证最终状态一致性
          const finalState = store.getState();
          const actualSelectedIds = new Set(finalState.video.selectedVideos.map(v => v.id));
          
          // 1. 验证Redux状态中的选中视频数量与预期一致
          expect(actualSelectedIds.size).toBe(expectedSelectedIds.size);
          
          // 2. 验证Redux状态中的选中视频ID与预期一致
          expectedSelectedIds.forEach(id => {
            expect(actualSelectedIds.has(id)).toBe(true);
          });
          
          // 3. 验证选中视频列表中没有重复项
          const selectedVideoIds = finalState.video.selectedVideos.map(v => v.id);
          const uniqueSelectedIds = [...new Set(selectedVideoIds)];
          expect(selectedVideoIds.length).toBe(uniqueSelectedIds.length);
          
          // 4. 验证所有选中的视频都存在于原始视频列表中
          finalState.video.selectedVideos.forEach(selectedVideo => {
            const originalVideo = uniqueVideos.find(v => v.id === selectedVideo.id);
            expect(originalVideo).toBeDefined();
            expect(selectedVideo).toEqual(originalVideo);
          });
        }
      ),
      { 
        numRuns: 100,
        verbose: true
      }
    );
  });

  /**
   * 属性测试：视频选择操作的幂等性
   * 验证重复选择同一个视频不会改变状态
   */
  test('属性测试：视频选择操作的幂等性', () => {
    fc.assert(
      fc.property(
        fc.array(videoGenerator, { minLength: 1, maxLength: 5 }),
        fc.integer({ min: 0, max: 4 }),
        fc.integer({ min: 2, max: 5 }),
        (videos: Video[], videoIndex: number, repeatCount: number) => {
          const uniqueVideos = videos.map((video, index) => ({
            ...video,
            id: index + 1,
          }));

          if (videoIndex >= uniqueVideos.length) return;

          const store = createTestStore(uniqueVideos);
          const targetVideo = uniqueVideos[videoIndex];

          // 重复选择同一个视频多次
          for (let i = 0; i < repeatCount; i++) {
            store.dispatch(addSelectedVideo(targetVideo));
          }

          // 验证最终状态：视频只被选择一次
          const finalState = store.getState();
          const selectedCount = finalState.video.selectedVideos.filter(v => v.id === targetVideo.id).length;
          expect(selectedCount).toBe(1);
          expect(finalState.video.selectedVideos.some(v => v.id === targetVideo.id)).toBe(true);
        }
      ),
      { numRuns: 50 }
    );
  });

  /**
   * 属性测试：视频取消选择的正确性
   * 验证取消选择操作能正确移除视频
   */
  test('属性测试：视频取消选择的正确性', () => {
    fc.assert(
      fc.property(
        fc.array(videoGenerator, { minLength: 2, maxLength: 5 }),
        (videos: Video[]) => {
          const uniqueVideos = videos.map((video, index) => ({
            ...video,
            id: index + 1,
          }));

          const store = createTestStore(uniqueVideos);

          // 先选择所有视频
          uniqueVideos.forEach(video => {
            store.dispatch(addSelectedVideo(video));
          });

          let state = store.getState();
          expect(state.video.selectedVideos.length).toBe(uniqueVideos.length);

          // 随机取消选择一个视频
          const randomVideo = uniqueVideos[Math.floor(Math.random() * uniqueVideos.length)];
          store.dispatch(removeSelectedVideo(randomVideo.id));

          // 验证状态
          const finalState = store.getState();
          expect(finalState.video.selectedVideos.length).toBe(uniqueVideos.length - 1);
          expect(finalState.video.selectedVideos.some(v => v.id === randomVideo.id)).toBe(false);
        }
      ),
      { numRuns: 30 }
    );
  });

  /**
   * 属性测试：清空选择功能的正确性
   * 验证清空选择能正确重置所有状态
   */
  test('属性测试：清空选择功能的正确性', () => {
    fc.assert(
      fc.property(
        fc.array(videoGenerator, { minLength: 1, maxLength: 8 }),
        (videos: Video[]) => {
          const uniqueVideos = videos.map((video, index) => ({
            ...video,
            id: index + 1,
          }));

          const store = createTestStore(uniqueVideos);

          // 随机选择一些视频
          const videosToSelect = uniqueVideos.slice(0, Math.ceil(uniqueVideos.length / 2));
          videosToSelect.forEach(video => {
            store.dispatch(addSelectedVideo(video));
          });

          let state = store.getState();
          expect(state.video.selectedVideos.length).toBe(videosToSelect.length);

          // 清空选择
          store.dispatch(clearSelectedVideos());

          // 验证所有状态都被重置
          const finalState = store.getState();
          expect(finalState.video.selectedVideos.length).toBe(0);
        }
      ),
      { numRuns: 25 }
    );
  });

  /**
   * 属性测试：视频重新排序的正确性
   * 验证重新排序操作保持选中视频的完整性
   */
  test('属性测试：视频重新排序的正确性', () => {
    fc.assert(
      fc.property(
        fc.array(videoGenerator, { minLength: 2, maxLength: 6 }),
        (videos: Video[]) => {
          const uniqueVideos = videos.map((video, index) => ({
            ...video,
            id: index + 1,
          }));

          const store = createTestStore(uniqueVideos);

          // 选择所有视频
          uniqueVideos.forEach(video => {
            store.dispatch(addSelectedVideo(video));
          });

          const originalState = store.getState();
          const originalSelectedVideos = [...originalState.video.selectedVideos];

          // 随机重新排序
          const shuffledVideos = [...originalSelectedVideos].sort(() => Math.random() - 0.5);
          store.dispatch(reorderSelectedVideos(shuffledVideos));

          // 验证重新排序后的状态
          const finalState = store.getState();
          
          // 1. 视频数量应该保持不变
          expect(finalState.video.selectedVideos.length).toBe(originalSelectedVideos.length);
          
          // 2. 所有原始视频都应该还在选中列表中
          originalSelectedVideos.forEach(originalVideo => {
            expect(finalState.video.selectedVideos.some(v => v.id === originalVideo.id)).toBe(true);
          });
          
          // 3. 不应该有重复的视频
          const selectedIds = finalState.video.selectedVideos.map(v => v.id);
          const uniqueIds = [...new Set(selectedIds)];
          expect(selectedIds.length).toBe(uniqueIds.length);
        }
      ),
      { numRuns: 30 }
    );
  });
});