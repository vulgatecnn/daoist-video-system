/**
 * 认证功能单元测试
 * 专注测试核心认证逻辑和组件行为
 */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

describe('认证单元测试', () => {
  describe('登录表单组件', () => {
    // 简化的登录表单组件用于测试
    const SimpleLoginForm = () => {
      const [formData, setFormData] = React.useState({
        username: '',
        password: '',
      });
      const [loading, setLoading] = React.useState(false);
      const [error, setError] = React.useState<string | null>(null);

      const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value } = e.target;
        setFormData(prev => ({
          ...prev,
          [name]: value,
        }));
      };

      const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        
        if (!formData.username || !formData.password) {
          setError('用户名和密码不能为空');
          return;
        }

        setLoading(true);
        setError(null);
        
        // 模拟API调用
        setTimeout(() => {
          if (formData.username === 'admin' && formData.password === 'admin123') {
            setLoading(false);
            // 登录成功逻辑
          } else {
            setLoading(false);
            setError('用户名或密码错误');
          }
        }, 100);
      };

      const isFormValid = formData.username.trim() !== '' && formData.password.trim() !== '';

      return (
        <div data-testid="login-form">
          <h2>道士经文视频管理系统</h2>
          <p>请登录您的账户</p>
          
          <form onSubmit={handleSubmit}>
            {error && (
              <div data-testid="error-message" style={{ color: 'red' }}>
                {error}
              </div>
            )}
            
            <div>
              <label htmlFor="username">用户名</label>
              <input
                id="username"
                name="username"
                type="text"
                required
                placeholder="请输入用户名"
                value={formData.username}
                onChange={handleInputChange}
                data-testid="username-input"
              />
            </div>
            
            <div>
              <label htmlFor="password">密码</label>
              <input
                id="password"
                name="password"
                type="password"
                required
                placeholder="请输入密码"
                value={formData.password}
                onChange={handleInputChange}
                data-testid="password-input"
              />
            </div>

            <button
              type="submit"
              disabled={loading || !isFormValid}
              data-testid="submit-button"
            >
              {loading ? '登录中...' : '登录'}
            </button>
          </form>
        </div>
      );
    };

    test('应该渲染所有必要的表单元素', () => {
      render(<SimpleLoginForm />);
      
      expect(screen.getByText('道士经文视频管理系统')).toBeInTheDocument();
      expect(screen.getByText('请登录您的账户')).toBeInTheDocument();
      expect(screen.getByLabelText('用户名')).toBeInTheDocument();
      expect(screen.getByLabelText('密码')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('请输入用户名')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('请输入密码')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '登录' })).toBeInTheDocument();
    });

    test('应该正确处理表单输入', () => {
      render(<SimpleLoginForm />);
      
      const usernameInput = screen.getByTestId('username-input') as HTMLInputElement;
      const passwordInput = screen.getByTestId('password-input') as HTMLInputElement;
      
      fireEvent.change(usernameInput, { target: { value: 'testuser' } });
      fireEvent.change(passwordInput, { target: { value: 'testpass' } });
      
      expect(usernameInput.value).toBe('testuser');
      expect(passwordInput.value).toBe('testpass');
    });

    test('应该验证表单字段', () => {
      render(<SimpleLoginForm />);
      
      const submitButton = screen.getByTestId('submit-button');
      const usernameInput = screen.getByTestId('username-input');
      const passwordInput = screen.getByTestId('password-input');
      
      // 初始状态下按钮应该被禁用
      expect(submitButton).toBeDisabled();
      
      // 只输入用户名
      fireEvent.change(usernameInput, { target: { value: 'testuser' } });
      expect(submitButton).toBeDisabled();
      
      // 输入密码后按钮应该启用
      fireEvent.change(passwordInput, { target: { value: 'testpass' } });
      expect(submitButton).not.toBeDisabled();
      
      // 清空用户名，按钮应该再次禁用
      fireEvent.change(usernameInput, { target: { value: '' } });
      expect(submitButton).toBeDisabled();
    });

    test('应该处理空表单提交', () => {
      render(<SimpleLoginForm />);
      
      const form = screen.getByTestId('login-form').querySelector('form');
      fireEvent.submit(form!);
      
      expect(screen.getByTestId('error-message')).toHaveTextContent('用户名和密码不能为空');
    });

    test('应该显示加载状态', async () => {
      render(<SimpleLoginForm />);
      
      const usernameInput = screen.getByTestId('username-input');
      const passwordInput = screen.getByTestId('password-input');
      const submitButton = screen.getByTestId('submit-button');
      
      fireEvent.change(usernameInput, { target: { value: 'admin' } });
      fireEvent.change(passwordInput, { target: { value: 'admin123' } });
      
      fireEvent.click(submitButton);
      
      expect(screen.getByText('登录中...')).toBeInTheDocument();
      expect(submitButton).toBeDisabled();
    });
  });

  describe('权限控制组件', () => {
    interface User {
      id: number;
      username: string;
      role: 'admin' | 'user';
    }

    const ProtectedRoute = ({ 
      children, 
      requireAuth = false, 
      requireAdmin = false,
      isAuthenticated = false,
      user = null 
    }: {
      children: React.ReactNode;
      requireAuth?: boolean;
      requireAdmin?: boolean;
      isAuthenticated?: boolean;
      user?: User | null;
    }) => {
      if (requireAuth && !isAuthenticated) {
        return <div data-testid="redirect-login">重定向到登录页面</div>;
      }

      if (requireAdmin && (!isAuthenticated || user?.role !== 'admin')) {
        return <div data-testid="redirect-home">重定向到首页</div>;
      }

      return <>{children}</>;
    };

    test('未认证用户访问受保护路由应该重定向', () => {
      render(
        <ProtectedRoute requireAuth={true} isAuthenticated={false}>
          <div data-testid="protected-content">受保护的内容</div>
        </ProtectedRoute>
      );
      
      expect(screen.getByTestId('redirect-login')).toBeInTheDocument();
      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
    });

    test('已认证用户可以访问受保护路由', () => {
      const user = { id: 1, username: 'testuser', role: 'user' as const };
      
      render(
        <ProtectedRoute requireAuth={true} isAuthenticated={true} user={user}>
          <div data-testid="protected-content">受保护的内容</div>
        </ProtectedRoute>
      );
      
      expect(screen.getByTestId('protected-content')).toBeInTheDocument();
      expect(screen.queryByTestId('redirect-login')).not.toBeInTheDocument();
    });

    test('普通用户访问管理员路由应该重定向', () => {
      const user = { id: 1, username: 'testuser', role: 'user' as const };
      
      render(
        <ProtectedRoute requireAuth={true} requireAdmin={true} isAuthenticated={true} user={user}>
          <div data-testid="admin-content">管理员内容</div>
        </ProtectedRoute>
      );
      
      expect(screen.getByTestId('redirect-home')).toBeInTheDocument();
      expect(screen.queryByTestId('admin-content')).not.toBeInTheDocument();
    });

    test('管理员用户可以访问管理员路由', () => {
      const user = { id: 1, username: 'admin', role: 'admin' as const };
      
      render(
        <ProtectedRoute requireAuth={true} requireAdmin={true} isAuthenticated={true} user={user}>
          <div data-testid="admin-content">管理员内容</div>
        </ProtectedRoute>
      );
      
      expect(screen.getByTestId('admin-content')).toBeInTheDocument();
      expect(screen.queryByTestId('redirect-home')).not.toBeInTheDocument();
    });
  });

  describe('认证状态管理', () => {
    const AuthStateManager = () => {
      const [authState, setAuthState] = React.useState({
        user: null as any,
        accessToken: null as string | null,
        refreshToken: null as string | null,
        isAuthenticated: false,
        loading: false,
        error: null as string | null,
      });

      const login = (userData: any, tokens: any) => {
        setAuthState({
          user: userData,
          accessToken: tokens.access,
          refreshToken: tokens.refresh,
          isAuthenticated: true,
          loading: false,
          error: null,
        });
      };

      const logout = () => {
        setAuthState({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
          loading: false,
          error: null,
        });
      };

      const setError = (error: string) => {
        setAuthState(prev => ({
          ...prev,
          error,
          loading: false,
        }));
      };

      const clearError = () => {
        setAuthState(prev => ({
          ...prev,
          error: null,
        }));
      };

      return (
        <div>
          <div data-testid="auth-status">
            {authState.isAuthenticated ? '已登录' : '未登录'}
          </div>
          <div data-testid="user-info">
            {authState.user ? authState.user.username : '无用户'}
          </div>
          {authState.error && (
            <div data-testid="error">{authState.error}</div>
          )}
          
          <button
            data-testid="login-btn"
            onClick={() => login(
              { id: 1, username: 'testuser', role: 'user' },
              { access: 'access-token', refresh: 'refresh-token' }
            )}
          >
            登录
          </button>
          
          <button data-testid="logout-btn" onClick={logout}>
            登出
          </button>
          
          <button data-testid="set-error-btn" onClick={() => setError('测试错误')}>
            设置错误
          </button>
          
          <button data-testid="clear-error-btn" onClick={clearError}>
            清除错误
          </button>
        </div>
      );
    };

    test('应该正确管理登录状态', () => {
      render(<AuthStateManager />);
      
      expect(screen.getByTestId('auth-status')).toHaveTextContent('未登录');
      expect(screen.getByTestId('user-info')).toHaveTextContent('无用户');
      
      fireEvent.click(screen.getByTestId('login-btn'));
      
      expect(screen.getByTestId('auth-status')).toHaveTextContent('已登录');
      expect(screen.getByTestId('user-info')).toHaveTextContent('testuser');
    });

    test('应该正确处理登出', () => {
      render(<AuthStateManager />);
      
      // 先登录
      fireEvent.click(screen.getByTestId('login-btn'));
      expect(screen.getByTestId('auth-status')).toHaveTextContent('已登录');
      
      // 然后登出
      fireEvent.click(screen.getByTestId('logout-btn'));
      expect(screen.getByTestId('auth-status')).toHaveTextContent('未登录');
      expect(screen.getByTestId('user-info')).toHaveTextContent('无用户');
    });

    test('应该正确管理错误状态', () => {
      render(<AuthStateManager />);
      
      fireEvent.click(screen.getByTestId('set-error-btn'));
      expect(screen.getByTestId('error')).toHaveTextContent('测试错误');
      
      fireEvent.click(screen.getByTestId('clear-error-btn'));
      expect(screen.queryByTestId('error')).not.toBeInTheDocument();
    });
  });
});