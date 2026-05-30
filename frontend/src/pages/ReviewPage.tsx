/**
 * 复核统计页
 * 采纳率统计图表 + 复核历史列表
 * 使用 Statistic, Progress 组件展示数据
 */
import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Spin,
  Empty,
  Typography,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  EditOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { reviewApi, type ReviewStatsData } from '../services/api';

const { Title } = Typography;

/**
 * ReviewPage 复核统计页组件
 * 展示复核统计数据和历史记录
 */
const ReviewPage: React.FC = () => {
  const [stats, setStats] = useState<ReviewStatsData | null>(null);
  const [loading, setLoading] = useState(false);

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
      setStats(response);
    } catch {
      // 加载失败时使用空数据
    } finally {
      setLoading(false);
    }
  };

  /**
   * 渲染统计概览卡片
   */
  const renderStatsOverview = () => {
    if (!stats) return null;

    return (
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="总复核数"
              value={stats.total_reviews}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="确认正确"
              value={stats.confirmed_count}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="已修正"
              value={stats.corrected_count}
              valueStyle={{ color: '#faad14' }}
              prefix={<EditOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="标记错误"
              value={stats.incorrect_count}
              valueStyle={{ color: '#ff4d4f' }}
              prefix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>
    );
  };

  /**
   * 渲染采纳率统计
   */
  const renderAcceptanceRate = () => {
    if (!stats) return null;

    return (
      <Card
        title="采纳率统计"
        style={{ marginBottom: 24, borderRadius: 8 }}
      >
        <div style={{ marginBottom: 24 }}>
          <div style={{ marginBottom: 8, fontWeight: 500 }}>
            总体采纳率
          </div>
          <Progress
            percent={Math.round(stats.adoption_rate)}
            strokeColor="#1890ff"
            size="default"
          />
        </div>

        {stats.by_source_type && Object.keys(stats.by_source_type).length > 0 && (
          <Row gutter={[16, 16]}>
            {Object.entries(stats.by_source_type).map(([sourceType, data]) => (
              <Col xs={24} sm={12} key={sourceType}>
                <div style={{ marginBottom: 4, fontSize: 13, color: '#595959' }}>
                  {sourceType === 'chat' ? '法律问答' : sourceType === 'contract' ? '合同审查' : sourceType} 采纳率
                </div>
                <Progress
                  percent={Math.round(data.adoption_rate)}
                  strokeColor="#1890ff"
                  size="small"
                />
                <div style={{ fontSize: 12, color: '#8c8c8c', marginTop: 4 }}>
                  总数: {data.total} / 已确认: {data.confirmed} / 已修正: {data.corrected}
                </div>
              </Col>
            ))}
          </Row>
        )}
      </Card>
    );
  };

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0 }}>
          <BarChartOutlined style={{ marginRight: 8 }} />
          复核统计
        </Title>
      </div>

      {loading && (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" />
        </div>
      )}

      {stats && !loading && (
        <>
          {renderStatsOverview()}
          {renderAcceptanceRate()}
        </>
      )}

      {!stats && !loading && (
        <Empty description="暂无复核统计数据" />
      )}
    </div>
  );
};

export default ReviewPage;
