/**
 * 视频合成页面
 * 支持多视频选择、拖拽排序和合成任务管理
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { RootState } from '../store';
import { videoService } from '../services/videoService';
import { Video, PaginatedResponse, CompositionTask } from '../types';
import {
  setLoading,
  setVideos,
  setError,
  clearError,
  addSelectedVideo,
  removeSelectedVideo,
  clearSelectedVideos,
  reorderSelectedVideos,
  setSearchQuery,
  setSelectedCategory,
  setPagination,
} from '../store/slices/videoSlice';

interface VideoSelectionCardProps {
  video: Video;
  isSelected: boolean;
  onToggleSelect: (video: Video) => void;
}

// 视频选择卡片组件
const VideoSelectionCard: React.FC<VideoSelectionCardProps> = ({ 
  video, 
  isSelected, 
  onToggleSelect 
}) => {
  const [imageError, setImageError] = useState(false);
  
  // 格式化时长
  const formatDuration = (duration: string): string => {
    if (!duration) return '未知';
    
    const parts = duration.split(':');
    if (parts.length === 3) {
      const hours = parseInt(parts[0]);
      const minutes = parseInt(parts[1]);
      const seconds = parseInt(parts[2]);
      
      if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
      } else {
        return `${minutes}:${seconds.toString().padStart(2, '0')}`;
      }
    }
    return duration;
  };

  return (
    <div
      className="video-selection-card"
      style={{
        background: 'white',
        borderRadius: '8px',
        boxShadow: isSelected ? '0 4px 12px rgba(79, 70, 229, 0.3)' : '0 2px 8px rgba(0,0,0,0.1)',
        border: isSelected ? '2px solid #4f46e5' : '2px solid transparent',
        overflow: 'hidden',
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        marginBottom: '1rem',
        position: 'relative'
      }}
      onClick={() => onToggleSelect(video)}
    >
      {/* 选择复选框 */}
      <div style={{
        position: 'absolute',
        top: '8px',
        left: '8px',
        zIndex: 10,
        backgroundColor: 'rgba(255, 255, 255, 0.9)',
        borderRadius: '4px',
        padding: '4px'
      }}>
        <input
          type="checkbox"
          checked={isSelected}
          onChange={() => onToggleSelect(video)}
          style={{
            width: '18px',
            height: '18px',
            cursor: 'pointer'
          }}
          onClick={(e) => e.stopPropagation()}
        />
      </div>

      {/* 缩略图 */}
      <div style={{ position: 'relative', aspectRatio: '16/9', backgroundColor: '#f3f4f6' }}>
        {!imageError && video.thumbnail ? (
          <img
            src={video.thumbnail}
            alt={video.title}
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            onError={() => setImageError(true)}
          />
        ) : (
          <div style={{ 
            width: '100%', 
            height: '100%', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            backgroundColor: '#f9fafb'
          }}>
            <svg style={{ width: '48px', height: '48px', color: '#9ca3af' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </div>
        )}
        
        {/* 时长标签 */}
        {video.duration && (
          <div style={{
            position: 'absolute',
            bottom: '8px',
            right: '8px',
            backgroundColor: 'rgba(0,0,0,0.75)',
            color: 'white',
            fontSize: '12px',
            padding: '4px 8px',
            borderRadius: '4px'
          }}>
            {formatDuration(video.duration)}
          </div>
        )}
      </div>

      {/* 视频信息 */}
      <div style={{ padding: '12px' }}>
        <h3 style={{
          fontWeight: '600',
          color: '#111827',
          fontSize: '16px',
          marginBottom: '4px',
          lineHeight: '1.4',
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden'
        }}>
          {video.title}
        </h3>
        
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          fontSize: '12px',
          color: '#6b7280'
        }}>
          <span style={{
            backgroundColor: '#dbeafe',
            color: '#1e40af',
            padding: '2px 6px',
            borderRadius: '8px',
            fontSize: '11px'
          }}>
            {video.category}
          </span>
          <span>{video.view_count} 次播放</span>
        </div>
      </div>
    </div>
  );
};

interface SelectedVideoItemProps {
  video: Video;
  index: number;
  onRemove: (video: Video) => void;
  onMoveUp: (index: number) => void;
  onMoveDown: (index: number) => void;
  totalCount: number;
}

