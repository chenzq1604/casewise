/**
 * CaseWise 法律AI助手 - API调用封装
 * 统一管理所有与后端交互的接口
 */
import axios from 'axios';
import type {
  ApiResponse,
  ChatMessage,
  ChatHistoryParams,
  ContractAnalysis,
  ReviewFeedback,
  ReviewStats,
} from '../types';

/** 创建axios实例，baseURL从环境变量读取 */
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
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
    // 401未授权时跳转登录
    if (error.response?.status === 401) {
      localStorage.removeItem('casewise_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

/**
 * 法律问答相关API
 */
export const chatApi = {
  /**
   * 发送消息给AI助手
   * @param content - 用户输入的消息内容
   * @returns AI回复消息
   */
  sendMessage: async (content: string): Promise<ApiResponse<ChatMessage>> => {
    const response = await apiClient.post('/chat/send', { content });
    return response.data;
  },

  /**
   * 获取对话历史记录
   * @param params - 分页参数
   * @returns 对话消息列表
   */
  getHistory: async (
    params: ChatHistoryParams
  ): Promise<ApiResponse<{ items: ChatMessage[]; total: number }>> => {
    const response = await apiClient.get('/chat/history', { params });
    return response.data;
  },
};

/**
 * 合同审查相关API
 */
export const contractApi = {
  /**
   * 上传合同文件
   * @param file - 合同文件（PDF/Word）
   * @returns 上传后的文件标识
   */
  uploadContract: async (
    file: File
  ): Promise<ApiResponse<{ fileId: string; fileName: string }>> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post('/contract/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  /**
   * 分析合同内容，返回风险审查结果
   * @param fileId - 上传后的文件标识
   * @returns 合同分析结果
   */
  analyzeContract: async (fileId: string): Promise<ApiResponse<ContractAnalysis>> => {
    const response = await apiClient.post('/contract/analyze', { fileId });
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
  submitReview: async (
    feedback: Omit<ReviewFeedback, 'id' | 'reviewedAt'>
  ): Promise<ApiResponse<ReviewFeedback>> => {
    const response = await apiClient.post('/review/submit', feedback);
    return response.data;
  },

  /**
   * 获取复核统计数据
   * @returns 复核统计信息
   */
  getStats: async (): Promise<ApiResponse<ReviewStats>> => {
    const response = await apiClient.get('/review/stats');
    return response.data;
  },
};

export default apiClient;
