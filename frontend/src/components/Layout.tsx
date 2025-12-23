/**
 * 应用布局组件
 */
import React from 'react';
import { useSelector } from 'react-redux';
import { RootState } from '../store';
import Navbar from './Navbar';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { isAuthenticated } = useSelector((state: RootState) => state.auth);

  return (
    <div className="min-h-screen bg-gray-50">
      {isAuthenticated && <Navbar />}
      <main className={isAuthenticated ? 'pt-0' : ''}>
        {children}
      </main>
    </div>
  );
};

export default Layout;