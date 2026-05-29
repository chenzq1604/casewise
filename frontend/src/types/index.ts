/**
 * CaseWise 法律AI助手 - 全局类型定义
 * 包含对话、合同审查、复核统计等核心业务类型
 */

/** 风险等级枚举 */
export type RiskLevel = 'high' | 'medium' | 'low';

/** 引用类型：法条引用或判例引用 */
export type CitationType = 'law' | 'case';

/** 引用验证状态 */
export type VerifyStatus = 'verified' | 'pending' | 'unverifiable';

/** 复核结果 */
export type ReviewResult = 'accepted' | 'rejected';

/**
 * 法条/判例引用信息
 * 用于展示AI回答中引用的法律依据
 */
export interface Citation {
  /** 引用唯一标识 */
  id: string;
  /** 引用类型：法条或判例 */
  type: CitationType;
  /** 法条编号或判例案号 */
  code: string;
  /** 法条标题或判例名称 */
  title: string;
  /** 引用摘要 */
  summary: string;
  /** 法条/判例全文（展开时显示） */
  fullText?: string;
  /** 验证状态 */
  verifyStatus: VerifyStatus;
}

/**
 * 合规声明信息
 * 每条AI回答底部附带的免责/合规声明
 */
export interface ComplianceInfo {
  /** 声明文本 */
  disclaimer: string;
  /** 生成时间戳 */
  generatedAt: string;
  /** 模型版本 */
  modelVersion: string;
  /** 是否经过人工复核 */
  humanReviewed: boolean;
}

/**
 * 对话消息
 * 包含用户消息和AI回复
 */
export interface ChatMessage {
  /** 消息唯一标识 */
  id: string;
  /** 消息角色：用户或AI助手 */
  role: 'user' | 'assistant';
  /** 消息内容 */
  content: string;
  /** 发送时间 */
  timestamp: string;
  /** AI回答附带的法条/判例引用列表 */
  citations?: Citation[];
  /** 合规声明信息 */
  compliance?: ComplianceInfo;
}

/**
 * 风险条款项
 * 合同审查中发现的风险条款
 */
export interface RiskItem {
  /** 风险项唯一标识 */
  id: string;
  /** 风险等级 */
  level: RiskLevel;
  /** 风险条款在合同中的位置（段落号或行号） */
  location: string;
  /** 风险条款原文 */
  originalText: string;
  /** 风险描述 */
  description: string;
  /** 法条依据引用列表 */
  lawCitations: Citation[];
  /** 相关判例引用列表 */
  caseCitations: Citation[];
  /** 修改建议 */
  suggestion: string;
  /** 复核状态 */
  reviewResult?: ReviewResult;
}

/**
 * 合同分析结果
 * 上传合同后的完整审查结果
 */
export interface ContractAnalysis {
  /** 分析任务唯一标识 */
  id: string;
  /** 合同文件名 */
  fileName: string;
  /** 分析状态 */
  status: 'analyzing' | 'completed' | 'failed';
  /** 合同原文文本 */
  originalText: string;
  /** 风险条款列表 */
  risks: RiskItem[];
  /** 风险摘要统计 */
  riskSummary: {
    high: number;
    medium: number;
    low: number;
  };
  /** 分析完成时间 */
  analyzedAt?: string;
}

/**
 * 复核反馈
 * 人工对AI审查结果的复核意见
 */
export interface ReviewFeedback {
  /** 反馈唯一标识 */
  id: string;
  /** 关联的风险项ID */
  riskItemId: string;
  /** 关联的合同分析ID */
  contractAnalysisId: string;
  /** 复核结果 */
  result: ReviewResult;
  /** 复核人 */
  reviewer: string;
  /** 复核时间 */
  reviewedAt: string;
  /** 复核备注 */
  comment?: string;
}

/**
 * 复核统计数据
 * 用于复核统计页面的图表和指标展示
 */
export interface ReviewStats {
  /** 总审查项数 */
  totalItems: number;
  /** 已采纳数 */
  acceptedCount: number;
  /** 已拒绝（误报）数 */
  rejectedCount: number;
  /** 待复核数 */
  pendingCount: number;
  /** 采纳率（百分比） */
  acceptanceRate: number;
  /** 按风险等级统计的采纳率 */
  acceptanceByLevel: {
    high: number;
    medium: number;
    low: number;
  };
  /** 近期复核历史 */
  recentReviews: ReviewFeedback[];
}

/** 对话历史请求参数 */
export interface ChatHistoryParams {
  /** 页码 */
  page: number;
  /** 每页条数 */
  pageSize: number;
}

/** API通用响应结构 */
export interface ApiResponse<T> {
  /** 状态码 */
  code: number;
  /** 响应消息 */
  message: string;
  /** 响应数据 */
  data: T;
}
