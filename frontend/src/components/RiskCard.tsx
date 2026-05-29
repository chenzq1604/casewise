/**
 * 风险条款卡片组件
 * 展示合同审查中发现的风险条款，含溯源信息
 * 支持风险等级标识、法条依据、判例引用和修改建议
 */
import React from 'react';
import { Card, Tag, Button, Space, Divider } from 'antd';
import {
  CheckOutlined,
  CloseOutlined,
} from '@ant-design/icons';
import type { RiskItem, RiskLevel, ReviewResult } from '../types';
import CitationCard from './CitationCard';

/** 风险卡片组件属性 */
interface RiskCardProps {
  /** 风险项数据 */
  risk: RiskItem;
  /** 复核标记回调 */
  onReview?: (riskId: string, result: ReviewResult) => void;
}

/**
 * 获取风险等级对应的颜色和标签
 * @param level - 风险等级
 * @returns 包含颜色和文本的对象
 */
const getRiskLevelConfig = (level: RiskLevel) => {
  const configMap = {
    high: { color: '#ff4d4f', bgColor: '#fff2f0', tagColor: 'error', text: '高风险' },
    medium: { color: '#faad14', bgColor: '#fffbe6', tagColor: 'warning', text: '中风险' },
    low: { color: '#52c41a', bgColor: '#f6ffed', tagColor: 'success', text: '低风险' },
  };
  return configMap[level];
};

/**
 * RiskCard 风险条款卡片组件
 * 展示风险等级、条款定位、法条依据、判例引用、修改建议和复核按钮
 */
const RiskCard: React.FC<RiskCardProps> = ({ risk, onReview }) => {
  /** 风险等级配置 */
  const levelConfig = getRiskLevelConfig(risk.level);

  /**
   * 处理复核操作
   * @param result - 复核结果（接受/拒绝）
   */
  const handleReview = (result: ReviewResult) => {
    onReview?.(risk.id, result);
  };

  return (
    <Card
      size="small"
      className={`risk-card risk-${risk.level}`}
      style={{ marginBottom: 12 }}
    >
      {/* 风险等级标签 + 条款位置 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <Tag color={levelConfig.tagColor}>{levelConfig.text}</Tag>
        <span className="risk-location">位置：{risk.location}</span>
        {/* 复核状态显示 */}
        {risk.reviewResult && (
          <Tag
            color={risk.reviewResult === 'accepted' ? 'success' : 'error'}
            style={{ marginLeft: 'auto' }}
          >
            {risk.reviewResult === 'accepted' ? '已采纳' : '已标记误报'}
          </Tag>
        )}
      </div>

      {/* 风险条款原文 */}
      <div
        style={{
          padding: '8px 12px',
          background: '#fafafa',
          borderRadius: 4,
          fontSize: 13,
          color: '#595959',
          marginBottom: 8,
          borderLeft: '3px solid #d9d9d9',
        }}
      >
        {risk.originalText}
      </div>

      {/* 风险描述 */}
      <div className="risk-description">{risk.description}</div>

      {/* 法条依据 */}
      {risk.lawCitations.length > 0 && (
        <>
          <Divider orientation="left" style={{ margin: '12px 0 8px', fontSize: 13 }}>
            法条依据
          </Divider>
          {risk.lawCitations.map((citation) => (
            <CitationCard key={citation.id} citation={citation} />
          ))}
        </>
      )}

      {/* 判例引用 */}
      {risk.caseCitations.length > 0 && (
        <>
          <Divider orientation="left" style={{ margin: '12px 0 8px', fontSize: 13 }}>
            相关判例
          </Divider>
          {risk.caseCitations.map((citation) => (
            <CitationCard key={citation.id} citation={citation} />
          ))}
        </>
      )}

      {/* 修改建议 */}
      <Divider orientation="left" style={{ margin: '12px 0 8px', fontSize: 13 }}>
        修改建议
      </Divider>
      <div className="risk-suggestion">{risk.suggestion}</div>

      {/* 复核操作按钮 */}
      {!risk.reviewResult && onReview && (
        <div style={{ marginTop: 12, textAlign: 'right' }}>
          <Space>
            <Button
              size="small"
              icon={<CheckOutlined />}
              className="review-mark-btn"
              onClick={() => handleReview('accepted')}
            >
              采纳
            </Button>
            <Button
              size="small"
              danger
              icon={<CloseOutlined />}
              className="review-mark-btn"
              onClick={() => handleReview('rejected')}
            >
              误报
            </Button>
          </Space>
        </div>
      )}
    </Card>
  );
};

export default RiskCard;
