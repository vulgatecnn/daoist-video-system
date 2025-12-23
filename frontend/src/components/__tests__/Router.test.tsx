/**
 * 路由权限控制单元测试
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import { Provider } from 'react-redux';
import { MemoryRouter } from 'react-router-dom';
import { configureStore } from '@reduxjs/toolkit';
import AppRouter from '../Router';
import authReducer from '../../store/slices/authSlice';

// Mock 页面组件
jest.mock('../../pages/LoginPage', () => {
  return function MockLoginPage() {
    return <div data-testid="login-page">登录页面</div>;
  };
});

jest.mock('../../pages/RegisterPage', () => {
  return function MockRegisterPage() {
    return <div data-testid="register-page">注册页面</div>;
  };
});

jest.mock('../../pages/HomePage', () => {
  return function MockHomePage() {
    return <div data-testid="home-page">首页</div>;
  };
});

jest.mock('../../pages/VideoListPage', () => {
  return function MockVideoListPage() {
    return <div data-testid="video-list-page">视频列表页面</div>;
  };
});

jest.mock('../../pages/AdminDashboard', () => {
  return function MockAdminDashboard() {
    return <div data-testid="admin-dashboard">管理员仪表板</div>;
  };
});

jest.mock('../../pages/VideoUploadPage', () => {
  return function MockVideoUploadPage() {
    return <div data-testid="video-upload-page">视频上传页面</div>;
  };
});

jest.mock('../Layout', () => {
  return function MockLayout({ children }: { children: React.ReactNode }) {
    return <div data-testid="layout">{children}</div>;
  };
});

// 创建测试用的store
const createTestStore = (authState = {}) => {
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
        ...authState,
      },
    },
  });
};

// 测试组件包装器
const renderWithRouter = (initialEntries: string[], authState = {}) => {
  const store = createTestStore(authState);
  return render(
    <Provider store={store}>
      <MemoryRouter initialEntries={initialEntries}>
        <AppRouter />
      </MemoryRouter>
    </Provider>
  );
};

describe('路由权限控制测试', () => {
  describe('公开路由', () => {
    test('未认证用户可以访问登录页面', () => {
      renderWithRouter(['/login']);
      expect(screen.getByTestId('login-page')).toBeInTheDocument();
    });

    test('未认证用户可以访问注册页面', () => {
      renderWithRouter(['/register']);
      expect(screen.getByTestId('register-page')).toBeInTheDocument();
    });
  });

  describe('需要认证的路由', () => {
    test('未认证用户访问首页应该重定向到登录页面', () => {
      renderWithRouter(['/']);
      expect(screen.getByTestId('login-page')).toBeInTheDocument();
    });

    test('未认证用户访问视频列表应该重定向到登录页面', () => {
      renderWithRouter(['/videos']);
      expect(screen.getByTestId('login-page')).toBeInTheDocument();
    });

    test('已认证用户可以访问首页', () => {
      const authState = {
        isAuthenticated: true,
        user: {
          id: 1,
          username: 'testuser',
          email: 'test@example.com',
          role: 'user' as const,
          is_active: true,
          created_at: '2023-01-01',
        },
      };
      renderWithRouter(['/'], authState);
      expect(screen.getByTestId('home-page')).toBeInTheDocument();
    });

    test('已认证用户可以访问视频列表', () => {
      const authState = {
        isAuthenticated: true,
        user: {
          id: 1,
          username: 'testuser',
          email: 'test@example.com',
          role: 'user' as const,
          is_active: true,
          created_at: '2023-01-01',
        },
      };
      renderWithRouter(['/videos'], authState);
      expect(screen.getByTestId('video-list-page')).toBeInTheDocument();
    });
  });

  describe('管理员专用路由', () => {
    test('未认证用户访问管理员页面应该重定向到登录页面', () => {
      renderWithRouter(['/admin']);
      expect(screen.getByTestId('login-page')).toBeInTheDocument();
    });

    test('普通用户访问管理员页面应该重定向到首页', () => {
      const authState = {
        isAuthenticated: true,
        user: {
          id: 1,
          username: 'testuser',
          email: 'test@example.com',
          role: 'user' as const,
          is_active: true,
          created_at: '2023-01-01',
        },
      };
      renderWithRouter(['/admin'], authState);
      expect(screen.getByTestId('home-page')).toBeInTheDocument();
    });

    test('管理员用户可以访问管理员页面', () => {
      const authState = {
        isAuthenticated: true,
        user: {
          id: 1,
          username: 'admin',
          email: 'admin@example.com',
          role: 'admin' as const,
          is_active: true,
          created_at: '2023-01-01',
        },
      };
      renderWithRouter(['/admin'], authState);
      expect(screen.getByTestId('admin-dashboard')).toBeInTheDocument();
    });

    test('普通用户访问视频上传页面应该重定向到首页', () => {
      const authState = {
        isAuthenticated: true,
        user: {
          id: 1,
          username: 'testuser',
          email: 'test@example.com',
          role: 'user' as const,
          is_active: true,
          created_at: '2023-01-01',
        },
      };
      renderWithRouter(['/admin/upload'], authState);
      expect(screen.getByTestId('home-page')).toBeInTheDocument();
    });

    test('管理员用户可以访问视频上传页面', () => {
      const authState = {
        isAuthenticated: true,
        user: {
          id: 1,
          username: 'admin',
          email: 'admin@example.com',
          role: 'admin' as const,
          is_active: true,
          created_at: '2023-01-01',
        },
      };
      renderWithRouter(['/admin/upload'], authState);
      expect(screen.getByTestId('video-upload-page')).toBeInTheDocument();
    });
  });

  describe('路由重定向', () => {
    test('不存在的路由应该重定向到首页', () => {
      const authState = {
        isAuthenticated: true,
        user: {
          id: 1,
          username: 'testuser',
          email: 'test@example.com',
          role: 'user' as const,
          is_active: true,
          created_at: '2023-01-01',
        },
      };
      renderWithRouter(['/nonexistent'], authState);
      expect(screen.getByTestId('home-page')).toBeInTheDocument();
    });

    test('未认证用户访问不存在的路由应该重定向到登录页面', () => {
      renderWithRouter(['/nonexistent']);
      expect(screen.getByTestId('login-page')).toBeInTheDocument();
    });
  });

  describe('ProtectedRoute 组件测试', () => {
    test('requireAuth=true 且用户未认证时应该重定向', () => {
      renderWithRouter(['/videos']);
      expect(screen.getByTestId('login-page')).toBeInTheDocument();
    });

    test('requireAdmin=true 且用户不是管理员时应该重定向', () => {
      const authState = {
        isAuthenticated: true,
        user: {
          id: 1,
          username: 'testuser',
          email: 'test@example.com',
          role: 'user' as const,
          is_active: true,
          created_at: '2023-01-01',
        },
      };
      renderWithRouter(['/admin'], authState);
      expect(screen.getByTestId('home-page')).toBeInTheDocument();
    });

    test('满足权限要求时应该渲染子组件', () => {
      const authState = {
        isAuthenticated: true,
        user: {
          id: 1,
          username: 'admin',
          email: 'admin@example.com',
          role: 'admin' as const,
          is_active: true,
          created_at: '2023-01-01',
        },
      };
      renderWithRouter(['/admin'], authState);
      expect(screen.getByTestId('admin-dashboard')).toBeInTheDocument();
    });
  });
});