/**
 * 法律问答页
 * 顶部对话区域，底部输入框
 * AI回答附带法条/判例引用卡片和合规声明
 */
import React, { useState, useRef, useEffect } from 'react';
import { Input, Button, Spin, Empty, Typography } from 'antd';
import { SendOutlined } from '@ant-design/icons';
import ChatBubble from '../components/ChatBubble';
import { chatApi } from '../services/api';
import type { ChatMessage, ComplianceInfo, Citation } from '../types';
import type { CitationCardData } from '../services/api';

const { TextArea } = Input;
const { Paragraph } = Typography;

/**
 * 将后端CitationCard转换为前端Citation类型
 * @param card - 后端返回的引用卡片数据
 * @returns 前端Citation对象
 */
function mapCitationCard(card: CitationCardData): Citation {
  return {
    id: `cite-${card.law_name}-${card.article_number}`,
    type: 'law' as const,
    code: card.article_number,
    title: `${card.law_name} ${card.article_number}`,
    summary: card.article_content || '点击查看详情',
    fullText: card.article_content,
    verifyStatus: card.verification_status === '已验证'
      ? 'verified' as const
      : card.verification_status === '待确认'
        ? 'pending' as const
        : 'unverifiable' as const,
  };
}

/**
 * ChatPage 法律问答页组件
 * 提供与AI助手的对话交互界面
 */
const ChatPage: React.FC = () => {
  /** 对话消息列表 */
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  /** 用户输入内容 */
  const [inputValue, setInputValue] = useState('');
  /** 是否正在等待AI回复 */
  const [loading, setLoading] = useState(false);
  /** 当前会话ID */
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);

  /** 对话区域滚动容器引用 */
  const chatContainerRef = useRef<HTMLDivElement>(null);

  /**
   * 自动滚动到对话区域底部
   * 每次消息更新后调用
   */
  const scrollToBottom = () => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  };

  /** 消息更新时自动滚动到底部 */
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  /**
   * 发送消息
   * 将用户消息添加到列表，调用API获取AI回复
   */
  const handleSend = async () => {
    const trimmed = inputValue.trim();
    if (!trimmed || loading) return;

    /** 构造用户消息 */
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: trimmed,
      timestamp: new Date().toLocaleString('zh-CN'),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setLoading(true);

    try {
      /** 调用后端API获取AI回复 */
      const data = await chatApi.sendMessage(trimmed, sessionId);

      /** 保存session_id用于多轮对话 */
      if (data.session_id) {
        setSessionId(data.session_id);
      }

      /** 将后端响应转换为前端ChatMessage格式 */
      const aiMessage: ChatMessage = {
        id: `ai-${Date.now()}`,
        role: 'assistant',
        content: data.answer,
        timestamp: new Date().toLocaleString('zh-CN'),
        citations: (data.citations || []).map(mapCitationCard),
        compliance: {
          disclaimer: data.compliance_notice || '本内容仅供参考，不构成法律意见',
          generatedAt: data.created_at || new Date().toLocaleString('zh-CN'),
          modelVersion: 'Doubao-Seed-2.0-Code',
          humanReviewed: false,
        } as ComplianceInfo,
      };
      setMessages((prev) => [...prev, aiMessage]);
    } catch (error) {
      /** API调用失败时显示错误消息 */
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: '抱歉，获取回答时出现错误，请稍后重试。',
        timestamp: new Date().toLocaleString('zh-CN'),
        compliance: {
          disclaimer: '此消息为系统错误提示，非AI生成内容',
          generatedAt: new Date().toLocaleString('zh-CN'),
          modelVersion: '-',
          humanReviewed: false,
        } as ComplianceInfo,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  /**
   * 处理键盘事件
   * Enter发送消息，Shift+Enter换行
   * @param e - 键盘事件
   */
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - 64px - 48px)',
        background: '#fff',
        borderRadius: 8,
        overflow: 'hidden',
      }}
    >
      {/* 对话消息区域 */}
      <div
        ref={chatContainerRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '16px 24px',
        }}
      >
        {messages.length === 0 ? (
          <Empty
            description="开始与AI助手对话吧"
            style={{ marginTop: 80 }}
          >
            <Paragraph style={{ color: '#8c8c8c', fontSize: 13 }}>
              您可以咨询法律问题，AI助手将为您提供附带法条引用的专业回答
            </Paragraph>
          </Empty>
        ) : (
          messages.map((msg) => (
            <ChatBubble key={msg.id} message={msg} />
          ))
        )}

        {/* 加载中提示 */}
        {loading && (
          <div style={{ textAlign: 'center', padding: 16 }}>
            <Spin tip="AI助手正在思考..." />
          </div>
        )}
      </div>

      {/* 底部输入区域 */}
      <div
        style={{
          borderTop: '1px solid #f0f0f0',
          padding: '12px 24px',
          background: '#fafafa',
        }}
      >
        <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
          <TextArea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入您的法律问题...（Enter发送，Shift+Enter换行）"
            autoSize={{ minRows: 1, maxRows: 4 }}
            style={{ flex: 1 }}
            disabled={loading}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            loading={loading}
            disabled={!inputValue.trim()}
          >
            发送
          </Button>
        </div>
        {/* 输入区合规提示 */}
        <div style={{ marginTop: 4, fontSize: 11, color: '#bfbfbf' }}>
          AI回答仅供参考，不构成法律意见。请核实引用内容的准确性。
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
