/**
 * 合同审查页
 * 两个TAB：上传审查 + 历史记录
 * 上传审查：拖拽上传PDF/Word → 自动分析 → 对照/批注模式查看
 * 历史记录：审查历史列表 → 查看详情
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Tabs,
  Upload,
  Card,
  Collapse,
  Badge,
  Tag,
  Spin,
  Empty,
  Row,
  Col,
  Statistic,
  App,
  Table,
  Button,
  Typography,
} from 'antd';
import {
  InboxOutlined,
  FileTextOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  HistoryOutlined,
  EyeOutlined,
  DownloadOutlined,
} from '@ant-design/icons';
import {
  contractApi,
  reviewApi,
  reportApi,
  type ContractAnalyzeData,
  type ContractHistoryItem,
  type ContractReviewDetail,
} from '../services/api';
import ContractViewer from '../components/ContractViewer';
import RiskCard from '../components/RiskCard';
import type { ContractAnalysis, RiskLevel, ReviewResult } from '../types';

const { Dragger } = Upload;
const { Text } = Typography;

/**
 * 将后端ContractAnalyzeData转换为前端ContractAnalysis
 * @param data - 后端返回的合同分析数据
 * @param contractText - 合同原文文本
 * @returns 前端使用的合同分析结果
 */
const adaptAnalysis = (data: ContractAnalyzeData | ContractReviewDetail, contractText: string, htmlPreview?: string): ContractAnalysis => {
  const riskLevelMap: Record<string, RiskLevel> = { '高': 'high', '中': 'medium', '低': 'low', high: 'high', medium: 'medium', low: 'low' };
  const risks = data.risks.map((item, idx) => ({
    id: `risk-${idx}`,
    level: riskLevelMap[item.risk_level] || 'medium',
    location: item.clause || `条款 ${idx + 1}`,
    originalText: item.clause,
    description: item.risk_description,
    lawCitations: item.related_law ? [{
      id: `cite-${idx}`,
      type: 'law' as const,
      code: item.related_law,
      title: item.related_law,
      summary: item.related_law,
      verifyStatus: 'pending' as const,
    }] : [],
    caseCitations: [],
    suggestion: item.suggestion,
  }));
  const high = risks.filter((r) => r.level === 'high').length;
  const medium = risks.filter((r) => r.level === 'medium').length;
  const low = risks.filter((r) => r.level === 'low').length;
  return {
    id: data.file_id,
    fileName: 'filename' in data ? data.filename : data.file_id,
    status: 'completed' as const,
    originalText: contractText,
    htmlPreview: htmlPreview || '',
    reviewId: 'review_id' in data ? data.review_id : ('id' in data ? data.id : 0),
    risks,
    riskSummary: { high, medium, low },
    analyzedAt: data.analyzed_at || new Date().toISOString(),
  };
};

/**
 * 获取风险等级Tag颜色
 * @param level - 风险等级
 */
const getRiskTagColor = (level: string) => {
  const map: Record<string, string> = { '高': 'error', '中': 'warning', '低': 'success' };
  return map[level] || 'default';
};

/**
 * 格式化时间字符串
 * @param timeStr - ISO时间字符串
 */
const formatTime = (timeStr: string | null | undefined) => {
  if (!timeStr) return '-';
  try {
    return new Date(timeStr).toLocaleString('zh-CN');
  } catch {
    return timeStr;
  }
};

/**
 * ContractPage 合同审查页组件
 */
