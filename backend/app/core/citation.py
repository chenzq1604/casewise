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
    # 支持多种引用格式：书名号格式、无书名号格式、简称格式、纯条款格式
    CITATION_PATTERNS = [
        # 《法律名称》第X条第X款（需放在第X条之前，优先匹配更精确的模式）
        re.compile(r"《([^》]+)》第([一二三四五六七八九十百千万零\d]+)条第([一二三四五六七八九十百千万零\d]+)款"),
        # 《法律名称》第X章第X条
        re.compile(r"《([^》]+)》第([一二三四五六七八九十百千万零\d]+)章第([一二三四五六七八九十百千万零\d]+)条"),
        # 《法律名称》第X条
        re.compile(r"《([^》]+)》第([一二三四五六七八九十百千万零\d]+)条"),
        # 无书名号：法律名称 第X条（中间有空格，法律名称以法/条例/规定/办法/解释/通则/典结尾）
        re.compile(r"([\u4e00-\u9fff]+(?:法|条例|规定|办法|解释|通则|典))\s+第([一二三四五六七八九十百千万零\d]+)条"),
        # 简称+数字条款：民法典第585条（法律简称后直接跟第X条，无空格）
        re.compile(r"([\u4e00-\u9fff]+(?:法|典))第(\d+)条"),
        # 第X条第X款（无法律名称时从上下文推断）
        re.compile(r"第([一二三四五六七八九十百千万零\d]+)条第([一二三四五六七八九十百千万零\d]+)款"),
    ]

    # 法律名称简称到全称的映射表，用于从简称推断完整法律名称
    LAW_NAME_ALIASES: dict[str, str] = {
        "民法典": "中华人民共和国民法典",
        "劳动法": "中华人民共和国劳动法",
        "劳动合同法": "中华人民共和国劳动合同法",
        "公司法": "中华人民共和国公司法",
        "建筑法": "中华人民共和国建筑法",
        "刑法": "中华人民共和国刑法",
        "银行法": "中华人民共和国商业银行法",
        "证券法": "中华人民共和国证券法",
        "保险法": "中华人民共和国保险法",
    }

    def __init__(self) -> None:
        """
        初始化法条引用校验器
        """
        logger.info("CitationVerifier 初始化完成")

    def extract_citations(self, text: str) -> list[dict]:
        """
        从文本中提取法条引用

        使用正则表达式匹配常见的法条引用格式，
        提取法律名称和条款编号。对于无法律名称的匹配，
        尝试从上文推断法律名称。

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
                law_name = ""
                article_number = ""
                paragraph_number = ""

                # 根据匹配组数判断匹配模式
                if len(match) == 3:
                    # 三组匹配：《法律名》第X条第X款 / 《法律名》第X章第X条 / 第X条第X款
                    if pattern == self.CITATION_PATTERNS[5]:
                        # 纯条款格式：第X条第X款（无法律名称）
                        article_number = f"第{match[0]}条"
                        paragraph_number = f"第{match[1]}款"
                        # 尝试从上文推断法律名称
                        law_name = self._infer_law_name(text, match[0])
                    else:
                        # 带法律名称的三组匹配
                        law_name = match[0]
                        article_number = f"第{match[1]}条"
                        paragraph_number = f"第{match[2]}款"
                elif len(match) == 2:
                    # 两组匹配：《法律名》第X条 / 无书名号法律名 第X条 / 简称第X条
                    law_name = match[0]
                    article_number = f"第{match[1]}条"
                else:
                    continue

                # 规范化法律名称：将简称映射为全称
                law_name = self._normalize_law_name(law_name)

                # 构建完整条款编号
                full_article = article_number
                if paragraph_number:
                    full_article += paragraph_number

                citation_key = f"{law_name}_{full_article}"
                if citation_key not in seen:
                    seen.add(citation_key)
                    citation = {
                        "law_name": law_name,
                        "article_number": full_article,
                    }
                    if paragraph_number:
                        citation["paragraph_number"] = paragraph_number
                    citations.append(citation)

        logger.debug("从文本中提取到 %d 条法条引用", len(citations))
        return citations

    def _normalize_law_name(self, law_name: str) -> str:
        """
        规范化法律名称

        将法律名称的简称映射为完整正式名称，
        如果映射表中没有则原样返回。

        Args:
            law_name: 原始法律名称（可能是简称）

        Returns:
            str: 规范化后的法律名称
        """
        return self.LAW_NAME_ALIASES.get(law_name, law_name)

    def _infer_law_name(self, text: str, article_number: str) -> str:
        """
        从上下文推断法律名称

        当匹配到纯条款格式（如"第585条第2款"）时，
        在文本中向前搜索最近的法律名称引用。

        Args:
            text: 完整文本
            article_number: 条款编号

        Returns:
            str: 推断出的法律名称，无法推断时返回空字符串
        """
        # 在文本中查找所有带书名号的法律名称
        book_pattern = re.compile(r"《([^》]+)》")
        book_matches = list(book_pattern.finditer(text))

        if book_matches:
            # 取最后一个法律名称作为上下文推断结果
            return book_matches[-1].group(1)

        # 查找无书名号的法律名称
        no_book_pattern = re.compile(r"([\u4e00-\u9fff]+(?:法|条例|规定|办法|解释|通则|典))")
        no_book_matches = list(no_book_pattern.finditer(text))

        if no_book_matches:
            name = no_book_matches[-1].group(1)
            return self._normalize_law_name(name)

        return ""

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
