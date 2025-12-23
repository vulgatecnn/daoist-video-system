/**
 * 视频管理服务
 */
import api from './api';

interface VideoListParams {
  page?: number;
  search?: string;
  category?: string;
}

interface VideoUploadData {
  title: string;
  description: string;
  category: string;
  file: File;
}

interface CompositionTaskData {
  video_ids: number[];
}

interface PlaybackProgressData {
  current_time: number;
  total_duration: number;
  session_id?: string;
}

export const videoService = {
  // 获取视频列表
  async getVideos(params: VideoListParams = {}) {
    const response = await api.get('/videos/', { params });
    return response.data;
  },

  // 管理员专用API
  
  // 获取管理员视频列表（包含已删除的视频）
  async getAdminVideos(params: VideoListParams & { is_active?: boolean } = {}) {
    const response = await api.get('/videos/admin/list/', { params });
    return response.data;
  },

  // 批量删除视频
  async batchDeleteVideos(videoIds: number[]) {
    const response = await api.post('/videos/admin/batch-delete/', {
      video_ids: videoIds
    });
    return response.data;
  },

  // 批量更新视频分类
  async batchUpdateCategory(videoIds: number[], category: string) {
    const response = await api.post('/videos/admin/batch-category/', {
      video_ids: videoIds,
      category: category
    });
    return response.data;
  },

  // 管理员编辑视频
  async adminUpdateVideo(id: number, data: Partial<VideoUploadData>) {
    const response = await api.patch(`/videos/admin/${id}/edit/`, data);
    return response.data;
  },

  // 获取视频分类列表
  async getVideoCategories() {
    const response = await api.get('/videos/categories/');
    return response.data;
  },

  // 获取视频详情
  async getVideoDetail(id: number) {
    const response = await api.get(`/videos/${id}/`);
    return response.data;
  },

  // 上传视频
  async uploadVideo(data: VideoUploadData) {
    const formData = new FormData();
    formData.append('title', data.title);
    formData.append('description', data.description);
    formData.append('category', data.category);
    formData.append('file', data.file);

    const response = await api.post('/videos/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // 更新视频信息
  async updateVideo(id: number, data: Partial<VideoUploadData>) {
    const response = await api.patch(`/videos/${id}/`, data);
    return response.data;
  },

  // 删除视频
  async deleteVideo(id: number) {
    await api.delete(`/videos/${id}/`);
  },

  // 创建视频合成任务
  async createCompositionTask(data: CompositionTaskData) {
    const response = await api.post('/videos/composition/create/', data);
    return response.data;
  },

  // 获取合成任务状态
  async getCompositionTaskStatus(taskId: string) {
    const response = await api.get(`/videos/composition/${taskId}/`);
    return response.data;
  },

  // 下载合成视频
  getCompositionDownloadUrl(taskId: string): string {
    return `${api.defaults.baseURL}/videos/composition/${taskId}/download/`;
  },

  // 获取合成视频流式播放URL
  getCompositionStreamUrl(taskId: string): string {
    return `${api.defaults.baseURL}/videos/composition/${taskId}/stream/`;
  },

  // 获取合成视频 Blob URL（带认证）
  async getCompositionVideoBlob(taskId: string): Promise<string> {
    const response = await api.get(`/videos/composition/${taskId}/stream/`, {
      responseType: 'blob'
    });
    const blob = new Blob([response.data], { type: 'video/mp4' });
    return URL.createObjectURL(blob);
  },

  // 取消合成任务
  async cancelCompositionTask(taskId: string) {
    const response = await api.delete(`/videos/composition/${taskId}/cancel/`);
    return response.data;
  },

  // 获取合成任务列表
  async getCompositionTaskList(params: { page?: number; status?: string } = {}) {
    const response = await api.get('/videos/composition/', { params });
    return response.data;
  },

  // 增加视频播放次数
  async incrementViewCount(id: number) {
    await api.post(`/videos/${id}/view/`);
  },

  // 播放统计相关API
  
  // 更新播放进度
  async updatePlaybackProgress(videoId: number, data: PlaybackProgressData) {
    const response = await api.post(`/videos/${videoId}/progress/`, data);
    return response.data;
  },

  // 获取视频播放进度
  async getVideoProgress(videoId: number, sessionId?: string) {
    const params = sessionId ? { session_id: sessionId } : {};
    const response = await api.get(`/videos/${videoId}/progress/get/`, { params });
    return response.data;
  },

  // 获取播放历史
  async getPlaybackHistory(params: { video_id?: number; limit?: number } = {}) {
    const response = await api.get('/videos/playback-history/', { params });
    return response.data;
  },
};