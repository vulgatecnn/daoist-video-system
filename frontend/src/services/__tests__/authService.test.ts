/**
 * 认证服务单元测试
 */
import { authService } from '../authService';

// Mock api module
jest.mock('../api', () => ({
  __esModule: true,
  default: {
    post: jest.fn(),
    get: jest.fn(),
    put: jest.fn(),
  },
}));

import api from '../api';
const mockedApi = api as jest.Mocked<typeof api>;

describe('authService 测试', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('login', () => {
    test('应该发送正确的登录请求', async () => {
      const credentials = { username: 'testuser', password: 'testpassword' };
      const mockResponse = {
        data: {
          message: '登录成功',
          user: {
            id: 1,
            username: 'testuser',
            email: 'test@example.com',
            role: 'user' as const,
            is_active: true,
            created_at: '2023-01-01',
          },
          tokens: {
            access: 'access-token',
            refresh: 'refresh-token',
          },
        },
      };

      mockedApi.post.mockResolvedValue(mockResponse);

      const result = await authService.login(credentials);

      expect(mockedApi.post).toHaveBeenCalledWith('/auth/login/', credentials);
      expect(result).toEqual(mockResponse.data);
    });

    test('应该处理登录失败', async () => {
      const credentials = { username: 'testuser', password: 'wrongpassword' };
      const mockError = new Error('登录失败');

      mockedApi.post.mockRejectedValue(mockError);

      await expect(authService.login(credentials)).rejects.toThrow('登录失败');
      expect(mockedApi.post).toHaveBeenCalledWith('/auth/login/', credentials);
    });
  });

  describe('register', () => {
    test('应该发送正确的注册请求', async () => {
      const registerData = {
        username: 'newuser',
        email: 'newuser@example.com',
        password: 'newpassword',
        password_confirm: 'newpassword',
      };
      const mockResponse = {
        data: {
          message: '注册成功',
          user: {
            id: 2,
            username: 'newuser',
            email: 'newuser@example.com',
            role: 'user' as const,
            is_active: true,
            created_at: '2023-01-01',
          },
          tokens: {
            access: 'access-token',
            refresh: 'refresh-token',
          },
        },
      };

      mockedApi.post.mockResolvedValue(mockResponse);

      const result = await authService.register(registerData);

      expect(mockedApi.post).toHaveBeenCalledWith('/auth/register/', registerData);
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('getCurrentUser', () => {
    test('应该获取当前用户信息', async () => {
      const mockUser = {
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        role: 'user' as const,
        is_active: true,
        created_at: '2023-01-01',
      };
      const mockResponse = { data: mockUser };

      mockedApi.get.mockResolvedValue(mockResponse);

      const result = await authService.getCurrentUser();

      expect(mockedApi.get).toHaveBeenCalledWith('/auth/profile/');
      expect(result).toEqual(mockUser);
    });
  });

  describe('checkPermissions', () => {
    test('应该检查用户权限', async () => {
      const mockPermissions = {
        user_id: 1,
        username: 'testuser',
        role: 'user',
        is_admin: false,
        is_regular_user: true,
        permissions: {
          can_upload_video: false,
          can_manage_videos: false,
          can_view_videos: true,
          can_compose_videos: true,
        },
      };
      const mockResponse = { data: mockPermissions };

      mockedApi.get.mockResolvedValue(mockResponse);

      const result = await authService.checkPermissions();

      expect(mockedApi.get).toHaveBeenCalledWith('/auth/check-permission/');
      expect(result).toEqual(mockPermissions);
    });
  });

  describe('logout', () => {
    test('应该发送登出请求', async () => {
      const refreshToken = 'refresh-token';
      const mockResponse = { data: {} };

      mockedApi.post.mockResolvedValue(mockResponse);

      await authService.logout(refreshToken);

      expect(mockedApi.post).toHaveBeenCalledWith('/auth/logout/', { refresh_token: refreshToken });
    });
  });

  describe('refreshToken', () => {
    test('应该刷新访问令牌', async () => {
      const refreshToken = 'refresh-token';
      const mockResponse = {
        data: {
          access: 'new-access-token',
        },
      };

      mockedApi.post.mockResolvedValue(mockResponse);

      const result = await authService.refreshToken(refreshToken);

      expect(mockedApi.post).toHaveBeenCalledWith('/auth/token/refresh/', { refresh: refreshToken });
      expect(result).toEqual(mockResponse.data);
    });

    test('应该处理刷新令牌失败', async () => {
      const refreshToken = 'invalid-refresh-token';
      const mockError = new Error('刷新令牌失败');

      mockedApi.post.mockRejectedValue(mockError);

      await expect(authService.refreshToken(refreshToken)).rejects.toThrow('刷新令牌失败');
      expect(mockedApi.post).toHaveBeenCalledWith('/auth/token/refresh/', { refresh: refreshToken });
    });
  });

  describe('updateProfile', () => {
    test('应该更新用户资料', async () => {
      const updateData = { email: 'newemail@example.com' };
      const mockResponse = {
        data: {
          message: '更新成功',
          user: {
            id: 1,
            username: 'testuser',
            email: 'newemail@example.com',
            role: 'user' as const,
            is_active: true,
            created_at: '2023-01-01',
          },
        },
      };

      mockedApi.put.mockResolvedValue(mockResponse);

      const result = await authService.updateProfile(updateData);

      expect(mockedApi.put).toHaveBeenCalledWith('/auth/profile/update/', updateData);
      expect(result).toEqual(mockResponse.data);
    });
  });
});