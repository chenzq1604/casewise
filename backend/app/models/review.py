"""
CaseWise 法律AI工具 - 复核反馈数据模型

定义复核反馈相关的请求、响应和数据库模型。
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ========== 请求模型 ==========

class ReviewSubmitRequest(BaseModel):
    """
    复核反馈提交请求模型

    Attributes:
        source_type: 反馈来源类型（chat/contract）
        source_id: 来源记录ID
        original_output: AI原始输出
        feedback_type: 反馈类型（corrected/confirmed/incorrect）
        corrected_content: 修正后的内容（feedback_type为corrected时必填）
        comment: 复核意见
        reviewer: 复核人
    """
    source_type: str = Field(
        ...,
        description="反馈来源类型：chat/contract"
    )
    source_id: int = Field(
        ...,
        description="来源记录ID"
    )
    original_output: str = Field(
        ...,
        description="AI原始输出"
    )
    feedback_type: str = Field(
        ...,
        description="反馈类型：corrected/confirmed/incorrect"
    )
    corrected_content: Optional[str] = Field(
        default=None,
        description="修正后的内容（feedback_type为corrected时必填）"
    )
    comment: str = Field(
        default="",
        description="复核意见"
    )
    reviewer: str = Field(
        default="",
        description="复核人"
    )


# ========== 响应模型 ==========

class ReviewSubmitResponse(BaseModel):
    """
    复核反馈提交响应模型

    Attributes:
        review_id: 反馈记录ID
        message: 提交结果消息
    """
    review_id: int = Field(
        ...,
        description="反馈记录ID"
    )
    message: str = Field(
        default="反馈提交成功",
        description="提交结果消息"
    )


class ReviewStatsResponse(BaseModel):
    """
    复核反馈统计响应模型

    Attributes:
        total_reviews: 总反馈数
        confirmed_count: 确认正确数
        corrected_count: 修正数
        incorrect_count: 标记错误数
        adoption_rate: 采纳率（确认正确的比例）
        by_source_type: 按来源类型分类的统计
    """
    total_reviews: int = Field(
        default=0,
        description="总反馈数"
    )
    confirmed_count: int = Field(
        default=0,
        description="确认正确数"
    )
    corrected_count: int = Field(
        default=0,
        description="修正数"
    )
    incorrect_count: int = Field(
        default=0,
        description="标记错误数"
    )
    adoption_rate: float = Field(
        default=0.0,
        description="采纳率（确认正确的比例）"
    )
    by_source_type: dict[str, dict] = Field(
        default_factory=dict,
        description="按来源类型分类的统计"
    )


# ========== 数据库记录模型 ==========

class ReviewFeedbackRecord(BaseModel):
    """
    复核反馈记录模型（对应数据库 review_feedback 表）

    Attributes:
        id: 记录ID
        source_type: 反馈来源类型
        source_id: 来源记录ID
        original_output: AI原始输出
        feedback_type: 反馈类型
        corrected_content: 修正后的内容
        comment: 复核意见
        reviewer: 复核人
        created_at: 创建时间
    """
    id: Optional[int] = None
    source_type: str
    source_id: int
    original_output: str
    feedback_type: str
    corrected_content: Optional[str] = None
    comment: str = ""
    reviewer: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
