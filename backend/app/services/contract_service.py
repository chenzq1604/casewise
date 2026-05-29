"""
CaseWise 法律AI工具 - 合同审查业务逻辑模块

处理合同上传、文本提取、AI 分析、风险识别等完整业务流程。
"""

import json
import logging
import uuid
from pathlib import Path
from typing import Optional

from app.config import settings
from app.core.llm import get_llm_service
from app.core.compliance import get_compliance_service
from app.db.database import get_db
from app.models.contract import (
    ContractUploadResponse,
    ContractAnalyzeRequest,
    ContractAnalyzeResponse,
    RiskItem,
    ContractReviewRecord,
)

logger = logging.getLogger(__name__)


# 合同审查系统提示词
CONTRACT_ANALYZE_PROMPT = """你是一位专业的合同审查AI助手。你的职责是：

1. 仔细阅读合同全文，理解合同的核心条款和约定
2. 识别合同中可能存在的法律风险和不合理条款
3. 对每个风险点给出具体的风险等级（高/中/低）和修改建议
4. 引用相关法律条文作为判断依据
5. 给出合同的整体风险评估

请按以下JSON格式输出分析结果：
{
    "summary": "合同摘要",
    "risks": [
        {
            "clause": "涉及的合同条款",
            "risk_level": "高/中/低",
            "risk_description": "风险描述",
            "suggestion": "修改建议",
            "related_law": "相关法律依据"
        }
    ],
    "overall_risk_level": "高/中/低"
}

请严格按照以上格式输出，确保JSON格式正确。"""