// 已选择视频项组件
const SelectedVideoItem: React.FC<SelectedVideoItemProps> = ({
  video,
  index,
  onRemove,
  onMoveUp,
  onMoveDown,
  totalCount
}) => {
  const [imageError, setImageError] = useState(false);

  return (
    <div 
      data-testid={`selected-video-${video.id}`}
      style={{
        display: 'flex',
        alignItems: 'center',
        backgroundColor: 'white',
        border: '1px solid #e5e7eb',
        borderRadius: '8px',
        padding: '12px',
        marginBottom: '8px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
      }}>
      {/* 序号 */}
      <div style={{
        width: '32px',
        height: '32px',
        backgroundColor: '#4f46e5',
        color: 'white',
        borderRadius: '50%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '14px',
        fontWeight: '600',
        marginRight: '12px',
        flexShrink: 0
      }}>
        {index + 1}
      </div>

      {/* 缩略图 */}
      <div style={{
        width: '60px',
        height: '40px',
        backgroundColor: '#f3f4f6',
        borderRadius: '4px',
        overflow: 'hidden',
        marginRight: '12px',
        flexShrink: 0
      }}>
        {!imageError && video.thumbnail ? (
          <img
            src={video.thumbnail}
            alt={video.title}
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            onError={() => setImageError(true)}
          />
        ) : (
          <div style={{ 
            width: '100%', 
            height: '100%', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center'
          }}>
            <svg style={{ width: '20px', height: '20px', color: '#9ca3af' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </div>
        )}
      </div>

      {/* 视频信息 */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <h4 style={{
          fontSize: '14px',
          fontWeight: '500',
          color: '#111827',
          marginBottom: '2px',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap'
        }}>
          {video.title}
        </h4>
        <p style={{
          fontSize: '12px',
          color: '#6b7280',
          margin: 0
        }}>
          {video.category}
        </p>
      </div>

      {/* 操作按钮 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginLeft: '12px' }}>
        {/* 上移按钮 */}
        <button
          onClick={() => onMoveUp(index)}
          disabled={index === 0}
          style={{
            width: '28px',
            height: '28px',
            border: '1px solid #d1d5db',
            backgroundColor: 'white',
            borderRadius: '4px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: index === 0 ? 'not-allowed' : 'pointer',
            opacity: index === 0 ? 0.5 : 1
          }}
          title="上移"
        >
          <svg style={{ width: '14px', height: '14px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
          </svg>
        </button>

        {/* 下移按钮 */}
        <button
          onClick={() => onMoveDown(index)}
          disabled={index === totalCount - 1}
          style={{
            width: '28px',
            height: '28px',
            border: '1px solid #d1d5db',
            backgroundColor: 'white',
            borderRadius: '4px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: index === totalCount - 1 ? 'not-allowed' : 'pointer',
            opacity: index === totalCount - 1 ? 0.5 : 1
          }}
          title="下移"
        >
          <svg style={{ width: '14px', height: '14px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {/* 删除按钮 */}
        <button
          onClick={() => onRemove(video)}
          style={{
            width: '28px',
            height: '28px',
            border: '1px solid #ef4444',
            backgroundColor: 'white',
            borderRadius: '4px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            color: '#ef4444'
          }}
          title="移除"
        >
          <svg style={{ width: '14px', height: '14px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
};

const CompositionPage: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  
  // Redux 状态
  const {
    videos,
    selectedVideos,
    loading,
    error,
    searchQuery,
    selectedCategory,
    pagination
  } = useSelector((state: RootState) => state.video);

  // 本地状态
  const [compositionTask, setCompositionTask] = useState<CompositionTask | null>(null);
  const [compositionLoading, setCompositionLoading] = useState(false);
  const [compositionError, setCompositionError] = useState<string | null>(null);
  const [taskHistory, setTaskHistory] = useState<CompositionTask[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [showVideoPlayer, setShowVideoPlayer] = useState(false);
  const [playingTaskId, setPlayingTaskId] = useState<string | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [videoLoading, setVideoLoading] = useState(false);

  // 分页配置
  const itemsPerPage = 12;

  // 视频分类选项
  const categories = [
    { value: '', label: '全部分类' },
    { value: '道德经', label: '道德经' },
    { value: '太上感应篇', label: '太上感应篇' },
    { value: '清静经', label: '清静经' },
    { value: '黄庭经', label: '黄庭经' },
    { value: '阴符经', label: '阴符经' },
    { value: '其他经文', label: '其他经文' }
  ];

  // 加载视频列表
  const loadVideos = useCallback(async () => {
    try {
      dispatch(setLoading(true));
      dispatch(clearError());
      
      const params: any = {
        page: pagination.page,
        page_size: itemsPerPage
      };
      
      if (searchQuery.trim()) {
        params.search = searchQuery.trim();
      }
      
      if (selectedCategory) {
        params.category = selectedCategory;
      }

      const response: PaginatedResponse<Video> = await videoService.getVideos(params);
      dispatch(setVideos(response.results));
      dispatch(setPagination({
        page: pagination.page,
        totalPages: Math.ceil(response.count / itemsPerPage),
        totalCount: response.count
      }));
    } catch (err: any) {
      dispatch(setError(err.message || '加载视频列表失败'));
    }
  }, [dispatch, pagination.page, searchQuery, selectedCategory]);

  // 初始加载
  useEffect(() => {
    loadVideos();
  }, [loadVideos]);

  // 处理视频选择
  const handleToggleVideoSelect = (video: Video) => {
    const isSelected = selectedVideos.some(v => v.id === video.id);
    if (isSelected) {
      dispatch(removeSelectedVideo(video.id));
    } else {
      dispatch(addSelectedVideo(video));
    }
  };

  // 处理搜索
  const handleSearch = (query: string) => {
    dispatch(setSearchQuery(query));
    dispatch(setPagination({ ...pagination, page: 1 }));
  };

  // 处理分类筛选
  const handleCategoryChange = (category: string) => {
    dispatch(setSelectedCategory(category));
    dispatch(setPagination({ ...pagination, page: 1 }));
  };

  // 处理分页
  const handlePageChange = (page: number) => {
    dispatch(setPagination({ ...pagination, page }));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // 移除选中的视频
  const handleRemoveSelectedVideo = (video: Video) => {
    dispatch(removeSelectedVideo(video.id));
  };

  // 上移视频
  const handleMoveVideoUp = (index: number) => {
    if (index > 0) {
      const newSelectedVideos = [...selectedVideos];
      [newSelectedVideos[index - 1], newSelectedVideos[index]] = [newSelectedVideos[index], newSelectedVideos[index - 1]];
      dispatch(reorderSelectedVideos(newSelectedVideos));
    }
  };

  // 下移视频
  const handleMoveVideoDown = (index: number) => {
    if (index < selectedVideos.length - 1) {
      const newSelectedVideos = [...selectedVideos];
      [newSelectedVideos[index], newSelectedVideos[index + 1]] = [newSelectedVideos[index + 1], newSelectedVideos[index]];
      dispatch(reorderSelectedVideos(newSelectedVideos));
    }
  };

  // 清空选择
  const handleClearSelection = () => {
    dispatch(clearSelectedVideos());
  };

  // 开始合成
  const handleStartComposition = async () => {
    if (selectedVideos.length < 2) {
      alert('请至少选择两个视频进行合成');
      return;
    }

    try {
      setCompositionLoading(true);
      setCompositionError(null);
      
      const videoIds = selectedVideos.map(v => v.id);
      const task = await videoService.createCompositionTask({ video_ids: videoIds });
      setCompositionTask(task);
      
      // 开始轮询任务状态
      pollTaskStatus(task.task_id);
    } catch (err: any) {
      setCompositionError(err.message || '创建合成任务失败');
      setCompositionLoading(false);
    }
  };

  // 轮询任务状态
  const pollTaskStatus = async (taskId: string) => {
    try {
      const task = await videoService.getCompositionTaskStatus(taskId);
      setCompositionTask(task);
      
      if (task.status === 'processing') {
        // 继续轮询
        setTimeout(() => pollTaskStatus(taskId), 2000);
      } else {
        setCompositionLoading(false);
        if (task.status === 'failed') {
          setCompositionError(task.error_message || '合成失败');
        }
      }
    } catch (err: any) {
      setCompositionError(err.message || '获取任务状态失败');
      setCompositionLoading(false);
    }
  };

  // 下载合成视频
  const handleDownload = () => {
    if (compositionTask && compositionTask.status === 'completed') {
      const downloadUrl = videoService.getCompositionDownloadUrl(compositionTask.task_id);
      window.open(downloadUrl, '_blank');
    }
  };

  // 重置合成状态
  const handleResetComposition = () => {
    setCompositionTask(null);
    setCompositionError(null);
    setCompositionLoading(false);
  };

  // 取消合成任务
  const handleCancelComposition = async () => {
    if (!compositionTask || compositionTask.status !== 'processing') return;
    
    try {
      await videoService.cancelCompositionTask(compositionTask.task_id);
      setCompositionTask(prev => prev ? { ...prev, status: 'cancelled' } : null);
      setCompositionLoading(false);
      setCompositionError('任务已取消');
    } catch (err: any) {
      setCompositionError(err.message || '取消任务失败');
    }
  };

  // 重试合成任务
  const handleRetryComposition = () => {
    if (selectedVideos.length < 2) return;
    
    // 重置状态并重新开始合成
    setCompositionTask(null);
    setCompositionError(null);
    handleStartComposition();
  };

  // 加载任务历史
  const loadTaskHistory = useCallback(async () => {
    try {
      const response = await videoService.getCompositionTaskList({ page: 1 });
      setTaskHistory(response.results || []);
    } catch (err: any) {
      console.error('加载任务历史失败:', err);
    }
  }, []);

  // 切换历史记录显示
  const toggleHistory = () => {
    setShowHistory(!showHistory);
    if (!showHistory && taskHistory.length === 0) {
      loadTaskHistory();
    }
  };

  // 播放合成视频
  const handlePlayVideo = async (taskId: string) => {
    setPlayingTaskId(taskId);
    setShowVideoPlayer(true);
    setVideoLoading(true);
    
    try {
      // 使用带认证的请求获取视频
      const blobUrl = await videoService.getCompositionVideoBlob(taskId);
      setVideoUrl(blobUrl);
    } catch (err: any) {
      console.error('加载视频失败:', err);
      setCompositionError('加载视频失败，请重试');
      setShowVideoPlayer(false);
    } finally {
      setVideoLoading(false);
    }
  };

  // 关闭视频播放器
  const handleClosePlayer = () => {
    setShowVideoPlayer(false);
    setPlayingTaskId(null);
    // 释放 Blob URL
    if (videoUrl) {
      URL.revokeObjectURL(videoUrl);
      setVideoUrl(null);
    }
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f9fafb' }}>
      <div className="container" style={{ paddingTop: '2rem', paddingBottom: '2rem' }}>
        {/* 页面标题 */}
        <div style={{ marginBottom: '2rem' }}>
          <h1 style={{ fontSize: '2rem', fontWeight: 'bold', color: '#111827', marginBottom: '0.5rem' }}>
            视频合成
          </h1>
          <p style={{ color: '#6b7280' }}>
            选择多个经文视频进行合成，创建完整的经文合集
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 400px', gap: '2rem' }}>
          {/* 左侧：视频选择区域 */}
          <div>
            {/* 搜索和筛选栏 */}
            <div className="card" style={{ marginBottom: '2rem' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {/* 搜索框 */}
                <div style={{ flex: 1 }}>
                  <div style={{ position: 'relative' }}>
                    <input
                      type="text"
                      placeholder="搜索视频标题或描述..."
                      value={searchQuery}
                      onChange={(e) => handleSearch(e.target.value)}
                      className="form-input"
                      style={{ paddingLeft: '2.5rem' }}
                    />
                    <svg
                      style={{
                        position: 'absolute',
                        left: '12px',
                        top: '50%',
                        transform: 'translateY(-50%)',
                        height: '20px',
                        width: '20px',
                        color: '#9ca3af'
                      }}
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                      />
                    </svg>
                  </div>
                </div>

                {/* 分类筛选 */}
                <div style={{ width: '200px' }}>
                  <select
                    value={selectedCategory}
                    onChange={(e) => handleCategoryChange(e.target.value)}
                    className="form-input"
                  >
                    {categories.map((category) => (
                      <option key={category.value} value={category.value}>
                        {category.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {/* 错误提示 */}
            {error && (
              <div className="error" style={{ display: 'flex', alignItems: 'center', marginBottom: '1rem' }}>
                <svg style={{ height: '20px', width: '20px', marginRight: '8px' }} viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <span>{error}</span>
                <button
                  onClick={loadVideos}
                  style={{ marginLeft: '1rem', textDecoration: 'underline', background: 'none', border: 'none', cursor: 'pointer' }}
                >
                  重试
                </button>
              </div>
            )}

            {/* 加载状态 */}
            {loading && (
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '3rem 0' }}>
                <div style={{
                  width: '32px',
                  height: '32px',
                  border: '2px solid #e5e7eb',
                  borderTop: '2px solid #4f46e5',
                  borderRadius: '50%',
                  animation: 'spin 1s linear infinite'
                }}></div>
                <span style={{ marginLeft: '0.5rem', color: '#6b7280' }}>加载中...</span>
              </div>
            )}

            {/* 视频网格 */}
            {!loading && videos.length > 0 && (
              <>
                <div className="grid grid-cols-1 md:grid-cols-3" style={{ marginBottom: '2rem' }}>
                  {videos.map((video) => (
                    <VideoSelectionCard
                      key={video.id}
                      video={video}
                      isSelected={selectedVideos.some(v => v.id === video.id)}
                      onToggleSelect={handleToggleVideoSelect}
                    />
                  ))}
                </div>

                {/* 分页组件 */}
                {pagination.totalPages > 1 && (
                  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem' }}>
                    <button
                      onClick={() => handlePageChange(pagination.page - 1)}
                      disabled={pagination.page === 1}
                      className="btn"
                      style={{
                        backgroundColor: 'white',
                        color: '#6b7280',
                        border: '1px solid #d1d5db',
                        opacity: pagination.page === 1 ? 0.5 : 1,
                        cursor: pagination.page === 1 ? 'not-allowed' : 'pointer'
                      }}
                    >
                      上一页
                    </button>

                    {Array.from({ length: Math.min(5, pagination.totalPages) }, (_, i) => {
                      let pageNum: number;
                      if (pagination.totalPages <= 5) {
                        pageNum = i + 1;
                      } else if (pagination.page <= 3) {
                        pageNum = i + 1;
                      } else if (pagination.page >= pagination.totalPages - 2) {
                        pageNum = pagination.totalPages - 4 + i;
                      } else {
                        pageNum = pagination.page - 2 + i;
                      }

                      return (
                        <button
                          key={pageNum}
                          onClick={() => handlePageChange(pageNum)}
                          className="btn"
                          style={{
                            backgroundColor: pagination.page === pageNum ? '#4f46e5' : 'white',
                            color: pagination.page === pageNum ? 'white' : '#374151',
                            border: `1px solid ${pagination.page === pageNum ? '#4f46e5' : '#d1d5db'}`
                          }}
                        >
                          {pageNum}
                        </button>
                      );
                    })}

                    <button
                      onClick={() => handlePageChange(pagination.page + 1)}
                      disabled={pagination.page === pagination.totalPages}
                      className="btn"
                      style={{
                        backgroundColor: 'white',
                        color: '#6b7280',
                        border: '1px solid #d1d5db',
                        opacity: pagination.page === pagination.totalPages ? 0.5 : 1,
                        cursor: pagination.page === pagination.totalPages ? 'not-allowed' : 'pointer'
                      }}
                    >
                      下一页
                    </button>
                  </div>
                )}
              </>
            )}

            {/* 空状态 */}
            {!loading && videos.length === 0 && !error && (
              <div style={{ textAlign: 'center', padding: '3rem 0' }}>
                <svg style={{ margin: '0 auto', height: '48px', width: '48px', color: '#9ca3af' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                <h3 style={{ marginTop: '0.5rem', fontSize: '14px', fontWeight: '500', color: '#111827' }}>暂无视频</h3>
                <p style={{ marginTop: '0.25rem', fontSize: '14px', color: '#6b7280' }}>
                  {searchQuery || selectedCategory ? '没有找到符合条件的视频' : '还没有上传任何视频'}
                </p>
              </div>
            )}
          </div>

          {/* 右侧：选中视频和合成控制 */}
          <div>
            <div className="card" style={{ position: 'sticky', top: '2rem' }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: '600', color: '#111827', marginBottom: '1rem' }}>
                已选择视频 ({selectedVideos.length})
              </h2>

              {selectedVideos.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '2rem 0', color: '#6b7280' }}>
                  <svg style={{ margin: '0 auto', height: '48px', width: '48px', marginBottom: '1rem' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                  <p>请从左侧选择要合成的视频</p>
                  <p style={{ fontSize: '14px', marginTop: '0.5rem' }}>至少需要选择2个视频</p>
                </div>
              ) : (
                <>
                  {/* 选中视频列表 */}
                  <div style={{ maxHeight: '400px', overflowY: 'auto', marginBottom: '1rem' }}>
                    {selectedVideos.map((video, index) => (
                      <SelectedVideoItem
                        key={video.id}
                        video={video}
                        index={index}
                        onRemove={handleRemoveSelectedVideo}
                        onMoveUp={handleMoveVideoUp}
                        onMoveDown={handleMoveVideoDown}
                        totalCount={selectedVideos.length}
                      />
                    ))}
                  </div>

                  {/* 操作按钮 */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    <button
                      onClick={handleStartComposition}
                      disabled={selectedVideos.length < 2 || compositionLoading}
                      className="btn btn-primary"
                      style={{
                        opacity: selectedVideos.length < 2 || compositionLoading ? 0.5 : 1,
                        cursor: selectedVideos.length < 2 || compositionLoading ? 'not-allowed' : 'pointer'
                      }}
                    >
                      {compositionLoading ? '合成中...' : '开始合成'}
                    </button>
                    
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button
                        onClick={handleClearSelection}
                        className="btn"
                        style={{
                          flex: 1,
                          backgroundColor: 'white',
                          color: '#6b7280',
                          border: '1px solid #d1d5db'
                        }}
                      >
                        清空选择
                      </button>
                      
                      <button
                        onClick={toggleHistory}
                        className="btn"
                        style={{
                          flex: 1,
                          backgroundColor: 'white',
                          color: '#6b7280',
                          border: '1px solid #d1d5db'
                        }}
                      >
                        {showHistory ? '隐藏历史' : '查看历史'}
                      </button>
                    </div>
                  </div>

                  {/* 合成状态 */}
                  {compositionTask && (
                    <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: '#f9fafb', borderRadius: '8px' }}>
                      <h3 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '0.5rem' }}>合成状态</h3>
                      
                      {compositionTask.status === 'processing' && (
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', marginBottom: '0.5rem' }}>
                            <div style={{
                              width: '16px',
                              height: '16px',
                              border: '2px solid #e5e7eb',
                              borderTop: '2px solid #4f46e5',
                              borderRadius: '50%',
                              animation: 'spin 1s linear infinite',
                              marginRight: '0.5rem'
                            }}></div>
                            <span style={{ fontSize: '14px', color: '#6b7280' }}>正在合成...</span>
                          </div>
                          <div style={{ 
                            width: '100%', 
                            height: '8px', 
                            backgroundColor: '#e5e7eb', 
                            borderRadius: '4px',
                            overflow: 'hidden',
                            marginBottom: '0.5rem'
                          }}>
                            <div style={{
                              width: `${compositionTask.progress}%`,
                              height: '100%',
                              backgroundColor: '#4f46e5',
                              transition: 'width 0.3s ease'
                            }}></div>
                          </div>
                          <p style={{ fontSize: '12px', color: '#6b7280', marginBottom: '0.5rem' }}>
                            进度: {compositionTask.progress}%
                          </p>
                          <button
                            onClick={handleCancelComposition}
                            className="btn"
                            style={{
                              width: '100%',
                              backgroundColor: '#fef2f2',
                              color: '#ef4444',
                              border: '1px solid #fecaca'
                            }}
                          >
                            取消合成
                          </button>
                        </div>
                      )}

                      {compositionTask.status === 'completed' && (
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', marginBottom: '0.5rem' }}>
                            <svg style={{ width: '16px', height: '16px', color: '#10b981', marginRight: '0.5rem' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                            <span style={{ fontSize: '14px', color: '#10b981' }}>合成完成</span>
                          </div>
                          <button
                            onClick={() => handlePlayVideo(compositionTask.task_id)}
                            className="btn btn-primary"
                            style={{ width: '100%', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
                          >
                            <svg style={{ width: '16px', height: '16px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            在线播放
                          </button>
                          <button
                            onClick={handleDownload}
                            className="btn"
                            style={{ width: '100%', marginBottom: '0.5rem', backgroundColor: '#dbeafe', color: '#1e40af', border: '1px solid #bfdbfe' }}
                          >
                            下载合成视频
                          </button>
                          <button
                            onClick={handleResetComposition}
                            className="btn"
                            style={{
                              width: '100%',
                              backgroundColor: 'white',
                              color: '#6b7280',
                              border: '1px solid #d1d5db'
                            }}
                          >
                            重新合成
                          </button>
                        </div>
                      )}

                      {compositionTask.status === 'failed' && (
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', marginBottom: '0.5rem' }}>
                            <svg style={{ width: '16px', height: '16px', color: '#ef4444', marginRight: '0.5rem' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                            <span style={{ fontSize: '14px', color: '#ef4444' }}>合成失败</span>
                          </div>
                          {compositionError && (
                            <p style={{ fontSize: '12px', color: '#6b7280', marginBottom: '0.5rem' }}>
                              {compositionError}
                            </p>
                          )}
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                            <button
                              onClick={handleRetryComposition}
                              className="btn btn-primary"
                              style={{ width: '100%' }}
                            >
                              重试合成
                            </button>
                            <button
                              onClick={handleResetComposition}
                              className="btn"
                              style={{
                                width: '100%',
                                backgroundColor: 'white',
                                color: '#6b7280',
                                border: '1px solid #d1d5db'
                              }}
                            >
                              重新选择
                            </button>
                          </div>
                        </div>
                      )}

                      {compositionTask.status === 'cancelled' && (
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', marginBottom: '0.5rem' }}>
                            <svg style={{ width: '16px', height: '16px', color: '#f59e0b', marginRight: '0.5rem' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                            </svg>
                            <span style={{ fontSize: '14px', color: '#f59e0b' }}>任务已取消</span>
                          </div>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                            <button
                              onClick={handleRetryComposition}
                              className="btn btn-primary"
                              style={{ width: '100%' }}
                            >
                              重新合成
                            </button>
                            <button
                              onClick={handleResetComposition}
                              className="btn"
                              style={{
                                width: '100%',
                                backgroundColor: 'white',
                                color: '#6b7280',
                                border: '1px solid #d1d5db'
                              }}
                            >
                              重新选择
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* 合成错误 */}
                  {compositionError && !compositionTask && (
                    <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: '#fef2f2', borderRadius: '8px', border: '1px solid #fecaca' }}>
                      <div style={{ display: 'flex', alignItems: 'center' }}>
                        <svg style={{ width: '16px', height: '16px', color: '#ef4444', marginRight: '0.5rem' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                        <span style={{ fontSize: '14px', color: '#ef4444' }}>{compositionError}</span>
                      </div>
                    </div>
                  )}

                  {/* 任务历史记录 */}
                  {showHistory && (
                    <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: '#f9fafb', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                      <h3 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '0.5rem', color: '#111827' }}>
                        合成历史
                      </h3>
                      
                      {taskHistory.length === 0 ? (
                        <p style={{ fontSize: '12px', color: '#6b7280', textAlign: 'center', padding: '1rem 0' }}>
                          暂无合成历史
                        </p>
                      ) : (
                        <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
                          {taskHistory.map((task) => (
                            <div
                              key={task.task_id}
                              style={{
                                padding: '0.5rem',
                                marginBottom: '0.5rem',
                                backgroundColor: 'white',
                                borderRadius: '4px',
                                border: '1px solid #e5e7eb',
                                fontSize: '12px'
                              }}
                            >
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                                <span style={{ fontWeight: '500', color: '#111827' }}>
                                  {`任务 ${task.task_id.slice(-8)}`}
                                </span>
                                <span style={{
                                  padding: '2px 6px',
                                  borderRadius: '4px',
                                  fontSize: '10px',
                                  backgroundColor: 
                                    task.status === 'completed' ? '#dcfce7' :
                                    task.status === 'failed' ? '#fef2f2' :
                                    task.status === 'cancelled' ? '#fef3c7' : '#f3f4f6',
                                  color:
                                    task.status === 'completed' ? '#166534' :
                                    task.status === 'failed' ? '#dc2626' :
                                    task.status === 'cancelled' ? '#d97706' : '#6b7280'
                                }}>
                                  {task.status === 'completed' ? '已完成' :
                                   task.status === 'failed' ? '失败' :
                                   task.status === 'cancelled' ? '已取消' :
                                   task.status === 'processing' ? '处理中' : '等待中'}
                                </span>
                              </div>
                              
                              <div style={{ color: '#6b7280' }}>
                                视频数量: {task.video_list?.length || 0}
                              </div>
                              
                              {task.status === 'completed' && task.output_file && (
                                <div style={{ display: 'flex', gap: '4px', marginTop: '0.25rem' }}>
                                  <button
                                    onClick={() => handlePlayVideo(task.task_id)}
                                    style={{
                                      padding: '2px 6px',
                                      fontSize: '10px',
                                      backgroundColor: '#dcfce7',
                                      color: '#166534',
                                      border: '1px solid #bbf7d0',
                                      borderRadius: '4px',
                                      cursor: 'pointer'
                                    }}
                                  >
                                    播放
                                  </button>
                                  <button
                                    onClick={() => window.open(videoService.getCompositionDownloadUrl(task.task_id), '_blank')}
                                    style={{
                                      padding: '2px 6px',
                                      fontSize: '10px',
                                      backgroundColor: '#dbeafe',
                                      color: '#1e40af',
                                      border: '1px solid #bfdbfe',
                                      borderRadius: '4px',
                                      cursor: 'pointer'
                                    }}
                                  >
                                    下载
                                  </button>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 添加旋转动画 */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        
        @media (min-width: 768px) {
          .grid.md\\:grid-cols-3 {
            grid-template-columns: repeat(3, 1fr);
          }
        }
        
        @media (max-width: 1024px) {
          .container > div {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>

      {/* 视频播放器弹窗 */}
      {showVideoPlayer && playingTaskId && (
        <div 
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000
          }}
          onClick={handleClosePlayer}
        >
          <div 
            style={{
              backgroundColor: '#000',
              borderRadius: '8px',
              overflow: 'hidden',
              maxWidth: '90vw',
              maxHeight: '90vh',
              position: 'relative',
              minWidth: '400px',
              minHeight: '300px'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* 关闭按钮 */}
            <button
              onClick={handleClosePlayer}
              style={{
                position: 'absolute',
                top: '10px',
                right: '10px',
                width: '36px',
                height: '36px',
                backgroundColor: 'rgba(0, 0, 0, 0.6)',
                color: 'white',
                border: 'none',
                borderRadius: '50%',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 10
              }}
            >
              <svg style={{ width: '20px', height: '20px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            
            {/* 加载状态 */}
            {videoLoading && (
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '4rem',
                color: 'white'
              }}>
                <div style={{
                  width: '48px',
                  height: '48px',
                  border: '3px solid rgba(255,255,255,0.3)',
                  borderTop: '3px solid white',
                  borderRadius: '50%',
                  animation: 'spin 1s linear infinite',
                  marginBottom: '1rem'
                }}></div>
                <span>正在加载视频...</span>
              </div>
            )}
            
            {/* 视频播放器 */}
            {!videoLoading && videoUrl && (
              <>
                <video
                  controls
                  autoPlay
                  style={{
                    maxWidth: '90vw',
                    maxHeight: '80vh',
                    display: 'block'
                  }}
                  src={videoUrl}
                >
                  您的浏览器不支持视频播放
                </video>
                
                {/* 标题栏 */}
                <div style={{
                  padding: '12px 16px',
                  backgroundColor: '#111',
                  color: 'white',
                  fontSize: '14px'
                }}>
                  合成视频播放
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default CompositionPage;