"""
CaseWise 法律AI工具 - 法律问答业务逻辑模块

编排 LLM、RAG、溯源校验、合规声明等核心组件，
完成法律问答的完整业务流程。
"""

import json
import logging
import uuid
from typing import AsyncGenerator, Optional

from app.core.llm import get_llm_service
from app.core.rag import get_parent_child_rag, get_self_rag
from app.core.citation import get_citation_verifier
from app.core.compliance import get_compliance_service
from app.db.database import get_db
from app.models.chat import ChatRequest, ChatResponse, CitationCard, ChatHistoryRecord

logger = logging.getLogger(__name__)


# 法律问答系统提示词
CHAT_SYSTEM_PROMPT = """你是一位专业的法律AI助手，名为 CaseWise。你的职责是：

1. 基于提供的法律知识库内容回答用户问题
2. 引用具体的法律条文时，必须标注法律名称和条款编号
3. 如果知识库中没有相关内容，请如实告知用户
4. 不得编造不存在的法律条文
5. 回答应当客观、准确、有依据

请严格按照以上要求回答用户的问题。"""


class ChatService:
    """
    法律问答业务服务

    编排 RAG 检索、LLM 生成、溯源校验、合规声明等步骤，
    完成法律问答的完整业务流程。
    """

    def __init__(self) -> None:
        """
        初始化法律问答服务
        """
        self.llm_service = get_llm_service()
        self.parent_child_rag = get_parent_child_rag()
        self.self_rag = get_self_rag()
        self.citation_verifier = get_citation_verifier()
        self.compliance_service = get_compliance_service()
        logger.info("ChatService 初始化完成")

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        处理法律问答请求

        完整流程：
        1. RAG 检索相关法律知识
        2. 构建带上下文的提示词
        3. LLM 生成回答
        4. 提取并验证法条引用
        5. 附加合规声明
        6. 保存历史记录

        Args:
            request: 法律问答请求

        Returns:
            ChatResponse: 法律问答响应
        """
        # 生成或使用已有的 session_id
        session_id = request.session_id or str(uuid.uuid4())

        # 1. RAG 检索相关法律知识
        rag_context = await self._retrieve_context(request.question)

        # 2. 构建带上下文的消息
        messages = self._build_messages(request.question, rag_context, session_id)

        # 3. LLM 生成回答
        answer = await self.llm_service.chat_completion(
            messages=messages,
            temperature=0.3,  # 法律场景使用较低温度，保证准确性
        )
        if answer is None:
            answer = "抱歉，AI 服务暂时不可用，请稍后重试。"

        # 4. 提取并验证法条引用
        citations = await self._verify_citations(answer)

        # 5. 附加合规声明
        compliance_notice = self.compliance_service.generate_notice(scene="chat")

        # 6. 保存历史记录
        await self._save_history(session_id, request.question, answer, citations)

        return ChatResponse(
            answer=answer,
            citations=citations,
            session_id=session_id,
            compliance_notice=compliance_notice,
        )

    async def chat_stream(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        """
        流式处理法律问答请求

        逐步生成回答文本，适用于需要实时展示的场景。

        Args:
            request: 法律问答请求

        Yields:
            str: 逐步生成的回答文本片段
        """
        session_id = request.session_id or str(uuid.uuid4())

        # RAG 检索
        rag_context = await self._retrieve_context(request.question)

        # 构建消息
        messages = self._build_messages(request.question, rag_context, session_id)

        # 流式生成
        full_answer = ""
        async for chunk in self.llm_service.chat_completion_stream(
            messages=messages,
            temperature=0.3,
        ):
            full_answer += chunk
            yield chunk

        # 保存历史记录
        citations = self.citation_verifier.extract_citations(full_answer)
        await self._save_history(session_id, request.question, full_answer, citations)

    async def _retrieve_context(self, question: str) -> str:
        """
        使用 Parent-Child RAG 检索相关法律知识

        Args:
            question: 用户问题

        Returns:
            str: 检索到的法律知识上下文文本
        """
        try:
            results = await self.parent_child_rag.search_with_parent_context(
                query=question, top_k=5
            )

            if not results:
                return ""

            # 拼接检索结果为上下文
            context_parts = []
            for i, result in enumerate(results, 1):
                parent_context = result.get("parent_context", result.get("child_text", ""))
                context_parts.append(f"[参考资料{i}]\n{parent_context}")

            return "\n\n".join(context_parts)

        except Exception as e:
            logger.error("RAG 检索失败: %s", str(e))
            return ""

    def _build_messages(self, question: str, rag_context: str, session_id: str) -> list[dict]:
        """
        构建发送给 LLM 的消息列表

        将系统提示、RAG 上下文和用户问题组合为完整的消息列表。

        Args:
            question: 用户问题
            rag_context: RAG 检索到的上下文
            session_id: 会话ID

        Returns:
            list[dict]: 消息列表
        """
        system_content = CHAT_SYSTEM_PROMPT

        if rag_context:
            system_content += f"\n\n以下是从法律知识库中检索到的相关参考资料：\n\n{rag_context}"

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": question},
        ]

        return messages

    async def _verify_citations(self, answer: str) -> list[CitationCard]:
        """
        提取并验证回答中的法条引用

        Args:
            answer: AI 生成的回答文本

        Returns:
            list[CitationCard]: 验证后的法条引用卡片列表
        """
        # 提取引用
        raw_citations = self.citation_verifier.extract_citations(answer)

        if not raw_citations:
            return []

        # 验证引用
        citation_cards = []
        for citation in raw_citations:
            verification = await self.citation_verifier.verify_citation(
                law_name=citation["law_name"],
                article_number=citation["article_number"],
            )
            card = CitationCard(
                law_name=citation["law_name"],
                article_number=citation["article_number"],
                article_content=verification.get("matched_text", ""),
                verification_status=verification.get("status", "无法验证"),
            )
            citation_cards.append(card)

        return citation_cards

    async def _save_history(
        self,
        session_id: str,
        question: str,
        answer: str,
        citations: list,
    ) -> None:
        """
        保存问答历史记录到数据库

        Args:
            session_id: 会话ID
            question: 用户问题
            answer: AI回答
            citations: 法条引用列表
        """
        try:
            db = await get_db()
            citations_json = json.dumps(
                [c.dict() if hasattr(c, "dict") else c for c in citations],
                ensure_ascii=False,
            )
            await db.execute(
                """INSERT INTO chat_history (session_id, question, answer, citations_json)
                   VALUES (?, ?, ?, ?)""",
                (session_id, question, answer, citations_json),
            )
            await db.commit()
            logger.debug("问答历史已保存，session_id: %s", session_id)
        except Exception as e:
            logger.error("保存问答历史失败: %s", str(e))


# 全局服务单例
_chat_service: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    """
    获取法律问答服务单例

    Returns:
        ChatService: 法律问答服务实例
    """
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
