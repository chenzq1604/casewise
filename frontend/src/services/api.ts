/**
 * CaseWise 法律AI助手 - API调用封装
 * 统一管理所有与后端交互的接口
 */
import axios from 'axios';
import type { CollectionProgress, DataStatus, LawCategory } from '../types';

/** 创建axios实例，baseURL指向后端根路径，Vite代理会转发/api请求 */
const apiClient = axios.create({
  baseURL: '',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * 请求拦截器 - 添加认证Token
 */
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('casewise_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

/**
 * 响应拦截器 - 统一处理错误
 */
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('casewise_token');
    }
    return Promise.reject(error);
  }
);

/**
 * 法条引用卡片类型（与后端CitationCard对齐）
 */
export interface CitationCardData {
  law_name: string;
  article_number: string;
  article_content: string;
  verification_status: string;
}

/**
 * 法律问答响应类型（与后端ChatResponse对齐）
 */
export interface ChatResponseData {
  answer: string;
  citations: CitationCardData[];
  session_id: string;
  compliance_notice: string;
  created_at: string;
}

/**
 * 合同上传响应类型
 */
export interface ContractUploadData {
  file_id: string;
  filename: string;
  contract_text: string;
}

/**
 * 风险条款类型（与后端RiskItem对齐）
 */
export interface RiskItemData {
  clause_index: number;
  clause_text: string;
  risk_level: string;
  risk_description: string;
  law_reference: string;
  suggestion: string;
}

/**
 * 合同分析响应类型
 */
export interface ContractAnalyzeData {
  file_id: string;
  overall_risk_level: string;
  risk_items: RiskItemData[];
  summary: string;
  compliance_notice: string;
}

/**
 * 复核反馈提交类型
 */
export interface ReviewSubmitData {
  source_type: string;
  source_id: number;
  original_output: string;
  feedback_type: string;
  corrected_content?: string;
  comment?: string;
  reviewer?: string;
}

/**
 * 复核统计数据类型
 */
export interface ReviewStatsData {
  total_feedbacks: number;
  accepted_count: number;
  rejected_count: number;
  acceptance_rate: number;
  by_source_type: Record<string, { total: number; accepted: number; rate: number }>;
}

/**
 * 法律问答相关API
 */
export const chatApi = {
  /**
   * 发送法律问题给AI助手（非流式，作为fallback使用）
   * @param question - 用户提出的法律问题
   * @param sessionId - 会话ID（可选）
   * @returns AI回复（直接对应后端ChatResponse）
   */
  sendMessage: async (question: string, sessionId?: string): Promise<ChatResponseData> => {
    const response = await apiClient.post<ChatResponseData>('/api/chat', {
      question,
      session_id: sessionId || null,
    });
    return response.data;
  },

  /**
   * 流式发送法律问题，通过SSE实时接收AI回答
   * 使用 fetch + ReadableStream 消费SSE事件流
   * @param question - 用户提出的法律问题
   * @param sessionId - 会话ID（可选，用于多轮对话）
   * @param onToken - 收到token片段时的回调，参数为文本片段
   * @param onCitation - 收到引用卡片时的回调，参数为引用数据
   * @param onCompliance - 收到合规声明时的回调，参数为合规数据
   * @param onDone - 回答完成时的回调，参数为会话ID
   * @param onError - 错误回调，参数为错误消息
   */
  sendMessageStream: async (
    question: string,
    sessionId: string | undefined,
    onToken: (content: string) => void,
    onCitation: (citation: CitationCardData) => void,
    onCompliance: (compliance: { notice: string }) => void,
    onDone: (sessionId: string) => void,
    onError: (error: string) => void,
  ): Promise<void> => {
    /** 获取认证Token */
    const token = localStorage.getItem('casewise_token');
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    /** 发起SSE流式请求 */
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers,
      body: JSON.stringify({ question, session_id: sessionId || null }),
    });

    /** 检查HTTP响应状态 */
    if (!response.ok) {
      onError(`请求失败: ${response.status} ${response.statusText}`);
      return;
    }

    /** 获取可读流 */
    const reader = response.body?.getReader();
    if (!reader) {
      onError('无法读取响应流');
      return;
    }

    const decoder = new TextDecoder();
    /** 缓冲区，用于处理不完整的SSE行 */
    let buffer = '';
    /** 当前SSE事件类型 */
    let currentEvent = '';

    /** 循环读取流数据 */
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      /** 将二进制数据解码为文本，追加到缓冲区 */
      buffer += decoder.decode(value, { stream: true });

      /** 按换行符拆分，最后一行可能不完整，保留在缓冲区 */
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      /** 逐行解析SSE事件 */
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          /** 解析事件类型 */
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith('data: ')) {
          /** 解析事件数据 */
          const data = line.slice(6);
          try {
            const parsed = JSON.parse(data);
            switch (currentEvent) {
              case 'token':
                /** 文本片段，追加到流式内容 */
                onToken(parsed.content || '');
                break;
              case 'citation':
                /** 引用卡片数据 */
                onCitation(parsed);
                break;
              case 'compliance':
                /** 合规声明数据 */
                onCompliance(parsed);
                break;
              case 'done':
                /** 回答完成，返回会话ID */
                onDone(parsed.session_id || '');
                break;
              case 'error':
                /** 服务端错误 */
                onError(parsed.message || '未知错误');
                break;
            }
          } catch {
            /** 忽略JSON解析错误，可能是不完整数据 */
          }
        }
      }
    }
  },
};

