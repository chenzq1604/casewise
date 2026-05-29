/**
 * 法条/判例引用卡片组件
 * 展示AI回答中引用的法律依据，支持展开查看全文
 * 区分法条引用（蓝色）和判例引用（橙色）
 */
import React, { useState } from 'react';
import { Tag, Card } from 'antd';
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CloseCircleOutlined,
  DownOutlined,
  UpOutlined,
} from '@ant-design/icons';
import type { Citation, VerifyStatus } from '../types';

/** 引用卡片组件属性 */
interface CitationCardProps {
  /** 引用数据 */
  citation: Citation;
}

/**
 * 获取验证状态对应的图标和颜色
 * @param status - 验证状态
 * @returns 包含图标、颜色和文本的对象
 */
const getVerifyStatusConfig = (status: VerifyStatus) => {
  const configMap = {
    verified: {
      icon: <CheckCircleOutlined />,
      color: '#52c41a',
      text: '已验证',
    },
    pending: {
      icon: <ExclamationCircleOutlined />,
      color: '#faad14',
      text: '待确认',
    },
    unverifiable: {
      icon: <CloseCircleOutlined />,
      color: '#ff4d4f',
      text: '无法验证',
    },
  };
  return configMap[status];
};

/**
 * CitationCard 引用卡片组件
 * 支持展开/收起全文，区分法条和判例类型
 */
const CitationCard: React.FC<CitationCardProps> = ({ citation }) => {
  /** 控制全文展开/收起状态 */
  const [expanded, setExpanded] = useState(false);

  /** 验证状态配置 */
  const verifyConfig = getVerifyStatusConfig(citation.verifyStatus);

  /** 根据引用类型确定CSS类名和标签颜色 */
  const isLaw = citation.type === 'law';
  const cardClassName = `citation-card ${isLaw ? 'citation-law' : 'citation-case'}`;
  const tagColor = isLaw ? 'blue' : 'orange';
  const tagLabel = isLaw ? '法条' : '判例';

  return (
    <Card
      size="small"
      className={cardClassName}
      style={{ marginBottom: 8 }}
    >
      {/* 卡片头部：类型标签 + 编号 + 验证状态 */}
      <div className="citation-header">
        <Tag color={tagColor}>{tagLabel}</Tag>
        <span className="citation-code">{citation.code}</span>
        <Tag
          icon={verifyConfig.icon}
          color={verifyConfig.color === '#52c41a' ? 'success' : verifyConfig.color === '#faad14' ? 'warning' : 'error'}
          style={{ marginLeft: 'auto' }}
        >
          {verifyConfig.text}
        </Tag>
      </div>

      {/* 法条/判例标题 */}
      <div style={{ fontWeight: 500, marginBottom: 4 }}>{citation.title}</div>

      {/* 摘要 */}
      <div className="citation-summary">{citation.summary}</div>

      {/* 展开查看全文 */}
      {citation.fullText && (
        <>
          <div
            onClick={() => setExpanded(!expanded)}
            style={{
              marginTop: 8,
              color: '#1890ff',
              cursor: 'pointer',
              fontSize: 13,
              display: 'flex',
              alignItems: 'center',
              gap: 4,
            }}
          >
            {expanded ? <UpOutlined /> : <DownOutlined />}
            {expanded ? '收起全文' : '展开全文'}
          </div>
          {expanded && (
            <div className="citation-full-text">{citation.fullText}</div>
          )}
        </>
      )}
    </Card>
  );
};

export default CitationCard;
