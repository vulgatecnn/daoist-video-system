/**
 * 用户认证服务
 */
import api from './api';

interface LoginCredentials {
  username: string;
  password: string;
}

interface RegisterData {
  username: string;
  email: string;
  password: string;
  password_confirm: string;
  role?: 'admin' | 'user';
}

interface User {
  id: number;
  username: string;
  email: string;
  role: 'admin' | 'user';
  is_active: boolean;
  created_at: string;
}

interface AuthResponse {
  message: string;
  user: User;
  tokens: {
    access: string;
    refresh: string;
  };
}

interface UserPermissions {
  user_id: number;
  username: string;
  role: string;
  is_admin: boolean;
  is_regular_user: boolean;
  permissions: {
    can_upload_video: boolean;
    can_manage_videos: boolean;
    can_view_videos: boolean;
    can_compose_videos: boolean;
  };
}

export const authService = {
  // 用户登录
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await api.post('/auth/login/', credentials);
    return response.data;
  },

  // 用户注册
  async register(data: RegisterData): Promise<AuthResponse> {
    const response = await api.post('/auth/register/', data);
    return response.data;
  },

  // 获取当前用户信息
  async getCurrentUser(): Promise<User> {
    const response = await api.get('/auth/profile/');
    return response.data;
  },

  // 检查用户权限
  async checkPermissions(): Promise<UserPermissions> {
    const response = await api.get('/auth/check-permission/');
    return response.data;
  },

  // 用户登出
  async logout(refreshToken: string): Promise<void> {
    await api.post('/auth/logout/', { refresh_token: refreshToken });
  },

  // 刷新令牌
  async refreshToken(refreshToken: string): Promise<{ access: string }> {
    const response = await api.post('/auth/token/refresh/', { refresh: refreshToken });
    return response.data;
  },

  // 更新用户资料
  async updateProfile(data: Partial<User>): Promise<{ message: string; user: User }> {
    const response = await api.put('/auth/profile/update/', data);
    return response.data;
  },
};