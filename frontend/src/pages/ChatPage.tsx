/**
 * 法律问答页
 * 顶部对话区域，底部输入框
 * AI回答附带法条/判例引用卡片和合规声明
 * 支持SSE流式接收，实时展示AI回答
 */
import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Input, Button, Empty, Typography } from 'antd';
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
 * 提供与AI助手的对话交互界面，支持流式接收
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
  /** 流式输出中的文本内容，实时拼接 */
  const [streamingContent, setStreamingContent] = useState('');
  /** 流式输出中的引用卡片列表 */
  const [streamingCitations, setStreamingCitations] = useState<Citation[]>([]);
  /** 流式输出中的合规声明 */
  const [streamingCompliance, setStreamingCompliance] = useState<ComplianceInfo | null>(null);

  /** 对话区域滚动容器引用 */
  const chatContainerRef = useRef<HTMLDivElement>(null);

  /**
   * 自动滚动到对话区域底部
   * 每次消息更新或流式内容更新后调用
   */
  const scrollToBottom = useCallback(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, []);

  /** 消息更新时自动滚动到底部 */
  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  /** 流式内容更新时自动滚动到底部 */
  useEffect(() => {
    scrollToBottom();
  }, [streamingContent, scrollToBottom]);

  /**
   * 发送消息（流式接收）
   * 优先使用SSE流式接口，失败时fallback到非流式接口
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

    /** 重置流式状态 */
    setStreamingContent('');
    setStreamingCitations([]);
    setStreamingCompliance(null);

    try {
      /** 调用SSE流式接口 */
      await chatApi.sendMessageStream(
        trimmed,
        sessionId,
        /** onToken: 追加文本到流式内容 */
        (content: string) => {
          setStreamingContent((prev) => prev + content);
        },
        /** onCitation: 收到引用卡片，追加到流式引用列表 */
        (citation: CitationCardData) => {
          setStreamingCitations((prev) => [...prev, mapCitationCard(citation)]);
        },
        /** onCompliance: 收到合规声明 */
        (compliance: { notice: string }) => {
          setStreamingCompliance({
            disclaimer: compliance.notice || '本内容仅供参考，不构成法律意见',
            generatedAt: new Date().toLocaleString('zh-CN'),
            modelVersion: 'Doubao-Seed-2.0-Code',
            humanReviewed: false,
          });
        },
        /** onDone: 流式完成，将完整消息添加到消息列表 */
        (newSessionId: string) => {
          /** 保存session_id用于多轮对话 */
          if (newSessionId) {
            setSessionId(newSessionId);
          }

          /** 获取当前流式内容，构造完整AI消息 */
          setStreamingContent((finalContent) => {
            setStreamingCitations((finalCitations) => {
              setStreamingCompliance((finalCompliance) => {
                const aiMessage: ChatMessage = {
                  id: `ai-${Date.now()}`,
                  role: 'assistant',
                  content: finalContent,
                  timestamp: new Date().toLocaleString('zh-CN'),
                  citations: finalCitations.length > 0 ? finalCitations : undefined,
                  compliance: finalCompliance || undefined,
                };
                setMessages((prev) => [...prev, aiMessage]);

                /** 清空流式状态 */
                setStreamingCitations([]);
                setStreamingCompliance(null);
                return null;
              });
              return [];
            });
            return '';
          });

          setLoading(false);
        },
        /** onError: 流式错误，fallback到非流式接口 */
        async (error: string) => {
          console.warn('流式请求失败，尝试非流式fallback:', error);
          try {
            /** fallback: 使用非流式接口 */
            const data = await chatApi.sendMessage(trimmed, sessionId);
            if (data.session_id) {
              setSessionId(data.session_id);
            }
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
          } catch {
            /** 非流式接口也失败，显示错误消息 */
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
            /** 清空流式状态 */
            setStreamingContent('');
            setStreamingCitations([]);
            setStreamingCompliance(null);
            setLoading(false);
          }
        },
      );
    } catch {
      /** 流式请求异常，fallback到非流式接口 */
      try {
        const data = await chatApi.sendMessage(trimmed, sessionId);
        if (data.session_id) {
          setSessionId(data.session_id);
        }
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
      } catch {
        /** 非流式接口也失败，显示错误消息 */
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
        /** 清空流式状态 */
        setStreamingContent('');
        setStreamingCitations([]);
        setStreamingCompliance(null);
        setLoading(false);
      }
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
        {messages.length === 0 && !streamingContent ? (
          <Empty
            description="开始与AI助手对话吧"
            style={{ marginTop: 80 }}
          >
            <Paragraph style={{ color: '#8c8c8c', fontSize: 13 }}>
              您可以咨询法律问题，AI助手将为您提供附带法条引用的专业回答
            </Paragraph>
          </Empty>
        ) : (
          <>
            {/* 已完成的消息列表 */}
            {messages.map((msg) => (
              <ChatBubble key={msg.id} message={msg} />
            ))}

            {/* 流式输出中的临时AI消息气泡 */}
            {streamingContent && (
              <ChatBubble
                message={{
                  id: 'streaming',
                  role: 'assistant',
                  content: streamingContent,
                  timestamp: new Date().toLocaleString('zh-CN'),
                  citations: streamingCitations.length > 0 ? streamingCitations : undefined,
                  compliance: streamingCompliance || undefined,
                }}
                streaming={true}
              />
            )}
          </>
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
