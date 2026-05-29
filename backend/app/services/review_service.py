"""
CaseWise 法律AI工具 - 复核反馈业务逻辑模块

处理复核反馈的提交、统计和查询等业务逻辑，
支持对 AI 输出的人工复核和质量追踪。
"""

import logging
from typing import Optional

from app.db.database import get_db
from app.models.review import (
    ReviewSubmitRequest,
    ReviewSubmitResponse,
    ReviewStatsResponse,
    ReviewFeedbackRecord,
)

logger = logging.getLogger(__name__)


class ReviewService:
    """
    复核反馈业务服务

    处理复核反馈的提交、统计和查询，
    支持对 AI 输出的人工复核和质量追踪。
    """

    def __init__(self) -> None:
        """
        初始化复核反馈服务
        """
        logger.info("ReviewService 初始化完成")

    async def submit_review(self, request: ReviewSubmitRequest) -> ReviewSubmitResponse:
        """
        提交复核反馈

        将人工复核结果保存到数据库，用于追踪 AI 输出质量。

        Args:
            request: 复核反馈提交请求

        Returns:
            ReviewSubmitResponse: 提交响应，包含反馈记录ID
        """
        try:
            db = await get_db()
            cursor = await db.execute(
                """INSERT INTO review_feedback
                   (source_type, source_id, original_output, feedback_type, corrected_content, comment, reviewer)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    request.source_type,
                    request.source_id,
                    request.original_output,
                    request.feedback_type,
                    request.corrected_content,
                    request.comment,
                    request.reviewer,
                ),
            )
            await db.commit()
            review_id = cursor.lastrowid

            logger.info(
                "复核反馈提交成功，review_id: %d，来源: %s/%d，类型: %s",
                review_id,
                request.source_type,
                request.source_id,
                request.feedback_type,
            )

            return ReviewSubmitResponse(
                review_id=review_id,
                message="反馈提交成功",
            )

        except Exception as e:
            logger.error("提交复核反馈失败: %s", str(e))
            return ReviewSubmitResponse(
                review_id=-1,
                message=f"反馈提交失败: {str(e)}",
            )

    async def get_stats(self) -> ReviewStatsResponse:
        """
        获取复核反馈统计信息

        统计各类型反馈的数量和采纳率，
        支持按来源类型（chat/contract）分类统计。

        Returns:
            ReviewStatsResponse: 统计响应，包含总数、分类数和采纳率
        """
        try:
            db = await get_db()

            # 总体统计
            cursor = await db.execute(
                """SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN feedback_type = 'confirmed' THEN 1 ELSE 0 END) as confirmed,
                    SUM(CASE WHEN feedback_type = 'corrected' THEN 1 ELSE 0 END) as corrected,
                    SUM(CASE WHEN feedback_type = 'incorrect' THEN 1 ELSE 0 END) as incorrect
                FROM review_feedback"""
            )
            row = await cursor.fetchone()

            total = row[0] if row else 0
            confirmed = row[1] if row else 0
            corrected = row[2] if row else 0
            incorrect = row[3] if row else 0

            # 计算采纳率
            adoption_rate = (confirmed / total * 100) if total > 0 else 0.0

            # 按来源类型分类统计
            cursor = await db.execute(
                """SELECT source_type,
                    COUNT(*) as total,
                    SUM(CASE WHEN feedback_type = 'confirmed' THEN 1 ELSE 0 END) as confirmed,
                    SUM(CASE WHEN feedback_type = 'corrected' THEN 1 ELSE 0 END) as corrected,
                    SUM(CASE WHEN feedback_type = 'incorrect' THEN 1 ELSE 0 END) as incorrect
                FROM review_feedback
                GROUP BY source_type"""
            )
            rows = await cursor.fetchall()

            by_source_type = {}
            for row in rows:
                source_type = row[0]
                src_total = row[1]
                src_confirmed = row[2]
                src_corrected = row[3]
                src_incorrect = row[4]
                src_adoption_rate = (src_confirmed / src_total * 100) if src_total > 0 else 0.0

                by_source_type[source_type] = {
                    "total": src_total,
                    "confirmed": src_confirmed,
                    "corrected": src_corrected,
                    "incorrect": src_incorrect,
                    "adoption_rate": round(src_adoption_rate, 2),
                }

            return ReviewStatsResponse(
                total_reviews=total,
                confirmed_count=confirmed,
                corrected_count=corrected,
                incorrect_count=incorrect,
                adoption_rate=round(adoption_rate, 2),
                by_source_type=by_source_type,
            )

        except Exception as e:
            logger.error("获取复核统计失败: %s", str(e))
            return ReviewStatsResponse()

    async def get_reviews_by_source(
        self,
        source_type: str,
        source_id: int,
    ) -> list[ReviewFeedbackRecord]:
        """
        根据来源查询复核反馈记录

        Args:
            source_type: 来源类型（chat/contract）
            source_id: 来源记录ID

        Returns:
            list[ReviewFeedbackRecord]: 复核反馈记录列表
        """
        try:
            db = await get_db()
            cursor = await db.execute(
                """SELECT id, source_type, source_id, original_output, feedback_type,
                          corrected_content, comment, reviewer, created_at
                   FROM review_feedback
                   WHERE source_type = ? AND source_id = ?
                   ORDER BY created_at DESC""",
                (source_type, source_id),
            )
            rows = await cursor.fetchall()

            records = []
            for row in rows:
                records.append(ReviewFeedbackRecord(
                    id=row[0],
                    source_type=row[1],
                    source_id=row[2],
                    original_output=row[3],
                    feedback_type=row[4],
                    corrected_content=row[5],
                    comment=row[6] or "",
                    reviewer=row[7] or "",
                    created_at=row[8],
                ))

            return records

        except Exception as e:
            logger.error("查询复核反馈失败: %s", str(e))
            return []


# 全局服务单例
_review_service: Optional[ReviewService] = None


def get_review_service() -> ReviewService:
    """
    获取复核反馈服务单例

    Returns:
        ReviewService: 复核反馈服务实例
    """
    global _review_service
    if _review_service is None:
        _review_service = ReviewService()
    return _review_service
