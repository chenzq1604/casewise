"""
CaseWise 法律AI工具 - 溯源校验层模块

验证 LLM 输出的法条引用是否在法条库中真实存在，
返回验证结果（已验证/待确认/无法验证），
确保 AI 回答中的法律依据可追溯、可验证。
"""

import logging
import re
from typing import Optional

from app.core.rag import get_hybrid_rag

logger = logging.getLogger(__name__)


class CitationVerifier:
    """
    法条引用溯源校验器

    从 AI 回答中提取法条引用，在法条库中进行验证，
    确保引用的法律条文真实存在且内容准确。
    """

    # 法条引用的正则模式
    # 匹配格式如：《中华人民共和国民法典》第一千二百三十四条
    CITATION_PATTERNS = [
        # 《法律名称》第X条
        re.compile(r"《([^》]+)》第([一二三四五六七八九十百千万零\d]+)条"),
        # 《法律名称》第X条第X款
        re.compile(r"《([^》]+)》第([一二三四五六七八九十百千万零\d]+)条第([一二三四五六七八九十百千万零\d]+)款"),
        # 《法律名称》第X章第X条
        re.compile(r"《([^》]+)》第([一二三四五六七八九十百千万零\d]+)章第([一二三四五六七八九十百千万零\d]+)条"),
    ]

    def __init__(self) -> None:
        """
        初始化法条引用校验器
        """
        logger.info("CitationVerifier 初始化完成")

    def extract_citations(self, text: str) -> list[dict]:
        """
        从文本中提取法条引用

        使用正则表达式匹配常见的法条引用格式，
        提取法律名称和条款编号。

        Args:
            text: 需要提取法条引用的文本

        Returns:
            list[dict]: 提取到的法条引用列表，每项包含 law_name 和 article_number
        """
        citations = []
        seen = set()  # 去重

        for pattern in self.CITATION_PATTERNS:
            matches = pattern.findall(text)
            for match in matches:
                law_name = match[0]
                article_number = f"第{match[1]}条"
                if len(match) > 2:
                    # 有更细粒度的条款信息
                    pass

                citation_key = f"{law_name}_{article_number}"
                if citation_key not in seen:
                    seen.add(citation_key)
                    citations.append({
                        "law_name": law_name,
                        "article_number": article_number,
                    })

        logger.debug("从文本中提取到 %d 条法条引用", len(citations))
        return citations

    async def verify_citation(self, law_name: str, article_number: str) -> dict:
        """
        验证单条法条引用的真实性

        在法条库中检索指定法律和条款，判断引用是否真实存在。

        Args:
            law_name: 法律法规名称
            article_number: 条款编号

        Returns:
            dict: 验证结果，包含 status、confidence、matched_text
        """
        hybrid_rag = get_hybrid_rag()
        verify_query = f"{law_name} {article_number}"

        try:
            results = await hybrid_rag.search(verify_query, top_k=3)

            if not results:
                return {
                    "status": "无法验证",
                    "confidence": 0.0,
                    "matched_text": "",
                    "message": "法条库中未找到相关记录",
                }

            best_match = results[0]
            score = best_match.get("score", 0)

            if score > 0.7:
                return {
                    "status": "已验证",
                    "confidence": score,
                    "matched_text": best_match.get("text", ""),
                    "message": "法条引用已在法条库中验证通过",
                }
            elif score > 0.4:
                return {
                    "status": "待确认",
                    "confidence": score,
                    "matched_text": best_match.get("text", ""),
                    "message": "法条引用部分匹配，需人工确认",
                }
            else:
                return {
                    "status": "无法验证",
                    "confidence": score,
                    "matched_text": best_match.get("text", ""),
                    "message": "法条库中未找到足够匹配的记录",
                }

        except Exception as e:
            logger.error("法条引用验证异常: %s", str(e))
            return {
                "status": "无法验证",
                "confidence": 0.0,
                "matched_text": "",
                "message": f"验证过程发生异常: {str(e)}",
            }

    async def verify_text_citations(self, text: str) -> list[dict]:
        """
        验证文本中所有法条引用

        先提取文本中的法条引用，然后逐一验证其真实性。

        Args:
            text: 需要验证法条引用的文本

        Returns:
            list[dict]: 验证结果列表，每项包含 law_name、article_number、verification
        """
        # 提取引用
        citations = self.extract_citations(text)

        if not citations:
            logger.info("文本中未检测到法条引用")
            return []

        # 逐一验证
        verified = []
        for citation in citations:
            verification = await self.verify_citation(
                law_name=citation["law_name"],
                article_number=citation["article_number"],
            )
            verified.append({
                "law_name": citation["law_name"],
                "article_number": citation["article_number"],
                "verification": verification,
            })

        # 统计验证结果
        status_counts = {}
        for item in verified:
            status = item["verification"]["status"]
            status_counts[status] = status_counts.get(status, 0) + 1

        logger.info(
            "法条引用验证完成，总计 %d 条，验证结果: %s",
            len(verified),
            status_counts,
        )

        return verified


# 全局校验器单例
_citation_verifier: Optional[CitationVerifier] = None


def get_citation_verifier() -> CitationVerifier:
    """
    获取法条引用校验器单例

    Returns:
        CitationVerifier: 法条引用校验器实例
    """
    global _citation_verifier
    if _citation_verifier is None:
        _citation_verifier = CitationVerifier()
    return _citation_verifier
