/**
 * 全局布局组件
 * 桌面端：左侧导航栏 + 顶部标题栏 + 内容区
 * 移动端：顶部标题栏 + 内容区 + 底部Tab栏
 * 响应式断点：768px
 * 根据用户角色动态显示菜单项
 */
import React, { useState, useEffect, useMemo } from 'react';
import { Layout, Menu, Typography, Tag, Dropdown, Avatar, Space } from 'antd';
import type { MenuProps } from 'antd';
import {
  HomeOutlined,
  MessageOutlined,
  FileSearchOutlined,
  BarChartOutlined,
  DatabaseOutlined,
  LogoutOutlined,
  UserOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const { Header, Sider, Content } = Layout;
const { Title, Text } = Typography;

/**
 * 角色标签颜色映射
 */
const ROLE_TAG_MAP: Record<string, { color: string; label: string }> = {
  admin: { color: 'red', label: '管理员' },
  lawyer: { color: 'green', label: '律师' },
  client: { color: 'blue', label: '客户' },
};

/**
 * 菜单项允许访问的角色配置
 */
const MENU_ROLE_MAP: Record<string, string[]> = {
  '/': ['admin', 'lawyer', 'client'],
  '/chat': ['admin', 'lawyer', 'client'],
  '/contract': ['admin', 'lawyer', 'client'],
  '/review': ['admin', 'lawyer'],
  '/data': ['admin', 'lawyer'],
};

/**
 * 全部菜单项定义
 */
const ALL_MENU_ITEMS = [
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

/**
 * AppLayout 全局布局组件
 * 管理侧边栏/底部Tab导航、顶部标题栏和内容区域
 * 根据用户角色动态过滤菜单项
 */
const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, logout, hasRole } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  const navigate = useNavigate();
  const location = useLocation();

  /**
   * 根据用户角色过滤菜单项
   */
  const menuItems = useMemo(() => {
    if (!user) return ALL_MENU_ITEMS;
    return ALL_MENU_ITEMS.filter((item) => {
      const allowedRoles = MENU_ROLE_MAP[item.key] || ['admin', 'lawyer', 'client'];
      return allowedRoles.includes(user.role);
    });
  }, [user]);

  /** 底部Tab栏菜单项 */
  const tabItems = useMemo(() => menuItems.map((item) => ({
    key: item.key,
    label: item.label,
    icon: item.icon,
  })), [menuItems]);

  /**
   * 监听窗口尺寸变化，判断是否为移动端
   */
  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth <= 768);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const handleMenuClick: MenuProps['onClick'] = (info) => {
    navigate(info.key);
  };

  /**
   * 用户下拉菜单
   */
  const userMenuItems: MenuProps['items'] = [
    {
      key: 'userinfo',
      label: (
        <Space direction="vertical" size={0} style={{ padding: '4px 0' }}>
          <Text strong>{user?.display_name || user?.username}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {user?.username} · {ROLE_TAG_MAP[user?.role || 'client']?.label}
          </Text>
        </Space>
      ),
      disabled: true,
    },
    { type: 'divider' },
    ...(hasRole('admin')
      ? [{ key: 'settings', icon: <SettingOutlined />, label: '系统管理' }]
      : []),
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      danger: true,
    },
  ];

  const handleUserMenuClick: MenuProps['onClick'] = ({ key }) => {
    if (key === 'logout') {
      logout();
      navigate('/');
    }
  };

  const roleInfo = ROLE_TAG_MAP[user?.role || 'client'];

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
          style={{ borderRight: '1px solid #f0f0f0' }}
        >
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
            justifyContent: 'space-between',
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

          {/* 用户信息区域 */}
          <Dropdown
            menu={{ items: userMenuItems, onClick: handleUserMenuClick }}
            placement="bottomRight"
          >
            <Space style={{ cursor: 'pointer' }}>
              <Avatar size="small" icon={<UserOutlined />} style={{ backgroundColor: '#1890ff' }} />
              <span style={{ fontSize: 14, color: '#262626' }}>
                {user?.display_name || user?.username}
              </span>
              <Tag color={roleInfo?.color} style={{ margin: 0, fontSize: 11 }}>
                {roleInfo?.label}
              </Tag>
            </Space>
          </Dropdown>
        </Header>

        {/* 内容区域 */}
        <Content
          className="main-content-area"
          style={{
            padding: 24,
            background: '#f5f5f5',
            minHeight: 'calc(100vh - 64px)',
            overflow: 'auto',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <div style={{ flex: 1 }}>
            {children}
          </div>
          <div style={{
            textAlign: 'center',
            padding: '16px 0 0',
            fontSize: 12,
            color: '#8c8c8c',
          }}>
            <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer" style={{ color: '#8c8c8c' }}>
              粤ICP备2026056746号
            </a>
          </div>
        </Content>
      </Layout>

      {/* 移动端底部Tab栏 */}
      {isMobile && (
        <div className="mobile-tab-bar">
          <Menu
            mode="horizontal"
            selectedKeys={[location.pathname]}
            items={tabItems}
            onClick={handleMenuClick}
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
