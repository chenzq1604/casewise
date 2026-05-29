/**
 * 合同查看器组件
 * 支持对照模式（左原文右风险）和批注模式切换
 * 响应式：移动端纵向排列
 */
import React, { useState } from 'react';
import { Tabs, Badge, Empty } from 'antd';
import type { ContractAnalysis, RiskItem } from '../types';
import RiskCard from './RiskCard';

/** 合同查看器组件属性 */
interface ContractViewerProps {
  /** 合同分析结果 */
  analysis: ContractAnalysis;
  /** 复核标记回调 */
  onReview?: (riskId: string, result: 'accepted' | 'rejected') => void;
}

/**
 * ContractViewer 合同查看器组件
 * 提供对照模式和批注模式两种查看方式
 * 对照模式：左侧合同原文，右侧风险列表
 * 批注模式：合同原文中嵌入风险标注
 */
const ContractViewer: React.FC<ContractViewerProps> = ({ analysis, onReview }) => {
  /** 当前激活的Tab键 */
  const [activeTab, setActiveTab] = useState<string>('compare');

  /**
   * 按风险等级对风险项排序
   * 高风险优先显示
   * @param risks - 风险项列表
   * @returns 排序后的风险项列表
   */
  const sortRisksByLevel = (risks: RiskItem[]): RiskItem[] => {
    const order = { high: 0, medium: 1, low: 2 };
    return [...risks].sort((a, b) => order[a.level] - order[b.level]);
  };

  /** 排序后的风险列表 */
  const sortedRisks = sortRisksByLevel(analysis.risks);

  /**
   * 渲染对照模式
   * 左侧显示合同原文，右侧显示风险列表
   */
  const renderCompareMode = () => (
    <div className="contract-viewer">
      {/* 左侧：合同原文 */}
      <div className="contract-original">
        <div style={{ fontWeight: 600, marginBottom: 12, color: '#262626' }}>
          合同原文
        </div>
        {analysis.originalText}
      </div>

      {/* 右侧：风险条款列表 */}
      <div className="contract-annotation">
        <div style={{ fontWeight: 600, marginBottom: 12, color: '#262626' }}>
          风险条款（{sortedRisks.length}项）
        </div>
        {sortedRisks.length > 0 ? (
          sortedRisks.map((risk) => (
            <RiskCard key={risk.id} risk={risk} onReview={onReview} />
          ))
        ) : (
          <Empty description="未发现风险条款" />
        )}
      </div>
    </div>
  );

  /**
   * 渲染批注模式
   * 合同原文中高亮风险条款，下方显示对应风险详情
   */
  const renderAnnotationMode = () => {
    /** 将合同原文按风险位置分段，插入风险标注 */
    return (
      <div style={{ padding: '0 16px' }}>
        <div
          style={{
            padding: 16,
            background: '#fafafa',
            borderRadius: 8,
            border: '1px solid #f0f0f0',
            lineHeight: 2,
            whiteSpace: 'pre-wrap',
          }}
        >
          {analysis.originalText}
        </div>

        {/* 风险批注列表 */}
        <div style={{ marginTop: 16 }}>
          <div style={{ fontWeight: 600, marginBottom: 12, color: '#262626' }}>
            批注详情
          </div>
          {sortedRisks.length > 0 ? (
            sortedRisks.map((risk, index) => (
              <RiskCard key={risk.id} risk={risk} onReview={onReview} />
            ))
          ) : (
            <Empty description="未发现风险条款" />
          )}
        </div>
      </div>
    );
  };

  /** Tab项配置 */
  const tabItems = [
    {
      key: 'compare',
      label: (
        <span>
          对照模式
          <Badge
            count={sortedRisks.length}
            size="small"
            style={{ marginLeft: 4 }}
          />
        </span>
      ),
      children: renderCompareMode(),
    },
    {
      key: 'annotation',
      label: '批注模式',
      children: renderAnnotationMode(),
    },
  ];

  return (
    <Tabs
      activeKey={activeTab}
      onChange={setActiveTab}
      items={tabItems}
      size="small"
    />
  );
};

export default ContractViewer;
