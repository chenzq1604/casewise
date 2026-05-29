/**
 * 全局布局组件
 * 桌面端：左侧导航栏 + 顶部标题栏 + 内容区
 * 移动端：顶部标题栏 + 内容区 + 底部Tab栏
 * 响应式断点：768px
 */
import React, { useState, useEffect } from 'react';
import { Layout, Menu, Typography } from 'antd';
import {
  HomeOutlined,
  MessageOutlined,
  FileSearchOutlined,
  BarChartOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';

const { Header, Sider, Content } = Layout;
const { Title } = Typography;

/** 导航菜单项配置 */
const menuItems = [
  {
    key: '/',
    icon: <HomeOutlined />,
    label: '首页',
  },
  {
    key: '/chat',
    icon: <MessageOutlined />,
    label: '法律问答',
  },
  {
    key: '/contract',
    icon: <FileSearchOutlined />,
    label: '合同审查',
  },
  {
    key: '/review',
    icon: <BarChartOutlined />,
    label: '复核统计',
  },
  {
    key: '/data',
    icon: <DatabaseOutlined />,
    label: '数据管理',
  },
];

/** 底部Tab栏菜单项（与侧边栏一致） */
const tabItems = menuItems.map((item) => ({
  key: item.key,
  label: item.label,
  icon: item.icon,
}));

/**
 * AppLayout 全局布局组件
 * 管理侧边栏/底部Tab导航、顶部标题栏和内容区域
 */
const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  /** 侧边栏折叠状态 */
  const [collapsed, setCollapsed] = useState(false);
  /** 是否为移动端视图 */
  const [isMobile, setIsMobile] = useState(false);

  const navigate = useNavigate();
  const location = useLocation();

  /**
   * 监听窗口尺寸变化，判断是否为移动端
   * 断点：768px
   */
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);

    return () => {
      window.removeEventListener('resize', checkMobile);
    };
  }, []);

  /**
   * 处理侧边栏菜单点击
   * @param info - 菜单点击信息
   */
  const handleMenuClick = (info: { key: string }) => {
    navigate(info.key);
  };

  /**
   * 处理底部Tab栏切换
   * @param key - 选中的Tab键
   */
  const handleTabChange = (key: string) => {
    navigate(key);
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* 桌面端侧边栏 */}
      {!isMobile && (
        <Sider
          className="desktop-sidebar"
          collapsible
          collapsed={collapsed}
          onCollapse={setCollapsed}
          theme="light"
          style={{
            borderRight: '1px solid #f0f0f0',
          }}
        >
          {/* 侧边栏Logo区域 */}
          <div
            style={{
              height: 64,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderBottom: '1px solid #f0f0f0',
            }}
          >
            <Title
              level={4}
              style={{
                margin: 0,
                color: '#1890ff',
                fontSize: collapsed ? 16 : 18,
                whiteSpace: 'nowrap',
              }}
            >
              {collapsed ? 'CW' : 'CaseWise'}
            </Title>
          </div>

          {/* 导航菜单 */}
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
            items={menuItems}
            onClick={handleMenuClick}
            style={{ borderRight: 'none' }}
          />
        </Sider>
      )}

      <Layout>
        {/* 顶部标题栏 */}
        <Header
          className="app-header"
          style={{
            background: '#fff',
            padding: '0 24px',
            display: 'flex',
            alignItems: 'center',
            borderBottom: '1px solid #f0f0f0',
            height: 64,
          }}
        >
          <Title
            level={4}
            className="header-title"
            style={{ margin: 0, color: '#262626' }}
          >
            CaseWise 法律AI助手
          </Title>
        </Header>

        {/* 内容区域 */}
        <Content
          className="main-content-area"
          style={{
            padding: 24,
            background: '#f5f5f5',
            minHeight: 'calc(100vh - 64px)',
            overflow: 'auto',
          }}
        >
          {children}
        </Content>
      </Layout>

      {/* 移动端底部Tab栏 */}
      {isMobile && (
        <div className="mobile-tab-bar">
          <Menu
            mode="horizontal"
            selectedKeys={[location.pathname]}
            items={tabItems}
            onClick={handleTabChange}
            style={{
              width: '100%',
              display: 'flex',
              justifyContent: 'space-around',
              border: 'none',
            }}
          />
        </div>
      )}
    </Layout>
  );
};

export default AppLayout;
