/**
 * 法律文书生成页
 * 左侧表单区域：文书类型选择、场景描述、补充信息
 * 右侧预览区域：文书标题、正文（Markdown渲染）、法律依据、使用提示、免责声明
 * 生成中显示loading状态，所有角色可访问
 */
import React, { useState } from 'react';
import {
  Card,
  Form,
  Select,
  Input,
  Button,
  Collapse,
  Spin,
  Empty,
  Typography,
  Tag,
  Alert,
  Space,
  App,
  Row,
  Col,
} from 'antd';
import {
  FileTextOutlined,
  CopyOutlined,
  DownloadOutlined,
  ThunderboltOutlined,
  SafetyCertificateOutlined,
  InfoCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import apiClient from '../services/api';

const { TextArea } = Input;
const { Title, Paragraph, Text } = Typography;

/**
 * 文书类型选项配置
 * 定义可选的法律文书类型及其标签
 */
const DOC_TYPE_OPTIONS = [
  { value: 'demand_letter', label: '催收函' },
  { value: 'labor_arbitration', label: '劳动仲裁申请书' },
  { value: 'civil_complaint', label: '民事起诉状' },
  { value: 'termination_notice', label: '解除劳动合同通知书' },
  { value: 'power_of_attorney', label: '授权委托书' },
];

/**
 * 文书类型中文映射
 * 用于将后端返回的doc_type转换为中文显示
 */
const DOC_TYPE_LABEL_MAP: Record<string, string> = {
  collection_letter: '催收函',
  labor_arbitration: '劳动仲裁申请书',
  civil_complaint: '民事起诉状',
  termination_notice: '解除劳动合同通知书',
  power_of_attorney: '授权委托书',
};

/**
 * 文书生成响应数据类型
 * 与后端 /api/document/generate 响应对齐
 */
interface DocumentGenerateResponse {
  /** 文书类型 */
  doc_type: string;
  /** 文书标题 */
  title: string;
  /** 文书正文（Markdown格式） */
  content: string;
  /** 法律依据列表 */
  legal_basis: string[];
  /** 使用提示 */
  tips: string[];
  /** 免责声明 */
  disclaimer: string;
}

/**
 * 补充信息表单字段类型
 */
interface DetailFields {
  /** 当事人姓名 */
  partyName?: string;
  /** 对方当事人 */
  counterParty?: string;
  /** 金额（催收函场景） */
  amount?: string;
  /** 其他补充信息 */
  otherInfo?: string;
}

/**
 * DocumentPage 法律文书生成页组件
 * 提供法律文书生成表单和预览功能
 */
const DocumentPage: React.FC = () => {
  const { message } = App.useApp();
  /** Ant Design Form实例 */
  const [form] = Form.useForm();
  /** 是否正在生成文书 */
  const [loading, setLoading] = useState(false);
  /** 生成的文书结果 */
  const [docResult, setDocResult] = useState<DocumentGenerateResponse | null>(null);
  /** 当前选中的文书类型，用于控制金额字段显隐 */
  const [selectedDocType, setSelectedDocType] = useState<string | undefined>(undefined);

  /**
   * 处理文书类型变更
   * @param value - 选中的文书类型值
   */
  const handleDocTypeChange = (value: string) => {
    setSelectedDocType(value);
  };

  /**
   * 提交文书生成请求
   * 收集表单数据，调用后端API生成法律文书
   */
  const handleGenerate = async () => {
    try {
      /** 校验必填字段 */
      const values = await form.validateFields();
      const { docType, scenario, partyName, counterParty, amount, otherInfo } = values;

      /** 构造补充信息对象，过滤空值 */
      const details: DetailFields = {};
      if (partyName) details.partyName = partyName;
      if (counterParty) details.counterParty = counterParty;
      if (amount) details.amount = amount;
      if (otherInfo) details.otherInfo = otherInfo;

      setLoading(true);
      setDocResult(null);

      /** 调用后端文书生成接口 */
      const response = await apiClient.post<DocumentGenerateResponse>(
        '/api/document/generate',
        {
          doc_type: docType,
          scenario,
          details,
        }
      );

      setDocResult(response.data);
      message.success('文书生成成功');
    } catch (err: unknown) {
      /** 表单校验失败不提示错误（Ant Design会自动标红） */
      if (err && typeof err === 'object' && 'errorFields' in err) {
        return;
      }
      message.error('文书生成失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  /**
   * 复制文书内容到剪贴板
   * 将文书标题和正文拼接后复制
   */
  const handleCopy = async () => {
    if (!docResult) return;
    const fullText = `${docResult.title}\n\n${docResult.content}`;
    try {
      await navigator.clipboard.writeText(fullText);
      message.success('已复制到剪贴板');
    } catch {
      message.error('复制失败，请手动复制');
    }
  };

  /**
   * 导出文书为文本文件
   * 将完整文书信息导出为.txt文件下载
   */
  const handleExport = () => {
    if (!docResult) return;

    /** 拼接导出内容 */
    const exportContent = [
      docResult.title,
      '',
      docResult.content,
      '',
      '─'.repeat(40),
      '法律依据：',
      ...docResult.legal_basis.map((item, idx) => `  ${idx + 1}. ${item}`),
      '',
      '使用提示：',
      ...docResult.tips.map((item, idx) => `  ${idx + 1}. ${item}`),
      '',
      '─'.repeat(40),
      `免责声明：${docResult.disclaimer}`,
    ].join('\n');

    /** 创建Blob并触发下载 */
    const blob = new Blob([exportContent], { type: 'text/plain;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${docResult.title}.txt`;
    link.click();
    window.URL.revokeObjectURL(url);
    message.success('文书已导出');
  };

  /**
   * 渲染左侧表单区域
   * 包含文书类型选择、场景描述、补充信息折叠面板和生成按钮
   */
  const renderFormArea = () => (
    <Card
      title={
        <span>
          <FileTextOutlined style={{ marginRight: 8 }} />
          文书信息
        </span>
      }
      style={{ borderRadius: 8 }}
    >
      <Form
        form={form}
        layout="vertical"
        requiredMark
      >
        {/* 文书类型选择 */}
        <Form.Item
          label="文书类型"
          name="docType"
          rules={[{ required: true, message: '请选择文书类型' }]}
        >
          <Select
            placeholder="请选择文书类型"
            options={DOC_TYPE_OPTIONS}
            onChange={handleDocTypeChange}
            size="large"
          />
        </Form.Item>

        {/* 场景描述 */}
        <Form.Item
          label="场景描述"
          name="scenario"
          rules={[{ required: true, message: '请描述您的具体情况' }]}
          extra="请用自然语言描述您的情况，AI将据此生成法律文书"
        >
          <TextArea
            rows={4}
            placeholder="例如：我在某公司工作了3年，公司未与我签订劳动合同，现在无故辞退我，我想要申请劳动仲裁..."
            showCount
            maxLength={2000}
          />
        </Form.Item>

        {/* 补充信息折叠面板 */}
        <Collapse
          ghost
          items={[
            {
              key: 'details',
              label: (
                <span style={{ color: '#8c8c8c' }}>
                  <InfoCircleOutlined style={{ marginRight: 4 }} />
                  补充信息（可选）
                </span>
              ),
              children: (
                <>
                  {/* 当事人姓名 */}
                  <Form.Item label="当事人姓名" name="partyName">
                    <Input placeholder="请输入您的姓名" />
                  </Form.Item>

                  {/* 对方当事人 */}
                  <Form.Item label="对方当事人" name="counterParty">
                    <Input placeholder="请输入对方当事人姓名或单位名称" />
                  </Form.Item>

                  {/* 金额（仅催收函场景显示） */}
                  {selectedDocType === 'collection_letter' && (
                    <Form.Item label="金额" name="amount">
                      <Input placeholder="请输入催收金额，如：50000元" />
                    </Form.Item>
                  )}

                  {/* 其他补充 */}
                  <Form.Item label="其他补充" name="otherInfo">
                    <TextArea
                      rows={2}
                      placeholder="其他需要补充的信息..."
                    />
                  </Form.Item>
                </>
              ),
            },
          ]}
        />

        {/* 生成按钮 */}
        <Form.Item style={{ marginTop: 16, marginBottom: 0 }}>
          <Button
            type="primary"
            icon={<ThunderboltOutlined />}
            onClick={handleGenerate}
            loading={loading}
            block
            size="large"
          >
            {loading ? '正在生成...' : '生成文书'}
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );

  /**
   * 渲染右侧预览区域
   * 包含文书标题、正文、法律依据、使用提示和免责声明
   */
  const renderPreviewArea = () => {
    /** 生成中显示加载状态 */
    if (loading) {
      return (
        <Card style={{ borderRadius: 8, minHeight: 400 }}>
          <div style={{ textAlign: 'center', padding: '80px 0' }}>
            <Spin size="large" tip="正在生成法律文书，请稍候...">
              <div style={{ minHeight: 120 }} />
            </Spin>
          </div>
        </Card>
      );
    }

    /** 无结果时显示空状态 */
    if (!docResult) {
      return (
        <Card style={{ borderRadius: 8, minHeight: 400 }}>
          <Empty
            description="填写左侧表单并点击生成，预览文书内容"
            style={{ marginTop: 80 }}
          >
            <Paragraph style={{ color: '#8c8c8c', fontSize: 13 }}>
              AI将根据您提供的信息生成专业的法律文书
            </Paragraph>
          </Empty>
        </Card>
      );
    }

    /** 有结果时渲染文书预览 */
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* 文书标题与操作按钮 */}
        <Card style={{ borderRadius: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <Title level={4} style={{ margin: 0 }}>
                {docResult.title}
              </Title>
              <Tag color="blue" style={{ marginTop: 8 }}>
                {DOC_TYPE_LABEL_MAP[docResult.doc_type] || docResult.doc_type}
              </Tag>
            </div>
            <Space>
              <Button
                icon={<CopyOutlined />}
                onClick={handleCopy}
              >
                复制
              </Button>
              <Button
                icon={<DownloadOutlined />}
                onClick={handleExport}
              >
                导出
              </Button>
            </Space>
          </div>
        </Card>

        {/* 文书正文（Markdown渲染） */}
        <Card
          title={
            <span>
              <FileTextOutlined style={{ marginRight: 8 }} />
              文书正文
            </span>
          }
          style={{ borderRadius: 8 }}
        >
          <div
            className="document-content"
            style={{
              lineHeight: 1.8,
              fontSize: 14,
              color: '#262626',
            }}
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
              {docResult.content}
            </ReactMarkdown>
          </div>
        </Card>

        {/* 法律依据列表 */}
        {docResult.legal_basis && docResult.legal_basis.length > 0 && (
          <Card
            title={
              <span>
                <SafetyCertificateOutlined style={{ marginRight: 8 }} />
                法律依据
              </span>
            }
            style={{ borderRadius: 8 }}
            size="small"
          >
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              {docResult.legal_basis.map((item, idx) => (
                <li key={idx} style={{ marginBottom: 4, color: '#595959', fontSize: 13 }}>
                  {item}
                </li>
              ))}
            </ul>
          </Card>
        )}

        {/* 使用提示 */}
        {docResult.tips && docResult.tips.length > 0 && (
          <Card
            title={
              <span>
                <InfoCircleOutlined style={{ marginRight: 8 }} />
                使用提示
              </span>
            }
            style={{ borderRadius: 8 }}
            size="small"
          >
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              {docResult.tips.map((item, idx) => (
                <li key={idx} style={{ marginBottom: 4, color: '#595959', fontSize: 13 }}>
                  {item}
                </li>
              ))}
            </ul>
          </Card>
        )}

        {/* 免责声明 */}
        <Alert
          type="warning"
          showIcon
          icon={<WarningOutlined />}
          message="免责声明"
          description={docResult.disclaimer || '本法律文书由AI生成，仅供参考，不构成法律意见。请在专业律师指导下使用，并核实相关法律依据的准确性。'}
          style={{ borderRadius: 8 }}
        />
      </div>
    );
  };

  return (
    <div style={{ maxWidth: 1400, margin: '0 auto' }}>
      {/* 页面标题 */}
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0 }}>
          <FileTextOutlined style={{ marginRight: 8 }} />
          法律文书生成
        </Title>
        <Text type="secondary" style={{ fontSize: 13 }}>
          选择文书类型并描述您的场景，AI将为您生成专业的法律文书
        </Text>
      </div>

      {/* 左右布局：表单 + 预览 */}
      <Row gutter={24}>
        {/* 左侧表单区域 */}
        <Col xs={24} lg={8}>
          {renderFormArea()}
        </Col>

        {/* 右侧预览区域 */}
        <Col xs={24} lg={16}>
          {renderPreviewArea()}
        </Col>
      </Row>

      {/* Markdown内容样式 */}
      <style>{`
        .document-content h1 { font-size: 20px; margin: 16px 0 8px; }
        .document-content h2 { font-size: 18px; margin: 14px 0 8px; }
        .document-content h3 { font-size: 16px; margin: 12px 0 6px; }
        .document-content p { margin: 8px 0; }
        .document-content ul, .document-content ol { padding-left: 24px; margin: 8px 0; }
        .document-content li { margin: 4px 0; }
        .document-content blockquote {
          border-left: 4px solid #1890ff;
          padding: 8px 16px;
          margin: 12px 0;
          background: #f6f8fa;
          color: #595959;
        }
        .document-content table {
          border-collapse: collapse;
          width: 100%;
          margin: 12px 0;
        }
        .document-content th, .document-content td {
          border: 1px solid #e8e8e8;
          padding: 8px 12px;
          text-align: left;
        }
        .document-content th {
          background: #fafafa;
          font-weight: 600;
        }
        .document-content hr {
          border: none;
          border-top: 1px solid #e8e8e8;
          margin: 16px 0;
        }
      `}</style>
    </div>
  );
};

export default DocumentPage;
