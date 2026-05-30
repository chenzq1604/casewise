"""
CaseWise 法律AI工具 - 合同审查数据模型

定义合同审查相关的请求、响应和数据库模型。
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ========== 请求模型 ==========

class ContractUploadResponse(BaseModel):
    """
    合同上传响应模型

    Attributes:
        file_id: 上传文件的唯一标识
        filename: 文件名
        file_size: 文件大小（字节）
        contract_text: 从文件中提取的文本内容
        upload_time: 上传时间
    """
    file_id: str = Field(
        ...,
        description="上传文件的唯一标识"
    )
    filename: str = Field(
        ...,
        description="文件名"
    )
    file_size: int = Field(
        ...,
        description="文件大小（字节）"
    )
    contract_text: str = Field(
        default="",
        description="从文件中提取的文本内容"
    )
    html_preview: str = Field(
        default="",
        description="HTML预览文件的API路径"
    )
    upload_time: datetime = Field(
        default_factory=datetime.now,
        description="上传时间"
    )


class ContractAnalyzeRequest(BaseModel):
    """
    合同分析请求模型

    Attributes:
        file_id: 已上传合同的文件ID
        contract_type: 合同类型（如：劳动合同、租赁合同等）
        focus_areas: 重点关注领域列表
    """
    file_id: str = Field(
        ...,
        description="已上传合同的文件ID"
    )
    contract_type: Optional[str] = Field(
        default=None,
        description="合同类型（如：劳动合同、租赁合同等）"
    )
    focus_areas: list[str] = Field(
        default_factory=list,
        description="重点关注领域列表"
    )


# ========== 风险条目模型 ==========

class RiskItem(BaseModel):
    """
    合同风险条目模型

    Attributes:
        clause: 涉及的合同条款
        risk_level: 风险等级（高/中/低）
        risk_description: 风险描述
        suggestion: 修改建议
        related_law: 相关法律依据
    """
    clause: str = Field(
        ...,
        description="涉及的合同条款"
    )
    risk_level: str = Field(
        ...,
        description="风险等级：高/中/低"
    )
    risk_description: str = Field(
        ...,
        description="风险描述"
    )
    suggestion: str = Field(
        default="",
        description="修改建议"
    )
    related_law: str = Field(
        default="",
        description="相关法律依据"
    )


# ========== 响应模型 ==========

class ContractAnalyzeResponse(BaseModel):
    """
    合同分析响应模型

    Attributes:
        file_id: 合同文件ID
        review_id: 审查记录ID（用于复核反馈关联）
        summary: 合同摘要
        risks: 风险条目列表
        overall_risk_level: 整体风险等级
        compliance_notice: 合规声明
        analyzed_at: 分析时间
    """
    file_id: str = Field(
        ...,
        description="合同文件ID"
    )
    review_id: int = Field(
        default=0,
        description="审查记录ID，用于复核反馈关联"
    )
    summary: str = Field(
        default="",
        description="合同摘要"
    )
    risks: list[RiskItem] = Field(
        default_factory=list,
        description="风险条目列表"
    )
    overall_risk_level: str = Field(
        default="低",
        description="整体风险等级：高/中/低"
    )
    compliance_notice: str = Field(
        default="本内容仅供参考，不构成法律意见",
        description="合规声明"
    )
    analyzed_at: datetime = Field(
        default_factory=datetime.now,
        description="分析时间"
    )


# ========== 数据库记录模型 ==========

class ContractReviewRecord(BaseModel):
    """
    合同审查记录模型（对应数据库 contract_reviews 表）

    Attributes:
        id: 记录ID
        file_id: 合同文件ID
        filename: 文件名
        contract_type: 合同类型
        summary: 合同摘要
        risks_json: 风险条目的JSON字符串
        overall_risk_level: 整体风险等级
        created_at: 创建时间
    """
    id: Optional[int] = None
    file_id: str
    filename: str = ""
    contract_type: str = ""
    summary: str = ""
    risks_json: str = "[]"
    overall_risk_level: str = "低"
    created_at: datetime = Field(default_factory=datetime.now)
