"""
CaseWise 法律AI工具 - 报告导出API路由

提供报告导出相关的HTTP接口：
- POST /api/report/contract/{review_id}: 导出合同审查报告
- POST /api/report/chat: 导出法律问答记录
"""

import io
import json
import logging
from datetime import datetime
from typing import Optional

import aiosqlite
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.auth import get_current_user
from app.db.database import get_db
from app.models.user import UserInfo

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/report", tags=["报告导出"])


# ========== 请求模型 ==========

class ChatReportRequest(BaseModel):
    """
    法律问答报告导出请求模型

    Attributes:
        question: 用户提问
        answer: AI回答
        citations: 法条引用列表
    """
    question: str = Field(..., description="用户提问")
    answer: str = Field(..., description="AI回答")
    citations: list[dict] = Field(default_factory=list, description="法条引用列表")


# ========== HTML模板 ==========

def _build_contract_report_html(
    review_id: int,
    filename: str,
    contract_type: str,
    summary: str,
    overall_risk_level: str,
    risks: list[dict],
    analyzed_at: Optional[str],
) -> str:
    """
    生成合同审查报告HTML

    构建包含审查时间、合同信息、风险摘要、风险详情的打印友好HTML报告。

    Args:
        review_id: 审查记录ID
        filename: 合同文件名
        contract_type: 合同类型
        summary: 合同摘要
        overall_risk_level: 整体风险等级
        risks: 风险条目列表
        analyzed_at: 审查时间

    Returns:
        str: 完整的HTML字符串
    """
    high_count = sum(1 for r in risks if r.get("risk_level") == "高")
    medium_count = sum(1 for r in risks if r.get("risk_level") == "中")
    low_count = sum(1 for r in risks if r.get("risk_level") == "低")

    risk_level_color = {"高": "#dc2626", "中": "#f59e0b", "低": "#22c55e"}
    overall_color = risk_level_color.get(overall_risk_level, "#6b7280")

    review_time = analyzed_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    risk_rows = ""
    for i, risk in enumerate(risks, 1):
        level = risk.get("risk_level", "低")
        level_color = risk_level_color.get(level, "#6b7280")
        risk_rows += f"""
        <tr>
            <td style="text-align:center;">{i}</td>
            <td style="text-align:center;"><span style="color:{level_color};font-weight:bold;">{level}</span></td>
            <td>{risk.get('clause', '')}</td>
            <td>{risk.get('risk_description', '')}</td>
            <td>{risk.get('related_law', '')}</td>
            <td>{risk.get('suggestion', '')}</td>
        </tr>"""

    if not risk_rows:
        risk_rows = '<tr><td colspan="6" style="text-align:center;color:#9ca3af;">未发现风险条款</td></tr>'

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>CaseWise 合同审查报告</title>
<style>
@page {{ size: A4; margin: 20mm; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: "Microsoft YaHei", "SimSun", sans-serif; color: #1f2937; line-height: 1.6; padding: 20px; font-size: 14px; }}
.header {{ text-align: center; border-bottom: 3px solid #1e40af; padding-bottom: 16px; margin-bottom: 24px; }}
.header h1 {{ font-size: 24px; color: #1e40af; margin-bottom: 4px; }}
.header .subtitle {{ color: #6b7280; font-size: 13px; }}
.section {{ margin-bottom: 20px; }}
.section-title {{ font-size: 16px; font-weight: bold; color: #1e40af; border-left: 4px solid #1e40af; padding-left: 10px; margin-bottom: 10px; }}
.info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px 24px; background: #f9fafb; padding: 12px 16px; border-radius: 6px; }}
.info-item {{ display: flex; gap: 8px; }}
.info-label {{ color: #6b7280; white-space: nowrap; min-width: 80px; }}
.info-value {{ color: #1f2937; font-weight: 500; }}
.summary-box {{ background: #f9fafb; padding: 12px 16px; border-radius: 6px; line-height: 1.8; }}
.stats-row {{ display: flex; gap: 16px; margin-bottom: 12px; }}
.stat-card {{ flex: 1; text-align: center; padding: 12px; border-radius: 6px; color: white; }}
.stat-card.high {{ background: #dc2626; }}
.stat-card.medium {{ background: #f59e0b; }}
.stat-card.low {{ background: #22c55e; }}
.stat-card .num {{ font-size: 28px; font-weight: bold; }}
.stat-card .label {{ font-size: 12px; opacity: 0.9; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th, td {{ border: 1px solid #e5e7eb; padding: 8px 10px; text-align: left; vertical-align: top; }}
th {{ background: #1e40af; color: white; font-weight: 500; white-space: nowrap; }}
tr:nth-child(even) {{ background: #f9fafb; }}
.footer {{ margin-top: 32px; padding-top: 12px; border-top: 1px solid #e5e7eb; text-align: center; color: #9ca3af; font-size: 11px; line-height: 1.8; }}
@media print {{
    body {{ padding: 0; }}
    .stat-card {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    th {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
}}
</style>
</head>
<body>
<div class="header">
    <h1>CaseWise 合同审查报告</h1>
    <div class="subtitle">AI智能合同风险分析报告</div>
</div>

<div class="section">
    <div class="section-title">基本信息</div>
    <div class="info-grid">
        <div class="info-item"><span class="info-label">审查编号：</span><span class="info-value">{review_id}</span></div>
        <div class="info-item"><span class="info-label">审查时间：</span><span class="info-value">{review_time}</span></div>
        <div class="info-item"><span class="info-label">合同文件：</span><span class="info-value">{filename}</span></div>
        <div class="info-item"><span class="info-label">合同类型：</span><span class="info-value">{contract_type or '未指定'}</span></div>
        <div class="info-item"><span class="info-label">整体风险：</span><span class="info-value" style="color:{overall_color};font-weight:bold;">{overall_risk_level}</span></div>
    </div>
</div>

<div class="section">
    <div class="section-title">合同摘要</div>
    <div class="summary-box">{summary or '无摘要'}</div>
</div>

<div class="section">
    <div class="section-title">风险摘要统计</div>
    <div class="stats-row">
        <div class="stat-card high"><div class="num">{high_count}</div><div class="label">高风险</div></div>
        <div class="stat-card medium"><div class="num">{medium_count}</div><div class="label">中风险</div></div>
        <div class="stat-card low"><div class="num">{low_count}</div><div class="label">低风险</div></div>
    </div>
</div>

<div class="section">
    <div class="section-title">风险条款详情</div>
    <table>
        <thead>
            <tr>
                <th style="width:40px;">序号</th>
                <th style="width:60px;">等级</th>
                <th style="width:120px;">条款位置</th>
                <th>风险描述</th>
                <th style="width:140px;">法条依据</th>
                <th style="width:140px;">修改建议</th>
            </tr>
        </thead>
        <tbody>
            {risk_rows}
        </tbody>
    </table>
</div>

<div class="footer">
    <div>粤ICP备2026056746号</div>
    <div>免责声明：本报告由AI自动生成，仅供参考，不构成法律意见。如有法律问题，请咨询专业律师。</div>
</div>
</body>
</html>"""
    return html


def _build_chat_report_html(
    question: str,
    answer: str,
    citations: list[dict],
) -> str:
    """
    生成法律问答报告HTML

    构建包含咨询时间、问题、回答、法条引用的打印友好HTML报告。

    Args:
        question: 用户提问
        answer: AI回答
        citations: 法条引用列表

    Returns:
        str: 完整的HTML字符串
    """
    consult_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    citation_rows = ""
    for i, cite in enumerate(citations, 1):
        citation_rows += f"""
        <tr>
            <td style="text-align:center;">{i}</td>
            <td>{cite.get('law_name', cite.get('title', ''))}</td>
            <td>{cite.get('article', cite.get('content', ''))}</td>
        </tr>"""

    if not citation_rows:
        citation_rows = '<tr><td colspan="3" style="text-align:center;color:#9ca3af;">无引用法条</td></tr>'

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>CaseWise 法律咨询报告</title>
<style>
@page {{ size: A4; margin: 20mm; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: "Microsoft YaHei", "SimSun", sans-serif; color: #1f2937; line-height: 1.6; padding: 20px; font-size: 14px; }}
.header {{ text-align: center; border-bottom: 3px solid #1e40af; padding-bottom: 16px; margin-bottom: 24px; }}
.header h1 {{ font-size: 24px; color: #1e40af; margin-bottom: 4px; }}
.header .subtitle {{ color: #6b7280; font-size: 13px; }}
.section {{ margin-bottom: 20px; }}
.section-title {{ font-size: 16px; font-weight: bold; color: #1e40af; border-left: 4px solid #1e40af; padding-left: 10px; margin-bottom: 10px; }}
.info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px 24px; background: #f9fafb; padding: 12px 16px; border-radius: 6px; }}
.info-item {{ display: flex; gap: 8px; }}
.info-label {{ color: #6b7280; white-space: nowrap; min-width: 80px; }}
.info-value {{ color: #1f2937; font-weight: 500; }}
.content-box {{ background: #f9fafb; padding: 12px 16px; border-radius: 6px; line-height: 1.8; white-space: pre-wrap; }}
.question-box {{ background: #eff6ff; padding: 12px 16px; border-radius: 6px; line-height: 1.8; white-space: pre-wrap; border-left: 4px solid #3b82f6; }}
.answer-box {{ background: #f0fdf4; padding: 12px 16px; border-radius: 6px; line-height: 1.8; white-space: pre-wrap; border-left: 4px solid #22c55e; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th, td {{ border: 1px solid #e5e7eb; padding: 8px 10px; text-align: left; vertical-align: top; }}
th {{ background: #1e40af; color: white; font-weight: 500; white-space: nowrap; }}
tr:nth-child(even) {{ background: #f9fafb; }}
.footer {{ margin-top: 32px; padding-top: 12px; border-top: 1px solid #e5e7eb; text-align: center; color: #9ca3af; font-size: 11px; line-height: 1.8; }}
@media print {{
    body {{ padding: 0; }}
    th {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
}}
</style>
</head>
<body>
<div class="header">
    <h1>CaseWise 法律咨询报告</h1>
    <div class="subtitle">AI智能法律咨询记录</div>
</div>

<div class="section">
    <div class="section-title">基本信息</div>
    <div class="info-grid">
        <div class="info-item"><span class="info-label">咨询时间：</span><span class="info-value">{consult_time}</span></div>
    </div>
</div>

<div class="section">
    <div class="section-title">咨询问题</div>
    <div class="question-box">{question}</div>
</div>

<div class="section">
    <div class="section-title">法律解答</div>
    <div class="answer-box">{answer}</div>
</div>

<div class="section">
    <div class="section-title">法条引用</div>
    <table>
        <thead>
            <tr>
                <th style="width:40px;">序号</th>
                <th style="width:160px;">法律名称</th>
                <th>条款内容</th>
            </tr>
        </thead>
        <tbody>
            {citation_rows}
        </tbody>
    </table>
</div>

<div class="footer">
    <div>粤ICP备2026056746号</div>
    <div>免责声明：本报告由AI自动生成，仅供参考，不构成法律意见。如有法律问题，请咨询专业律师。</div>
</div>
</body>
</html>"""
    return html


# ========== 路由接口 ==========

@router.post("/contract/{review_id}", summary="导出合同审查报告")
async def export_contract_report(
    review_id: int,
    current_user: UserInfo = Depends(get_current_user),
) -> StreamingResponse:
    """
    导出合同审查报告

    根据审查记录ID从数据库读取合同审查结果，
    生成打印友好的HTML报告，浏览器可直接打印为PDF。

    Args:
        review_id: 审查记录ID
        current_user: 当前登录用户

    Returns:
        StreamingResponse: HTML文件流

    Raises:
        HTTPException: 审查记录不存在或查询失败
    """
    try:
        db = await get_db()
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT id, file_id, filename, contract_type, summary, overall_risk_level,
                      risks_json, analyzed_at, created_at
               FROM contract_reviews WHERE id = ?""",
            (review_id,),
        )
        row = await cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="审查记录不存在")

        risks = json.loads(row["risks_json"])
        html = _build_contract_report_html(
            review_id=row["id"],
            filename=row["filename"],
            contract_type=row["contract_type"],
            summary=row["summary"],
            overall_risk_level=row["overall_risk_level"],
            risks=risks,
            analyzed_at=row["analyzed_at"],
        )

        buffer = io.BytesIO(html.encode("utf-8"))

        return StreamingResponse(
            buffer,
            media_type="text/html; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="contract_report_{review_id}.html"',
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("导出合同审查报告异常: %s", str(e))
        raise HTTPException(status_code=500, detail=f"报告导出失败: {str(e)}")


@router.post("/chat", summary="导出法律问答记录")
async def export_chat_report(
    request: ChatReportRequest,
    current_user: UserInfo = Depends(get_current_user),
) -> StreamingResponse:
    """
    导出法律问答记录

    根据请求体中的问题和回答生成法律咨询HTML报告，
    浏览器可直接打印为PDF。

    Args:
        request: 问答报告请求，包含 question、answer、citations
        current_user: 当前登录用户

    Returns:
        StreamingResponse: HTML文件流

    Raises:
        HTTPException: 生成报告失败
    """
    try:
        html = _build_chat_report_html(
            question=request.question,
            answer=request.answer,
            citations=request.citations,
        )

        buffer = io.BytesIO(html.encode("utf-8"))

        return StreamingResponse(
            buffer,
            media_type="text/html; charset=utf-8",
            headers={
                "Content-Disposition": 'attachment; filename="chat_report.html"',
            },
        )

    except Exception as e:
        logger.error("导出法律问答报告异常: %s", str(e))
        raise HTTPException(status_code=500, detail=f"报告导出失败: {str(e)}")
