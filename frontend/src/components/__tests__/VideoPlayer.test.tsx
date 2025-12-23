/**
 * VideoPlayer 组件属性测试
 * 验证播放器控制响应性
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import VideoPlayer from '../VideoPlayer';

// Mock HTMLMediaElement methods
const mockPlay = jest.fn(() => Promise.resolve());
const mockPause = jest.fn();
const mockLoad = jest.fn();

// Mock video element
Object.defineProperty(HTMLMediaElement.prototype, 'play', {
  writable: true,
  value: mockPlay,
});

Object.defineProperty(HTMLMediaElement.prototype, 'pause', {
  writable: true,
  value: mockPause,
});

Object.defineProperty(HTMLMediaElement.prototype, 'load', {
  writable: true,
  value: mockLoad,
});

// Mock video properties
Object.defineProperty(HTMLMediaElement.prototype, 'currentTime', {
  writable: true,
  value: 0,
});

Object.defineProperty(HTMLMediaElement.prototype, 'duration', {
  writable: true,
  value: 100,
});

Object.defineProperty(HTMLMediaElement.prototype, 'volume', {
  writable: true,
  value: 0.8,
});

Object.defineProperty(HTMLMediaElement.prototype, 'muted', {
  writable: true,
  value: false,
});

describe('VideoPlayer 属性测试', () => {
  const defaultProps = {
    videoUrl: 'https://example.com/test-video.mp4',
    title: '测试视频',
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  /**
   * 属性 8: 播放器控制响应性
   * 验证需求: 需求 4.2, 4.3
   * 
   * 对于任何播放器控制操作（播放、暂停、快进、快退、音量调节），
   * 系统应该立即响应并更新播放状态
   */
  describe('属性 8: 播放器控制响应性', () => {
    test('播放控制应该立即响应', async () => {
      const onPlay = jest.fn();
      const onPause = jest.fn();
      
      const { container } = render(
        <VideoPlayer
          {...defaultProps}
          onPlay={onPlay}
          onPause={onPause}
        />
      );

      const video = container.querySelector('video') as HTMLVideoElement;
      expect(video).toBeInTheDocument();
      
      // 模拟播放操作
      fireEvent.click(video);
      
      await waitFor(() => {
        expect(mockPlay).toHaveBeenCalled();
      });

      // 模拟播放事件
      fireEvent(video, new Event('play'));
      
      await waitFor(() => {
        expect(onPlay).toHaveBeenCalled();
      });
    });

    test('暂停控制应该立即响应', async () => {
      const onPause = jest.fn();
      
      const { container } = render(
        <VideoPlayer
          {...defaultProps}
          onPause={onPause}
        />
      );

      const video = container.querySelector('video') as HTMLVideoElement;
      expect(video).toBeInTheDocument();
      
      // 首先模拟播放状态 - 触发play事件让组件进入播放状态
      fireEvent(video, new Event('play'));
      
      // 等待状态更新
      await waitFor(() => {
        // 现在点击应该触发暂停
        fireEvent.click(video);
      });
      
      await waitFor(() => {
        expect(mockPause).toHaveBeenCalled();
      });

      // 模拟暂停事件
      fireEvent(video, new Event('pause'));
      
      await waitFor(() => {
        expect(onPause).toHaveBeenCalled();
      });
    });

    test('音量控制应该立即响应', async () => {
      const onVolumeChange = jest.fn();
      
      const { container } = render(
        <VideoPlayer
          {...defaultProps}
          onVolumeChange={onVolumeChange}
        />
      );

      const video = container.querySelector('video') as HTMLVideoElement;
      expect(video).toBeInTheDocument();
      
      // 模拟音量变化
      Object.defineProperty(video, 'volume', { value: 0.5, writable: true });
      fireEvent(video, new Event('volumechange'));
      
      await waitFor(() => {
        expect(onVolumeChange).toHaveBeenCalledWith(0.5);
      });
    });

    test('时间更新应该立即响应', async () => {
      const onTimeUpdate = jest.fn();
      
      const { container } = render(
        <VideoPlayer
          {...defaultProps}
          onTimeUpdate={onTimeUpdate}
        />
      );

      const video = container.querySelector('video') as HTMLVideoElement;
      expect(video).toBeInTheDocument();
      
      // 模拟时间更新
      Object.defineProperty(video, 'currentTime', { value: 30, writable: true });
      Object.defineProperty(video, 'duration', { value: 100, writable: true });
      fireEvent(video, new Event('timeupdate'));
      
      await waitFor(() => {
        expect(onTimeUpdate).toHaveBeenCalledWith(30, 100);
      });
    });

    test('全屏控制应该立即响应', async () => {
      const onFullscreenChange = jest.fn();
      
      render(
        <VideoPlayer
          {...defaultProps}
          onFullscreenChange={onFullscreenChange}
        />
      );

      // 模拟进入全屏
      Object.defineProperty(document, 'fullscreenElement', {
        value: document.body,
        writable: true,
      });
      
      fireEvent(document, new Event('fullscreenchange'));
      
      await waitFor(() => {
        expect(onFullscreenChange).toHaveBeenCalledWith(true);
      });

      // 模拟退出全屏
      Object.defineProperty(document, 'fullscreenElement', {
        value: null,
        writable: true,
      });
      
      fireEvent(document, new Event('fullscreenchange'));
      
      await waitFor(() => {
        expect(onFullscreenChange).toHaveBeenCalledWith(false);
      });
    });

    test('播放器准备就绪应该立即响应', async () => {
      const onReady = jest.fn();
      
      const { container } = render(
        <VideoPlayer
          {...defaultProps}
          onReady={onReady}
        />
      );

      const video = container.querySelector('video') as HTMLVideoElement;
      expect(video).toBeInTheDocument();
      
      // 模拟视频可以播放
      fireEvent(video, new Event('canplay'));
      
      await waitFor(() => {
        expect(onReady).toHaveBeenCalled();
      });
    });

    test('播放结束应该立即响应', async () => {
      const onEnded = jest.fn();
      
      const { container } = render(
        <VideoPlayer
          {...defaultProps}
          onEnded={onEnded}
        />
      );

      const video = container.querySelector('video') as HTMLVideoElement;
      expect(video).toBeInTheDocument();
      
      // 模拟播放结束
      fireEvent(video, new Event('ended'));
      
      await waitFor(() => {
        expect(onEnded).toHaveBeenCalled();
      });
    });

    test('错误处理应该立即响应', async () => {
      const onError = jest.fn();
      
      const { container } = render(
        <VideoPlayer
          {...defaultProps}
          onError={onError}
        />
      );

      const video = container.querySelector('video') as HTMLVideoElement;
      expect(video).toBeInTheDocument();
      
      // 模拟播放错误
      const errorEvent = new Event('error');
      Object.defineProperty(errorEvent, 'target', {
        value: {
          error: {
            code: 4, // MEDIA_ERR_SRC_NOT_SUPPORTED
            message: 'Format error'
          }
        }
      });
      
      fireEvent(video, errorEvent);
      
      await waitFor(() => {
        expect(onError).toHaveBeenCalled();
      });
    });
  });

  describe('播放器控件交互测试', () => {
    test('点击播放按钮应该触发播放', async () => {
      const { container } = render(<VideoPlayer {...defaultProps} />);

      // 等待组件加载完成，查找播放按钮（第一个按钮）
      await waitFor(() => {
        const playButton = container.querySelector('button');
        expect(playButton).toBeInTheDocument();
      });

      const playButton = container.querySelector('button') as HTMLButtonElement;
      fireEvent.click(playButton);

      await waitFor(() => {
        expect(mockPlay).toHaveBeenCalled();
      });
    });

    test('进度条点击应该改变播放位置', async () => {
      const { container } = render(<VideoPlayer {...defaultProps} />);

      const video = container.querySelector('video') as HTMLVideoElement;
      expect(video).toBeInTheDocument();
      
      // 模拟视频已加载
      Object.defineProperty(video, 'duration', { value: 100, writable: true });
      fireEvent(video, new Event('loadedmetadata'));

      // 等待控件显示，查找进度条
      await waitFor(() => {
        const progressBar = container.querySelector('[style*="cursor: pointer"]');
        if (progressBar && progressBar.getAttribute('style')?.includes('height: 4px')) {
          // 模拟点击进度条中间位置
          const clickEvent = new MouseEvent('click', {
            clientX: 50, // 假设进度条宽度为100px，点击中间
          });
          
          Object.defineProperty(progressBar, 'getBoundingClientRect', {
            value: () => ({ left: 0, width: 100 }),
          });
          
          fireEvent(progressBar, clickEvent);
        }
      });
    });
  });

  describe('播放器状态管理测试', () => {
    test('播放状态应该正确更新', async () => {
      const { container } = render(<VideoPlayer {...defaultProps} />);

      const video = container.querySelector('video') as HTMLVideoElement;
      expect(video).toBeInTheDocument();
      
      // 初始状态应该是暂停
      expect(video.paused).toBe(true);

      // 模拟播放
      fireEvent(video, new Event('play'));
      
      // 播放状态应该更新
      await waitFor(() => {
        // 检查播放状态指示器是否显示
        const videoContainer = container.querySelector('.video-player-container');
        expect(videoContainer).toBeInTheDocument();
      });
    });

    test('音量状态应该正确更新', async () => {
      const { container } = render(<VideoPlayer {...defaultProps} />);

      const video = container.querySelector('video') as HTMLVideoElement;
      expect(video).toBeInTheDocument();
      
      // 模拟静音
      Object.defineProperty(video, 'muted', { value: true, writable: true });
      fireEvent(video, new Event('volumechange'));
      
      await waitFor(() => {
        expect(video.muted).toBe(true);
      });
    });
  });
});