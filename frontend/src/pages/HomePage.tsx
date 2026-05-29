/**
 * 首页/欢迎页
 * 产品介绍 + 功能入口卡片 + 合规声明
 * 移动端友好的大按钮布局
 */
import React from 'react';
import { Card, Row, Col, Typography, Button, Divider } from 'antd';
import {
  MessageOutlined,
  FileSearchOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Title, Paragraph, Text } = Typography;

/**
 * HomePage 首页组件
 * 展示产品介绍和功能入口
 */
const HomePage: React.FC = () => {
  const navigate = useNavigate();

  /**
   * 跳转到法律问答页
   */
  const goToChat = () => {
    navigate('/chat');
  };

  /**
   * 跳转到合同审查页
   */
  const goToContract = () => {
    navigate('/contract');
  };

  return (
    <div style={{ maxWidth: 960, margin: '0 auto' }}>
      {/* 产品介绍区域 */}
      <div className="text-center" style={{ marginBottom: 40 }}>
        <Title level={2} style={{ color: '#1890ff', marginBottom: 16 }}>
          CaseWise 法律AI助手
        </Title>
        <Paragraph
          style={{
            fontSize: 16,
            color: '#595959',
            maxWidth: 600,
            margin: '0 auto',
            lineHeight: 1.8,
          }}
        >
          基于人工智能的法律咨询与合同审查工具，为您提供智能法律问答、合同风险识别与合规建议。
          每条回答均附带法条引用与判例依据，支持人工复核与溯源验证。
        </Paragraph>
      </div>

      {/* 功能入口卡片 */}
      <Row gutter={[24, 24]} style={{ marginBottom: 40 }}>
        {/* 法律问答入口 */}
        <Col xs={24} sm={12}>
          <Card
            className="entry-card"
            onClick={goToChat}
            hoverable
            style={{ textAlign: 'center', padding: '24px 16px' }}
          >
            <MessageOutlined
              className="entry-card-icon"
              style={{ color: '#1890ff' }}
            />
            <div className="entry-card-title">法律问答</div>
            <div className="entry-card-desc">
              向AI助手咨询法律问题，获取附带法条引用和判例依据的专业回答
            </div>
            <Button
              type="primary"
              size="large"
              style={{ marginTop: 16, width: '100%' }}
            >
              开始咨询
            </Button>
          </Card>
        </Col>

        {/* 合同审查入口 */}
        <Col xs={24} sm={12}>
          <Card
            className="entry-card"
            onClick={goToContract}
            hoverable
            style={{ textAlign: 'center', padding: '24px 16px' }}
          >
            <FileSearchOutlined
              className="entry-card-icon"
              style={{ color: '#fa8c16' }}
            />
            <div className="entry-card-title">合同审查</div>
            <div className="entry-card-desc">
              上传合同文件，AI自动识别风险条款，提供法条依据、判例参考和修改建议
            </div>
            <Button
              type="primary"
              size="large"
              style={{ marginTop: 16, width: '100%', background: '#fa8c16', borderColor: '#fa8c16' }}
            >
              上传合同
            </Button>
          </Card>
        </Col>
      </Row>

      {/* 功能特色说明 */}
      <Divider orientation="left">核心特色</Divider>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <Card size="small" style={{ textAlign: 'center' }}>
            <SafetyCertificateOutlined style={{ fontSize: 32, color: '#52c41a', marginBottom: 8 }} />
            <Title level={5}>引用溯源</Title>
            <Paragraph style={{ fontSize: 13, color: '#8c8c8c' }}>
              每条回答附带法条与判例引用，支持验证状态标识
            </Paragraph>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card size="small" style={{ textAlign: 'center' }}>
            <SafetyCertificateOutlined style={{ fontSize: 32, color: '#1890ff', marginBottom: 8 }} />
            <Title level={5}>人工复核</Title>
            <Paragraph style={{ fontSize: 13, color: '#8c8c8c' }}>
              AI审查结果支持人工复核标记，确保审查质量
            </Paragraph>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card size="small" style={{ textAlign: 'center' }}>
            <SafetyCertificateOutlined style={{ fontSize: 32, color: '#fa8c16', marginBottom: 8 }} />
            <Title level={5}>合规声明</Title>
            <Paragraph style={{ fontSize: 13, color: '#8c8c8c' }}>
              每条AI回答均附带合规声明，明确AI辅助定位
            </Paragraph>
          </Card>
        </Col>
      </Row>

      {/* 合规声明 */}
      <div className="compliance-disclaimer" style={{ marginTop: 32 }}>
        <SafetyCertificateOutlined className="disclaimer-icon" />
        <Text type="secondary" style={{ fontSize: 12 }}>
          CaseWise 法律AI助手仅提供法律信息参考，不构成法律意见。AI生成内容可能存在不准确之处，
          重要法律决策请咨询专业律师。所有AI回答均附带引用来源，请核实引用的完整性和准确性。
        </Text>
      </div>
    </div>
  );
};

export default HomePage;
