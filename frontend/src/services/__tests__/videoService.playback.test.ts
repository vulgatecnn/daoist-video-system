/**
 * 视频播放统计服务单元测试
 * 测试播放次数统计和播放进度记录功能
 */
import { videoService } from '../videoService';

// Mock api module
jest.mock('../api', () => ({
  __esModule: true,
  default: {
    post: jest.fn(),
    get: jest.fn(),
    defaults: {
      baseURL: 'http://localhost:8000/api',
    },
  },
}));

import api from '../api';
const mockedApi = api as jest.Mocked<typeof api>;

describe('视频播放统计服务测试', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('播放次数统计', () => {
    test('应该能够增加视频播放次数', async () => {
      const videoId = 1;
      mockedApi.post.mockResolvedValue({ data: { success: true } });

      await videoService.incrementViewCount(videoId);

      expect(mockedApi.post).toHaveBeenCalledWith(`/videos/${videoId}/view/`);
      expect(mockedApi.post).toHaveBeenCalledTimes(1);
    });

    test('播放次数增加失败时应该抛出错误', async () => {
      const videoId = 1;
      const errorMessage = '网络错误';
      mockedApi.post.mockRejectedValue(new Error(errorMessage));

      await expect(videoService.incrementViewCount(videoId)).rejects.toThrow(errorMessage);
    });
  });

  describe('播放进度记录', () => {
    test('应该能够更新播放进度', async () => {
      const videoId = 1;
      const progressData = {
        current_time: 30,
        total_duration: 100,
        session_id: 'test-session-123',
      };

      const mockResponse = {
        id: 1,
        video: videoId,
        current_time: 30,
        total_duration: 100,
        session_id: 'test-session-123',
        updated_at: '2024-01-01T00:00:00Z',
      };

      mockedApi.post.mockResolvedValue({ data: mockResponse });

      const result = await videoService.updatePlaybackProgress(videoId, progressData);

      expect(mockedApi.post).toHaveBeenCalledWith(
        `/videos/${videoId}/progress/`,
        progressData
      );
      expect(result).toEqual(mockResponse);
    });

    test('应该能够获取视频播放进度', async () => {
      const videoId = 1;
      const sessionId = 'test-session-123';

      const mockResponse = {
        current_time: 30,
        total_duration: 100,
        progress_percentage: 30,
      };

      mockedApi.get.mockResolvedValue({ data: mockResponse });

      const result = await videoService.getVideoProgress(videoId, sessionId);

      expect(mockedApi.get).toHaveBeenCalledWith(
        `/videos/${videoId}/progress/get/`,
        { params: { session_id: sessionId } }
      );
      expect(result).toEqual(mockResponse);
    });

    test('获取播放进度时不传session_id应该使用空参数', async () => {
      const videoId = 1;

      const mockResponse = {
        current_time: 0,
        total_duration: 100,
        progress_percentage: 0,
      };

      mockedApi.get.mockResolvedValue({ data: mockResponse });

      const result = await videoService.getVideoProgress(videoId);

      expect(mockedApi.get).toHaveBeenCalledWith(
        `/videos/${videoId}/progress/get/`,
        { params: {} }
      );
      expect(result).toEqual(mockResponse);
    });

    test('更新播放进度失败时应该抛出错误', async () => {
      const videoId = 1;
      const progressData = {
        current_time: 30,
        total_duration: 100,
      };

      const errorMessage = '保存失败';
      mockedApi.post.mockRejectedValue(new Error(errorMessage));

      await expect(
        videoService.updatePlaybackProgress(videoId, progressData)
      ).rejects.toThrow(errorMessage);
    });
  });

  describe('播放历史记录', () => {
    test('应该能够获取播放历史列表', async () => {
      const mockHistory = [
        {
          id: 1,
          video: {
            id: 1,
            title: '测试视频1',
            thumbnail: '/media/thumbnails/test1.jpg',
          },
          current_time: 30,
          total_duration: 100,
          progress_percentage: 30,
          last_played: '2024-01-01T00:00:00Z',
        },
        {
          id: 2,
          video: {
            id: 2,
            title: '测试视频2',
            thumbnail: '/media/thumbnails/test2.jpg',
          },
          current_time: 50,
          total_duration: 120,
          progress_percentage: 41.67,
          last_played: '2024-01-02T00:00:00Z',
        },
      ];

      mockedApi.get.mockResolvedValue({ data: mockHistory });

      const result = await videoService.getPlaybackHistory();

      expect(mockedApi.get).toHaveBeenCalledWith('/videos/playback-history/', { params: {} });
      expect(result).toEqual(mockHistory);
      expect(result).toHaveLength(2);
    });

    test('应该能够按视频ID筛选播放历史', async () => {
      const videoId = 1;
      const mockHistory = [
        {
          id: 1,
          video: {
            id: videoId,
            title: '测试视频1',
            thumbnail: '/media/thumbnails/test1.jpg',
          },
          current_time: 30,
          total_duration: 100,
          progress_percentage: 30,
          last_played: '2024-01-01T00:00:00Z',
        },
      ];

      mockedApi.get.mockResolvedValue({ data: mockHistory });

      const result = await videoService.getPlaybackHistory({ video_id: videoId });

      expect(mockedApi.get).toHaveBeenCalledWith('/videos/playback-history/', {
        params: { video_id: videoId },
      });
      expect(result).toEqual(mockHistory);
    });

    test('应该能够限制播放历史返回数量', async () => {
      const limit = 5;
      const mockHistory = Array(5).fill(null).map((_, index) => ({
        id: index + 1,
        video: {
          id: index + 1,
          title: `测试视频${index + 1}`,
          thumbnail: `/media/thumbnails/test${index + 1}.jpg`,
        },
        current_time: 30,
        total_duration: 100,
        progress_percentage: 30,
        last_played: '2024-01-01T00:00:00Z',
      }));

      mockedApi.get.mockResolvedValue({ data: mockHistory });

      const result = await videoService.getPlaybackHistory({ limit });

      expect(mockedApi.get).toHaveBeenCalledWith('/videos/playback-history/', {
        params: { limit },
      });
      expect(result).toHaveLength(5);
    });

    test('获取播放历史失败时应该抛出错误', async () => {
      const errorMessage = '获取失败';
      mockedApi.get.mockRejectedValue(new Error(errorMessage));

      await expect(videoService.getPlaybackHistory()).rejects.toThrow(errorMessage);
    });
  });

  describe('播放进度准确性测试', () => {
    test('播放进度百分比应该正确计算', async () => {
      const videoId = 1;
      const testCases = [
        { current_time: 0, total_duration: 100, expected: 0 },
        { current_time: 25, total_duration: 100, expected: 25 },
        { current_time: 50, total_duration: 100, expected: 50 },
        { current_time: 75, total_duration: 100, expected: 75 },
        { current_time: 100, total_duration: 100, expected: 100 },
      ];

      for (const testCase of testCases) {
        const mockResponse = {
          current_time: testCase.current_time,
          total_duration: testCase.total_duration,
          progress_percentage: testCase.expected,
        };

        mockedApi.post.mockResolvedValue({ data: mockResponse });

        const result = await videoService.updatePlaybackProgress(videoId, {
          current_time: testCase.current_time,
          total_duration: testCase.total_duration,
        });

        expect(result.progress_percentage).toBe(testCase.expected);
      }
    });

    test('播放时间不应该超过总时长', async () => {
      const videoId = 1;
      const progressData = {
        current_time: 150, // 超过总时长
        total_duration: 100,
      };

      // 后端应该处理这种情况，将current_time限制为total_duration
      const mockResponse = {
        current_time: 100, // 被限制为总时长
        total_duration: 100,
        progress_percentage: 100,
      };

      mockedApi.post.mockResolvedValue({ data: mockResponse });

      const result = await videoService.updatePlaybackProgress(videoId, progressData);

      expect(result.current_time).toBeLessThanOrEqual(result.total_duration);
      expect(result.progress_percentage).toBe(100);
    });

    test('播放时间不应该为负数', async () => {
      const videoId = 1;
      const progressData = {
        current_time: -10, // 负数时间
        total_duration: 100,
      };

      // 后端应该处理这种情况，将current_time设置为0
      const mockResponse = {
        current_time: 0, // 被设置为0
        total_duration: 100,
        progress_percentage: 0,
      };

      mockedApi.post.mockResolvedValue({ data: mockResponse });

      const result = await videoService.updatePlaybackProgress(videoId, progressData);

      expect(result.current_time).toBeGreaterThanOrEqual(0);
      expect(result.progress_percentage).toBe(0);
    });
  });

  describe('会话管理测试', () => {
    test('同一会话应该能够更新播放进度', async () => {
      const videoId = 1;
      const sessionId = 'test-session-123';

      // 第一次更新
      const firstUpdate = {
        current_time: 30,
        total_duration: 100,
        session_id: sessionId,
      };

      mockedApi.post.mockResolvedValue({
        data: { ...firstUpdate, id: 1 },
      });

      await videoService.updatePlaybackProgress(videoId, firstUpdate);

      // 第二次更新（同一会话）
      const secondUpdate = {
        current_time: 60,
        total_duration: 100,
        session_id: sessionId,
      };

      mockedApi.post.mockResolvedValue({
        data: { ...secondUpdate, id: 1 }, // 同一个记录ID
      });

      const result = await videoService.updatePlaybackProgress(videoId, secondUpdate);

      expect(result.session_id).toBe(sessionId);
      expect(result.current_time).toBe(60);
    });

    test('不同会话应该创建不同的播放记录', async () => {
      const videoId = 1;

      // 第一个会话
      const session1 = {
        current_time: 30,
        total_duration: 100,
        session_id: 'session-1',
      };

      mockedApi.post.mockResolvedValue({
        data: { ...session1, id: 1 },
      });

      const result1 = await videoService.updatePlaybackProgress(videoId, session1);

      // 第二个会话
      const session2 = {
        current_time: 50,
        total_duration: 100,
        session_id: 'session-2',
      };

      mockedApi.post.mockResolvedValue({
        data: { ...session2, id: 2 }, // 不同的记录ID
      });

      const result2 = await videoService.updatePlaybackProgress(videoId, session2);

      expect(result1.id).not.toBe(result2.id);
      expect(result1.session_id).not.toBe(result2.session_id);
    });
  });
});
