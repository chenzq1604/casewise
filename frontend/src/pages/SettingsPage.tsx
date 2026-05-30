/**
 * 系统管理页面
 * 管理员专属，包含用户管理、模型配置、数据备份三个Tab
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Tabs,
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Switch,
  Tag,
  Space,
  App,
  Typography,
  Descriptions,
  Spin,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  UserOutlined,
  SettingOutlined,
  DatabaseOutlined,
  PlusOutlined,
  KeyOutlined,
  DownloadOutlined,
  ReloadOutlined,
  LockOutlined,
} from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';
import { authApi, adminApi } from '../services/api';

const { Title, Text } = Typography;

/**
 * 用户记录类型
 */
interface UserRecord {
  id: number;
  username: string;
  role: string;
  display_name: string;
  is_active: boolean;
  created_at: string;
}

/**
 * 模型配置类型
 */
interface ConfigData {
  ARK_CHAT_MODEL: string;
  ARK_EMBEDDING_MODEL: string;
  ARK_API_URL: string;
  ARK_API_KEY: string;
  [key: string]: string;
}

/**
 * 备份记录类型
 */
interface BackupRecord {
  filename: string;
  size: number;
  created_at: string;
}

/**
 * 角色标签映射
 */
const ROLE_TAG_MAP: Record<string, { color: string; label: string }> = {
  admin: { color: 'red', label: '管理员' },
  lawyer: { color: 'green', label: '律师' },
  client: { color: 'blue', label: '客户' },
};

/**
 * SettingsPage 系统管理页面组件
 * 提供用户管理、模型配置、数据备份功能
 */
