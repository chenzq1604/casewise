"""
CaseWise 法律AI工具 - RAG 引擎模块

实现三种 RAG 策略的融合：
1. Hybrid RAG：语义检索（ChromaDB laws_child）+ BM25 关键词检索 + RRF 融合排序
2. Parent-Child RAG：小 chunk 检索（laws_child），返回大 chunk 上下文（laws_parent）
3. Self-RAG：生成后自检法条引用真实性

使用 ChromaDB 的 PersistentClient 进行向量存储和检索，
与 data_collector.py 共享 laws_child 和 laws_parent 两个 collection。
"""

import logging
import pickle
from pathlib import Path
from typing import Optional

from rank_bm25 import BM25Okapi

from app.config import settings
from app.core.chroma_client import get_chroma_client
from app.core.embedding import get_embedding_service

logger = logging.getLogger(__name__)


class HybridRAG:
    """
    混合 RAG 引擎

    结合语义检索和关键词检索，使用 RRF（Reciprocal Rank Fusion）算法
    融合两种检索结果，提升检索的准确率和召回率。
    直接从 laws_child collection 检索，与数据采集器对齐。
    """

    def __init__(self) -> None:
        """
        初始化混合 RAG 引擎

        获取 ChromaDB 中的 laws_child collection，
        加载 BM25 索引（如果存在）。
        """
        self.chroma_client = get_chroma_client()
        self.collection = self.chroma_client.get_or_create_collection(
            name="laws_child",
            metadata={"description": "法条子文档（每款一段），用于精确检索"},
        )
        self.bm25: Optional[BM25Okapi] = None
        self.corpus: list[str] = []
        self.corpus_metadata: list[dict] = []
        self._load_bm25_index()
        logger.info("HybridRAG 初始化完成，ChromaDB 文档数: %d, BM25语料数: %d", self.collection.count(), len(self.corpus))

    def _load_bm25_index(self) -> None:
        """
        从磁盘加载 BM25 索引

        BM25 索引由数据采集器构建并保存到 data/laws/bm25_index.pkl，
        如果文件不存在则跳过（首次运行时可能尚未采集数据）。
        """
        bm25_path = Path(settings.CHROMA_PERSIST_DIR).parent / "laws" / "bm25_index.pkl"
        if bm25_path.exists():
            try:
                import json
                json_path = bm25_path.with_suffix('.json')
                if json_path.exists():
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                else:
                    with open(bm25_path, "rb") as f:
                        data = pickle.load(f)
                self.bm25 = data.get("bm25")
                self.corpus = data.get("corpus", [])
                self.corpus_metadata = data.get("corpus_metadata", [])
                logger.info("BM25 索引加载成功，语料数: %d", len(self.corpus))
            except Exception as e:
                logger.warning("BM25 索引加载失败: %s", str(e))
        else:
            logger.info("BM25 索引文件不存在，跳过加载")

    def _tokenize_chinese(self, text: str) -> list[str]:
        """
        中文文本分词（简易字符级分词）

        对中文文本按字符切分，同时保留英文单词的完整性。
        生产环境建议替换为 jieba 等专业分词工具。

        Args:
            text: 待分词的文本

        Returns:
            list[str]: 分词结果列表
        """
        tokens = []
        current_word = ""
        for char in text:
            if "\u4e00" <= char <= "\u9fff":
                if current_word:
                    tokens.append(current_word.lower())
                    current_word = ""
                tokens.append(char)
            elif char.isalnum():
                current_word += char
            else:
                if current_word:
                    tokens.append(current_word.lower())
                    current_word = ""
        if current_word:
            tokens.append(current_word.lower())
        return tokens

    async def search(
        self,
        query: str,
        top_k: int = 5,
        semantic_weight: float = 0.6,
        bm25_weight: float = 0.4,
    ) -> list[dict]:
        """
        混合检索：语义检索 + BM25 关键词检索 + RRF 融合

        Args:
            query: 查询文本
            top_k: 返回结果数量
            semantic_weight: 语义检索权重
            bm25_weight: BM25 检索权重

        Returns:
            list[dict]: 检索结果列表，每项包含 text、metadata、score
        """
        doc_count = self.collection.count()
        if doc_count == 0:
            logger.warning("ChromaDB laws_child 为空，跳过检索")
            return []

        actual_top_k = min(top_k, doc_count)

        semantic_results = await self._semantic_search(query, top_k=actual_top_k * 2)
        bm25_results = self._bm25_search(query, top_k=actual_top_k * 2)

        fused_results = self._rrf_fusion(
            semantic_results=semantic_results,
            bm25_results=bm25_results,
            semantic_weight=semantic_weight,
            bm25_weight=bm25_weight,
        )

        return fused_results[:top_k]

    async def _semantic_search(self, query: str, top_k: int = 10) -> list[dict]:
        """
        语义向量检索

        使用 ChromaDB laws_child collection 进行向量相似度检索。

        Args:
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            list[dict]: 语义检索结果列表
        """
        doc_count = self.collection.count()
        if doc_count == 0:
            return []

        actual_top_k = min(top_k, doc_count)

        embedding_service = get_embedding_service()
        query_embedding = await embedding_service.get_embedding(query)

        if query_embedding is None:
            logger.error("查询 Embedding 生成失败")
            return []

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=actual_top_k,
            include=["documents", "metadatas", "distances"],
        )

        search_results = []
        if results and results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                search_results.append({
                    "text": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "score": 1 - results["distances"][0][i] if results["distances"] else 0,
                    "rank": i + 1,
                })

        return search_results

    def _bm25_search(self, query: str, top_k: int = 10) -> list[dict]:
        """
        BM25 关键词检索

        使用 BM25 算法进行关键词匹配检索。

        Args:
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            list[dict]: BM25 检索结果列表
        """
        if self.bm25 is None or not self.corpus:
            return []

        tokenized_query = self._tokenize_chinese(query)
        scores = self.bm25.get_scores(tokenized_query)

        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        top_indices = ranked_indices[:top_k]

        results = []
        for rank, idx in enumerate(top_indices):
            if scores[idx] > 0:
                results.append({
                    "text": self.corpus[idx],
                    "metadata": self.corpus_metadata[idx] if idx < len(self.corpus_metadata) else {},
                    "score": float(scores[idx]),
                    "rank": rank + 1,
                })

        return results

    def _rrf_fusion(
        self,
        semantic_results: list[dict],
        bm25_results: list[dict],
        semantic_weight: float = 0.6,
        bm25_weight: float = 0.4,
        k: int = 60,
    ) -> list[dict]:
        """
        RRF（Reciprocal Rank Fusion）融合排序

        将语义检索和 BM25 检索的结果按排名倒数加权融合。

        Args:
            semantic_results: 语义检索结果
            bm25_results: BM25 检索结果
            semantic_weight: 语义检索权重
            bm25_weight: BM25 检索权重
            k: RRF 平滑常数

        Returns:
            list[dict]: 融合排序后的结果列表
        """
        rrf_scores: dict[str, float] = {}
        result_map: dict[str, dict] = {}

        for result in semantic_results:
            text_key = result["text"][:200]
            rrf_scores[text_key] = rrf_scores.get(text_key, 0) + semantic_weight / (k + result["rank"])
            result_map[text_key] = result

        for result in bm25_results:
            text_key = result["text"][:200]
            rrf_scores[text_key] = rrf_scores.get(text_key, 0) + bm25_weight / (k + result["rank"])
            result_map[text_key] = result

        sorted_keys = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        fused_results = []
        for key in sorted_keys:
            result = result_map[key].copy()
            result["rrf_score"] = rrf_scores[key]
            fused_results.append(result)

        return fused_results


