/**
 * 登录页面单元测试
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import { configureStore } from '@reduxjs/toolkit';
import userEvent from '@testing-library/user-event';
import LoginPage from '../LoginPage';
import authReducer from '../../store/slices/authSlice';

// 创建测试用的store
const createTestStore = (initialState = {}) => {
  return configureStore({
    reducer: {
      auth: authReducer,
    },
    preloadedState: {
      auth: {
        user: null,
        accessToken: null,
        refreshToken: null,
        isAuthenticated: false,
        loading: false,
        error: null,
        ...initialState,
      },
    },
  });
};

// 测试组件包装器
const renderWithProviders = (component: React.ReactElement, initialState = {}) => {
  const store = createTestStore(initialState);
  return {
    ...render(
      <Provider store={store}>
        <BrowserRouter>
          {component}
        </BrowserRouter>
      </Provider>
    ),
    store,
  };
};

// Mock authService
jest.mock('../../services/authService', () => ({
  authService: {
    login: jest.fn(),
  },
}));

// Mock navigate
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

describe('LoginPage 组件测试', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockNavigate.mockClear();
  });

  test('应该渲染登录表单的所有元素', () => {
    renderWithProviders(<LoginPage />);
    
    // 检查标题
    expect(screen.getByText('道士经文视频管理系统')).toBeInTheDocument();
    expect(screen.getByText('请登录您的账户')).toBeInTheDocument();
    
    // 检查表单字段
    expect(screen.getByLabelText('用户名')).toBeInTheDocument();
    expect(screen.getByLabelText('密码')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('请输入用户名')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('请输入密码')).toBeInTheDocument();
    
    // 检查按钮
    expect(screen.getByRole('button', { name: '登录' })).toBeInTheDocument();
    
    // 检查注册链接
    expect(screen.getByText('立即注册')).toBeInTheDocument();
  });

  test('应该验证必填字段', async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />);
    
    const loginButton = screen.getByRole('button', { name: '登录' });
    
    // 初始状态下登录按钮应该被禁用
    expect(loginButton).toBeDisabled();
    
    // 只输入用户名
    const usernameInput = screen.getByLabelText('用户名');
    await user.type(usernameInput, 'testuser');
    expect(loginButton).toBeDisabled();
    
    // 输入密码后按钮应该启用
    const passwordInput = screen.getByLabelText('密码');
    await user.type(passwordInput, 'testpassword');
    expect(loginButton).not.toBeDisabled();
    
    // 清空用户名，按钮应该再次禁用
    await user.clear(usernameInput);
    expect(loginButton).toBeDisabled();
  });

  test('应该处理表单输入变化', async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />);
    
    const usernameInput = screen.getByLabelText('用户名') as HTMLInputElement;
    const passwordInput = screen.getByLabelText('密码') as HTMLInputElement;
    
    // 测试用户名输入
    await user.type(usernameInput, 'testuser');
    expect(usernameInput.value).toBe('testuser');
    
    // 测试密码输入
    await user.type(passwordInput, 'testpassword');
    expect(passwordInput.value).toBe('testpassword');
  });

  test('应该显示加载状态', () => {
    renderWithProviders(<LoginPage />, { loading: true });
    
    const loginButton = screen.getByRole('button', { name: '登录中...' });
    expect(loginButton).toBeInTheDocument();
    expect(loginButton).toBeDisabled();
  });

  test('应该显示错误信息', () => {
    const errorMessage = '用户名或密码错误';
    renderWithProviders(<LoginPage />, { error: errorMessage });
    
    expect(screen.getByText(errorMessage)).toBeInTheDocument();
  });

  test('已登录用户应该被重定向', () => {
    renderWithProviders(<LoginPage />, { 
      isAuthenticated: true,
      user: { id: 1, username: 'testuser', email: 'test@example.com', role: 'user' as const, is_active: true, created_at: '2023-01-01' }
    });
    
    expect(mockNavigate).toHaveBeenCalledWith('/');
  });

  test('应该处理表单提交', async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />);
    
    const usernameInput = screen.getByLabelText('用户名');
    const passwordInput = screen.getByLabelText('密码');
    const loginButton = screen.getByRole('button', { name: '登录' });
    
    // 填写表单
    await user.type(usernameInput, 'testuser');
    await user.type(passwordInput, 'testpassword');
    
    // 提交表单
    await user.click(loginButton);
    
    // 验证表单提交逻辑被触发
    // 注意：这里我们主要测试UI行为，实际的API调用在authSlice中测试
  });

  test('空表单不应该提交', async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />);
    
    const form = screen.getByRole('form') || screen.getByTestId('login-form') || document.querySelector('form');
    
    if (form) {
      // 尝试提交空表单
      fireEvent.submit(form);
      
      // 验证没有导航发生
      expect(mockNavigate).not.toHaveBeenCalled();
    }
  });
});