/**
 * CaseWise 法律AI工具 - 登录页面
 *
 * 提供用户登录和注册功能，支持3种角色选择。
 */

import React, { useState } from 'react';
import { Form, Input, Button, Card, Select, Typography, Divider, Space, Tag, App } from 'antd';
import { UserOutlined, LockOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';

const { Title, Text } = Typography;

const ROLE_OPTIONS = [
  { value: 'client', label: '客户', color: 'blue', desc: '提交合同、法律问询、获取报告' },
  { value: 'lawyer', label: '律师', color: 'green', desc: '数据抓取、合同审核、复核统计' },
  { value: 'admin', label: '管理员', color: 'red', desc: '系统管理、模型配置、数据备份' },
];

/**
 * 登录页面组件
 */
const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [form] = Form.useForm();

  const handleSubmit = async (values: { username: string; password: string; role?: string; display_name?: string }) => {
    setLoading(true);
    try {
      await login(values.username, values.password);
      message.success('登录成功');
    } catch (err: unknown) {
      const errorMsg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '登录失败，请检查用户名和密码';
      message.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (values: { username: string; password: string; role: string; display_name?: string }) => {
    setLoading(true);
    try {
      const { authApi } = await import('../services/api');
      const res = await authApi.register({
        username: values.username,
        password: values.password,
        role: values.role,
        display_name: values.display_name,
      });
      message.success('注册成功，已自动登录');
      await login(res.user.username, values.password);
    } catch (err: unknown) {
      const errorMsg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '注册失败';
      message.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      padding: 24,
    }}>
      <Card
        style={{ width: 420, maxWidth: '100%', borderRadius: 12, boxShadow: '0 8px 40px rgba(0,0,0,0.12)' }}
        styles={{ body: { padding: '32px 28px' } }}
      >
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <SafetyCertificateOutlined style={{ fontSize: 42, color: '#1890ff', marginBottom: 8 }} />
          <Title level={3} style={{ margin: 0, color: '#262626' }}>CaseWise</Title>
          <Text type="secondary" style={{ fontSize: 14 }}>法律AI助手 · 智能合规审查平台</Text>
        </div>

        {mode === 'login' ? (
          <Form form={form} onFinish={handleSubmit} size="large" autoComplete="off">
            <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
              <Input prefix={<UserOutlined />} placeholder="用户名" />
            </Form.Item>
            <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
              <Input.Password prefix={<LockOutlined />} placeholder="密码" />
            </Form.Item>
            <Form.Item style={{ marginBottom: 12 }}>
              <Button type="primary" htmlType="submit" loading={loading} block>
                登录
              </Button>
            </Form.Item>
          </Form>
        ) : (
          <Form form={form} onFinish={handleRegister} size="large" autoComplete="off" initialValues={{ role: 'client' }}>
            <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }, { min: 2, message: '至少2个字符' }]}>
              <Input prefix={<UserOutlined />} placeholder="用户名" />
            </Form.Item>
            <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }, { min: 6, message: '至少6个字符' }]}>
              <Input.Password prefix={<LockOutlined />} placeholder="密码（至少6位）" />
            </Form.Item>
            <Form.Item name="display_name">
              <Input placeholder="显示名称（选填）" />
            </Form.Item>
            <Form.Item name="role" rules={[{ required: true, message: '请选择角色' }]}>
              <Select placeholder="选择角色">
                {ROLE_OPTIONS.map((opt) => (
                  <Select.Option key={opt.value} value={opt.value}>
                    <Space>
                      <Tag color={opt.color}>{opt.label}</Tag>
                      <span style={{ fontSize: 12, color: '#8c8c8c' }}>{opt.desc}</span>
                    </Space>
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>
            <Form.Item style={{ marginBottom: 12 }}>
              <Button type="primary" htmlType="submit" loading={loading} block>
                注册
              </Button>
            </Form.Item>
          </Form>
        )}

        <Divider style={{ margin: '16px 0' }} />
        <div style={{ textAlign: 'center' }}>
          <Text type="secondary" style={{ fontSize: 13 }}>
            {mode === 'login' ? '没有账号？' : '已有账号？'}
            <Button type="link" size="small" onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>
              {mode === 'login' ? '立即注册' : '返回登录'}
            </Button>
          </Text>
        </div>

        {mode === 'login' && (
          <>
            <Divider plain style={{ margin: '12px 0', fontSize: 12, color: '#bfbfbf' }}>演示账号</Divider>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'center', flexWrap: 'wrap' }}>
              {ROLE_OPTIONS.map((opt) => (
                <Tag
                  key={opt.value}
                  color={opt.color}
                  style={{ cursor: 'pointer', margin: 0 }}
                  onClick={() => form.setFieldsValue({ username: opt.value, password: `${opt.value}123` })}
                >
                  {opt.label}: {opt.value} / {opt.value}123
                </Tag>
              ))}
            </div>
          </>
        )}
      </Card>
    </div>
  );
};

export default LoginPage;