class ParentChildRAG:
    """
    Parent-Child RAG 引擎

    从 laws_child 检索小 chunk，通过 parent_id 关联到 laws_parent 获取完整上下文。
    """

    def __init__(self, hybrid_rag: HybridRAG) -> None:
        """
        初始化 Parent-Child RAG 引擎

        Args:
            hybrid_rag: HybridRAG 实例，用于底层检索
        """
        self.hybrid_rag = hybrid_rag
        self.chroma_client = get_chroma_client()
        self.parent_collection = self.chroma_client.get_or_create_collection(
            name="laws_parent",
            metadata={"description": "法条父文档（完整法条），用于提供上下文"},
        )
        logger.info("ParentChildRAG 初始化完成，parent文档数: %d", self.parent_collection.count())

    async def search_with_parent_context(self, query: str, top_k: int = 5) -> list[dict]:
        """
        检索子 chunk 并返回父 chunk 上下文

        先从 laws_child 检索匹配的子文档，
        再通过 metadata 中的 parent_id 从 laws_parent 获取完整法条。

        Args:
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            list[dict]: 检索结果列表，每项包含 child_text、parent_context、metadata、score
        """
        child_results = await self.hybrid_rag.search(query, top_k=top_k)

        results_with_parent = []
        for result in child_results:
            metadata = result.get("metadata", {})
            parent_id = metadata.get("parent_id", "")

            parent_context = result["text"]
            if parent_id and self.parent_collection.count() > 0:
                try:
                    parent_results = self.parent_collection.get(
                        ids=[parent_id],
                        include=["documents"],
                    )
                    if parent_results and parent_results["documents"] and parent_results["documents"][0]:
                        parent_context = parent_results["documents"][0]
                except Exception as e:
                    logger.warning("获取父文档失败: %s", str(e))

            results_with_parent.append({
                "child_text": result["text"],
                "parent_context": parent_context,
                "metadata": metadata,
                "score": result.get("rrf_score", result.get("score", 0)),
            })

        return results_with_parent


