/**
 * 视频列表页面
 * 支持搜索、分类筛选、分页和响应式布局
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { videoService } from '../services/videoService';
import { Video, PaginatedResponse } from '../types';

interface VideoCardProps {
  video: Video;
  onClick: (video: Video) => void;
}

// 视频卡片组件
const VideoCard: React.FC<VideoCardProps> = ({ video, onClick }) => {
  const [imageError, setImageError] = useState(false);
  
  // 格式化时长
  const formatDuration = (duration: string): string => {
    if (!duration) return '未知';
    
    // 假设 duration 格式为 "HH:MM:SS" 或 "MM:SS"
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

  // 格式化上传时间
  const formatUploadTime = (uploadTime: string): string => {
    const date = new Date(uploadTime);
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  // 格式化文件大小
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <div
      onClick={() => onClick(video)}
      className="video-card"
      style={{
        background: 'white',
        borderRadius: '8px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        overflow: 'hidden',
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        marginBottom: '1rem'
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'translateY(-2px)';
        e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateY(0)';
        e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
      }}
    >
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
      <div style={{ padding: '16px' }}>
        <h3 style={{
          fontWeight: '600',
          color: '#111827',
          fontSize: '18px',
          marginBottom: '8px',
          lineHeight: '1.4',
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden'
        }}>
          {video.title}
        </h3>
        
        {video.description && (
          <p style={{
            color: '#6b7280',
            fontSize: '14px',
            marginBottom: '12px',
            lineHeight: '1.4',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden'
          }}>
            {video.description}
          </p>
        )}

        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          fontSize: '14px',
          color: '#6b7280',
          marginBottom: '8px'
        }}>
          <span style={{
            backgroundColor: '#dbeafe',
            color: '#1e40af',
            padding: '4px 8px',
            borderRadius: '12px',
            fontSize: '12px'
          }}>
            {video.category}
          </span>
          <span>{video.view_count} 次播放</span>
        </div>

        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          fontSize: '12px',
          color: '#9ca3af'
        }}>
          <span>{formatUploadTime(video.upload_time)}</span>
          <span>{formatFileSize(video.file_size)}</span>
        </div>
      </div>
    </div>
  );
};

const VideoListPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  
  // 状态管理
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalCount, setTotalCount] = useState(0);
  
  // 搜索和筛选状态
  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') || '');
  const [selectedCategory, setSelectedCategory] = useState(searchParams.get('category') || '');
  const [currentPage, setCurrentPage] = useState(parseInt(searchParams.get('page') || '1'));
  
  // 分页配置
  const itemsPerPage = 12;
  const totalPages = Math.ceil(totalCount / itemsPerPage);

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
      setLoading(true);
      setError(null);
      
      const params: any = {
        page: currentPage,
        page_size: itemsPerPage
      };
      
      if (searchQuery.trim()) {
        params.search = searchQuery.trim();
      }
      
      if (selectedCategory) {
        params.category = selectedCategory;
      }

      const response: PaginatedResponse<Video> = await videoService.getVideos(params);
      setVideos(response.results);
      setTotalCount(response.count);
    } catch (err: any) {
      setError(err.message || '加载视频列表失败');
      setVideos([]);
      setTotalCount(0);
    } finally {
      setLoading(false);
    }
  }, [currentPage, searchQuery, selectedCategory]);

  // 更新 URL 参数
  const updateSearchParams = useCallback(() => {
    const params = new URLSearchParams();
    
    if (searchQuery.trim()) {
      params.set('search', searchQuery.trim());
    }
    
    if (selectedCategory) {
      params.set('category', selectedCategory);
    }
    
    if (currentPage > 1) {
      params.set('page', currentPage.toString());
    }
    
    setSearchParams(params);
  }, [searchQuery, selectedCategory, currentPage, setSearchParams]);

  // 初始加载和参数变化时重新加载
  useEffect(() => {
    loadVideos();
  }, [loadVideos]);

  // 更新 URL 参数
  useEffect(() => {
    updateSearchParams();
  }, [updateSearchParams]);

  // 处理搜索
  const handleSearch = (query: string) => {
    setSearchQuery(query);
    setCurrentPage(1); // 重置到第一页
  };

  // 处理分类筛选
  const handleCategoryChange = (category: string) => {
    setSelectedCategory(category);
    setCurrentPage(1); // 重置到第一页
  };

  // 处理分页
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // 处理视频点击
  const handleVideoClick = (video: Video) => {
    navigate(`/videos/${video.id}`);
  };

  // 重试加载
  const retryLoad = () => {
    loadVideos();
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f9fafb' }}>
      <div className="container" style={{ paddingTop: '2rem', paddingBottom: '2rem' }}>
        {/* 页面标题 */}
        <div style={{ marginBottom: '2rem' }}>
          <h1 style={{ fontSize: '2rem', fontWeight: 'bold', color: '#111827', marginBottom: '0.5rem' }}>
            经文视频库
          </h1>
          <p style={{ color: '#6b7280' }}>
            浏览和观看道教经文视频，共 {totalCount} 个视频
          </p>
        </div>

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
          <div className="error" style={{ display: 'flex', alignItems: 'center' }}>
            <svg style={{ height: '20px', width: '20px', marginRight: '8px' }} viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <span>{error}</span>
            <button
              onClick={retryLoad}
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
                <VideoCard
                  key={video.id}
                  video={video}
                  onClick={handleVideoClick}
                />
              ))}
            </div>

            {/* 分页组件 */}
            {totalPages > 1 && (
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem' }}>
                {/* 上一页 */}
                <button
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage === 1}
                  className="btn"
                  style={{
                    backgroundColor: 'white',
                    color: '#6b7280',
                    border: '1px solid #d1d5db',
                    opacity: currentPage === 1 ? 0.5 : 1,
                    cursor: currentPage === 1 ? 'not-allowed' : 'pointer'
                  }}
                >
                  上一页
                </button>

                {/* 页码 */}
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  let pageNum: number;
                  if (totalPages <= 5) {
                    pageNum = i + 1;
                  } else if (currentPage <= 3) {
                    pageNum = i + 1;
                  } else if (currentPage >= totalPages - 2) {
                    pageNum = totalPages - 4 + i;
                  } else {
                    pageNum = currentPage - 2 + i;
                  }

                  return (
                    <button
                      key={pageNum}
                      onClick={() => handlePageChange(pageNum)}
                      className="btn"
                      style={{
                        backgroundColor: currentPage === pageNum ? '#4f46e5' : 'white',
                        color: currentPage === pageNum ? 'white' : '#374151',
                        border: `1px solid ${currentPage === pageNum ? '#4f46e5' : '#d1d5db'}`
                      }}
                    >
                      {pageNum}
                    </button>
                  );
                })}

                {/* 下一页 */}
                <button
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage === totalPages}
                  className="btn"
                  style={{
                    backgroundColor: 'white',
                    color: '#6b7280',
                    border: '1px solid #d1d5db',
                    opacity: currentPage === totalPages ? 0.5 : 1,
                    cursor: currentPage === totalPages ? 'not-allowed' : 'pointer'
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
            {(searchQuery || selectedCategory) && (
              <button
                onClick={() => {
                  setSearchQuery('');
                  setSelectedCategory('');
                  setCurrentPage(1);
                }}
                style={{ 
                  marginTop: '1rem', 
                  color: '#4f46e5', 
                  fontSize: '14px',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  textDecoration: 'underline'
                }}
              >
                清除筛选条件
              </button>
            )}
          </div>
        )}
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
      `}</style>
    </div>
  );
};

export default VideoListPage;