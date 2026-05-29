"""
CaseWise 法律AI工具 - 复核反馈API路由

提供复核反馈相关的HTTP接口：
- POST /api/review: 提交复核反馈
- GET /api/review/stats: 获取采纳率统计
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.review import ReviewSubmitRequest, ReviewSubmitResponse, ReviewStatsResponse
from app.services.review_service import get_review_service

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/review", tags=["复核反馈"])


@router.post("", response_model=ReviewSubmitResponse, summary="提交复核反馈")
async def submit_review(request: ReviewSubmitRequest) -> ReviewSubmitResponse:
    """
    复核反馈提交接口

    接收人工复核结果，记录对 AI 输出的评价（确认正确/修正/标记错误），
    用于追踪 AI 输出质量和持续改进。

    Args:
        request: 复核反馈请求，包含 source_type、source_id、feedback_type 等

    Returns:
        ReviewSubmitResponse: 包含 review_id 和提交结果消息

    Raises:
        HTTPException: 当提交失败时返回错误
    """
    try:
        # 参数校验
        if request.feedback_type not in ("corrected", "confirmed", "incorrect"):
            raise HTTPException(
                status_code=400,
                detail="feedback_type 必须为 corrected/confirmed/incorrect",
            )

        if request.source_type not in ("chat", "contract"):
            raise HTTPException(
                status_code=400,
                detail="source_type 必须为 chat/contract",
            )

        if request.feedback_type == "corrected" and not request.corrected_content:
            raise HTTPException(
                status_code=400,
                detail="feedback_type 为 corrected 时必须提供 corrected_content",
            )

        review_service = get_review_service()
        response = await review_service.submit_review(request)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("复核反馈提交接口异常: %s", str(e))
        raise HTTPException(status_code=500, detail=f"复核反馈服务异常: {str(e)}")


@router.get("/stats", response_model=ReviewStatsResponse, summary="获取采纳率统计")
async def get_review_stats() -> ReviewStatsResponse:
    """
    复核反馈统计接口

    返回复核反馈的汇总统计信息，包括总数、各类型数量、采纳率，
    以及按来源类型（chat/contract）分类的统计。

    Returns:
        ReviewStatsResponse: 包含 total_reviews、adoption_rate、by_source_type 的统计响应

    Raises:
        HTTPException: 当查询失败时返回错误
    """
    try:
        review_service = get_review_service()
        response = await review_service.get_stats()
        return response
    except Exception as e:
        logger.error("复核统计接口异常: %s", str(e))
        raise HTTPException(status_code=500, detail=f"复核统计服务异常: {str(e)}")