class ContractService:
    """
    合同审查业务服务

    处理合同文件上传、文本提取、AI 分析、风险识别等完整业务流程。
    """

    def __init__(self) -> None:
        """
        初始化合同审查服务
        """
        self.llm_service = get_llm_service()
        self.compliance_service = get_compliance_service()
        logger.info("ContractService 初始化完成")

    async def upload_contract(self, filename: str, file_content: bytes) -> ContractUploadResponse:
        """
        处理合同文件上传

        将上传的合同文件保存到指定目录，返回文件ID。

        Args:
            filename: 文件名
            file_content: 文件二进制内容

        Returns:
            ContractUploadResponse: 上传响应，包含文件ID和基本信息
        """
        # 生成唯一文件ID
        file_id = str(uuid.uuid4())

        # 确保上传目录存在
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)

        # 保存文件（使用 file_id 作为文件名前缀，避免重名）
        file_ext = Path(filename).suffix
        save_path = upload_dir / f"{file_id}{file_ext}"
        save_path.write_bytes(file_content)

        logger.info("合同文件上传成功，file_id: %s, filename: %s", file_id, filename)

        return ContractUploadResponse(
            file_id=file_id,
            filename=filename,
            file_size=len(file_content),
        )

    async def extract_text(self, file_id: str) -> Optional[str]:
        """
        从上传的合同文件中提取文本内容

        使用 markitdown 库支持多种文件格式（PDF、Word、Excel等）。

        Args:
            file_id: 文件ID

        Returns:
            str: 提取的文本内容，失败时返回 None
        """
        upload_dir = Path(settings.UPLOAD_DIR)

        # 查找文件（file_id 开头的文件）
        matching_files = list(upload_dir.glob(f"{file_id}*"))
        if not matching_files:
            logger.error("未找到文件，file_id: %s", file_id)
            return None

        file_path = matching_files[0]

        try:
            from markitdown import MarkItDown
            md = MarkItDown()
            result = md.convert(str(file_path))
            text = result.text_content
            logger.info("合同文本提取成功，file_id: %s，文本长度: %d", file_id, len(text))
            return text
        except Exception as e:
            logger.error("合同文本提取失败: %s", str(e))
            return None

    async def analyze_contract(self, request: ContractAnalyzeRequest) -> ContractAnalyzeResponse:
        """
        分析合同内容

        完整流程：
        1. 提取合同文本
        2. 构建分析提示词
        3. LLM 分析合同风险
        4. 解析分析结果
        5. 附加合规声明
        6. 保存审查记录

        Args:
            request: 合同分析请求

        Returns:
            ContractAnalyzeResponse: 合同分析响应
        """
        # 1. 提取合同文本
        contract_text = await self.extract_text(request.file_id)
        if not contract_text:
            return ContractAnalyzeResponse(
                file_id=request.file_id,
                summary="合同文本提取失败，无法进行分析。",
                overall_risk_level="无法评估",
            )

        # 2. 构建分析消息
        user_message = f"请审查以下合同内容：\n\n{contract_text}"
        if request.contract_type:
            user_message = f"合同类型：{request.contract_type}\n\n{user_message}"
        if request.focus_areas:
            focus_text = "、".join(request.focus_areas)
            user_message = f"重点关注：{focus_text}\n\n{user_message}"

        messages = [
            {"role": "system", "content": CONTRACT_ANALYZE_PROMPT},
            {"role": "user", "content": user_message},
        ]

        # 3. LLM 分析
        analysis_text = await self.llm_service.chat_completion(
            messages=messages,
            temperature=0.2,  # 合同审查需要高准确性
            max_tokens=8192,
        )

        # 4. 解析分析结果
        summary, risks, overall_risk_level = self._parse_analysis_result(analysis_text)

        # 5. 附加合规声明
        compliance_notice = self.compliance_service.generate_notice(scene="contract")

        # 6. 保存审查记录
        await self._save_review_record(
            file_id=request.file_id,
            contract_type=request.contract_type or "",
            summary=summary,
            risks=risks,
            overall_risk_level=overall_risk_level,
        )

        return ContractAnalyzeResponse(
            file_id=request.file_id,
            summary=summary,
            risks=risks,
            overall_risk_level=overall_risk_level,
            compliance_notice=compliance_notice,
        )

    def _parse_analysis_result(self, analysis_text: Optional[str]) -> tuple:
        """
        解析 LLM 返回的合同分析结果

        尝试从 LLM 输出中提取 JSON 格式的分析结果，
        如果解析失败则返回默认值。

        Args:
            analysis_text: LLM 生成的分析文本

        Returns:
            tuple: (摘要, 风险列表, 整体风险等级)
        """
        if not analysis_text:
            return "分析结果为空", [], "无法评估"

        try:
            # 尝试提取 JSON 部分
            json_start = analysis_text.find("{")
            json_end = analysis_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = analysis_text[json_start:json_end]
                result = json.loads(json_str)

                summary = result.get("summary", "")
                overall_risk_level = result.get("overall_risk_level", "中")

                risks = []
                for risk_data in result.get("risks", []):
                    risks.append(RiskItem(
                        clause=risk_data.get("clause", ""),
                        risk_level=risk_data.get("risk_level", "中"),
                        risk_description=risk_data.get("risk_description", ""),
                        suggestion=risk_data.get("suggestion", ""),
                        related_law=risk_data.get("related_law", ""),
                    ))

                return summary, risks, overall_risk_level

        except json.JSONDecodeError as e:
            logger.error("合同分析结果 JSON 解析失败: %s", str(e))
        except Exception as e:
            logger.error("合同分析结果解析异常: %s", str(e))

        # 解析失败，返回原始文本作为摘要
        return analysis_text[:500], [], "无法评估"

    async def _save_review_record(
        self,
        file_id: str,
        contract_type: str,
        summary: str,
        risks: list[RiskItem],
        overall_risk_level: str,
    ) -> None:
        """
        保存合同审查记录到数据库

        Args:
            file_id: 合同文件ID
            contract_type: 合同类型
            summary: 合同摘要
            risks: 风险条目列表
            overall_risk_level: 整体风险等级
        """
        try:
            db = await get_db()
            risks_json = json.dumps(
                [r.dict() for r in risks],
                ensure_ascii=False,
            )
            await db.execute(
                """INSERT INTO contract_reviews (file_id, contract_type, summary, risks_json, overall_risk_level)
                   VALUES (?, ?, ?, ?, ?)""",
                (file_id, contract_type, summary, risks_json, overall_risk_level),
            )
            await db.commit()
            logger.debug("合同审查记录已保存，file_id: %s", file_id)
        except Exception as e:
            logger.error("保存合同审查记录失败: %s", str(e))


# 全局服务单例
_contract_service: Optional[ContractService] = None


def get_contract_service() -> ContractService:
    """
    获取合同审查服务单例

    Returns:
        ContractService: 合同审查服务实例
    """
    global _contract_service
    if _contract_service is None:
        _contract_service = ContractService()
    return _contract_service
