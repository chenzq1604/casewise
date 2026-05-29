"""
CaseWise 法律AI工具 - 法律问答API路由

提供法律问答相关的HTTP接口：
- POST /api/chat: 发送法律问题，返回AI回答和引用卡片
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from app.models.chat import ChatRequest, ChatResponse
from app.services.chat_service import get_chat_service

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api", tags=["法律问答"])


@router.post("/chat", response_model=ChatResponse, summary="法律问答")
async def chat(request: ChatRequest) -> ChatResponse:
    """
    法律问答接口

    接收用户提出的法律问题，通过 RAG 检索 + LLM 生成 + 溯源校验的完整流程，
    返回 AI 回答、法条引用卡片和合规声明。

    Args:
        request: 法律问答请求，包含 question、session_id、stream

    Returns:
        ChatResponse: 包含 answer、citations、compliance_notice 的响应

    Raises:
        HTTPException: 当服务异常时返回 500 错误
    """
    try:
        chat_service = get_chat_service()
        response = await chat_service.chat(request)
        return response
    except Exception as e:
        logger.error("法律问答接口异常: %s", str(e))
        raise HTTPException(status_code=500, detail=f"法律问答服务异常: {str(e)}")
