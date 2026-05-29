"""
CaseWise 法律AI工具 - 法律问答API路由

提供法律问答相关的HTTP接口：
- POST /api/chat: 发送法律问题，返回AI回答和引用卡片（非流式）
- POST /api/chat/stream: 发送法律问题，通过SSE流式返回AI回答（流式）
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

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


@router.post("/chat/stream", summary="法律问答（SSE流式）")
async def chat_stream(request: ChatRequest):
    """
    法律问答流式接口（SSE）

    使用 Server-Sent Events 逐 token 返回 AI 回答，
    前端可以实时渲染，无需等待完整响应。

    SSE 事件格式：
    - event: token      — AI 生成的文本片段
    - event: citation   — 法条引用卡片
    - event: compliance — 合规声明
    - event: done       — 回答完成
    - event: error      — 错误信息

    请求体与 /api/chat 相同，响应为 text/event-stream 流。

    Args:
        request: 法律问答请求，包含 question、session_id

    Returns:
        StreamingResponse: SSE 流式响应
    """
    try:
        chat_service = get_chat_service()
        return StreamingResponse(
            chat_service.chat_stream(request),
            media_type="text/event-stream",
            headers={
                # 禁止缓存，确保SSE事件实时传输
                "Cache-Control": "no-cache",
                # 保持连接活跃，避免代理服务器超时断开
                "Connection": "keep-alive",
                # 允许前端读取自定义SSE事件类型
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as e:
        logger.error("法律问答流式接口异常: %s", str(e))
        raise HTTPException(status_code=500, detail=f"法律问答流式服务异常: {str(e)}")
