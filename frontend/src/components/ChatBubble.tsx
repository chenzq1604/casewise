/**
 * 对话气泡组件
 * 展示用户消息和AI回复，AI回复附带引用卡片、合规声明和复核按钮
 */
import React, { useState } from 'react';
import { Avatar, Button, Space, Tag, App } from 'antd';
import {
  UserOutlined,
  RobotOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  DownloadOutlined,
} from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { ChatMessage } from '../types';
import { reviewApi, reportApi } from '../services/api';
import CitationCard from './CitationCard';
import ComplianceTag from './ComplianceTag';

/** 对话气泡组件属性 */
interface ChatBubbleProps {
  /** 消息数据 */
  message: ChatMessage;
  /** 是否正在流式输出（显示闪烁光标） */
  streaming?: boolean;
  /** 复核回调，通知父组件更新消息状态 */
  onReview?: (messageId: string, status: 'confirmed' | 'incorrect') => void;
}

/**
 * ChatBubble 对话气泡组件
 * 根据消息角色（用户/AI）渲染不同样式的气泡
 * AI回复使用Markdown渲染，额外展示引用卡片、合规声明和复核按钮
 */
const ChatBubble: React.FC<ChatBubbleProps> = ({ message, streaming = false, onReview }) => {
  const { message: messageApi } = App.useApp();
  const [reviewLoading, setReviewLoading] = useState(false);
  const isUser = message.role === 'user';

  /**
   * 提交复核反馈
   * @param feedbackType - confirmed(确认正确) 或 incorrect(标记有误)
   */
  const handleReview = async (feedbackType: 'confirmed' | 'incorrect') => {
    setReviewLoading(true);
    try {
      await reviewApi.submitReview({
        source_type: 'chat',
        source_id: 0,
        original_output: message.content.substring(0, 200),
        feedback_type: feedbackType,
        comment: `法律问答复核: ${feedbackType === 'confirmed' ? '确认正确' : '标记有误'}`,
      });
      onReview?.(message.id, feedbackType === 'confirmed' ? 'confirmed' : 'incorrect');
      messageApi.success(feedbackType === 'confirmed' ? '已确认正确' : '已标记有误');
    } catch {
      messageApi.error('复核反馈提交失败');
    } finally {
      setReviewLoading(false);
    }
  };

  return (
    <div className={`chat-bubble-wrapper ${isUser ? 'bubble-user' : 'bubble-assistant'}`}>
      {!isUser && (
        <Avatar
          icon={<RobotOutlined />}
          style={{ backgroundColor: '#1890ff', marginRight: 8, flexShrink: 0 }}
        />
      )}

      <div style={{ maxWidth: '80%' }}>
        <div className={`chat-bubble ${isUser ? 'bubble-user' : 'bubble-assistant'}`}>
          {isUser ? (
            message.content
          ) : (
            <div className={`markdown-body ${streaming ? 'typing-cursor' : ''}`}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {!isUser && !streaming && (
          <>
            {message.citations && message.citations.length > 0 && (
              <div style={{ marginTop: 8 }}>
                {message.citations.map((citation) => (
                  <CitationCard key={citation.id} citation={citation} />
                ))}
              </div>
            )}

            {message.compliance && (
              <ComplianceTag compliance={message.compliance} />
            )}

            <div style={{ marginTop: 6, display: 'flex', alignItems: 'center', gap: 4 }}>
              {message.reviewStatus ? (
                <Tag
                  color={message.reviewStatus === 'confirmed' ? 'success' : 'warning'}
                  icon={message.reviewStatus === 'confirmed' ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
                  style={{ margin: 0, fontSize: 11 }}
                >
                  {message.reviewStatus === 'confirmed' ? '已确认' : '有误'}
                </Tag>
              ) : (
                <Space size={4}>
                  <Button
                    type="text"
                    size="small"
                    icon={<CheckCircleOutlined />}
                    loading={reviewLoading}
                    onClick={() => handleReview('confirmed')}
                    style={{ fontSize: 11, color: '#52c41a', padding: '0 4px' }}
                  >
                    正确
                  </Button>
                  <Button
                    type="text"
                    size="small"
                    icon={<CloseCircleOutlined />}
                    loading={reviewLoading}
                    onClick={() => handleReview('incorrect')}
                    style={{ fontSize: 11, color: '#faad14', padding: '0 4px' }}
                  >
                    有误
                  </Button>
                </Space>
              )}
              <Button
                type="text"
                size="small"
                icon={<DownloadOutlined />}
                onClick={async () => {
                  try {
                    const blob = await reportApi.exportChatReport({
                      question: '',
                      answer: message.content,
                      citations: message.citations?.map((c) => ({
                        law_name: c.title,
                        article_number: c.code,
                        article_content: c.summary,
                      })),
                    });
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = '法律咨询报告.html';
                    a.click();
                    window.URL.revokeObjectURL(url);
                    messageApi.success('报告导出成功');
                  } catch {
                    messageApi.error('报告导出失败');
                  }
                }}
                style={{ fontSize: 11, color: '#1890ff', padding: '0 4px' }}
              >
                导出
              </Button>
            </div>
          </>
        )}

        <div
          style={{
            fontSize: 11,
            color: '#bfbfbf',
            marginTop: 4,
            textAlign: isUser ? 'right' : 'left',
          }}
        >
          {message.timestamp}
        </div>
      </div>

      {isUser && (
        <Avatar
          icon={<UserOutlined />}
          style={{ backgroundColor: '#87d068', marginLeft: 8, flexShrink: 0 }}
        />
      )}
    </div>
  );
};

export default ChatBubble;