/**
 * 合同审查相关API
 */
export const contractApi = {
  /**
   * 上传合同文件
   * @param file - 合同文件（PDF/Word）
   * @returns 上传后的文件标识和提取的文本
   */
  uploadContract: async (file: File): Promise<ContractUploadData> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post<ContractUploadData>('/api/contract/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  /**
   * 分析合同内容，返回风险审查结果
   * @param fileId - 上传后的文件标识
   * @returns 合同分析结果
   */
  analyzeContract: async (fileId: string): Promise<ContractAnalyzeData> => {
    const response = await apiClient.post<ContractAnalyzeData>('/api/contract/analyze', {
      file_id: fileId,
    });
    return response.data;
  },
};

/**
 * 复核统计相关API
 */
export const reviewApi = {
  /**
   * 提交复核反馈
   * @param feedback - 复核反馈数据
   * @returns 提交结果
   */
  submitReview: async (feedback: ReviewSubmitData): Promise<{ message: string; feedback_id: number }> => {
    const response = await apiClient.post('/api/review', feedback);
    return response.data;
  },

  /**
   * 获取复核统计数据
   * @returns 复核统计信息
   */
  getStats: async (): Promise<ReviewStatsData> => {
    const response = await apiClient.get('/api/review/stats');
    return response.data;
  },
};

export default apiClient;

/**
 * 数据管理相关API
 */
export const dataApi = {
  /**
   * 启动数据采集
   * @param categories - 要采集的法律类型列表
   * @param limit - 采集数量限制，0表示全量采集
   * @returns 采集任务信息
   */
  startCollect: async (categories: string[], limit: number = 0): Promise<{ task_id: string; message: string }> => {
    const response = await apiClient.post('/api/data/collect', { categories, limit });
    return response.data;
  },

  /**
   * 查询采集进度
   * @returns 当前采集进度信息
   */
  getProgress: async (): Promise<CollectionProgress> => {
    const response = await apiClient.get('/api/data/progress');
    return response.data;
  },

  /**
   * 查询数据状态
   * @returns 当前数据库统计信息
   */
  getStatus: async (): Promise<DataStatus> => {
    const response = await apiClient.get('/api/data/status');
    return response.data;
  },

  /**
   * 获取法律类型列表
   * @returns 可采集的法律分类列表
   */
  getCategories: async (): Promise<LawCategory[]> => {
    const response = await apiClient.get('/api/data/categories');
    return response.data;
  },

  /**
   * 取消采集任务
   * @returns 取消结果
   */
  cancelCollect: async (): Promise<{ message: string }> => {
    const response = await apiClient.post('/api/data/cancel');
    return response.data;
  },
};
