/**
 * 合同审查页
 * 上传区域（支持拖拽上传PDF/Word）
 * 审查结果：风险摘要列表 + 风险详情展开
 * 支持对照模式和批注模式切换
 */
import React, { useState } from 'react';
import {
  Upload,
  Button,
  Card,
  Collapse,
  Badge,
  Tag,
  Spin,
  Empty,
  Row,
  Col,
  Statistic,
  message,
} from 'antd';
import {
  InboxOutlined,
  FileTextOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
} from '@ant-design/icons';
import { contractApi } from '../services/api';
import ContractViewer from '../components/ContractViewer';
import RiskCard from '../components/RiskCard';
import type { ContractAnalysis, RiskLevel, ReviewResult } from '../types';

const { Dragger } = Upload;

/**
 * ContractPage 合同审查页组件
 * 提供合同上传、分析、风险查看功能
 */
const ContractPage: React.FC = () => {
  /** 合同分析结果 */
  const [analysis, setAnalysis] = useState<ContractAnalysis | null>(null);
  /** 上传/分析加载状态 */
  const [loading, setLoading] = useState(false);
  /** 当前展开的风险项ID列表 */
  const [expandedRisks, setExpandedRisks] = useState<string[]>([]);

  /**
   * 处理文件上传
   * 上传成功后自动触发合同分析
   * @param file - 上传的文件
   */
  const handleUpload = async (file: File) => {
    /** 校验文件类型 */
    const validTypes = [
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    ];
    if (!validTypes.includes(file.type)) {
      message.error('仅支持上传 PDF 或 Word 文件');
      return;
    }

    setLoading(true);
    try {
      /** 第一步：上传文件 */
      const uploadRes = await contractApi.uploadContract(file);
      message.success('文件上传成功，正在分析...');

      /** 第二步：分析合同 */
      const analysisRes = await contractApi.analyzeContract(uploadRes.data.fileId);
      setAnalysis(analysisRes.data);
      message.success('合同分析完成');
    } catch (error) {
      message.error('合同分析失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  /**
   * 处理复核操作
   * @param riskId - 风险项ID
   * @param result - 复核结果
   */
  const handleReview = (riskId: string, result: ReviewResult) => {
    if (!analysis) return;

    /** 更新风险项的复核状态 */
    const updatedRisks = analysis.risks.map((risk) =>
      risk.id === riskId ? { ...risk, reviewResult: result } : risk
    );
    setAnalysis({ ...analysis, risks: updatedRisks });
    message.success(result === 'accepted' ? '已标记为采纳' : '已标记为误报');
  };

  /**
   * 获取风险等级对应的Tag颜色
   * @param level - 风险等级
   */
  const getRiskTagColor = (level: RiskLevel) => {
    const colorMap: Record<RiskLevel, string> = {
      high: 'error',
      medium: 'warning',
      low: 'success',
    };
    return colorMap[level];
  };

  /**
   * 渲染上传区域
   * 支持拖拽上传和点击上传
   */
  const renderUploadArea = () => (
    <Card style={{ borderRadius: 8 }}>
      <Dragger
        accept=".pdf,.doc,.docx"
        showUploadList={false}
        beforeUpload={(file) => {
          handleUpload(file);
          return false; // 阻止自动上传
        }}
        disabled={loading}
      >
        <p className="ant-upload-drag-icon">
          <InboxOutlined style={{ fontSize: 48, color: '#1890ff' }} />
        </p>
        <p style={{ fontSize: 16, color: '#262626' }}>
          点击或拖拽文件到此区域上传
        </p>
        <p style={{ fontSize: 13, color: '#8c8c8c' }}>
          支持 PDF、Word 格式的合同文件
        </p>
      </Dragger>
    </Card>
  );

  /**
   * 渲染风险摘要统计
   * 显示高/中/低风险数量
   */
  const renderRiskSummary = () => {
    if (!analysis) return null;

    return (
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={8} sm={8}>
          <Card size="small">
            <Statistic
              title="高风险"
              value={analysis.riskSummary.high}
              valueStyle={{ color: '#ff4d4f' }}
              prefix={<ArrowUpOutlined />}
            />
          </Card>
        </Col>
        <Col xs={8} sm={8}>
          <Card size="small">
            <Statistic
              title="中风险"
              value={analysis.riskSummary.medium}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={8} sm={8}>
          <Card size="small">
            <Statistic
              title="低风险"
              value={analysis.riskSummary.low}
              valueStyle={{ color: '#52c41a' }}
              prefix={<ArrowDownOutlined />}
            />
          </Card>
        </Col>
      </Row>
    );
  };

  /**
   * 渲染风险摘要列表（折叠面板）
   * 点击展开查看风险详情
   */
  const renderRiskList = () => {
    if (!analysis || analysis.risks.length === 0) return null;

    /** 构建折叠面板项 */
    const collapseItems = analysis.risks.map((risk) => ({
      key: risk.id,
      label: (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Tag color={getRiskTagColor(risk.level)}>
            {risk.level === 'high' ? '高' : risk.level === 'medium' ? '中' : '低'}
          </Tag>
          <span style={{ fontWeight: 500 }}>{risk.description}</span>
          <span style={{ fontSize: 12, color: '#8c8c8c', marginLeft: 8 }}>
            位置：{risk.location}
          </span>
        </div>
      ),
      children: <RiskCard risk={risk} onReview={handleReview} />,
    }));

    return (
      <Collapse
        activeKey={expandedRisks}
        onChange={(keys) => setExpandedRisks(keys as string[])}
        items={collapseItems}
        style={{ marginBottom: 16 }}
      />
    );
  };

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      {/* 页面标题 */}
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ margin: 0 }}>
          <FileTextOutlined style={{ marginRight: 8 }} />
          合同审查
        </h2>
      </div>

      {/* 上传区域 */}
      {renderUploadArea()}

      {/* 加载状态 */}
      {loading && (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" tip="正在分析合同..." />
        </div>
      )}

      {/* 分析结果 */}
      {analysis && !loading && (
        <div style={{ marginTop: 24 }}>
          {/* 风险摘要统计 */}
          {renderRiskSummary()}

          {/* 合同查看器（对照/批注模式） */}
          <Card
            title={
              <span>
                审查结果
                <Badge
                  count={analysis.risks.length}
                  style={{ marginLeft: 8, backgroundColor: '#1890ff' }}
                />
              </span>
            }
            style={{ borderRadius: 8 }}
          >
            <ContractViewer analysis={analysis} onReview={handleReview} />
          </Card>

          {/* 风险摘要列表（折叠面板） */}
          <Card
            title="风险摘要列表"
            style={{ borderRadius: 8, marginTop: 16 }}
          >
            {renderRiskList()}
          </Card>
        </div>
      )}

      {/* 无分析结果时的提示 */}
      {!analysis && !loading && (
        <Empty
          description="请上传合同文件开始审查"
          style={{ marginTop: 40 }}
        />
      )}
    </div>
  );
};

export default ContractPage;
