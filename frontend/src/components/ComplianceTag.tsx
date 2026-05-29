/**
 * 合规声明标签组件
 * 在AI回答底部展示合规声明信息
 * 包含免责声明、模型版本、是否人工复核等
 */
import React from 'react';
import { Tag, Tooltip } from 'antd';
import {
  InfoCircleOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import type { ComplianceInfo } from '../types';

/** 合规声明标签组件属性 */
interface ComplianceTagProps {
  /** 合规声明数据 */
  compliance: ComplianceInfo;
}

/**
 * ComplianceTag 合规声明标签组件
 * 以灰色小字展示合规声明，鼠标悬停显示详细信息
 */
const ComplianceTag: React.FC<ComplianceTagProps> = ({ compliance }) => {
  return (
    <div className="compliance-disclaimer">
      <InfoCircleOutlined className="disclaimer-icon" />
      <span>{compliance.disclaimer}</span>
      <div style={{ marginTop: 4, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {/* 模型版本标签 */}
        <Tooltip title="生成此回答的AI模型版本">
          <Tag style={{ fontSize: 11, color: '#8c8c8c', border: 'none', background: '#e8e8e8' }}>
            模型: {compliance.modelVersion}
          </Tag>
        </Tooltip>
        {/* 生成时间标签 */}
        <Tooltip title="回答生成时间">
          <Tag style={{ fontSize: 11, color: '#8c8c8c', border: 'none', background: '#e8e8e8' }}>
            {compliance.generatedAt}
          </Tag>
        </Tooltip>
        {/* 人工复核状态标签 */}
        <Tooltip title={compliance.humanReviewed ? '此回答已通过人工复核' : '此回答尚未经过人工复核'}>
          <Tag
            icon={<SafetyCertificateOutlined />}
            color={compliance.humanReviewed ? 'success' : 'default'}
            style={{ fontSize: 11 }}
          >
            {compliance.humanReviewed ? '已复核' : '未复核'}
          </Tag>
        </Tooltip>
      </div>
    </div>
  );
};

export default ComplianceTag;
