/**
 * 主应用组件
 * 配置路由和全局布局
 * 使用 React Router 6.x 路由管理
 */
import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import AppLayout from './components/AppLayout';
import HomePage from './pages/HomePage';
import ChatPage from './pages/ChatPage';
import ContractPage from './pages/ContractPage';
import ReviewPage from './pages/ReviewPage';
import DataPage from './pages/DataPage';

/**
 * App 根组件
 * 包含Ant Design中文国际化配置和路由配置
 */
const App: React.FC = () => {
  return (
    /** Ant Design 中文国际化配置 */
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
        <AppLayout>
          <Routes>
            {/* 首页 */}
            <Route path="/" element={<HomePage />} />
            {/* 法律问答页 */}
            <Route path="/chat" element={<ChatPage />} />
            {/* 合同审查页 */}
            <Route path="/contract" element={<ContractPage />} />
            {/* 复核统计页 */}
            <Route path="/review" element={<ReviewPage />} />
            {/* 数据管理页 */}
            <Route path="/data" element={<DataPage />} />
          </Routes>
        </AppLayout>
      </BrowserRouter>
    </ConfigProvider>
  );
};

export default App;