class SelfRAG:
    """
    Self-RAG 引擎

    在生成回答后，自动检验法条引用的真实性：
    1. 提取回答中引用的法条
    2. 在法条库中验证引用是否存在
    3. 标记验证状态（已验证/待确认/无法验证）
    """

    def __init__(self, hybrid_rag: HybridRAG) -> None:
        """
        初始化 Self-RAG 引擎

        Args:
            hybrid_rag: HybridRAG 实例，用于法条库检索验证
        """
        self.hybrid_rag = hybrid_rag
        logger.info("SelfRAG 初始化完成")

    async def verify_citations(self, answer: str, citations: list[dict]) -> list[dict]:
        """
        验证回答中的法条引用真实性

        对每个引用，在法条库中检索验证其是否存在。

        Args:
            answer: AI 生成的回答文本
            citations: 引用列表

        Returns:
            list[dict]: 更新验证状态后的引用列表
        """
        verified_citations = []

        for citation in citations:
            law_name = citation.get("law_name", "")
            article_number = citation.get("article_number", "")

            verify_query = f"{law_name} {article_number}"

            try:
                results = await self.hybrid_rag.search(verify_query, top_k=3)

                if results and results[0].get("score", 0) > 0.5:
                    citation["verification_status"] = "已验证"
                    citation["verified_source"] = results[0].get("text", "")
                elif results and results[0].get("score", 0) > 0.3:
                    citation["verification_status"] = "待确认"
                else:
                    citation["verification_status"] = "无法验证"
            except Exception as e:
                logger.error("法条引用验证失败: %s", str(e))
                citation["verification_status"] = "无法验证"

            verified_citations.append(citation)

        logger.info(
            "法条引用验证完成，总计 %d 条，已验证: %d",
            len(verified_citations),
            sum(1 for c in verified_citations if c.get("verification_status") == "已验证"),
        )

        return verified_citations


_hybrid_rag: Optional[HybridRAG] = None
_parent_child_rag: Optional[ParentChildRAG] = None
_self_rag: Optional[SelfRAG] = None


def get_hybrid_rag() -> HybridRAG:
    """获取 HybridRAG 单例"""
    global _hybrid_rag
    if _hybrid_rag is None:
        _hybrid_rag = HybridRAG()
    return _hybrid_rag


def get_parent_child_rag() -> ParentChildRAG:
    """获取 ParentChildRAG 单例"""
    global _parent_child_rag
    if _parent_child_rag is None:
        _parent_child_rag = ParentChildRAG(get_hybrid_rag())
    return _parent_child_rag


def get_self_rag() -> SelfRAG:
    """获取 SelfRAG 单例"""
    global _self_rag
    if _self_rag is None:
        _self_rag = SelfRAG(get_hybrid_rag())
    return _self_rag
