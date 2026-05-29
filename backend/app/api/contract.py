"""
CaseWise 法律AI工具 - 合同审查API路由

提供合同审查相关的HTTP接口：
- POST /api/contract/upload: 上传合同文件
- POST /api/contract/analyze: 分析合同内容
"""

import logging
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.contract import (
    ContractUploadResponse,
    ContractAnalyzeRequest,
    ContractAnalyzeResponse,
)
from app.services.contract_service import get_contract_service

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/contract", tags=["合同审查"])


@router.post("/upload", response_model=ContractUploadResponse, summary="上传合同文件")
async def upload_contract(file: UploadFile = File(..., description="合同文件（支持 PDF、Word、Excel 等格式）")) -> ContractUploadResponse:
    """
    合同文件上传接口

    接收用户上传的合同文件，保存到服务器并返回文件ID，
    后续可使用该文件ID进行合同分析。

    Args:
        file: 上传的合同文件，支持 PDF、Word、Excel 等格式

    Returns:
        ContractUploadResponse: 包含 file_id、filename、file_size 的响应

    Raises:
        HTTPException: 当文件为空或上传失败时返回错误
    """
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")

        # 读取文件内容
        file_content = await file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="文件内容为空")

        # 限制文件大小（10MB）
        max_size = 10 * 1024 * 1024
        if len(file_content) > max_size:
            raise HTTPException(status_code=400, detail="文件大小超过10MB限制")

        contract_service = get_contract_service()
        response = await contract_service.upload_contract(file.filename, file_content)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("合同上传接口异常: %s", str(e))
        raise HTTPException(status_code=500, detail=f"合同上传服务异常: {str(e)}")


@router.post("/analyze", response_model=ContractAnalyzeResponse, summary="分析合同内容")
async def analyze_contract(request: ContractAnalyzeRequest) -> ContractAnalyzeResponse:
    """
    合同分析接口

    对已上传的合同文件进行 AI 分析，识别合同中的法律风险和不合理条款，
    返回风险条目列表和整体风险评估。

    Args:
        request: 合同分析请求，包含 file_id、contract_type、focus_areas

    Returns:
        ContractAnalyzeResponse: 包含 summary、risks、overall_risk_level 的响应

    Raises:
        HTTPException: 当文件不存在或分析失败时返回错误
    """
    try:
        contract_service = get_contract_service()
        response = await contract_service.analyze_contract(request)

        if response.overall_risk_level == "无法评估":
            logger.warning("合同分析结果为无法评估，file_id: %s", request.file_id)

        return response

    except Exception as e:
        logger.error("合同分析接口异常: %s", str(e))
        raise HTTPException(status_code=500, detail=f"合同分析服务异常: {str(e)}")
