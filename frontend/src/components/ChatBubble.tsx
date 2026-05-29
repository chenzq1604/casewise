/**
 * 对话气泡组件
 * 展示用户消息和AI回复，AI回复附带引用卡片和合规声明
 * 用户消息靠右蓝色，AI回复靠左灰色
 */
import React from 'react';
import { Avatar } from 'antd';
import {
  UserOutlined,
  RobotOutlined,
} from '@ant-design/icons';
import type { ChatMessage } from '../types';
import CitationCard from './CitationCard';
import ComplianceTag from './ComplianceTag';

/** 对话气泡组件属性 */
interface ChatBubbleProps {
  /** 消息数据 */
  message: ChatMessage;
}

/**
 * ChatBubble 对话气泡组件
 * 根据消息角色（用户/AI）渲染不同样式的气泡
 * AI回复额外展示引用卡片和合规声明
 */
const ChatBubble: React.FC<ChatBubbleProps> = ({ message }) => {
  /** 是否为用户消息 */
  const isUser = message.role === 'user';

  return (
    <div className={`chat-bubble-wrapper ${isUser ? 'bubble-user' : 'bubble-assistant'}`}>
      {/* AI头像（左侧） */}
      {!isUser && (
        <Avatar
          icon={<RobotOutlined />}
          style={{ backgroundColor: '#1890ff', marginRight: 8, flexShrink: 0 }}
        />
      )}

      <div style={{ maxWidth: '80%' }}>
        {/* 消息气泡 */}
        <div className={`chat-bubble ${isUser ? 'bubble-user' : 'bubble-assistant'}`}>
          {message.content}
        </div>

        {/* AI回复附加内容：引用卡片 + 合规声明 */}
        {!isUser && (
          <>
            {/* 法条/判例引用卡片列表 */}
            {message.citations && message.citations.length > 0 && (
              <div style={{ marginTop: 8 }}>
                {message.citations.map((citation) => (
                  <CitationCard key={citation.id} citation={citation} />
                ))}
              </div>
            )}

            {/* 合规声明 */}
            {message.compliance && (
              <ComplianceTag compliance={message.compliance} />
            )}
          </>
        )}

        {/* 消息时间 */}
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

      {/* 用户头像（右侧） */}
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
