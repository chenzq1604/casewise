"""
CaseWise 法律AI工具 - 法律问答数据模型

定义法律问答相关的请求、响应和数据库模型。
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ========== 请求模型 ==========

class ChatRequest(BaseModel):
    """
    法律问答请求模型

    Attributes:
        question: 用户提出的法律问题
        session_id: 会话ID，用于多轮对话上下文管理
        stream: 是否使用流式响应
    """
    question: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="用户提出的法律问题"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="会话ID，用于多轮对话上下文管理"
    )
    stream: bool = Field(
        default=False,
        description="是否使用流式响应"
    )


# ========== 引用卡片模型 ==========

class CitationCard(BaseModel):
    """
    法条引用卡片模型

    Attributes:
        law_name: 法律法规名称
        article_number: 条款编号
        article_content: 条款原文摘要
        verification_status: 验证状态：已验证/待确认/无法验证
    """
    law_name: str = Field(
        ...,
        description="法律法规名称"
    )
    article_number: str = Field(
        ...,
        description="条款编号"
    )
    article_content: str = Field(
        default="",
        description="条款原文摘要"
    )
    verification_status: str = Field(
        default="待确认",
        description="验证状态：已验证/待确认/无法验证"
    )


# ========== 响应模型 ==========

class ChatResponse(BaseModel):
    """
    法律问答响应模型

    Attributes:
        answer: AI生成的法律回答
        citations: 引用的法条卡片列表
        session_id: 会话ID
        compliance_notice: 合规声明
        created_at: 创建时间
    """
    answer: str = Field(
        ...,
        description="AI生成的法律回答"
    )
    citations: list[CitationCard] = Field(
        default_factory=list,
        description="引用的法条卡片列表"
    )
    session_id: str = Field(
        ...,
        description="会话ID"
    )
    compliance_notice: str = Field(
        default="本内容仅供参考，不构成法律意见",
        description="合规声明"
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="创建时间"
    )


# ========== 数据库记录模型 ==========

class ChatHistoryRecord(BaseModel):
    """
    问答历史记录模型（对应数据库 chat_history 表）

    Attributes:
        id: 记录ID
        session_id: 会话ID
        question: 用户问题
        answer: AI回答
        citations_json: 引用卡片的JSON字符串
        created_at: 创建时间
    """
    id: Optional[int] = None
    session_id: str
    question: str
    answer: str
    citations_json: str = "[]"
    created_at: datetime = Field(default_factory=datetime.now)
