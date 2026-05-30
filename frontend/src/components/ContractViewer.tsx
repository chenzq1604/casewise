/**
 * 合同查看器组件
 * 支持对照模式（左原文右风险）和批注模式切换
 * 响应式：移动端纵向排列
 */
import React, { useState } from 'react';
import { Tabs, Badge, Empty } from 'antd';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
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
 * 预处理合同文本为安全的Markdown格式
 * 保留合法Markdown格式，优化段落分隔
 * @param text - 原始合同文本
 * @returns 安全的Markdown文本
 */
const preprocessContractText = (text: string): string => {
  if (!text) return '（无合同文本）';

  const lines = text.split('\n');
  const processed = lines.map((line) => {
    const trimmed = line.trim();

    if (trimmed === '') return '';

    if (/^第[一二三四五六七八九十百千]+条/.test(trimmed)) {
      return `**${trimmed}**`;
    }

    return trimmed;
  });

  return processed.join('\n\n');
};

/**
 * ContractViewer 合同查看器组件
 * 提供对照模式和批注模式两种查看方式
 * 对照模式：左侧合同原文，右侧风险列表
 * 批注模式：合同原文中嵌入风险标注
 */
const ContractViewer: React.FC<ContractViewerProps> = ({ analysis, onReview }) => {
  const [activeTab, setActiveTab] = useState<string>('compare');

  /**
   * 按风险等级对风险项排序
   * @param risks - 风险项列表
   * @returns 排序后的风险项列表
   */
  const sortRisksByLevel = (risks: RiskItem[]): RiskItem[] => {
    const order = { high: 0, medium: 1, low: 2 };
    return [...risks].sort((a, b) => order[a.level] - order[b.level]);
  };

  const sortedRisks = sortRisksByLevel(analysis.risks);
  const processedText = preprocessContractText(analysis.originalText);

  /**
   * 渲染对照模式
   */
  const renderCompareMode = () => (
    <div className="contract-viewer">
      <div className="contract-original">
        <div style={{ fontWeight: 600, marginBottom: 12, color: '#262626' }}>
          合同原文
        </div>
        {analysis.htmlPreview ? (
          <iframe
            src={analysis.htmlPreview}
            style={{
              width: '100%',
              height: '560px',
              border: 'none',
              borderRadius: 4,
            }}
            title="合同原文预览"
          />
        ) : (
          <div className="markdown-body" style={{ lineHeight: 1.8 }}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {processedText}
            </ReactMarkdown>
          </div>
        )}
      </div>

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
   */
  const renderAnnotationMode = () => (
    <div style={{ padding: '0 16px' }}>
      {analysis.htmlPreview ? (
        <iframe
          src={analysis.htmlPreview}
          style={{
            width: '100%',
            height: '560px',
            border: 'none',
            borderRadius: 8,
          }}
          title="合同原文预览"
        />
      ) : (
        <div
          className="markdown-body"
          style={{
            padding: 16,
            background: '#fafafa',
            borderRadius: 8,
            border: '1px solid #f0f0f0',
            lineHeight: 1.8,
          }}
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {processedText}
          </ReactMarkdown>
        </div>
      )}

      <div style={{ marginTop: 16 }}>
        <div style={{ fontWeight: 600, marginBottom: 12, color: '#262626' }}>
          批注详情
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

  const tabItems = [
    {
      key: 'compare',
      label: (
        <span>
          对照模式
          <Badge count={sortedRisks.length} size="small" style={{ marginLeft: 4 }} />
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
