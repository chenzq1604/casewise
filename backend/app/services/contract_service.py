"""
CaseWise 法律AI工具 - 合同审查业务逻辑模块

处理合同上传、文本提取、AI 分析、风险识别等完整业务流程。
"""

import json
import logging
import uuid
from pathlib import Path
from typing import Optional

import aiosqlite
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

        将上传的合同文件保存到指定目录，提取文本内容，返回文件ID。

        Args:
            filename: 文件名
            file_content: 文件二进制内容

        Returns:
            ContractUploadResponse: 上传响应，包含文件ID、基本信息和提取的文本
        """
        file_id = str(uuid.uuid4())

        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_ext = Path(filename).suffix
        save_path = upload_dir / f"{file_id}{file_ext}"
        save_path.write_bytes(file_content)

        logger.info("合同文件上传成功，file_id: %s, filename: %s", file_id, filename)

        contract_text = await self.extract_text(file_id)

        html_path = await self.convert_to_html(file_id)

        return ContractUploadResponse(
            file_id=file_id,
            filename=filename,
            file_size=len(file_content),
            contract_text=contract_text or "",
            html_preview=html_path or "",
        )

    async def extract_text(self, file_id: str) -> Optional[str]:
        """
        从上传的合同文件中提取文本内容

        按优先级尝试多种方式：
        1. pywin32 COM（Windows + Word安装时，完美支持.doc/.docx）
        2. MarkItDown（支持.docx/.pdf/.xlsx等）
        3. olefile（.doc格式回退提取）
        4. mammoth（.docx格式回退提取）

        Args:
            file_id: 文件ID

        Returns:
            str: 提取的文本内容，失败时返回 None
        """
        upload_dir = Path(settings.UPLOAD_DIR)

        matching_files = list(upload_dir.glob(f"{file_id}*"))
        if not matching_files:
            logger.error("未找到文件，file_id: %s", file_id)
            return None

        file_path = matching_files[0]
        file_ext = file_path.suffix.lower()

        # 尝试方式1: pywin32 COM（Windows上最可靠的方式）
        if file_ext in ('.doc', '.docx', '.rtf'):
            try:
                text = self._extract_with_pywin32(file_path)
                if text and text.strip():
                    logger.info("合同文本提取成功（pywin32），file_id: %s，文本长度: %d", file_id, len(text))
                    return text
            except Exception as e:
                logger.warning("pywin32 提取失败: %s，尝试其他方式", str(e))

        # 尝试方式2: MarkItDown
        try:
            from markitdown import MarkItDown
            md = MarkItDown()
            result = md.convert(str(file_path))
            text = result.text_content
            if text and text.strip():
                logger.info("合同文本提取成功（MarkItDown），file_id: %s，文本长度: %d", file_id, len(text))
                return text
        except Exception as e:
            logger.warning("MarkItDown 提取失败: %s，尝试其他方式", str(e))

        # 尝试方式3: olefile（.doc格式回退）
        if file_ext == '.doc':
            try:
                text = self._extract_doc_with_olefile(file_path)
                if text and text.strip():
                    logger.info("合同文本提取成功（olefile），file_id: %s，文本长度: %d", file_id, len(text))
                    return text
            except Exception as e:
                logger.warning("olefile 提取 .doc 失败: %s", str(e))

        # 尝试方式4: mammoth（.docx格式回退）
        if file_ext == '.docx':
            try:
                text = self._extract_docx_with_mammoth(file_path)
                if text and text.strip():
                    logger.info("合同文本提取成功（mammoth），file_id: %s，文本长度: %d", file_id, len(text))
                    return text
            except Exception as e:
                logger.warning("mammoth 提取 .docx 失败: %s", str(e))

        logger.error("所有文本提取方式均失败，file_id: %s，文件格式: %s", file_id, file_ext)
        return None

    def _extract_with_pywin32(self, file_path: Path) -> Optional[str]:
        """
        使用 pywin32 COM 接口通过 Microsoft Word 提取文本

        此方法需要 Windows 系统且安装了 Microsoft Word。
        通过 COM 自动化打开 Word，直接读取 Content.Text 属性获取文本。

        Args:
            file_path: 文件路径

        Returns:
            str: 提取的文本，失败返回 None
        """
        import sys
        import os

        pywin32_system32 = os.path.join(
            os.path.dirname(sys.executable), 'Lib', 'site-packages', 'pywin32_system32'
        )
        if os.path.isdir(pywin32_system32) and pywin32_system32 not in os.environ.get('PATH', ''):
            os.environ['PATH'] = pywin32_system32 + os.pathsep + os.environ.get('PATH', '')

        import win32com.client
        import pythoncom

        pythoncom.CoInitialize()
        word = None
        doc = None

        try:
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            word.DisplayAlerts = False

            abs_path = str(file_path.resolve())
            doc = word.Documents.Open(abs_path, ReadOnly=True)

            text = doc.Content.Text

            if text:
                text = text.strip()

            return text
        finally:
            if doc:
                try:
                    doc.Close(False)
                except Exception:
                    pass
            if word:
                try:
                    word.Quit(False)
                except Exception:
                    pass
            pythoncom.CoUninitialize()

    async def convert_to_html(self, file_id: str) -> Optional[str]:
        """
        将合同文档转换为HTML格式用于前端预览

        使用 pywin32 COM 调用 Word 另存为 HTML，
        保持原始排版和样式，前端通过 iframe 嵌入显示。

        Args:
            file_id: 文件ID

        Returns:
            str: HTML文件的相对路径（如 /api/contract/preview/{file_id}），失败返回 None
        """
        upload_dir = Path(settings.UPLOAD_DIR)
        matching_files = list(upload_dir.glob(f"{file_id}*"))
        if not matching_files:
            return None

        file_path = matching_files[0]
        file_ext = file_path.suffix.lower()

        if file_ext not in ('.doc', '.docx', '.rtf'):
            return None

        import sys
        import os

        pywin32_system32 = os.path.join(
            os.path.dirname(sys.executable), 'Lib', 'site-packages', 'pywin32_system32'
        )
        if os.path.isdir(pywin32_system32) and pywin32_system32 not in os.environ.get('PATH', ''):
            os.environ['PATH'] = pywin32_system32 + os.pathsep + os.environ.get('PATH', '')

        import win32com.client
        import pythoncom

        pythoncom.CoInitialize()
        word = None
        doc = None

        try:
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            word.DisplayAlerts = False

            abs_path = str(file_path.resolve())
            doc = word.Documents.Open(abs_path, ReadOnly=True)

            html_dir = upload_dir / "html_preview"
            html_dir.mkdir(parents=True, exist_ok=True)
            html_path = html_dir / f"{file_id}.html"

            wdFormatHTML = 8
            doc.SaveAs2(str(html_path.resolve()), FileFormat=wdFormatHTML)

            self._fix_html_encoding(html_path)

            logger.info("合同文档转HTML成功，file_id: %s", file_id)
            return f"/api/contract/preview/{file_id}"
        except Exception as e:
            logger.warning("合同文档转HTML失败: %s", str(e))
            return None
        finally:
            if doc:
                try:
                    doc.Close(False)
                except Exception:
                    pass
            if word:
                try:
                    word.Quit(False)
                except Exception:
                    pass
            pythoncom.CoUninitialize()

    def _fix_html_encoding(self, html_path: Path) -> None:
        """
        修复Word生成HTML的编码问题

        Word SaveAs2 HTML默认使用gb2312编码，浏览器可能无法正确解析。
        此方法将HTML文件从gb2312转为utf-8编码，并更新meta charset声明。

        Args:
            html_path: HTML文件路径
        """
        import re

        try:
            raw = html_path.read_bytes()

            for encoding in ('gb2312', 'gbk', 'gb18030'):
                try:
                    text = raw.decode(encoding)
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            else:
                text = raw.decode('utf-8', errors='replace')

            text = re.sub(
                r'charset=gb2312',
                'charset=utf-8',
                text,
                flags=re.IGNORECASE
            )
            text = re.sub(
                r'charset=gbk',
                'charset=utf-8',
                text,
                flags=re.IGNORECASE
            )

            html_path.write_text(text, encoding='utf-8')
            logger.debug("HTML编码修复完成: %s", html_path.name)
        except Exception as e:
            logger.warning("HTML编码修复失败: %s，使用原始编码", str(e))

    def _extract_doc_with_olefile(self, file_path: Path) -> Optional[str]:
        """
        使用 olefile 从 .doc 文件中提取文本

        .doc 是 OLE 复合文档格式，文本存储在 WordDocument 流中。
        此方法尝试提取 1Table 或 0Table 流中的文本片段。

        Args:
            file_path: 文件路径

        Returns:
            str: 提取的文本，失败返回 None
        """
        import olefile
        import re

        ole = olefile.OleFileIO(str(file_path))
        text_parts = []

        for stream_name in ole.listdir():
            stream_path = '/'.join(stream_name)
            if 'word' in stream_path.lower() or 'table' in stream_path.lower():
                try:
                    data = ole.openstream(stream_name).read()
                    decoded = data.decode('utf-8', errors='ignore')
                    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', decoded)
                    if len(cleaned.strip()) > 20:
                        text_parts.append(cleaned.strip())
                except Exception:
                    continue

        ole.close()

        if text_parts:
            return '\n'.join(text_parts)
        return None

    def _is_poor_quality_text(self, text: str) -> bool:
        """
        检测文本质量是否不佳（如 olefile 提取的 .doc 文本包含大量乱码）

        Args:
            text: 待检测的文本

        Returns:
            bool: 文本质量不佳返回 True
        """
        if not text:
            return False
        total_chars = len(text)
        if total_chars == 0:
            return False
        garbage_chars = sum(1 for c in text if ord(c) < 32 and c not in '\n\r\t')
        garbage_ratio = garbage_chars / total_chars
        # 如果乱码字符占比超过 5%，认为文本质量不佳
        return garbage_ratio > 0.05

    async def _clean_text_with_llm(self, text: str) -> str:
        """
        使用大模型整理质量不佳的文本

        当 olefile 等方式提取的文本包含大量乱码时，
        让大模型先整理文本，去除无关字符，恢复可读内容。

        Args:
            text: 质量不佳的原始文本

        Returns:
            str: 整理后的文本
        """
        clean_prompt = """你是一位文本整理助手。以下文本是从文档中提取的，但包含大量乱码和无用字符。
