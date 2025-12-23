/**
 * 全局类型定义
 */

// 用户相关类型
export interface User {
  id: number;
  username: string;
  email: string;
  role: 'admin' | 'user';
}

// 视频相关类型
export interface Video {
  id: number;
  title: string;
  description: string;
  file_path?: string;
  file_url?: string;  // 完整的视频文件 URL
  thumbnail?: string;
  thumbnail_url?: string;  // 完整的缩略图 URL
  duration: string;
  file_size: number;
  category: string;
  upload_time: string;
  uploader?: number;
  uploader_name?: string;
  view_count: number;
  is_active?: boolean;
}

// 合成任务相关类型
export interface CompositionTask {
  id: number;
  task_id: string;
  user: number;
  video_list: number[];
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  output_file: string | null;
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
}

// API 响应类型
export interface ApiResponse<T> {
  data: T;
  message?: string;
  status: number;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// 表单相关类型
export interface LoginForm {
  username: string;
  password: string;
}

export interface RegisterForm {
  username: string;
  email: string;
  password: string;
  confirmPassword: string;
}

export interface VideoUploadForm {
  title: string;
  description: string;
  category: string;
  file: File | null;
}

// 路由相关类型
export interface RouteConfig {
  path: string;
  component: React.ComponentType;
  exact?: boolean;
  requireAuth?: boolean;
  requireAdmin?: boolean;
}