/**
 * 复核标记组件
 * 用于标记审查结果的采纳或拒绝状态
 * 显示 ✓ 已采纳 或 ✗ 误报 标识
 */
import React from 'react';
import { Tag, Space } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import type { ReviewResult } from '../types';

/** 复核标记组件属性 */
interface ReviewMarkProps {
  /** 复核结果 */
  result?: ReviewResult;
  /** 复核人 */
  reviewer?: string;
  /** 复核时间 */
  reviewedAt?: string;
  /** 尺寸：small 或 default */
  size?: 'small' | 'default';
}

/**
 * ReviewMark 复核标记组件
 * 根据复核结果显示对应的标记图标和颜色
 */
const ReviewMark: React.FC<ReviewMarkProps> = ({
  result,
  reviewer,
  reviewedAt,
  size = 'default',
}) => {
  /** 未复核状态 */
  if (!result) {
    return (
      <Tag
        color="default"
        style={{ fontSize: size === 'small' ? 11 : 13 }}
      >
        待复核
      </Tag>
    );
  }

  /** 已采纳状态 */
  if (result === 'accepted') {
    return (
      <Space size={4}>
        <Tag
          icon={<CheckCircleOutlined />}
          color="success"
          style={{ fontSize: size === 'small' ? 11 : 13 }}
        >
          已采纳
        </Tag>
        {reviewer && (
          <span style={{ fontSize: 11, color: '#8c8c8c' }}>
            {reviewer}
          </span>
        )}
        {reviewedAt && (
          <span style={{ fontSize: 11, color: '#bfbfbf' }}>
            {reviewedAt}
          </span>
        )}
      </Space>
    );
  }

  /** 已拒绝（误报）状态 */
  return (
    <Space size={4}>
      <Tag
        icon={<CloseCircleOutlined />}
        color="error"
        style={{ fontSize: size === 'small' ? 11 : 13 }}
      >
        误报
      </Tag>
      {reviewer && (
        <span style={{ fontSize: 11, color: '#8c8c8c' }}>
          {reviewer}
        </span>
      )}
      {reviewedAt && (
        <span style={{ fontSize: 11, color: '#bfbfbf' }}>
          {reviewedAt}
        </span>
      )}
    </Space>
  );
};

export default ReviewMark;
