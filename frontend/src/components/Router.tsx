/**
 * 应用路由配置
 */
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useSelector } from 'react-redux';
import { RootState } from '../store';
import Layout from './Layout';

// 页面组件
import LoginPage from '../pages/LoginPage';
import RegisterPage from '../pages/RegisterPage';
import HomePage from '../pages/HomePage';
import VideoListPage from '../pages/VideoListPage';
import VideoDetailPage from '../pages/VideoDetailPage';
import AdminDashboard from '../pages/AdminDashboard';
import VideoUploadPage from '../pages/VideoUploadPage';
import CompositionPage from '../pages/CompositionPage';

// 路由守卫组件
interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAuth?: boolean;
  requireAdmin?: boolean;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ 
  children, 
  requireAuth = false, 
  requireAdmin = false 
}) => {
  const { isAuthenticated, user } = useSelector((state: RootState) => state.auth);

  if (requireAuth && !isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (requireAdmin && (!isAuthenticated || user?.role !== 'admin')) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
};

const AppRouter: React.FC = () => {
  return (
    <Router>
      <Layout>
        <Routes>
          {/* 公开路由 */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          
          {/* 需要认证的路由 */}
          <Route 
            path="/" 
            element={
              <ProtectedRoute requireAuth>
                <HomePage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/videos" 
            element={
              <ProtectedRoute requireAuth>
                <VideoListPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/videos/:id" 
            element={
              <ProtectedRoute requireAuth>
                <VideoDetailPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/compose" 
            element={
              <ProtectedRoute requireAuth>
                <CompositionPage />
              </ProtectedRoute>
            } 
          />
          
          {/* 管理员专用路由 */}
          <Route 
            path="/admin" 
            element={
              <ProtectedRoute requireAuth requireAdmin>
                <AdminDashboard />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/admin/videos" 
            element={
              <ProtectedRoute requireAuth requireAdmin>
                <AdminDashboard />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/admin/upload" 
            element={
              <ProtectedRoute requireAuth requireAdmin>
                <VideoUploadPage />
              </ProtectedRoute>
            } 
          />
          
          {/* 默认重定向 */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </Router>
  );
};

export default AppRouter;