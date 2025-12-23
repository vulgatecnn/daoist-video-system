/**
 * 认证状态管理单元测试
 */
import { configureStore } from '@reduxjs/toolkit';
import authReducer, { 
  loginAsync, 
  logoutAsync, 
  refreshTokenAsync, 
  clearError, 
  logout 
} from '../authSlice';

// Mock authService
jest.mock('../../../services/authService', () => ({
  authService: {
    login: jest.fn(),
    logout: jest.fn(),
    refreshToken: jest.fn(),
  },
}));

import { authService } from '../../../services/authService';
const mockedAuthService = authService as jest.Mocked<typeof authService>;

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

describe('authSlice 测试', () => {
  let store: ReturnType<typeof configureStore>;

  beforeEach(() => {
    store = configureStore({
      reducer: {
        auth: authReducer,
      },
    });
    jest.clearAllMocks();
    localStorageMock.getItem.mockReturnValue(null);
  });

  describe('初始状态', () => {
    test('应该有正确的初始状态', () => {
      const state = store.getState().auth;
      expect(state).toEqual({
        user: null,
        accessToken: null,
        refreshToken: null,
        isAuthenticated: false,
        loading: false,
        error: null,
      });
    });

    test('应该从localStorage加载令牌', () => {
      const mockUser = { id: 1, username: 'testuser', email: 'test@example.com', role: 'user' as const, is_active: true, created_at: '2023-01-01' };
      const mockAccessToken = 'mock-access-token';
      const mockRefreshToken = 'mock-refresh-token';

      localStorageMock.getItem.mockImplementation((key) => {
        switch (key) {
          case 'accessToken':
            return mockAccessToken;
          case 'refreshToken':
            return mockRefreshToken;
          case 'user':
            return JSON.stringify(mockUser);
          default:
            return null;
        }
      });

      // 重新创建store以触发初始状态加载
      const newStore = configureStore({
        reducer: {
          auth: authReducer,
        },
      });

      const state = newStore.getState().auth;
      expect(state.accessToken).toBe(mockAccessToken);
      expect(state.refreshToken).toBe(mockRefreshToken);
      expect(state.user).toEqual(mockUser);
      expect(state.isAuthenticated).toBe(true);
    });
  });

  describe('同步actions', () => {
    test('clearError 应该清除错误信息', () => {
      // 先设置一个错误状态
      store.dispatch({ type: 'auth/loginAsync/rejected', payload: '登录失败' });
      expect(store.getState().auth.error).toBe('登录失败');

      // 清除错误
      store.dispatch(clearError());
      expect(store.getState().auth.error).toBeNull();
    });

    test('logout 应该清除认证状态和localStorage', () => {
      // 先设置认证状态
      const mockUser = { id: 1, username: 'testuser', email: 'test@example.com', role: 'user' as const, is_active: true, created_at: '2023-01-01' };
      store.dispatch({
        type: 'auth/loginAsync/fulfilled',
        payload: {
          user: mockUser,
          tokens: { access: 'access-token', refresh: 'refresh-token' },
        },
      });

      // 执行登出
      store.dispatch(logout());

      const state = store.getState().auth;
      expect(state.user).toBeNull();
      expect(state.accessToken).toBeNull();
      expect(state.refreshToken).toBeNull();
      expect(state.isAuthenticated).toBe(false);
      expect(state.error).toBeNull();

      // 验证localStorage被清除
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('accessToken');
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('refreshToken');
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('user');
    });
  });

  describe('loginAsync', () => {
    const mockCredentials = { username: 'testuser', password: 'testpassword' };
    const mockResponse = {
      message: '登录成功',
      user: { id: 1, username: 'testuser', email: 'test@example.com', role: 'user' as const, is_active: true, created_at: '2023-01-01' },
      tokens: { access: 'access-token', refresh: 'refresh-token' },
    };

    test('登录成功应该更新状态和localStorage', async () => {
      mockedAuthService.login.mockResolvedValue(mockResponse);

      await store.dispatch(loginAsync(mockCredentials));

      const state = store.getState().auth;
      expect(state.loading).toBe(false);
      expect(state.user).toEqual(mockResponse.user);
      expect(state.accessToken).toBe(mockResponse.tokens.access);
      expect(state.refreshToken).toBe(mockResponse.tokens.refresh);
      expect(state.isAuthenticated).toBe(true);
      expect(state.error).toBeNull();

      // 验证localStorage被更新
      expect(localStorageMock.setItem).toHaveBeenCalledWith('accessToken', mockResponse.tokens.access);
      expect(localStorageMock.setItem).toHaveBeenCalledWith('refreshToken', mockResponse.tokens.refresh);
      expect(localStorageMock.setItem).toHaveBeenCalledWith('user', JSON.stringify(mockResponse.user));
    });

    test('登录失败应该设置错误状态', async () => {
      const errorMessage = '用户名或密码错误';
      mockedAuthService.login.mockRejectedValue({
        response: { data: { message: errorMessage } },
      });

      await store.dispatch(loginAsync(mockCredentials));

      const state = store.getState().auth;
      expect(state.loading).toBe(false);
      expect(state.error).toBe(errorMessage);
      expect(state.isAuthenticated).toBe(false);
    });

    test('登录过程中应该显示加载状态', () => {
      mockedAuthService.login.mockImplementation(() => new Promise(() => {})); // 永不resolve

      store.dispatch(loginAsync(mockCredentials));

      const state = store.getState().auth;
      expect(state.loading).toBe(true);
      expect(state.error).toBeNull();
    });
  });

  describe('refreshTokenAsync', () => {
    test('刷新令牌成功应该更新accessToken', async () => {
      const mockRefreshToken = 'refresh-token';
      const mockNewAccessToken = 'new-access-token';

      // 设置初始状态
      store.dispatch({
        type: 'auth/loginAsync/fulfilled',
        payload: {
          user: { id: 1, username: 'testuser', email: 'test@example.com', role: 'user' as const, is_active: true, created_at: '2023-01-01' },
          tokens: { access: 'old-access-token', refresh: mockRefreshToken },
        },
      });

      mockedAuthService.refreshToken.mockResolvedValue({ access: mockNewAccessToken });

      await store.dispatch(refreshTokenAsync());

      const state = store.getState().auth;
      expect(state.accessToken).toBe(mockNewAccessToken);
      expect(localStorageMock.setItem).toHaveBeenCalledWith('accessToken', mockNewAccessToken);
    });

    test('刷新令牌失败应该清除认证状态', async () => {
      // 设置初始认证状态
      store.dispatch({
        type: 'auth/loginAsync/fulfilled',
        payload: {
          user: { id: 1, username: 'testuser', email: 'test@example.com', role: 'user' as const, is_active: true, created_at: '2023-01-01' },
          tokens: { access: 'access-token', refresh: 'refresh-token' },
        },
      });

      mockedAuthService.refreshToken.mockRejectedValue(new Error('刷新失败'));

      await store.dispatch(refreshTokenAsync());

      const state = store.getState().auth;
      expect(state.user).toBeNull();
      expect(state.accessToken).toBeNull();
      expect(state.refreshToken).toBeNull();
      expect(state.isAuthenticated).toBe(false);
    });

    test('没有refreshToken时应该失败', async () => {
      // 确保没有refreshToken
      const state = store.getState().auth;
      expect(state.refreshToken).toBeNull();

      await store.dispatch(refreshTokenAsync());

      // 验证状态没有改变（因为没有refreshToken）
      const newState = store.getState().auth;
      expect(newState.isAuthenticated).toBe(false);
    });
  });

  describe('logoutAsync', () => {
    test('登出成功应该清除状态', async () => {
      const mockRefreshToken = 'refresh-token';

      // 设置初始认证状态
      store.dispatch({
        type: 'auth/loginAsync/fulfilled',
        payload: {
          user: { id: 1, username: 'testuser', email: 'test@example.com', role: 'user' as const, is_active: true, created_at: '2023-01-01' },
          tokens: { access: 'access-token', refresh: mockRefreshToken },
        },
      });

      mockedAuthService.logout.mockResolvedValue();

      await store.dispatch(logoutAsync());

      const state = store.getState().auth;
      expect(state.user).toBeNull();
      expect(state.accessToken).toBeNull();
      expect(state.refreshToken).toBeNull();
      expect(state.isAuthenticated).toBe(false);
      expect(state.error).toBeNull();

      expect(mockedAuthService.logout).toHaveBeenCalledWith(mockRefreshToken);
    });
  });
});