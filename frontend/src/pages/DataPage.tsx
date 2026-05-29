/**
 * 数据管理页面
 * 提供法条数据采集、进度监控、状态查看等功能
 * 包含四个区域：数据状态卡片、采集控制、进度展示、采集日志
 */
import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Button,
  Checkbox,
  InputNumber,
  Progress,
  Steps,
  Typography,
  Space,
  Tag,
  Alert,
  Spin,
  message,
  Divider,
} from 'antd';
import {
  ReloadOutlined,
  PlayCircleOutlined,
  StopOutlined,
  DatabaseOutlined,
  FileTextOutlined,
  CloudServerOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import { dataApi } from '../services/api';
import type { DataStatus, LawCategory, CollectionProgress } from '../types';

const { Title, Text, Paragraph } = Typography;

/** 采集步骤定义 */
const COLLECTION_STEPS = [
  { title: '下载法条数据', icon: <CloudServerOutlined /> },
  { title: '解析法条', icon: <FileTextOutlined /> },
  { title: '生成向量', icon: <DatabaseOutlined /> },
  { title: '写入ChromaDB', icon: <DatabaseOutlined /> },
  { title: '构建BM25索引', icon: <DatabaseOutlined /> },
];

/** 进度轮询间隔（毫秒） */
const POLL_INTERVAL = 2000;

/**
 * DataPage 数据管理页面组件
 * 管理法条数据的采集、进度监控和状态展示
 */
const DataPage: React.FC = () => {
  /** 当前数据状态 */
  const [dataStatus, setDataStatus] = useState<DataStatus>({
    laws_count: 0,
    cases_count: 0,
    collections: [],
    last_updated: '-',
  });
  /** 法律类型列表 */
  const [categories, setCategories] = useState<LawCategory[]>([]);
  /** 选中的法律类型 */
  const [selectedCategories, setSelectedCategories] = useState<string[]>(['民法典']);
  /** 采集数量限制，0表示全量 */
  const [collectLimit, setCollectLimit] = useState<number>(0);
  /** 当前采集进度 */
  const [progress, setProgress] = useState<CollectionProgress | null>(null);
  /** 数据状态加载中 */
  const [statusLoading, setStatusLoading] = useState(false);
  /** 类型列表加载中 */
  const [categoriesLoading, setCategoriesLoading] = useState(false);
  /** 采集启动中 */
  const [collectStarting, setCollectStarting] = useState(false);
  /** 取消采集中 */
  const [cancelling, setCancelling] = useState(false);
  /** 采集日志列表 */
  const [logs, setLogs] = useState<string[]>([]);
  /** 轮询定时器引用 */
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  /** 日志区域引用，用于自动滚动 */
  const logContainerRef = useRef<HTMLDivElement>(null);

  /**
   * 添加一条日志记录
   * @param step - 步骤名称
   * @param detail - 详细信息
   */
  const addLog = useCallback((step: string, detail: string) => {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('zh-CN', { hour12: false });
    setLogs((prev) => [...prev, `[${timeStr}] ${step} - ${detail}`]);
  }, []);

  /**
   * 自动滚动日志区域到底部
   */
  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      if (logContainerRef.current) {
        logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
      }
    }, 100);
  }, []);

  /**
   * 加载数据状态信息
   */
  const fetchStatus = useCallback(async () => {
    setStatusLoading(true);
    try {
      const data = await dataApi.getStatus();
      setDataStatus(data);
    } catch {
      message.error('获取数据状态失败');
    } finally {
      setStatusLoading(false);
    }
  }, []);

  /**
   * 加载法律类型列表
   */
  const fetchCategories = useCallback(async () => {
    setCategoriesLoading(true);
    try {
      const data = await dataApi.getCategories();
      setCategories(data);
    } catch {
      message.error('获取法律类型列表失败');
    } finally {
      setCategoriesLoading(false);
    }
  }, []);

  /**
   * 查询采集进度
   */
  const fetchProgress = useCallback(async () => {
    try {
      const data = await dataApi.getProgress();
      setProgress(data);
      return data;
    } catch {
      return null;
    }
  }, []);

  /**
   * 启动进度轮询
   * 采集进行中时每2秒查询一次进度
   */
  const startPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
    }
    pollTimerRef.current = setInterval(async () => {
      const data = await fetchProgress();
      if (data && (data.status === 'completed' || data.status === 'failed' || data.status === 'idle')) {
        /** 采集结束，停止轮询 */
        if (pollTimerRef.current) {
          clearInterval(pollTimerRef.current);
          pollTimerRef.current = null;
        }
        /** 刷新数据状态 */
        fetchStatus();
        if (data.status === 'completed') {
          addLog('采集完成', `共处理 ${data.completed}/${data.total} 条`);
        } else if (data.status === 'failed') {
          addLog('采集失败', data.errors.join('; '));
        }
      } else if (data) {
        /** 记录进度日志 */
        addLog(data.current_step, `进度: ${data.completed}/${data.total}`);
      }
      scrollToBottom();
    }, POLL_INTERVAL);
  }, [fetchProgress, fetchStatus, addLog, scrollToBottom]);

  /**
   * 启动数据采集
   */
  const handleStartCollect = async () => {
    if (selectedCategories.length === 0) {
      message.warning('请至少选择一种法律类型');
      return;
    }
    setCollectStarting(true);
    try {
      const result = await dataApi.startCollect(selectedCategories, collectLimit);
      message.success('采集任务已启动');
      addLog('启动采集', `任务ID: ${result.task_id}，类型: ${selectedCategories.join(', ')}，数量限制: ${collectLimit || '全量'}`);
      /** 立即查询一次进度 */
      await fetchProgress();
      /** 启动轮询 */
      startPolling();
      scrollToBottom();
    } catch {
      message.error('启动采集失败');
      addLog('启动失败', '无法启动采集任务');
    } finally {
      setCollectStarting(false);
    }
  };

  /**
   * 取消数据采集
   */
  const handleCancelCollect = async () => {
    setCancelling(true);
    try {
      await dataApi.cancelCollect();
      message.success('采集任务已取消');
      addLog('取消采集', '用户手动取消采集任务');
      /** 停止轮询 */
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
      /** 刷新进度和状态 */
      await fetchProgress();
      await fetchStatus();
      scrollToBottom();
    } catch {
      message.error('取消采集失败');
    } finally {
      setCancelling(false);
    }
  };

  /**
   * 刷新数据状态
   */
  const handleRefresh = () => {
    fetchStatus();
    fetchProgress();
  };

  /**
   * 处理法律类型选择变化
   * @param checkedValues - 选中的法律类型名称列表
   */
  const handleCategoryChange = (checkedValues: string[]) => {
    setSelectedCategories(checkedValues);
  };

  /**
   * 根据步骤名称获取当前步骤索引
   * @param stepName - 步骤名称
   * @returns 步骤索引（0-based）
   */
  const getStepIndex = (stepName: string): number => {
    const index = COLLECTION_STEPS.findIndex(
      (s) => s.title === stepName || stepName.includes(s.title)
    );
    return index >= 0 ? index : 0;
  };

  /**
   * 计算进度百分比
   */
  const getProgressPercent = (): number => {
    if (!progress || progress.total === 0) return 0;
    return Math.round((progress.completed / progress.total) * 100);
  };

  /**
   * 获取进度条状态
   */
  const getProgressStatus = (): 'success' | 'exception' | 'normal' | 'active' => {
    if (!progress) return 'normal';
    if (progress.status === 'completed') return 'success';
    if (progress.status === 'failed') return 'exception';
    if (progress.status === 'running') return 'active';
    return 'normal';
  };

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

  /** 页面初始化：加载数据 */
  useEffect(() => {
    fetchStatus();
    fetchCategories();
    /** 检查是否有进行中的采集任务 */
    fetchProgress().then((data) => {
      if (data && data.status === 'running') {
        startPolling();
      }
    });
    /** 组件卸载时清理轮询定时器 */
    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** 日志更新时自动滚动 */
  useEffect(() => {
    scrollToBottom();
  }, [logs, scrollToBottom]);

  /** 是否正在采集中 */
  const isCollecting = progress?.status === 'running';

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      {/* ====== 区域1：当前数据状态卡片 ====== */}
      <Card
        title={
          <Space>
            <DatabaseOutlined />
            <span>当前数据状态</span>
          </Space>
        }
        extra={
          <Button
            icon={<ReloadOutlined />}
            onClick={handleRefresh}
            loading={statusLoading}
            size="small"
          >
            刷新
          </Button>
        }
        style={{ marginBottom: 24 }}
      >
        <Row gutter={[16, 16]}>
          {/* 法条总数 */}
          <Col xs={12} sm={6}>
            <Statistic
              title="法条总数"
              value={dataStatus.laws_count}
              prefix={<FileTextOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Col>
          {/* 案例总数 */}
          <Col xs={12} sm={6}>
            <Statistic
              title="案例总数"
              value={dataStatus.cases_count}
              prefix={<FileTextOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Col>
          {/* ChromaDB集合数 */}
          <Col xs={12} sm={6}>
            <Statistic
              title="ChromaDB集合"
              value={dataStatus.collections.length}
              prefix={<CloudServerOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Col>
          {/* 最后更新时间 */}
          <Col xs={12} sm={6}>
            <Statistic
              title="最后更新"
              value={formatTime(dataStatus.last_updated)}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#fa8c16', fontSize: 16 }}
            />
          </Col>
        </Row>
        {/* ChromaDB集合名称列表 */}
        {dataStatus.collections.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <Text type="secondary" style={{ marginRight: 8 }}>
              集合列表：
            </Text>
            {dataStatus.collections.map((col) => (
              <Tag key={col} color="blue">
                {col}
              </Tag>
            ))}
          </div>
        )}
      </Card>

      {/* ====== 区域2：数据采集控制 ====== */}
      <Card
        title={
          <Space>
            <PlayCircleOutlined />
            <span>数据采集控制</span>
          </Space>
        }
        style={{ marginBottom: 24 }}
      >
        <Spin spinning={categoriesLoading} tip="加载法律类型列表...">
          {/* 法律类型选择 */}
          <div style={{ marginBottom: 20 }}>
            <Title level={5} style={{ marginBottom: 12 }}>
              选择法律类型
            </Title>
            <Checkbox.Group
              value={selectedCategories}
              onChange={handleCategoryChange}
              disabled={isCollecting}
            >
              <Row gutter={[12, 12]}>
                {categories.map((cat) => (
                  <Col xs={24} sm={12} md={8} key={cat.name}>
                    <Checkbox value={cat.name} style={{ alignItems: 'flex-start' }}>
                      <div>
                        <Text strong>{cat.name}</Text>
                        <br />
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {cat.description}
                        </Text>
                      </div>
                    </Checkbox>
                  </Col>
                ))}
              </Row>
            </Checkbox.Group>
            {categories.length === 0 && !categoriesLoading && (
              <Text type="secondary">暂无可用的法律类型</Text>
            )}
          </div>

          <Divider style={{ margin: '16px 0' }} />

          {/* 采集数量限制 */}
          <div style={{ marginBottom: 20 }}>
            <Title level={5} style={{ marginBottom: 12 }}>
              采集数量限制
            </Title>
            <Space align="center">
              <InputNumber
                min={0}
                value={collectLimit}
                onChange={(val) => setCollectLimit(val ?? 0)}
                disabled={isCollecting}
                style={{ width: 160 }}
                addonAfter="条"
              />
              <Text type="secondary" style={{ fontSize: 12 }}>
                0 表示全量采集
              </Text>
            </Space>
          </div>

          <Divider style={{ margin: '16px 0' }} />

          {/* 操作按钮 */}
          <Space size="middle">
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={handleStartCollect}
              loading={collectStarting}
              disabled={isCollecting || selectedCategories.length === 0}
              size="large"
            >
              开始采集
            </Button>
            <Button
              danger
              icon={<StopOutlined />}
              onClick={handleCancelCollect}
              loading={cancelling}
              disabled={!isCollecting}
              size="large"
            >
              取消采集
            </Button>
          </Space>
        </Spin>
      </Card>

      {/* ====== 区域3：采集进度展示 ====== */}
      <Card
        title={
          <Space>
            <LoadingOutlined style={{ display: isCollecting ? 'inline-block' : 'none' }} />
            {!isCollecting && progress?.status === 'completed' && <CheckCircleOutlined style={{ color: '#52c41a' }} />}
            {!isCollecting && progress?.status === 'failed' && <CloseCircleOutlined style={{ color: '#ff4d4f' }} />}
            {!isCollecting && (!progress || progress.status === 'idle') && <ClockCircleOutlined />}
            <span>采集进度</span>
            {progress && progress.status !== 'idle' && (
              <Tag
                color={
                  progress.status === 'running'
                    ? 'processing'
                    : progress.status === 'completed'
                    ? 'success'
                    : progress.status === 'failed'
                    ? 'error'
                    : 'default'
                }
              >
                {progress.status === 'running'
                  ? '运行中'
                  : progress.status === 'completed'
                  ? '已完成'
                  : progress.status === 'failed'
                  ? '失败'
                  : '空闲'}
              </Tag>
            )}
          </Space>
        }
        style={{ marginBottom: 24 }}
      >
        {progress && progress.status !== 'idle' ? (
          <>
            {/* 进度条 */}
            <div style={{ marginBottom: 24 }}>
              <Progress
                percent={getProgressPercent()}
                status={getProgressStatus()}
                strokeColor={
                  isCollecting
                    ? { from: '#1890ff', to: '#52c41a' }
                    : undefined
                }
                size={['100%', 20]}
              />
              <div style={{ marginTop: 8, textAlign: 'center' }}>
                <Text type="secondary">
                  已完成 {progress.completed} / {progress.total} 条
                  {progress.total > 0 && ` (${getProgressPercent()}%)`}
                </Text>
              </div>
            </div>

            {/* 步骤条 */}
            <Steps
              current={isCollecting ? getStepIndex(progress.current_step) : progress.status === 'completed' ? COLLECTION_STEPS.length - 1 : getStepIndex(progress.current_step)}
              status={progress.status === 'failed' ? 'error' : 'process'}
              size="small"
              direction="vertical"
              items={COLLECTION_STEPS.map((step, index) => ({
                title: step.title,
                icon:
                  isCollecting && getStepIndex(progress.current_step) === index ? (
                    <LoadingOutlined />
                  ) : (
                    step.icon
                  ),
                description:
                  isCollecting && getStepIndex(progress.current_step) === index
                    ? progress.current_step
                    : undefined,
              }))}
              style={{ marginBottom: 16 }}
            />

            {/* 任务信息 */}
            <Row gutter={[16, 8]} style={{ marginBottom: 16 }}>
              <Col xs={24} sm={12}>
                <Text type="secondary">任务ID：</Text>
                <Text code>{progress.task_id}</Text>
              </Col>
              <Col xs={24} sm={12}>
                <Text type="secondary">开始时间：</Text>
                <Text>{formatTime(progress.started_at)}</Text>
              </Col>
              {progress.completed_at && (
                <Col xs={24} sm={12}>
                  <Text type="secondary">完成时间：</Text>
                  <Text>{formatTime(progress.completed_at)}</Text>
                </Col>
              )}
              <Col xs={24} sm={12}>
                <Text type="secondary">采集类型：</Text>
                {progress.selected_categories.map((cat) => (
                  <Tag key={cat} color="blue" style={{ marginLeft: 4 }}>
                    {cat}
                  </Tag>
                ))}
              </Col>
            </Row>

            {/* 错误信息列表 */}
            {progress.errors && progress.errors.length > 0 && (
              <Alert
                type="error"
                showIcon
                message="采集错误"
                description={
                  <ul style={{ margin: 0, paddingLeft: 20 }}>
                    {progress.errors.map((err, idx) => (
                      <li key={idx}>
                        <Text type="danger">{err}</Text>
                      </li>
                    ))}
                  </ul>
                }
                style={{ marginTop: 16 }}
              />
            )}
          </>
        ) : (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <ClockCircleOutlined style={{ fontSize: 48, color: '#d9d9d9', marginBottom: 16 }} />
            <Paragraph type="secondary">
              暂无进行中的采集任务
            </Paragraph>
            <Paragraph type="secondary" style={{ fontSize: 13 }}>
              请在上方选择法律类型并点击"开始采集"
            </Paragraph>
          </div>
        )}
      </Card>

      {/* ====== 区域4：采集历史/日志 ====== */}
      <Card
        title={
          <Space>
            <FileTextOutlined />
            <span>采集日志</span>
            {logs.length > 0 && (
              <Tag>{logs.length} 条</Tag>
            )}
          </Space>
        }
        extra={
          logs.length > 0 ? (
            <Button
              size="small"
              onClick={() => setLogs([])}
            >
              清空日志
            </Button>
          ) : null
        }
      >
        <div
          ref={logContainerRef}
          style={{
            background: '#1e1e1e',
            borderRadius: 8,
            padding: 16,
            maxHeight: 300,
            overflowY: 'auto',
            fontFamily: "'Consolas', 'Monaco', 'Courier New', monospace",
            fontSize: 13,
            lineHeight: 1.8,
          }}
        >
          {logs.length > 0 ? (
            logs.map((log, idx) => (
              <div key={idx} style={{ color: '#d4d4d4' }}>
                {log}
              </div>
            ))
          ) : (
            <div style={{ color: '#666', textAlign: 'center', padding: '20px 0' }}>
              暂无日志记录
            </div>
          )}
        </div>
      </Card>
    </div>
  );
};

export default DataPage;