请仔细阅读，去除所有乱码和无用字符，只保留有意义的合同文本内容。
如果某些部分完全无法辨认，请用 [无法辨认] 标记。直接输出整理后的文本，不要添加任何解释。"""

        messages = [
            {"role": "system", "content": clean_prompt},
            {"role": "user", "content": text},
        ]

        try:
            cleaned_text = await self.llm_service.chat_completion(
                messages=messages,
                temperature=0.1,
                max_tokens=8192,
            )
            if cleaned_text and len(cleaned_text.strip()) > 50:
                logger.info("大模型文本整理完成，原始长度: %d，整理后长度: %d", len(text), len(cleaned_text))
                return cleaned_text
            return text
        except Exception as e:
            logger.warning("大模型文本整理失败: %s，使用原始文本", str(e))
            return text

    def _extract_docx_with_mammoth(self, file_path: Path) -> Optional[str]:
        """
        使用 mammoth 从 .docx 文件中提取文本

        Args:
            file_path: 文件路径

        Returns:
            str: 提取的文本，失败返回 None
        """
        import mammoth

        with open(str(file_path), 'rb') as f:
            result = mammoth.extract_raw_text(f)
            return result.value

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
            raise ValueError(f"合同文本提取失败，文件格式可能不受支持（file_id: {request.file_id}）。建议上传 .docx 或 .pdf 格式。")

        # 1.5 当文本质量不佳时（如 olefile 提取的 .doc 文本），先让大模型整理文本
        if self._is_poor_quality_text(contract_text):
            logger.info("检测到文本质量不佳，先让大模型整理文本，file_id: %s", request.file_id)
            contract_text = await self._clean_text_with_llm(contract_text)

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
        review_id = await self._save_review_record(
            file_id=request.file_id,
            filename=request.file_id,
            contract_type=request.contract_type or "",
            summary=summary,
            risks=risks,
            overall_risk_level=overall_risk_level,
            contract_text=contract_text,
        )

        return ContractAnalyzeResponse(
            file_id=request.file_id,
            review_id=review_id,
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
        filename: str,
        contract_type: str,
        summary: str,
        risks: list[RiskItem],
        overall_risk_level: str,
        contract_text: str = "",
    ) -> int:
        """
        保存合同审查记录到数据库

        Args:
            file_id: 合同文件ID
            filename: 文件名
            contract_type: 合同类型
            summary: 合同摘要
            risks: 风险条目列表
            overall_risk_level: 整体风险等级
            contract_text: 合同原文

        Returns:
            int: 审查记录ID，失败返回0
        """
        try:
            db = await get_db()
            risks_json = json.dumps(
                [r.dict() for r in risks],
                ensure_ascii=False,
            )
            cursor = await db.execute(
                """INSERT INTO contract_reviews (file_id, filename, contract_type, summary, risks_json, overall_risk_level, contract_text, analyzed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                (file_id, filename, contract_type, summary, risks_json, overall_risk_level, contract_text),
            )
            await db.commit()
            review_id = cursor.lastrowid
            logger.debug("合同审查记录已保存，review_id: %d，file_id: %s", review_id, file_id)
            return review_id
        except Exception as e:
            logger.error("保存合同审查记录失败: %s", str(e))
            return 0

    async def get_review_history(self, limit: int = 20, offset: int = 0) -> list[dict]:
        """
        获取合同审查历史列表

        Args:
            limit: 返回条数
            offset: 偏移量

        Returns:
            list[dict]: 审查历史记录列表
        """
        try:
            db = await get_db()
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT id, file_id, filename, contract_type, summary, overall_risk_level,
                          risks_json, created_at, analyzed_at
                   FROM contract_reviews
                   ORDER BY created_at DESC
                   LIMIT ? OFFSET ?""",
                (limit, offset),
            )
            rows = await cursor.fetchall()
            result = []
            for row in rows:
                result.append({
                    "id": row["id"],
                    "file_id": row["file_id"],
                    "filename": row["filename"],
                    "contract_type": row["contract_type"],
                    "summary": row["summary"],
                    "overall_risk_level": row["overall_risk_level"],
                    "risk_count": len(json.loads(row["risks_json"])),
                    "created_at": row["created_at"],
                    "analyzed_at": row["analyzed_at"],
                })
            return result
        except Exception as e:
            logger.error("获取审查历史失败: %s", str(e))
            return []

    async def get_review_detail(self, review_id: int) -> Optional[dict]:
        """
        获取合同审查详情

        Args:
            review_id: 审查记录ID

        Returns:
            Optional[dict]: 审查详情，不存在返回None
        """
        try:
            db = await get_db()
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT id, file_id, filename, contract_type, summary, overall_risk_level,
                          risks_json, contract_text, created_at, analyzed_at
                   FROM contract_reviews WHERE id = ?""",
                (review_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return None
            risks = json.loads(row["risks_json"])
            html_preview = ""
            html_dir = Path(settings.UPLOAD_DIR) / "html_preview"
            html_file = html_dir / f"{row['file_id']}.html"
            if html_file.exists():
                html_preview = f"/api/contract/preview/{row['file_id']}"
            return {
                "id": row["id"],
                "file_id": row["file_id"],
                "filename": row["filename"],
                "contract_type": row["contract_type"],
                "summary": row["summary"],
                "overall_risk_level": row["overall_risk_level"],
                "risks": risks,
                "contract_text": row["contract_text"],
                "html_preview": html_preview,
                "compliance_notice": "本内容仅供参考，不构成法律意见。如有法律问题，请咨询专业律师。",
                "analyzed_at": row["analyzed_at"],
                "created_at": row["created_at"],
            }
        except Exception as e:
            logger.error("获取审查详情失败: %s", str(e))
            return None


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