const ContractPage: React.FC = () => {
  const { message } = App.useApp();
  const [activeTab, setActiveTab] = useState('upload');
  const [analysis, setAnalysis] = useState<ContractAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [expandedRisks, setExpandedRisks] = useState<string[]>([]);
  const [historyList, setHistoryList] = useState<ContractHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [viewingDetail, setViewingDetail] = useState<ContractAnalysis | null>(null);

  /**
   * 渲染风险折叠列表
   * @param risks - 要渲染的风险项列表
   */
  const renderRiskCollapse = (risks: ContractAnalysis['risks']) => {
    if (risks.length === 0) {
      return <Empty description="该等级暂无风险条款" />;
    }
    return (
      <Collapse
        activeKey={expandedRisks}
        onChange={(keys) => setExpandedRisks(keys as string[])}
        items={risks.map((risk) => ({
          key: risk.id,
          label: (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Tag color={getRiskTagColor(risk.level === 'high' ? '高' : risk.level === 'medium' ? '中' : '低')}>
                {risk.level === 'high' ? '高' : risk.level === 'medium' ? '中' : '低'}
              </Tag>
              <span style={{ fontWeight: 500 }}>{risk.description}</span>
              <span style={{ fontSize: 12, color: '#8c8c8c', marginLeft: 8 }}>
                位置：{risk.location}
              </span>
            </div>
          ),
          children: <RiskCard risk={risk} onReview={handleReview} />,
        }))}
      />
    );
  };

  /**
   * 加载审查历史列表
   */
  const fetchHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const data = await contractApi.getHistory();
      setHistoryList(data);
    } catch {
      message.error('加载审查历史失败');
    } finally {
      setHistoryLoading(false);
    }
  }, [message]);

  useEffect(() => {
    if (activeTab === 'history') {
      fetchHistory();
      setViewingDetail(null);
    }
  }, [activeTab, fetchHistory]);

  /**
   * 处理文件上传
   */
  const handleUpload = async (file: File) => {
    const validTypes = [
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    ];
    if (!validTypes.includes(file.type) && !file.name.match(/\.(pdf|doc|docx|xls|xlsx)$/i)) {
      message.error('仅支持上传 PDF、Word、Excel 格式的文件');
      return;
    }

    setLoading(true);
    try {
      const uploadRes = await contractApi.uploadContract(file);
      message.success('文件上传成功，正在分析...');

      const analysisRes = await contractApi.analyzeContract(uploadRes.file_id);
      setAnalysis(adaptAnalysis(analysisRes, uploadRes.contract_text, uploadRes.html_preview));
      message.success('合同分析完成');
    } catch {
      message.error('合同分析失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  /**
   * 处理复核操作
   * 调用后端API保存复核反馈，并更新前端状态
   */
  const handleReview = async (riskId: string, result: ReviewResult) => {
    const target = viewingDetail || analysis;
    if (!target) return;

    const risk = target.risks.find((r) => r.id === riskId);
    if (!risk) return;

    const feedbackType = result === 'accepted' ? 'confirmed' : 'incorrect';

    try {
      await reviewApi.submitReview({
        source_type: 'contract',
        source_id: target.reviewId,
        original_output: risk.description,
        feedback_type: feedbackType,
        comment: `风险条款：${risk.location}`,
      });

      const updatedRisks = target.risks.map((r) =>
        r.id === riskId ? { ...r, reviewResult: result } : r
      );
      if (viewingDetail) {
        setViewingDetail({ ...viewingDetail, risks: updatedRisks });
      } else {
        setAnalysis({ ...analysis!, risks: updatedRisks });
      }

      const remaining = updatedRisks.filter((r) => !r.reviewResult).length;
      if (remaining > 0) {
        message.success(
          result === 'accepted'
            ? `已采纳，还剩 ${remaining} 条待复核`
            : `已标记误报，还剩 ${remaining} 条待复核`
        );
      } else {
        message.success('所有风险条款已复核完毕，可前往「复核统计」查看汇总数据');
      }
    } catch {
      message.error('复核反馈提交失败，请重试');
    }
  };

  /**
   * 查看历史记录详情
   */
  const handleViewDetail = async (reviewId: number) => {
    try {
      const detail = await contractApi.getDetail(reviewId);
      setViewingDetail(adaptAnalysis(detail, detail.contract_text, detail.html_preview));
    } catch {
      message.error('加载审查详情失败');
    }
  };

  /**
   * 渲染上传审查TAB内容
   */
  const renderUploadTab = () => (
    <>
      <Card style={{ borderRadius: 8 }}>
        <Dragger
          accept=".pdf,.doc,.docx,.xls,.xlsx"
        showUploadList={false}
        beforeUpload={(file) => {
          handleUpload(file);
          return false;
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
          支持 PDF、Word（.doc/.docx）、Excel 格式的合同文件
        </p>
        </Dragger>
      </Card>

      {loading && (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" tip="正在分析合同...">
            <div style={{ minHeight: 100 }} />
          </Spin>
        </div>
      )}

      {analysis && !loading && (
        <div style={{ marginTop: 24 }}>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col xs={8}>
              <Card size="small">
                <Statistic title="高风险" value={analysis.riskSummary.high} valueStyle={{ color: '#ff4d4f' }} prefix={<ArrowUpOutlined />} />
              </Card>
            </Col>
            <Col xs={8}>
              <Card size="small">
                <Statistic title="中风险" value={analysis.riskSummary.medium} valueStyle={{ color: '#faad14' }} />
              </Card>
            </Col>
            <Col xs={8}>
              <Card size="small">
                <Statistic title="低风险" value={analysis.riskSummary.low} valueStyle={{ color: '#52c41a' }} prefix={<ArrowDownOutlined />} />
              </Card>
            </Col>
          </Row>

          <Card
            title={
              <span>
                审查结果
                <Badge count={analysis.risks.length} style={{ marginLeft: 8, backgroundColor: '#1890ff' }} />
              </span>
            }
            style={{ borderRadius: 8 }}
          >
            <ContractViewer analysis={analysis} onReview={handleReview} />
          </Card>

          <Card title="风险摘要列表" style={{ borderRadius: 8, marginTop: 16 }}>
            {analysis.risks.length > 0 ? (
              <Tabs
                defaultActiveKey="all"
                items={[
                  {
                    key: 'all',
                    label: <span>全部 <Badge count={analysis.risks.length} style={{ marginLeft: 4 }} /></span>,
                    children: renderRiskCollapse(analysis.risks),
                  },
                  {
                    key: 'high',
                    label: <span style={{ color: '#ff4d4f' }}>高风险 <Badge count={analysis.riskSummary.high} style={{ marginLeft: 4, backgroundColor: '#ff4d4f' }} /></span>,
                    children: renderRiskCollapse(analysis.risks.filter((r) => r.level === 'high')),
                  },
                  {
                    key: 'medium',
                    label: <span style={{ color: '#faad14' }}>中风险 <Badge count={analysis.riskSummary.medium} style={{ marginLeft: 4, backgroundColor: '#faad14' }} /></span>,
                    children: renderRiskCollapse(analysis.risks.filter((r) => r.level === 'medium')),
                  },
                  {
                    key: 'low',
                    label: <span style={{ color: '#52c41a' }}>低风险 <Badge count={analysis.riskSummary.low} style={{ marginLeft: 4, backgroundColor: '#52c41a' }} /></span>,
                    children: renderRiskCollapse(analysis.risks.filter((r) => r.level === 'low')),
                  },
                ]}
              />
            ) : (
              <Empty description="未发现风险条款" />
            )}
          </Card>
        </div>
      )}

      {!analysis && !loading && (
        <Empty description="请上传合同文件开始审查" style={{ marginTop: 40 }} />
      )}
    </>
  );

  /**
   * 渲染历史记录TAB内容
   */
  const renderHistoryTab = () => {
    if (viewingDetail) {
      return (
        <div>
          <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Button onClick={() => setViewingDetail(null)}>← 返回历史列表</Button>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              onClick={async () => {
                try {
                  const blob = await reportApi.exportContractReport(viewingDetail.reviewId);
                  const url = window.URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `合同审查报告_${viewingDetail.fileName || 'report'}.html`;
                  a.click();
                  window.URL.revokeObjectURL(url);
                  message.success('报告导出成功');
                } catch {
                  message.error('报告导出失败');
                }
              }}
            >
              导出报告
            </Button>
          </div>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col xs={8}>
              <Card size="small">
                <Statistic title="高风险" value={viewingDetail.riskSummary.high} valueStyle={{ color: '#ff4d4f' }} prefix={<ArrowUpOutlined />} />
              </Card>
            </Col>
            <Col xs={8}>
              <Card size="small">
                <Statistic title="中风险" value={viewingDetail.riskSummary.medium} valueStyle={{ color: '#faad14' }} />
              </Card>
            </Col>
            <Col xs={8}>
              <Card size="small">
                <Statistic title="低风险" value={viewingDetail.riskSummary.low} valueStyle={{ color: '#52c41a' }} prefix={<ArrowDownOutlined />} />
              </Card>
            </Col>
          </Row>
          <Card
            title={
              <span>
                审查结果
                <Badge count={viewingDetail.risks.length} style={{ marginLeft: 8, backgroundColor: '#1890ff' }} />
              </span>
            }
            style={{ borderRadius: 8 }}
          >
            <ContractViewer analysis={viewingDetail} onReview={handleReview} />
          </Card>
        </div>
      );
    }

    const columns = [
      {
        title: '文件名',
        dataIndex: 'filename',
        key: 'filename',
        ellipsis: true,
        render: (text: string) => text || <Text type="secondary">未命名</Text>,
      },
      {
        title: '风险等级',
        dataIndex: 'overall_risk_level',
        key: 'overall_risk_level',
        width: 100,
        render: (level: string) => <Tag color={getRiskTagColor(level)}>{level}</Tag>,
      },
      {
        title: '风险数',
        dataIndex: 'risk_count',
        key: 'risk_count',
        width: 80,
        align: 'center' as const,
      },
      {
        title: '上传时间',
        dataIndex: 'created_at',
        key: 'created_at',
        width: 170,
        render: (text: string) => formatTime(text),
      },
      {
        title: '审查时间',
        dataIndex: 'analyzed_at',
        key: 'analyzed_at',
        width: 170,
        render: (text: string) => formatTime(text),
      },
      {
        title: '操作',
        key: 'action',
        width: 80,
        render: (_: unknown, record: ContractHistoryItem) => (
          <Button type="link" icon={<EyeOutlined />} onClick={() => handleViewDetail(record.id)}>
            查看
          </Button>
        ),
      },
    ];

    return (
      <Card style={{ borderRadius: 8 }}>
        <Spin spinning={historyLoading} tip="加载历史记录...">
          <div>
            <Table
              columns={columns}
              dataSource={historyList}
              rowKey="id"
              pagination={{ pageSize: 10 }}
              locale={{ emptyText: <Empty description="暂无审查历史" /> }}
              size="middle"
            />
          </div>
        </Spin>
      </Card>
    );
  };

  const tabItems = [
    {
      key: 'upload',
      label: (
        <span>
          <FileTextOutlined style={{ marginRight: 4 }} />
          上传审查
        </span>
      ),
      children: renderUploadTab(),
    },
    {
      key: 'history',
      label: (
        <span>
          <HistoryOutlined style={{ marginRight: 4 }} />
          历史记录
        </span>
      ),
      children: renderHistoryTab(),
    },
  ];

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ margin: 0 }}>
          <FileTextOutlined style={{ marginRight: 8 }} />
          合同审查
        </h2>
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
        size="large"
      />
    </div>
  );
};

export default ContractPage;