const SettingsPage: React.FC = () => {
  const { message } = App.useApp();
  const { user } = useAuth();

  /** ====== 用户管理状态 ====== */
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [createUserModalOpen, setCreateUserModalOpen] = useState(false);
  const [createUserLoading, setCreateUserLoading] = useState(false);
  const [resetPasswordModalOpen, setResetPasswordModalOpen] = useState(false);
  const [resetPasswordLoading, setResetPasswordLoading] = useState(false);
  const [resetTargetUser, setResetTargetUser] = useState<UserRecord | null>(null);
  const [createUserForm] = Form.useForm();
  const [resetPasswordForm] = Form.useForm();

  /** ====== 模型配置状态 ====== */
  const [config, setConfig] = useState<ConfigData | null>(null);
  const [configLoading, setConfigLoading] = useState(false);
  const [configSaving, setConfigSaving] = useState(false);
  const [configForm] = Form.useForm();

  /** ====== 数据备份状态 ====== */
  const [backups, setBackups] = useState<BackupRecord[]>([]);
  const [backupsLoading, setBackupsLoading] = useState(false);
  const [backupCreating, setBackupCreating] = useState(false);

  /**
   * 格式化时间显示
   * @param timeStr - ISO时间字符串
   * @returns 格式化后的时间字符串
   */
  const formatTime = (timeStr: string): string => {
    if (!timeStr || timeStr === '-') return '-';
    try {
      return new Date(timeStr).toLocaleString('zh-CN', { hour12: false });
    } catch {
      return timeStr;
    }
  };

  /**
   * 格式化文件大小
   * @param bytes - 文件字节数
   * @returns 格式化后的大小字符串
   */
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  /**
   * API Key脱敏处理
   * @param key - 原始API Key
   * @returns 脱敏后的字符串（前8位+***）
   */
  const maskApiKey = (key: string): string => {
    if (!key) return '';
    if (key.length <= 8) return key + '***';
    return key.substring(0, 8) + '***';
  };

  /**
   * 加载用户列表
   */
  const fetchUsers = useCallback(async () => {
    setUsersLoading(true);
    try {
      const data = await authApi.listUsers();
      setUsers(data as unknown as UserRecord[]);
    } catch {
      message.error('获取用户列表失败');
    } finally {
      setUsersLoading(false);
    }
  }, [message]);

  /**
   * 加载模型配置
   */
  const fetchConfig = useCallback(async () => {
    setConfigLoading(true);
    try {
      const data = await adminApi.getConfig();
      setConfig(data as unknown as ConfigData);
      configForm.setFieldsValue({
        ARK_CHAT_MODEL: data.ARK_CHAT_MODEL,
        ARK_EMBEDDING_MODEL: data.ARK_EMBEDDING_MODEL,
        ARK_API_URL: data.ARK_API_URL,
        ARK_API_KEY: data.ARK_API_KEY,
      });
    } catch {
      message.error('获取模型配置失败');
    } finally {
      setConfigLoading(false);
    }
  }, [message, configForm]);

  /**
   * 加载备份列表
   */
  const fetchBackups = useCallback(async () => {
    setBackupsLoading(true);
    try {
      const data = await adminApi.listBackups();
      setBackups(data);
    } catch {
      message.error('获取备份列表失败');
    } finally {
      setBackupsLoading(false);
    }
  }, [message]);

  /**
   * 页面初始化加载数据
   */
  useEffect(() => {
    fetchUsers();
    fetchConfig();
    fetchBackups();
  }, [fetchUsers, fetchConfig, fetchBackups]);

  /**
   * 处理创建用户
   */
  const handleCreateUser = async () => {
    try {
      const values = await createUserForm.validateFields();
      setCreateUserLoading(true);
      await authApi.createUser(values);
      message.success('用户创建成功');
      setCreateUserModalOpen(false);
      createUserForm.resetFields();
      fetchUsers();
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } };
        message.error(axiosErr.response?.data?.detail || '创建用户失败');
      }
    } finally {
      setCreateUserLoading(false);
    }
  };

  /**
   * 打开重置密码弹窗
   * @param record - 目标用户记录
   */
  const openResetPassword = (record: UserRecord) => {
    setResetTargetUser(record);
    setResetPasswordModalOpen(true);
    resetPasswordForm.resetFields();
  };

  /**
   * 处理重置用户密码
   */
  const handleResetPassword = async () => {
    try {
      const values = await resetPasswordForm.validateFields();
      setResetPasswordLoading(true);
      await authApi.resetPassword(resetTargetUser!.id, values.newPassword);
      message.success(`用户 ${resetTargetUser!.username} 密码已重置`);
      setResetPasswordModalOpen(false);
      resetPasswordForm.resetFields();
      setResetTargetUser(null);
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } };
        message.error(axiosErr.response?.data?.detail || '重置密码失败');
      }
    } finally {
      setResetPasswordLoading(false);
    }
  };

  /**
   * 处理启用/禁用用户
   * @param record - 目标用户记录
   * @param checked - 是否启用
   */
  const handleToggleUser = async (record: UserRecord, checked: boolean) => {
    if (record.id === user?.id) {
      message.warning('不能禁用自己');
      return;
    }
    try {
      await authApi.toggleUser(record.id, checked);
      message.success(`用户 ${record.username} 已${checked ? '启用' : '禁用'}`);
      fetchUsers();
    } catch {
      message.error('操作失败');
    }
  };

  /**
   * 处理保存模型配置
   */
  const handleSaveConfig = async () => {
    try {
      const values = await configForm.validateFields();
      setConfigSaving(true);
      await adminApi.updateConfig(values);
      message.success('配置保存成功');
      fetchConfig();
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } };
        message.error(axiosErr.response?.data?.detail || '保存配置失败');
      }
    } finally {
      setConfigSaving(false);
    }
  };

  /**
   * 处理创建备份
   */
  const handleCreateBackup = async () => {
    setBackupCreating(true);
    try {
      await adminApi.createBackup();
      message.success('备份创建成功');
      fetchBackups();
    } catch {
      message.error('创建备份失败');
    } finally {
      setBackupCreating(false);
    }
  };

  /**
   * 处理下载备份
   * @param filename - 备份文件名
   */
  const handleDownloadBackup = (filename: string) => {
    const token = localStorage.getItem('casewise_token');
    const url = `/api/admin/backup/download?filename=${encodeURIComponent(filename)}&token=${encodeURIComponent(token || '')}`;
    window.open(url, '_blank');
  };

  /** 用户列表表格列定义 */
  const userColumns: ColumnsType<UserRecord> = [
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
      width: 120,
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      width: 100,
      render: (role: string) => {
        const info = ROLE_TAG_MAP[role];
        return info ? <Tag color={info.color}>{info.label}</Tag> : <Tag>{role}</Tag>;
      },
    },
    {
      title: '显示名',
      dataIndex: 'display_name',
      key: 'display_name',
      width: 120,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (isActive: boolean, record: UserRecord) => (
        <Switch
          checked={isActive}
          onChange={(checked) => handleToggleUser(record, checked)}
          disabled={record.id === user?.id}
          checkedChildren="启用"
          unCheckedChildren="禁用"
        />
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => formatTime(time),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: unknown, record: UserRecord) => (
        <Button
          type="link"
          icon={<KeyOutlined />}
          onClick={() => openResetPassword(record)}
        >
          重置密码
        </Button>
      ),
    },
  ];

  /** 备份列表表格列定义 */
  const backupColumns: ColumnsType<BackupRecord> = [
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
    },
    {
      title: '大小',
      dataIndex: 'size',
      key: 'size',
      width: 120,
      render: (size: number) => formatFileSize(size),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => formatTime(time),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: unknown, record: BackupRecord) => (
        <Button
          type="link"
          icon={<DownloadOutlined />}
          onClick={() => handleDownloadBackup(record.filename)}
        >
          下载
        </Button>
      ),
    },
  ];

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <Title level={4} style={{ marginBottom: 24 }}>
        <SettingOutlined style={{ marginRight: 8 }} />
        系统管理
      </Title>

      <Tabs
        defaultActiveKey="users"
        items={[
          {
            key: 'users',
            label: (
              <span>
                <UserOutlined style={{ marginRight: 4 }} />
                用户管理
              </span>
            ),
            children: (
              <Card>
                <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
                  <Title level={5} style={{ margin: 0 }}>用户列表</Title>
                  <Space>
                    <Button
                      icon={<ReloadOutlined />}
                      onClick={fetchUsers}
                      loading={usersLoading}
                    >
                      刷新
                    </Button>
                    <Button
                      type="primary"
                      icon={<PlusOutlined />}
                      onClick={() => {
                        createUserForm.resetFields();
                        setCreateUserModalOpen(true);
                      }}
                    >
                      创建用户
                    </Button>
                  </Space>
                </div>
                <Table
                  columns={userColumns}
                  dataSource={users}
                  rowKey="id"
                  loading={usersLoading}
                  pagination={false}
                  size="middle"
                />
              </Card>
            ),
          },
          {
            key: 'config',
            label: (
              <span>
                <SettingOutlined style={{ marginRight: 4 }} />
                模型配置
              </span>
            ),
            children: (
              <Card>
                <Spin spinning={configLoading}>
                  {config && (
                    <>
                      <Descriptions
                        title="当前配置"
                        bordered
                        column={1}
                        size="middle"
                        style={{ marginBottom: 24 }}
                      >
                        <Descriptions.Item label="对话模型">
                          {config.ARK_CHAT_MODEL}
                        </Descriptions.Item>
                        <Descriptions.Item label="向量模型">
                          {config.ARK_EMBEDDING_MODEL}
                        </Descriptions.Item>
                        <Descriptions.Item label="API地址">
                          {config.ARK_API_URL}
                        </Descriptions.Item>
                        <Descriptions.Item label="API Key">
                          <Text code>{maskApiKey(config.ARK_API_KEY)}</Text>
                        </Descriptions.Item>
                      </Descriptions>

                      <Title level={5}>修改配置</Title>
                      <Form
                        form={configForm}
                        layout="vertical"
                        style={{ maxWidth: 600 }}
                      >
                        <Form.Item
                          label="对话模型"
                          name="ARK_CHAT_MODEL"
                          rules={[{ required: true, message: '请输入对话模型名称' }]}
                        >
                          <Input placeholder="如: deepseek-v3-241226" />
                        </Form.Item>
                        <Form.Item
                          label="向量模型"
                          name="ARK_EMBEDDING_MODEL"
                          rules={[{ required: true, message: '请输入向量模型名称' }]}
                        >
                          <Input placeholder="如: doubao-embedding-large-250515" />
                        </Form.Item>
                        <Form.Item
                          label="API地址"
                          name="ARK_API_URL"
                          rules={[{ required: true, message: '请输入API地址' }]}
                        >
                          <Input placeholder="如: https://ark.cn-beijing.volces.com/api/v3" />
                        </Form.Item>
                        <Form.Item
                          label="API Key"
                          name="ARK_API_KEY"
                          rules={[{ required: true, message: '请输入API Key' }]}
                        >
                          <Input.Password placeholder="请输入API Key" />
                        </Form.Item>
                        <Form.Item>
                          <Button
                            type="primary"
                            onClick={handleSaveConfig}
                            loading={configSaving}
                          >
                            保存配置
                          </Button>
                        </Form.Item>
                      </Form>
                    </>
                  )}
                </Spin>
              </Card>
            ),
          },
          {
            key: 'backup',
            label: (
              <span>
                <DatabaseOutlined style={{ marginRight: 4 }} />
                数据备份
              </span>
            ),
            children: (
              <Card>
                <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
                  <Title level={5} style={{ margin: 0 }}>备份列表</Title>
                  <Space>
                    <Button
                      icon={<ReloadOutlined />}
                      onClick={fetchBackups}
                      loading={backupsLoading}
                    >
                      刷新
                    </Button>
                    <Button
                      type="primary"
                      icon={<DatabaseOutlined />}
                      onClick={handleCreateBackup}
                      loading={backupCreating}
                    >
                      创建备份
                    </Button>
                  </Space>
                </div>
                <Table
                  columns={backupColumns}
                  dataSource={backups}
                  rowKey="filename"
                  loading={backupsLoading}
                  pagination={false}
                  size="middle"
                  locale={{ emptyText: '暂无备份记录' }}
                />
              </Card>
            ),
          },
        ]}
      />

      {/* 创建用户弹窗 */}
      <Modal
        title="创建新用户"
        open={createUserModalOpen}
        onOk={handleCreateUser}
        onCancel={() => {
          setCreateUserModalOpen(false);
          createUserForm.resetFields();
        }}
        confirmLoading={createUserLoading}
        okText="创建"
        cancelText="取消"
      >
        <Form
          form={createUserForm}
          layout="vertical"
          style={{ marginTop: 16 }}
        >
          <Form.Item
            label="用户名"
            name="username"
            rules={[
              { required: true, message: '请输入用户名' },
              { min: 3, message: '用户名至少3个字符' },
            ]}
          >
            <Input prefix={<UserOutlined />} placeholder="请输入用户名" />
          </Form.Item>
          <Form.Item
            label="密码"
            name="password"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 6, message: '密码至少6个字符' },
            ]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="请输入密码" />
          </Form.Item>
          <Form.Item
            label="角色"
            name="role"
            rules={[{ required: true, message: '请选择角色' }]}
          >
            <Select placeholder="请选择角色">
              <Select.Option value="admin">管理员</Select.Option>
              <Select.Option value="lawyer">律师</Select.Option>
              <Select.Option value="client">客户</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            label="显示名"
            name="display_name"
          >
            <Input placeholder="请输入显示名（可选）" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 重置密码弹窗 */}
      <Modal
        title={`重置密码 - ${resetTargetUser?.username || ''}`}
        open={resetPasswordModalOpen}
        onOk={handleResetPassword}
        onCancel={() => {
          setResetPasswordModalOpen(false);
          resetPasswordForm.resetFields();
          setResetTargetUser(null);
        }}
        confirmLoading={resetPasswordLoading}
        okText="确认重置"
        cancelText="取消"
      >
        <Form
          form={resetPasswordForm}
          layout="vertical"
          style={{ marginTop: 16 }}
        >
          <Form.Item
            label="新密码"
            name="newPassword"
            rules={[
              { required: true, message: '请输入新密码' },
              { min: 6, message: '密码至少6个字符' },
            ]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="请输入新密码" />
          </Form.Item>
          <Form.Item
            label="确认新密码"
            name="confirmPassword"
            dependencies={['newPassword']}
            rules={[
              { required: true, message: '请确认新密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('newPassword') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'));
                },
              }),
            ]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="请再次输入新密码" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default SettingsPage;
