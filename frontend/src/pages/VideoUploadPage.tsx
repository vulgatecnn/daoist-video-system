/**
 * 管理员视频上传页面
 * 支持拖拽上传、进度显示、元数据输入和错误处理
 */
import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { RootState } from '../store';

interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

interface VideoMetadata {
  title: string;
  description: string;
  category: string;
}

const VideoUploadPage: React.FC = () => {
  const navigate = useNavigate();
  const { user, isAuthenticated } = useSelector((state: RootState) => state.auth);
  
  // 状态管理
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [metadata, setMetadata] = useState<VideoMetadata>({
    title: '',
    description: '',
    category: ''
  });
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // 文件拖拽处理
  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
    setError(null);
    setSuccess(false);
    
    if (rejectedFiles.length > 0) {
      const rejection = rejectedFiles[0];
      if (rejection.errors.some((e: any) => e.code === 'file-too-large')) {
        setError('文件大小超过限制（最大 500MB）');
      } else if (rejection.errors.some((e: any) => e.code === 'file-invalid-type')) {
        setError('不支持的文件格式，请选择 MP4、AVI、MOV、WMV 或 MKV 格式的视频文件');
      } else {
        setError('文件选择失败，请重试');
      }
      return;
    }

    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0];
      setSelectedFile(file);
      
      // 自动填充标题（去掉文件扩展名）
      if (!metadata.title) {
        const nameWithoutExt = file.name.replace(/\.[^/.]+$/, '');
        setMetadata(prev => ({ ...prev, title: nameWithoutExt }));
      }
    }
  }, [metadata.title]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'video/*': ['.mp4', '.avi', '.mov', '.wmv', '.mkv']
    },
    maxSize: 500 * 1024 * 1024, // 500MB
    multiple: false
  });

  // 处理元数据输入
  const handleMetadataChange = (field: keyof VideoMetadata, value: string) => {
    setMetadata(prev => ({ ...prev, [field]: value }));
  };

  // 移除选中的文件
  const removeFile = () => {
    setSelectedFile(null);
    setUploadProgress(null);
    setError(null);
    setSuccess(false);
  };

  // 上传视频
  const handleUpload = async () => {
    if (!selectedFile) {
      setError('请先选择视频文件');
      return;
    }

    if (!metadata.title.trim()) {
      setError('请输入视频标题');
      return;
    }

    if (!metadata.category.trim()) {
      setError('请选择视频分类');
      return;
    }

    setUploading(true);
    setError(null);
    setUploadProgress({ loaded: 0, total: selectedFile.size, percentage: 0 });

    try {
      // 创建 XMLHttpRequest 来跟踪上传进度
      const formData = new FormData();
      formData.append('title', metadata.title);
      formData.append('description', metadata.description);
      formData.append('category', metadata.category);
      formData.append('file', selectedFile);

      const xhr = new XMLHttpRequest();
      
      // 监听上传进度
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
          const percentage = Math.round((event.loaded / event.total) * 100);
          setUploadProgress({
            loaded: event.loaded,
            total: event.total,
            percentage
          });
        }
      });

      // 处理上传完成
      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          setSuccess(true);
          setUploading(false);
          setUploadProgress(null);
          
          // 重置表单
          setSelectedFile(null);
          setMetadata({ title: '', description: '', category: '' });
          
          // 3秒后跳转到视频列表
          setTimeout(() => {
            navigate('/admin/videos');
          }, 3000);
        } else {
          throw new Error('上传失败');
        }
      });

      // 处理上传错误
      xhr.addEventListener('error', () => {
        throw new Error('网络错误，上传失败');
      });

      // 发送请求
      const token = localStorage.getItem('accessToken');
      xhr.open('POST', `${process.env.REACT_APP_API_URL || 'http://localhost:6000/api'}/videos/`);
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      xhr.send(formData);

    } catch (err: any) {
      setError(err.message || '上传失败，请重试');
      setUploading(false);
      setUploadProgress(null);
    }
  };

  // 重试上传
  const retryUpload = () => {
    setError(null);
    setUploadProgress(null);
    handleUpload();
  };

  // 格式化文件大小
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // 检查用户权限
  if (!isAuthenticated || user?.role !== 'admin') {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#f9fafb' }}>
        <div style={{ maxWidth: '400px', width: '100%', backgroundColor: 'white', borderRadius: '8px', boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)', padding: '1.5rem' }}>
          <div style={{ textAlign: 'center' }}>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#111827', marginBottom: '1rem' }}>访问受限</h2>
            <p style={{ color: '#6b7280', marginBottom: '1rem' }}>只有管理员可以上传视频</p>
            <button
              onClick={() => navigate('/login')}
              className="btn btn-primary"
              style={{ width: '100%' }}
            >
              返回登录
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f9fafb', paddingTop: '2rem', paddingBottom: '2rem' }}>
      <div className="container">
        <div style={{ backgroundColor: 'white', borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.1)', overflow: 'hidden' }}>
          {/* 页面标题 */}
          <div style={{ padding: '1.5rem', borderBottom: '1px solid #e5e7eb' }}>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#111827' }}>上传经文视频</h1>
            <p style={{ marginTop: '0.25rem', fontSize: '14px', color: '#6b7280' }}>
              支持 MP4、AVI、MOV、WMV、MKV 格式，最大文件大小 500MB
            </p>
          </div>

          <div style={{ padding: '1.5rem' }}>
            {/* 成功提示 */}
            {success && (
              <div style={{ 
                marginBottom: '1.5rem', 
                backgroundColor: '#f0fdf4', 
                border: '1px solid #bbf7d0', 
                borderRadius: '6px', 
                padding: '1rem' 
              }}>
                <div style={{ display: 'flex' }}>
                  <div style={{ flexShrink: 0 }}>
                    <svg style={{ height: '20px', width: '20px', color: '#22c55e' }} viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div style={{ marginLeft: '0.75rem' }}>
                    <h3 style={{ fontSize: '14px', fontWeight: '500', color: '#166534' }}>上传成功！</h3>
                    <p style={{ marginTop: '0.25rem', fontSize: '14px', color: '#166534' }}>
                      视频已成功上传，3秒后将跳转到视频管理页面...
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* 错误提示 */}
            {error && (
              <div className="error" style={{ display: 'flex', marginBottom: '1.5rem' }}>
                <div style={{ flexShrink: 0 }}>
                  <svg style={{ height: '20px', width: '20px' }} viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                </div>
                <div style={{ marginLeft: '0.75rem' }}>
                  <h3 style={{ fontSize: '14px', fontWeight: '500' }}>上传失败</h3>
                  <p style={{ marginTop: '0.25rem', fontSize: '14px' }}>{error}</p>
                  {selectedFile && (
                    <button
                      onClick={retryUpload}
                      style={{ 
                        marginTop: '0.5rem', 
                        fontSize: '14px', 
                        backgroundColor: '#fecaca', 
                        color: '#dc2626', 
                        padding: '0.25rem 0.75rem', 
                        borderRadius: '6px', 
                        border: 'none',
                        cursor: 'pointer'
                      }}
                    >
                      重试上传
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* 文件上传区域 */}
            {!selectedFile && (
              <div
                {...getRootProps()}
                style={{
                  border: '2px dashed #d1d5db',
                  borderRadius: '8px',
                  padding: '2rem',
                  textAlign: 'center',
                  cursor: 'pointer',
                  transition: 'colors 0.2s',
                  borderColor: isDragActive ? '#3b82f6' : '#d1d5db',
                  backgroundColor: isDragActive ? '#eff6ff' : 'transparent'
                }}
              >
                <input {...getInputProps()} />
                <svg
                  style={{ margin: '0 auto', height: '48px', width: '48px', color: '#9ca3af' }}
                  stroke="currentColor"
                  fill="none"
                  viewBox="0 0 48 48"
                >
                  <path
                    d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                    strokeWidth={2}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                <div style={{ marginTop: '1rem' }}>
                  <p style={{ fontSize: '18px', fontWeight: '500', color: '#111827' }}>
                    {isDragActive ? '释放文件以上传' : '拖拽视频文件到此处'}
                  </p>
                  <p style={{ marginTop: '0.5rem', fontSize: '14px', color: '#6b7280' }}>
                    或者 <span style={{ color: '#3b82f6', fontWeight: '500' }}>点击选择文件</span>
                  </p>
                  <p style={{ marginTop: '0.25rem', fontSize: '12px', color: '#6b7280' }}>
                    支持 MP4, AVI, MOV, WMV, MKV 格式，最大 500MB
                  </p>
                </div>
              </div>
            )}

            {/* 已选择的文件信息 */}
            {selectedFile && (
              <div style={{ marginBottom: '1.5rem' }}>
                <div style={{ backgroundColor: '#f9fafb', borderRadius: '8px', padding: '1rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center' }}>
                      <svg style={{ height: '32px', width: '32px', color: '#3b82f6' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                      <div style={{ marginLeft: '0.75rem' }}>
                        <p style={{ fontSize: '14px', fontWeight: '500', color: '#111827' }}>{selectedFile.name}</p>
                        <p style={{ fontSize: '14px', color: '#6b7280' }}>{formatFileSize(selectedFile.size)}</p>
                      </div>
                    </div>
                    {!uploading && (
                      <button
                        onClick={removeFile}
                        style={{ color: '#dc2626', background: 'none', border: 'none', cursor: 'pointer' }}
                      >
                        <svg style={{ height: '20px', width: '20px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    )}
                  </div>

                  {/* 上传进度 */}
                  {uploadProgress && (
                    <div style={{ marginTop: '1rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '14px', color: '#6b7280', marginBottom: '0.25rem' }}>
                        <span>上传进度</span>
                        <span>{uploadProgress.percentage}%</span>
                      </div>
                      <div style={{ width: '100%', backgroundColor: '#e5e7eb', borderRadius: '9999px', height: '8px' }}>
                        <div
                          style={{
                            backgroundColor: '#3b82f6',
                            height: '8px',
                            borderRadius: '9999px',
                            transition: 'all 0.3s',
                            width: `${uploadProgress.percentage}%`
                          }}
                        ></div>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#6b7280', marginTop: '0.25rem' }}>
                        <span>{formatFileSize(uploadProgress.loaded)}</span>
                        <span>{formatFileSize(uploadProgress.total)}</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* 视频元数据表单 */}
            {selectedFile && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                <div className="form-group">
                  <label htmlFor="title" className="form-label">
                    视频标题 <span style={{ color: '#dc2626' }}>*</span>
                  </label>
                  <input
                    type="text"
                    id="title"
                    value={metadata.title}
                    onChange={(e) => handleMetadataChange('title', e.target.value)}
                    className="form-input"
                    placeholder="请输入视频标题"
                    disabled={uploading}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="description" className="form-label">
                    视频描述
                  </label>
                  <textarea
                    id="description"
                    rows={4}
                    value={metadata.description}
                    onChange={(e) => handleMetadataChange('description', e.target.value)}
                    className="form-input"
                    placeholder="请输入视频描述（可选）"
                    disabled={uploading}
                    style={{ resize: 'vertical' }}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="category" className="form-label">
                    视频分类 <span style={{ color: '#dc2626' }}>*</span>
                  </label>
                  <select
                    id="category"
                    value={metadata.category}
                    onChange={(e) => handleMetadataChange('category', e.target.value)}
                    className="form-input"
                    disabled={uploading}
                  >
                    <option value="">请选择分类</option>
                    <option value="道德经">道德经</option>
                    <option value="太上感应篇">太上感应篇</option>
                    <option value="清静经">清静经</option>
                    <option value="黄庭经">黄庭经</option>
                    <option value="阴符经">阴符经</option>
                    <option value="其他经文">其他经文</option>
                  </select>
                </div>

                {/* 上传按钮 */}
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
                  <button
                    onClick={removeFile}
                    disabled={uploading}
                    className="btn"
                    style={{
                      backgroundColor: 'white',
                      color: '#374151',
                      border: '1px solid #d1d5db',
                      opacity: uploading ? 0.5 : 1,
                      cursor: uploading ? 'not-allowed' : 'pointer'
                    }}
                  >
                    取消
                  </button>
                  <button
                    onClick={handleUpload}
                    disabled={uploading || !metadata.title.trim() || !metadata.category.trim()}
                    className="btn btn-primary"
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      opacity: (uploading || !metadata.title.trim() || !metadata.category.trim()) ? 0.5 : 1,
                      cursor: (uploading || !metadata.title.trim() || !metadata.category.trim()) ? 'not-allowed' : 'pointer'
                    }}
                  >
                    {uploading && (
                      <svg style={{ animation: 'spin 1s linear infinite', marginLeft: '-0.25rem', marginRight: '0.75rem', height: '20px', width: '20px' }} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle style={{ opacity: 0.25 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path style={{ opacity: 0.75 }} fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                    )}
                    {uploading ? '上传中...' : '开始上传'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 添加旋转动画 */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default VideoUploadPage;