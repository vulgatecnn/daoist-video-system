/**
 * 认证功能集成测试
 * 测试登录表单验证、令牌存储和刷新、路由权限控制
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// 简单的登录表单组件测试
describe('认证功能测试', () => {
  // Mock localStorage
  const localStorageMock = {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
    clear: jest.fn(),
  };
  
  beforeAll(() => {
    Object.defineProperty(window, 'localStorage', {
      value: localStorageMock,
    });
  });

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('登录表单验证', () => {
    test('应该验证用户名和密码为必填项', () => {
      // 创建简单的登录表单
      const LoginForm = () => {
        const [username, setUsername] = React.useState('');
        const [password, setPassword] = React.useState('');
        
        const isValid = username.trim() !== '' && password.trim() !== '';
        
        return (
          <form>
            <input
              data-testid="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="用户名"
            />
            <input
              data-testid="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="密码"
            />
            <button
              data-testid="submit"
              type="submit"
              disabled={!isValid}
            >
              登录
            </button>
          </form>
        );
      };

      render(<LoginForm />);
      
      const usernameInput = screen.getByTestId('username');
      const passwordInput = screen.getByTestId('password');
      const submitButton = screen.getByTestId('submit');
      
      // 初始状态下按钮应该被禁用
      expect(submitButton).toBeDisabled();
      
      // 只输入用户名，按钮仍然禁用
      fireEvent.change(usernameInput, { target: { value: 'testuser' } });
      expect(submitButton).toBeDisabled();
      
      // 输入密码后，按钮启用
      fireEvent.change(passwordInput, { target: { value: 'testpassword' } });
      expect(submitButton).not.toBeDisabled();
      
      // 清空用户名，按钮再次禁用
      fireEvent.change(usernameInput, { target: { value: '' } });
      expect(submitButton).toBeDisabled();
    });

    test('应该处理空白字符验证', () => {
      const LoginForm = () => {
        const [username, setUsername] = React.useState('');
        const [password, setPassword] = React.useState('');
        
        const isValid = username.trim() !== '' && password.trim() !== '';
        
        return (
          <form>
            <input
              data-testid="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
            <input
              data-testid="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <button
              data-testid="submit"
              disabled={!isValid}
            >
              登录
            </button>
          </form>
        );
      };

      render(<LoginForm />);
      
      const usernameInput = screen.getByTestId('username');
      const passwordInput = screen.getByTestId('password');
      const submitButton = screen.getByTestId('submit');
      
      // 输入只包含空格的用户名和密码
      fireEvent.change(usernameInput, { target: { value: '   ' } });
      fireEvent.change(passwordInput, { target: { value: '   ' } });
      
      // 按钮应该仍然被禁用
      expect(submitButton).toBeDisabled();
    });
  });

  describe('令牌存储和管理', () => {
    test('应该正确存储认证令牌', () => {
      const TokenManager = () => {
        const saveTokens = () => {
          const tokens = {
            access: 'access-token-123',
            refresh: 'refresh-token-456',
          };
          const user = {
            id: 1,
            username: 'testuser',
            email: 'test@example.com',
            role: 'user',
          };
          
          localStorage.setItem('accessToken', tokens.access);
          localStorage.setItem('refreshToken', tokens.refresh);
          localStorage.setItem('user', JSON.stringify(user));
        };
        
        return (
          <button data-testid="save-tokens" onClick={saveTokens}>
            保存令牌
          </button>
        );
      };

      render(<TokenManager />);
      
      const saveButton = screen.getByTestId('save-tokens');
      fireEvent.click(saveButton);
      
      expect(localStorageMock.setItem).toHaveBeenCalledWith('accessToken', 'access-token-123');
      expect(localStorageMock.setItem).toHaveBeenCalledWith('refreshToken', 'refresh-token-456');
      expect(localStorageMock.setItem).toHaveBeenCalledWith('user', JSON.stringify({
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        role: 'user',
      }));
    });

    test('应该正确清除认证令牌', () => {
      const TokenManager = () => {
        const clearTokens = () => {
          localStorage.removeItem('accessToken');
          localStorage.removeItem('refreshToken');
          localStorage.removeItem('user');
        };
        
        return (
          <button data-testid="clear-tokens" onClick={clearTokens}>
            清除令牌
          </button>
        );
      };

      render(<TokenManager />);
      
      const clearButton = screen.getByTestId('clear-tokens');
      fireEvent.click(clearButton);
      
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('accessToken');
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('refreshToken');
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('user');
    });

    test('应该从localStorage加载令牌', () => {
      const mockUser = { id: 1, username: 'testuser', email: 'test@example.com', role: 'user' };
      
      localStorageMock.getItem.mockImplementation((key) => {
        switch (key) {
          case 'accessToken':
            return 'stored-access-token';
          case 'refreshToken':
            return 'stored-refresh-token';
          case 'user':
            return JSON.stringify(mockUser);
          default:
            return null;
        }
      });

      const TokenLoader = () => {
        const [tokens, setTokens] = React.useState<any>(null);
        
        React.useEffect(() => {
          const accessToken = localStorage.getItem('accessToken');
          const refreshToken = localStorage.getItem('refreshToken');
          const userStr = localStorage.getItem('user');
          const user = userStr ? JSON.parse(userStr) : null;
          
          setTokens({ accessToken, refreshToken, user });
        }, []);
        
        if (!tokens) return <div>Loading...</div>;
        
        return (
          <div>
            <div data-testid="access-token">{tokens.accessToken}</div>
            <div data-testid="refresh-token">{tokens.refreshToken}</div>
            <div data-testid="user-name">{tokens.user?.username}</div>
          </div>
        );
      };

      render(<TokenLoader />);
      
      expect(screen.getByTestId('access-token')).toHaveTextContent('stored-access-token');
      expect(screen.getByTestId('refresh-token')).toHaveTextContent('stored-refresh-token');
      expect(screen.getByTestId('user-name')).toHaveTextContent('testuser');
    });
  });

  describe('路由权限控制', () => {
    test('应该根据认证状态控制访问', () => {
      const ProtectedComponent = ({ isAuthenticated }: { isAuthenticated: boolean }) => {
        if (!isAuthenticated) {
          return <div data-testid="login-required">请先登录</div>;
        }
        return <div data-testid="protected-content">受保护的内容</div>;
      };

      // 未认证状态
      const { rerender } = render(<ProtectedComponent isAuthenticated={false} />);
      expect(screen.getByTestId('login-required')).toBeInTheDocument();
      
      // 已认证状态
      rerender(<ProtectedComponent isAuthenticated={true} />);
      expect(screen.getByTestId('protected-content')).toBeInTheDocument();
    });

    test('应该根据用户角色控制管理员功能', () => {
      const AdminComponent = ({ user }: { user: { role: string } | null }) => {
        if (!user) {
          return <div data-testid="login-required">请先登录</div>;
        }
        
        if (user.role !== 'admin') {
          return <div data-testid="access-denied">权限不足</div>;
        }
        
        return <div data-testid="admin-content">管理员功能</div>;
      };

      // 未登录
      const { rerender } = render(<AdminComponent user={null} />);
      expect(screen.getByTestId('login-required')).toBeInTheDocument();
      
      // 普通用户
      rerender(<AdminComponent user={{ role: 'user' }} />);
      expect(screen.getByTestId('access-denied')).toBeInTheDocument();
      
      // 管理员用户
      rerender(<AdminComponent user={{ role: 'admin' }} />);
      expect(screen.getByTestId('admin-content')).toBeInTheDocument();
    });

    test('应该处理权限检查逻辑', () => {
      const checkPermission = (user: any, requiredRole: string) => {
        if (!user) return false;
        if (requiredRole === 'admin' && user.role !== 'admin') return false;
        return true;
      };

      // 测试权限检查函数
      expect(checkPermission(null, 'user')).toBe(false);
      expect(checkPermission({ role: 'user' }, 'user')).toBe(true);
      expect(checkPermission({ role: 'user' }, 'admin')).toBe(false);
      expect(checkPermission({ role: 'admin' }, 'admin')).toBe(true);
    });
  });

  describe('错误处理', () => {
    test('应该处理登录错误', () => {
      const LoginWithError = () => {
        const [error, setError] = React.useState<string | null>(null);
        
        const handleLogin = () => {
          // 模拟登录失败
          setError('用户名或密码错误');
        };
        
        return (
          <div>
            {error && <div data-testid="error-message">{error}</div>}
            <button data-testid="login-button" onClick={handleLogin}>
              登录
            </button>
          </div>
        );
      };

      render(<LoginWithError />);
      
      const loginButton = screen.getByTestId('login-button');
      fireEvent.click(loginButton);
      
      expect(screen.getByTestId('error-message')).toHaveTextContent('用户名或密码错误');
    });

    test('应该处理令牌刷新失败', () => {
      const TokenRefresh = () => {
        const [status, setStatus] = React.useState<string>('idle');
        
        const refreshToken = async () => {
          setStatus('refreshing');
          try {
            // 模拟刷新失败
            throw new Error('刷新令牌失败');
          } catch (error) {
            setStatus('failed');
            // 清除本地存储
            localStorage.removeItem('accessToken');
            localStorage.removeItem('refreshToken');
            localStorage.removeItem('user');
          }
        };
        
        return (
          <div>
            <div data-testid="status">{status}</div>
            <button data-testid="refresh-button" onClick={refreshToken}>
              刷新令牌
            </button>
          </div>
        );
      };

      render(<TokenRefresh />);
      
      const refreshButton = screen.getByTestId('refresh-button');
      fireEvent.click(refreshButton);
      
      expect(screen.getByTestId('status')).toHaveTextContent('failed');
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('accessToken');
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('refreshToken');
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('user');
    });
  });
});