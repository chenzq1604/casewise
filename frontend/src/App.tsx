/**
 * 主应用组件
 * 配置路由、全局布局和认证守卫
 * 使用 React Router 6.x 路由管理
 */
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, App as AntApp, Spin } from 'antd';
import { StyleProvider } from '@ant-design/cssinjs';
import zhCN from 'antd/locale/zh_CN';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import AppLayout from './components/AppLayout';
import HomePage from './pages/HomePage';
import ChatPage from './pages/ChatPage';
import ContractPage from './pages/ContractPage';
import ReviewPage from './pages/ReviewPage';
import DataPage from './pages/DataPage';
import SettingsPage from './pages/SettingsPage';
import LoginPage from './pages/LoginPage';
import GuidePage from './pages/GuidePage';
import DocumentPage from './pages/DocumentPage';
import CalculatorPage from './pages/CalculatorPage';

/**
 * 角色权限配置
 * 定义每个路由允许访问的角色
 */
const ROUTE_PERMISSIONS: Record<string, string[]> = {
  '/': ['admin', 'lawyer', 'client'],
  '/chat': ['admin', 'lawyer', 'client'],
  '/contract': ['admin', 'lawyer', 'client'],
  '/guide': ['admin', 'lawyer', 'client'],
  '/document': ['admin', 'lawyer', 'client'],
  '/calculator': ['admin', 'lawyer', 'client'],
  '/review': ['admin', 'lawyer'],
  '/data': ['admin', 'lawyer'],
  '/settings': ['admin'],
};

/**
 * 认证路由守卫组件
 *
 * 检查用户是否登录，未登录则跳转登录页；
 * 检查用户角色是否有权限访问当前路由。
 */
const AuthGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" tip="加载中...">
          <div />
        </Spin>
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  return <>{children}</>;
};

/**
 * 角色权限守卫组件
 *
 * 根据当前路由路径检查用户角色权限。
 */
const RoleGuard: React.FC<{ path: string; children: React.ReactNode }> = ({ path, children }) => {
  const { user } = useAuth();
  const allowedRoles = ROUTE_PERMISSIONS[path] || ['admin', 'lawyer', 'client'];

  if (user && !allowedRoles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
};

/**
 * App 根组件
 * 包含Ant Design中文国际化配置、认证上下文和路由配置
 */
const App: React.FC = () => {
  return (
    <StyleProvider container={document.head}>
      <ConfigProvider
        locale={zhCN}
        theme={{
          token: {
            colorPrimary: '#1890ff',
            borderRadius: 6,
          },
        }}
      >
        <BrowserRouter>
          <AuthProvider>
            <AntApp>
              <AuthGuard>
                <AppLayout>
                  <Routes>
                    <Route path="/" element={<RoleGuard path="/"><HomePage /></RoleGuard>} />
                    <Route path="/chat" element={<RoleGuard path="/chat"><ChatPage /></RoleGuard>} />
                    <Route path="/contract" element={<RoleGuard path="/contract"><ContractPage /></RoleGuard>} />
                    <Route path="/guide" element={<RoleGuard path="/guide"><GuidePage /></RoleGuard>} />
                    <Route path="/document" element={<RoleGuard path="/document"><DocumentPage /></RoleGuard>} />
                    <Route path="/calculator" element={<RoleGuard path="/calculator"><CalculatorPage /></RoleGuard>} />
                    <Route path="/review" element={<RoleGuard path="/review"><ReviewPage /></RoleGuard>} />
                    <Route path="/data" element={<RoleGuard path="/data"><DataPage /></RoleGuard>} />
                    <Route path="/settings" element={<RoleGuard path="/settings"><SettingsPage /></RoleGuard>} />
                  </Routes>
                </AppLayout>
              </AuthGuard>
            </AntApp>
          </AuthProvider>
        </BrowserRouter>
      </ConfigProvider>
    </StyleProvider>
  );
};

export default App;
