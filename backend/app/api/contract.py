"""
CaseWise 法律AI工具 - 合同审查API路由

提供合同审查相关的HTTP接口：
- POST /api/contract/upload: 上传合同文件
- POST /api/contract/analyze: 分析合同内容
- GET /api/contract/history: 获取审查历史列表
- GET /api/contract/detail/{review_id}: 获取审查详情
"""

import logging
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

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


@router.get("/history", summary="获取审查历史列表")
async def get_review_history(
    limit: int = Query(default=20, ge=1, le=100, description="返回条数"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
) -> list[dict]:
    """
    获取合同审查历史列表

    按时间倒序返回审查记录，包含文件名、风险等级、上传时间、审查时间等。

    Args:
        limit: 返回条数，默认20
        offset: 偏移量，默认0

    Returns:
        list[dict]: 审查历史记录列表
    """
    try:
        contract_service = get_contract_service()
        return await contract_service.get_review_history(limit=limit, offset=offset)
    except Exception as e:
        logger.error("获取审查历史接口异常: %s", str(e))
        raise HTTPException(status_code=500, detail=f"获取审查历史失败: {str(e)}")


@router.get("/detail/{review_id}", summary="获取审查详情")
async def get_review_detail(review_id: int) -> dict:
    """
    获取指定合同审查的详细结果

    包含合同原文、风险条目、合规声明等完整信息。

    Args:
        review_id: 审查记录ID

    Returns:
        dict: 审查详情
    """
    try:
        contract_service = get_contract_service()
        detail = await contract_service.get_review_detail(review_id)
        if not detail:
            raise HTTPException(status_code=404, detail="审查记录不存在")
        return detail
    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取审查详情接口异常: %s", str(e))
        raise HTTPException(status_code=500, detail=f"获取审查详情失败: {str(e)}")


@router.get("/preview/{file_id}", summary="预览合同HTML")
async def preview_contract_html(file_id: str) -> HTMLResponse:
    """
    返回合同的HTML预览文件

    前端通过 iframe 嵌入此接口返回的HTML，实现Word原始排版预览。
    自动将Word生成的gb2312编码转为utf-8，确保浏览器正确显示中文。

    Args:
        file_id: 合同文件ID

    Returns:
        HTMLResponse: HTML内容
    """
    from app.config import settings
    from pathlib import Path
    import re

    html_dir = Path(settings.UPLOAD_DIR) / "html_preview"
    html_file = html_dir / f"{file_id}.html"

    if not html_file.exists():
        raise HTTPException(status_code=404, detail="预览文件不存在")

    raw = html_file.read_bytes()

    for encoding in ('utf-8', 'gb2312', 'gbk', 'gb18030'):
        try:
            text = raw.decode(encoding)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    else:
        text = raw.decode('utf-8', errors='replace')

    text = re.sub(r'charset=gb2312', 'charset=utf-8', text, flags=re.IGNORECASE)
    text = re.sub(r'charset=gbk', 'charset=utf-8', text, flags=re.IGNORECASE)

    return HTMLResponse(content=text)


@router.get("/preview/{file_id}.files/{file_name:path}", summary="预览合同HTML附属资源")
async def preview_contract_html_asset(file_id: str, file_name: str) -> FileResponse:
    """
    返回合同HTML预览的附属资源文件

    Word另存为HTML时会生成附属文件夹（.files），包含主题、颜色映射等资源。
    此接口用于iframe加载HTML时引用的附属文件。

    Args:
        file_id: 合同文件ID
        file_name: 附属文件相对路径

    Returns:
        FileResponse: 资源文件
    """
    from app.config import settings
    from pathlib import Path
    import mimetypes

    html_dir = Path(settings.UPLOAD_DIR) / "html_preview"
    asset_dir = html_dir / f"{file_id}.files"
    asset_file = asset_dir / file_name

    if not asset_file.exists():
        raise HTTPException(status_code=404, detail="资源文件不存在")

    if not str(asset_file.resolve()).startswith(str(asset_dir.resolve())):
        raise HTTPException(status_code=403, detail="禁止访问")

    mime_type, _ = mimetypes.guess_type(str(asset_file))
    if not mime_type:
        mime_type = "application/octet-stream"

    return FileResponse(
        path=str(asset_file),
        media_type=mime_type,
    )
