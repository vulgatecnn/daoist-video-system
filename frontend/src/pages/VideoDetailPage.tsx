/**
 * 视频详情页面
 * 提供视频播放和详细信息展示
 */
import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import VideoPlayer from '../components/VideoPlayer';
import { videoService } from '../services/videoService';
import { Video } from '../types';

const VideoDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  
  const [video, setVideo] = useState<Video | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackStats, setPlaybackStats] = useState({
    currentTime: 0,
    duration: 0,
    hasStartedPlaying: false,
    sessionId: `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  });

  // 用于跟踪播放进度更新的引用
  const progressUpdateRef = useRef<NodeJS.Timeout | null>(null);
  const lastProgressUpdateRef = useRef<number>(0);

  // 加载视频详情和播放进度
  useEffect(() => {
    const loadVideo = async () => {
      if (!id) {
        setError('视频ID无效');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        
        // 并行加载视频详情和播放进度
        const [videoData, progressData] = await Promise.all([
          videoService.getVideoDetail(parseInt(id)),
          videoService.getVideoProgress(parseInt(id), playbackStats.sessionId).catch(() => ({
            last_position: 0,
            completion_percentage: 0,
            completed: false,
            duration_watched: 0
          }))
        ]);
        
        setVideo(videoData);
        
        // 如果有播放进度，更新状态
        if (progressData.last_position > 0) {
          setPlaybackStats(prev => ({
            ...prev,
            currentTime: progressData.last_position
          }));
        }
        
      } catch (err: any) {
        setError(err.message || '加载视频失败');
      } finally {
        setLoading(false);
      }
    };

    loadVideo();
  }, [id, playbackStats.sessionId]);

  // 清理定时器
  useEffect(() => {
    return () => {
      if (progressUpdateRef.current) {
        clearInterval(progressUpdateRef.current);
      }
    };
  }, []);

  // 格式化时长
  const formatDuration = (seconds: number): string => {
    if (!seconds || isNaN(seconds)) return '00:00';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    } else {
      return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }
  };

  // 格式化文件大小
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  // 格式化上传时间
  const formatUploadTime = (uploadTime: string): string => {
    const date = new Date(uploadTime);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // 更新播放进度到服务器
  const updateProgressToServer = async (currentTime: number, duration: number) => {
    if (!video || !id) return;
    
    try {
      await videoService.updatePlaybackProgress(parseInt(id), {
        current_time: currentTime,
        total_duration: duration,
        session_id: playbackStats.sessionId
      });
    } catch (error) {
      console.error('更新播放进度失败:', error);
    }
  };

  // 播放器事件处理
  const handlePlay = () => {
    setIsPlaying(true);
    
    if (!playbackStats.hasStartedPlaying) {
      setPlaybackStats(prev => ({ ...prev, hasStartedPlaying: true }));
    }

    // 开始定期更新播放进度
    if (progressUpdateRef.current) {
      clearInterval(progressUpdateRef.current);
    }
    
    progressUpdateRef.current = setInterval(() => {
      const now = Date.now();
      // 每10秒更新一次进度
      if (now - lastProgressUpdateRef.current >= 10000) {
        if (playbackStats.duration > 0) {
          updateProgressToServer(playbackStats.currentTime, playbackStats.duration);
          lastProgressUpdateRef.current = now;
        }
      }
    }, 1000);
  };

  const handlePause = () => {
    setIsPlaying(false);
    
    // 暂停时立即更新进度
    if (playbackStats.duration > 0) {
      updateProgressToServer(playbackStats.currentTime, playbackStats.duration);
    }
    
    // 清除定时器
    if (progressUpdateRef.current) {
      clearInterval(progressUpdateRef.current);
      progressUpdateRef.current = null;
    }
  };

  const handleEnded = () => {
    setIsPlaying(false);
    
    // 播放结束时更新进度
    if (playbackStats.duration > 0) {
      updateProgressToServer(playbackStats.duration, playbackStats.duration);
    }
    
    // 清除定时器
    if (progressUpdateRef.current) {
      clearInterval(progressUpdateRef.current);
      progressUpdateRef.current = null;
    }
  };

  const handleTimeUpdate = (currentTime: number, duration: number) => {
    setPlaybackStats(prev => ({
      ...prev,
      currentTime,
      duration
    }));
  };

  const handlePlayerError = (error: any) => {
    console.error('播放器错误:', error);
    setError('视频播放失败，请检查网络连接或稍后重试');
  };

  const handleGoBack = () => {
    // 页面离开时保存进度
    if (playbackStats.duration > 0 && video && id) {
      updateProgressToServer(playbackStats.currentTime, playbackStats.duration);
    }
    navigate(-1);
  };

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', backgroundColor: '#f9fafb', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            width: '40px',
            height: '40px',
            border: '3px solid #e5e7eb',
            borderTop: '3px solid #4f46e5',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 16px'
          }}></div>
          <div style={{ color: '#6b7280' }}>加载中...</div>
        </div>
      </div>
    );
  }

  if (error || !video) {
    return (
      <div style={{ minHeight: '100vh', backgroundColor: '#f9fafb', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center', padding: '2rem' }}>
          <svg style={{ width: '48px', height: '48px', margin: '0 auto 16px', color: '#ef4444' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#111827', marginBottom: '0.5rem' }}>
            加载失败
          </h2>
          <p style={{ color: '#6b7280', marginBottom: '1.5rem' }}>
            {error || '视频不存在'}
          </p>
          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
            <button
              onClick={handleGoBack}
              style={{
                backgroundColor: '#6b7280',
                color: 'white',
                border: 'none',
                padding: '0.75rem 1.5rem',
                borderRadius: '0.5rem',
                cursor: 'pointer',
                fontSize: '1rem'
              }}
            >
              返回
            </button>
            <button
              onClick={() => window.location.reload()}
              style={{
                backgroundColor: '#4f46e5',
                color: 'white',
                border: 'none',
                padding: '0.75rem 1.5rem',
                borderRadius: '0.5rem',
                cursor: 'pointer',
                fontSize: '1rem'
              }}
            >
              重试
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f9fafb' }}>
      <div className="container" style={{ paddingTop: '2rem', paddingBottom: '2rem' }}>
        {/* 返回按钮 */}
        <div style={{ marginBottom: '1.5rem' }}>
          <button
            onClick={handleGoBack}
            style={{
              display: 'flex',
              alignItems: 'center',
              backgroundColor: 'transparent',
              border: 'none',
              color: '#6b7280',
              cursor: 'pointer',
              fontSize: '1rem',
              padding: '0.5rem 0'
            }}
          >
            <svg style={{ width: '20px', height: '20px', marginRight: '0.5rem' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            返回视频列表
          </button>
        </div>

        <div className="video-detail-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', alignItems: 'start' }}>
          {/* 视频播放器区域 - 左侧 */}
          <div className="card" style={{ padding: 0, overflow: 'hidden', position: 'sticky', top: '1rem' }}>
            <VideoPlayer
              videoUrl={video.file_url || `${process.env.REACT_APP_MEDIA_URL?.replace('/media', '')}${video.file_path}`}
              title={video.title}
              poster={video.thumbnail_url || video.thumbnail}
              onPlay={handlePlay}
              onPause={handlePause}
              onEnded={handleEnded}
              onTimeUpdate={handleTimeUpdate}
              onError={handlePlayerError}
              style={{ borderRadius: '0.5rem', aspectRatio: '16/9' }}
            />
          </div>

          {/* 视频信息区域 - 右侧 */}
          <div className="card">
            <div style={{ marginBottom: '1.5rem' }}>
              <h1 style={{ fontSize: '2rem', fontWeight: 'bold', color: '#111827', marginBottom: '0.5rem' }}>
                {video.title}
              </h1>
              
              {/* 视频统计信息 */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', fontSize: '0.875rem', color: '#6b7280', marginBottom: '1rem' }}>
                <span>{video.view_count} 次播放</span>
                <span>•</span>
                <span>{formatUploadTime(video.upload_time)}</span>
                <span>•</span>
                <span>{formatFileSize(video.file_size)}</span>
                {playbackStats.duration > 0 && (
                  <>
                    <span>•</span>
                    <span>{formatDuration(playbackStats.duration)}</span>
                  </>
                )}
              </div>

              {/* 分类标签 */}
              <div style={{ marginBottom: '1rem' }}>
                <span style={{
                  backgroundColor: '#dbeafe',
                  color: '#1e40af',
                  padding: '0.25rem 0.75rem',
                  borderRadius: '1rem',
                  fontSize: '0.875rem',
                  fontWeight: '500'
                }}>
                  {video.category}
                </span>
              </div>

              {/* 播放状态指示器 */}
              {isPlaying && (
                <div style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  backgroundColor: '#dcfce7', 
                  color: '#166534', 
                  padding: '0.5rem 1rem', 
                  borderRadius: '0.5rem',
                  fontSize: '0.875rem',
                  marginBottom: '1rem'
                }}>
                  <div style={{
                    width: '8px',
                    height: '8px',
                    backgroundColor: '#22c55e',
                    borderRadius: '50%',
                    marginRight: '0.5rem',
                    animation: 'pulse 2s infinite'
                  }}></div>
                  正在播放 {playbackStats.currentTime > 0 && `• ${formatDuration(playbackStats.currentTime)}`}
                </div>
              )}

              {/* 播放进度指示器 */}
              {playbackStats.duration > 0 && playbackStats.currentTime > 0 && (
                <div style={{ marginBottom: '1rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                    <span style={{ fontSize: '0.875rem', color: '#6b7280' }}>播放进度</span>
                    <span style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                      {Math.round((playbackStats.currentTime / playbackStats.duration) * 100)}%
                    </span>
                  </div>
                  <div style={{ 
                    width: '100%', 
                    height: '4px', 
                    backgroundColor: '#e5e7eb', 
                    borderRadius: '2px',
                    overflow: 'hidden'
                  }}>
                    <div style={{
                      width: `${(playbackStats.currentTime / playbackStats.duration) * 100}%`,
                      height: '100%',
                      backgroundColor: '#4f46e5',
                      transition: 'width 0.3s ease'
                    }}></div>
                  </div>
                </div>
              )}
            </div>

            {/* 视频描述 */}
            {video.description && (
              <div>
                <h3 style={{ fontSize: '1.125rem', fontWeight: '600', color: '#111827', marginBottom: '0.75rem' }}>
                  视频描述
                </h3>
                <p style={{ 
                  color: '#374151', 
                  lineHeight: '1.6',
                  whiteSpace: 'pre-wrap'
                }}>
                  {video.description}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 添加动画样式 */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        
        .container {
          max-width: 1400px;
          margin: 0 auto;
          padding-left: 1rem;
          padding-right: 1rem;
        }
        
        @media (min-width: 768px) {
          .container {
            padding-left: 2rem;
            padding-right: 2rem;
          }
        }
        
        /* 小屏幕时改为单列布局 */
        @media (max-width: 1023px) {
          .video-detail-grid {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </div>
  );
};

export default VideoDetailPage;