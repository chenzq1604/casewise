/**
 * 复核统计页
 * 采纳率统计图表 + 复核历史列表
 * 使用 Statistic, Table, Progress 组件展示数据
 */
import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Progress,
  Tag,
  Spin,
  Empty,
  Typography,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { reviewApi } from '../services/api';
import ReviewMark from '../components/ReviewMark';
import type { ReviewStats, ReviewFeedback, RiskLevel } from '../types';

const { Title } = Typography;

/**
 * ReviewPage 复核统计页组件
 * 展示复核统计数据和历史记录
 */
const ReviewPage: React.FC = () => {
  /** 复核统计数据 */
  const [stats, setStats] = useState<ReviewStats | null>(null);
  /** 加载状态 */
  const [loading, setLoading] = useState(false);

  /**
   * 加载复核统计数据
   * 组件挂载时自动调用
   */
  useEffect(() => {
    fetchStats();
  }, []);

  /**
   * 获取复核统计数据
   */
  const fetchStats = async () => {
    setLoading(true);
    try {
      const response = await reviewApi.getStats();
      setStats(response.data);
    } catch (error) {
      // 加载失败时使用空数据
    } finally {
      setLoading(false);
    }
  };

  /**
   * 获取风险等级对应的进度条颜色
   * @param level - 风险等级
   */
  const getProgressColor = (level: RiskLevel) => {
    const colorMap: Record<RiskLevel, string> = {
      high: '#ff4d4f',
      medium: '#faad14',
      low: '#52c41a',
    };
    return colorMap[level];
  };

  /**
   * 复核历史表格列定义
   */
  const columns = [
    {
      title: '风险项ID',
      dataIndex: 'riskItemId',
      key: 'riskItemId',
      width: 120,
      ellipsis: true,
    },
    {
      title: '复核结果',
      dataIndex: 'result',
      key: 'result',
      width: 120,
      /** 渲染复核标记组件 */
      render: (result: 'accepted' | 'rejected', record: ReviewFeedback) => (
        <ReviewMark
          result={result}
          reviewer={record.reviewer}
          reviewedAt={record.reviewedAt}
          size="small"
        />
      ),
    },
    {
      title: '复核人',
      dataIndex: 'reviewer',
      key: 'reviewer',
      width: 100,
    },
    {
      title: '复核时间',
      dataIndex: 'reviewedAt',
      key: 'reviewedAt',
      width: 160,
    },
    {
      title: '备注',
      dataIndex: 'comment',
      key: 'comment',
      ellipsis: true,
      /** 无备注时显示占位符 */
      render: (text: string) => text || '-',
    },
  ];

  /**
   * 渲染统计概览卡片
   * 总审查项、已采纳、已拒绝、待复核
   */
  const renderStatsOverview = () => {
    if (!stats) return null;

    return (
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="总审查项"
              value={stats.totalItems}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="已采纳"
              value={stats.acceptedCount}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="已拒绝"
              value={stats.rejectedCount}
              valueStyle={{ color: '#ff4d4f' }}
              prefix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="待复核"
              value={stats.pendingCount}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>
    );
  };

  /**
   * 渲染采纳率统计
   * 总体采纳率进度条 + 按风险等级的采纳率
   */
  const renderAcceptanceRate = () => {
    if (!stats) return null;

    return (
      <Card
        title="采纳率统计"
        style={{ marginBottom: 24, borderRadius: 8 }}
      >
        {/* 总体采纳率 */}
        <div style={{ marginBottom: 24 }}>
          <div style={{ marginBottom: 8, fontWeight: 500 }}>
            总体采纳率
          </div>
          <Progress
            percent={stats.acceptanceRate}
            strokeColor="#1890ff"
            size="default"
          />
        </div>

        {/* 按风险等级的采纳率 */}
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={8}>
            <div style={{ marginBottom: 4, fontSize: 13, color: '#595959' }}>
              高风险采纳率
            </div>
            <Progress
              percent={stats.acceptanceByLevel.high}
              strokeColor={getProgressColor('high')}
              size="small"
            />
          </Col>
          <Col xs={24} sm={8}>
            <div style={{ marginBottom: 4, fontSize: 13, color: '#595959' }}>
              中风险采纳率
            </div>
            <Progress
              percent={stats.acceptanceByLevel.medium}
              strokeColor={getProgressColor('medium')}
              size="small"
            />
          </Col>
          <Col xs={24} sm={8}>
            <div style={{ marginBottom: 4, fontSize: 13, color: '#595959' }}>
              低风险采纳率
            </div>
            <Progress
              percent={stats.acceptanceByLevel.low}
              strokeColor={getProgressColor('low')}
              size="small"
            />
          </Col>
        </Row>
      </Card>
    );
  };

  /**
   * 渲染复核历史列表
   */
  const renderHistoryTable = () => {
    if (!stats) return null;

    return (
      <Card
        title="复核历史"
        style={{ borderRadius: 8 }}
      >
        <Table
          columns={columns}
          dataSource={stats.recentReviews}
          rowKey="id"
          size="small"
          pagination={{ pageSize: 10 }}
          scroll={{ x: 600 }}
          locale={{ emptyText: '暂无复核记录' }}
        />
      </Card>
    );
  };

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      {/* 页面标题 */}
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0 }}>
          <BarChartOutlined style={{ marginRight: 8 }} />
          复核统计
        </Title>
      </div>

      {/* 加载状态 */}
      {loading && (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" tip="加载统计数据..." />
        </div>
      )}

      {/* 统计内容 */}
      {stats && !loading && (
        <>
          {renderStatsOverview()}
          {renderAcceptanceRate()}
          {renderHistoryTable()}
        </>
      )}

      {/* 无数据提示 */}
      {!stats && !loading && (
        <Empty description="暂无复核统计数据" />
      )}
    </div>
  );
};

export default ReviewPage;
