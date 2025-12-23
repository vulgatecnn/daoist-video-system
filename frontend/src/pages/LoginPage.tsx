/**
 * 登录页面
 */
import React, { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate, Link } from 'react-router-dom';
import { AppDispatch, RootState } from '../store';
import { loginAsync, clearError } from '../store/slices/authSlice';

const LoginPage: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const navigate = useNavigate();
  const { loading, error, isAuthenticated } = useSelector((state: RootState) => state.auth);
  
  const [formData, setFormData] = useState({
    username: '',
    password: '',
  });

  // 如果已经登录，重定向到首页
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/');
    }
  }, [isAuthenticated, navigate]);

  // 清除错误信息
  useEffect(() => {
    return () => {
      dispatch(clearError());
    };
  }, [dispatch]);

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
      return;
    }

    try {
      await dispatch(loginAsync(formData)).unwrap();
      navigate('/');
    } catch (error) {
      // 错误已经在reducer中处理
    }
  };

  return (
    <div className="login-container">
      <div className="login-form">
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <h2 style={{ fontSize: '1.875rem', fontWeight: 'bold', color: '#111827', marginBottom: '0.5rem' }}>
            道士经文视频管理系统
          </h2>
          <p style={{ fontSize: '0.875rem', color: '#6b7280' }}>
            请登录您的账户
          </p>
        </div>
        
        <form onSubmit={handleSubmit}>
          {error && (
            <div className="error">
              {error}
            </div>
          )}
          
          <div className="form-group">
            <label htmlFor="username" className="form-label">
              用户名
            </label>
            <input
              id="username"
              name="username"
              type="text"
              required
              className="form-input"
              placeholder="请输入用户名"
              value={formData.username}
              onChange={handleInputChange}
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="password" className="form-label">
              密码
            </label>
            <input
              id="password"
              name="password"
              type="password"
              required
              className="form-input"
              placeholder="请输入密码"
              value={formData.password}
              onChange={handleInputChange}
            />
          </div>

          <div className="form-group">
            <button
              type="submit"
              disabled={loading || !formData.username || !formData.password}
              className="btn btn-primary"
              style={{ width: '100%', justifyContent: 'center' }}
            >
              {loading ? '登录中...' : '登录'}
            </button>
          </div>

          <div style={{ textAlign: 'center' }}>
            <p style={{ fontSize: '0.875rem', color: '#6b7280' }}>
              还没有账户？{' '}
              <Link to="/register" style={{ color: '#4f46e5', fontWeight: '500' }}>
                立即注册
              </Link>
            </p>
          </div>
        </form>
      </div>
    </div>
  );
};

export default LoginPage;