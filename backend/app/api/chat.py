"""
CaseWise 法律AI工具 - 法律问答API路由

提供法律问答相关的HTTP接口：
- POST /api/chat: 发送法律问题，返回AI回答和引用卡片（非流式）
- POST /api/chat/stream: 发送法律问题，通过SSE流式返回AI回答（流式）
- GET /api/chat/history: 获取对话历史记录
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse

from app.models.user import UserInfo
from app.api.auth import get_current_user
from app.models.chat import ChatRequest, ChatResponse
from app.services.chat_service import get_chat_service
from app.db.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["法律问答"])


@router.post("/chat", response_model=ChatResponse, summary="法律问答")
async def chat(
    request: ChatRequest,
    current_user: UserInfo = Depends(get_current_user),
) -> ChatResponse:
    """
    法律问答接口

    接收用户提出的法律问题，通过 RAG 检索 + LLM 生成 + 溯源校验的完整流程，
    返回 AI 回答、法条引用卡片和合规声明。

    Args:
        request: 法律问答请求，包含 question、session_id、stream
        current_user: 当前登录用户

    Returns:
        ChatResponse: 包含 answer、citations、compliance_notice 的响应

    Raises:
        HTTPException: 当服务异常时返回 500 错误
    """
    try:
        chat_service = get_chat_service()
        response = await chat_service.chat(request)

        if request.session_id and response.session_id:
            try:
                await _save_chat_history(
                    session_id=response.session_id,
                    question=request.question,
                    answer=response.answer,
                    citations=[
                        {
                            "law_name": c.law_name,
                            "article_number": c.article_number,
                            "article_content": c.article_content,
                        }
                        for c in (response.citations or [])
                    ],
                )
            except Exception as save_err:
                logger.warning("保存对话历史失败: %s", str(save_err))

        return response
    except Exception as e:
        logger.error("法律问答接口异常: %s", str(e))
        raise HTTPException(status_code=500, detail=f"法律问答服务异常: {str(e)}")


@router.post("/chat/stream", summary="法律问答（SSE流式）")
async def chat_stream(
    request: ChatRequest,
    current_user: UserInfo = Depends(get_current_user),
):
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

    Args:
        request: 法律问答请求，包含 question、session_id
        current_user: 当前登录用户

    Returns:
        StreamingResponse: SSE 流式响应
    """
    try:
        chat_service = get_chat_service()
        return StreamingResponse(
            chat_service.chat_stream(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as e:
        logger.error("法律问答流式接口异常: %s", str(e))
        raise HTTPException(status_code=500, detail=f"法律问答流式服务异常: {str(e)}")


@router.get("/chat/history", summary="获取对话历史记录")
async def get_chat_history(
    session_id: Optional[str] = Query(default=None, description="会话ID，不传则返回最近的会话列表"),
    limit: int = Query(default=50, ge=1, le=200, description="返回条数"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    current_user: UserInfo = Depends(get_current_user),
) -> dict:
    """
    获取对话历史记录

    如果提供 session_id，返回该会话的所有问答记录；
    否则返回最近的会话列表（每个会话只返回最后一条记录）。

    Args:
        session_id: 会话ID（可选）
        limit: 返回条数
        offset: 偏移量
        current_user: 当前登录用户

    Returns:
        dict: 对话历史记录
    """
    try:
        db = await get_db()
        db.row_factory = __import__('aiosqlite').Row

        if session_id:
            cursor = await db.execute(
                """SELECT id, session_id, question, answer, citations_json, created_at
                   FROM chat_history
                   WHERE session_id = ?
                   ORDER BY id ASC
                   LIMIT ? OFFSET ?""",
                (session_id, limit, offset),
            )
        else:
            cursor = await db.execute(
                """SELECT id, session_id, question, answer, citations_json, created_at
                   FROM chat_history
                   ORDER BY id DESC
                   LIMIT ? OFFSET ?""",
                (limit, offset),
            )

        rows = await cursor.fetchall()
        records = []
        for row in rows:
            citations = []
            try:
                citations = json.loads(row["citations_json"])
            except (json.JSONDecodeError, TypeError):
                pass
            records.append({
                "id": row["id"],
                "session_id": row["session_id"],
                "question": row["question"],
                "answer": row["answer"],
                "citations": citations,
                "created_at": row["created_at"],
            })

        if session_id:
            return {"session_id": session_id, "records": records}
        else:
            sessions = {}
            for r in records:
                sid = r["session_id"]
                if sid not in sessions:
                    sessions[sid] = {
                        "session_id": sid,
                        "last_question": r["question"],
                        "last_created_at": r["created_at"],
                        "record_count": 1,
                    }
                else:
                    sessions[sid]["record_count"] += 1
            return {"sessions": list(sessions.values())}

    except Exception as e:
        logger.error("获取对话历史异常: %s", str(e))
        raise HTTPException(status_code=500, detail=f"获取对话历史失败: {str(e)}")


async def _save_chat_history(
    session_id: str,
    question: str,
    answer: str,
    citations: list[dict],
) -> None:
    """
    保存对话历史到数据库

    Args:
        session_id: 会话ID
        question: 用户提问
        answer: AI回答
        citations: 法条引用列表
    """
    db = await get_db()
    citations_json = json.dumps(citations, ensure_ascii=False)
    await db.execute(
        """INSERT INTO chat_history (session_id, question, answer, citations_json)
           VALUES (?, ?, ?, ?)""",
        (session_id, question, answer, citations_json),
    )
    await db.commit()
