/**
 * API 客户端配置
 * 使用 Axios 进行 HTTP 请求，支持JWT令牌自动刷新和错误处理
 */
import axios, { AxiosError } from 'axios';
import { store } from '../store';
import { refreshTokenAsync, logout } from '../store/slices/authSlice';
import { errorService } from './errorService';

// 扩展 AxiosRequestConfig 类型以支持重试标记
declare module 'axios' {
  interface InternalAxiosRequestConfig {
    _retry?: boolean;
  }
}
declare module 'axios' {
  interface AxiosRequestConfig {
    metadata?: {
      startTime: Date;
    };
  }
}

// 创建 Axios 实例
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器 - 添加JWT认证令牌和请求时间记录
api.interceptors.request.use(
  (config) => {
    const state = store.getState();
    const token = state.auth.accessToken;
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // 记录请求开始时间
    config.metadata = { startTime: new Date() };
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器 - 处理令牌刷新、错误处理和性能监控
api.interceptors.response.use(
  (response) => {
    // 记录请求完成时间
    const endTime = new Date();
    const startTime = response.config.metadata?.startTime;
    if (startTime) {
      const duration = endTime.getTime() - startTime.getTime();
      console.log(`API请求完成: ${response.config.method?.toUpperCase()} ${response.config.url} - ${duration}ms`);
    }
    
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config;
    
    // 处理401错误 - 尝试刷新令牌
    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        // 尝试刷新令牌
        await store.dispatch(refreshTokenAsync()).unwrap();
        
        // 重新发送原始请求
        const state = store.getState();
        const newToken = state.auth.accessToken;
        
        if (newToken) {
          originalRequest.headers = originalRequest.headers || {};
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return api(originalRequest);
        }
      } catch (refreshError) {
        // 刷新令牌失败，清除认证状态并重定向到登录页
        store.dispatch(logout());
        
        // 不在登录页时才重定向
        if (!window.location.pathname.includes('/login')) {
          window.location.href = '/login';
        }
        
        return Promise.reject(refreshError);
      }
    }
    
    // 使用错误服务处理其他错误
    const apiError = errorService.handleApiError(error);
    
    // 显示错误消息（认证错误除外，因为会重定向）
    if (!errorService.isAuthError(apiError)) {
      errorService.showErrorMessage(apiError);
    }
    
    return Promise.reject(apiError);
  }
);

export default api;