"""
CaseWise 法律AI工具 - RAG 引擎模块

实现三种 RAG 策略的融合：
1. Hybrid RAG：语义检索（ChromaDB）+ BM25 关键词检索 + RRF 融合排序
2. Parent-Child RAG：小 chunk 检索，返回大 chunk 上下文
3. Self-RAG：生成后自检法条引用真实性

使用 ChromaDB 的 PersistentClient 进行向量存储和检索。
"""

import logging
from typing import Optional

import chromadb
from rank_bm25 import BM25Okapi

from app.config import settings
from app.core.embedding import get_embedding_service

logger = logging.getLogger(__name__)


class HybridRAG:
    """
    混合 RAG 引擎

    结合语义检索和关键词检索，使用 RRF（Reciprocal Rank Fusion）算法
    融合两种检索结果，提升检索的准确率和召回率。
    """

    def __init__(self) -> None:
        """
        初始化混合 RAG 引擎

        创建 ChromaDB PersistentClient 和默认 Collection，
        初始化 BM25 检索所需的语料库。
        """
        self.chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        self.collection = self.chroma_client.get_or_create_collection(
            name="legal_knowledge",
            metadata={"description": "法律知识库向量索引"},
        )
        # BM25 语料库（原始文档文本列表）
        self.corpus: list[str] = []
        # BM25 语料库对应的元数据列表
        self.corpus_metadata: list[dict] = []
        # BM25 模型实例
        self.bm25: Optional[BM25Okapi] = None
        logger.info("HybridRAG 初始化完成，ChromaDB 文档数: %d", self.collection.count())

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
                # 中文字符：先提交当前英文词，再将中文字符作为独立 token
                if current_word:
                    tokens.append(current_word.lower())
                    current_word = ""
                tokens.append(char)
            elif char.isalnum():
                # 英文/数字字符：累积为单词
                current_word += char
            else:
                # 其他字符（标点、空格等）：提交当前词
                if current_word:
                    tokens.append(current_word.lower())
                    current_word = ""
        if current_word:
            tokens.append(current_word.lower())
        return tokens

    async def index_documents(self, documents: list[str], metadatas: Optional[list[dict]] = None) -> None:
        """
        索引文档到 ChromaDB 和 BM25

        将文档同时存入向量数据库（用于语义检索）和 BM25 语料库（用于关键词检索）。

        Args:
            documents: 文档文本列表
            metadatas: 文档元数据列表，与 documents 一一对应
        """
        if not documents:
            return

        embedding_service = get_embedding_service()
        embeddings = await embedding_service.get_embeddings(documents)

        if embeddings is None:
            logger.error("文档 Embedding 生成失败，跳过索引")
            return

        # 生成唯一 ID
        ids = [f"doc_{len(self.corpus) + i}" for i in range(len(documents))]
        if metadatas is None:
            metadatas = [{} for _ in documents]

        # 写入 ChromaDB
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        # 更新 BM25 语料库
        self.corpus.extend(documents)
        self.corpus_metadata.extend(metadatas)
        tokenized_corpus = [self._tokenize_chinese(doc) for doc in self.corpus]
        self.bm25 = BM25Okapi(tokenized_corpus)

        logger.info("文档索引完成，新增 %d 篇，总计 %d 篇", len(documents), len(self.corpus))

    async def search(
        self,
        query: str,
        top_k: int = 5,
        semantic_weight: float = 0.7,
        bm25_weight: float = 0.3,
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
        # 1. 语义检索
        semantic_results = await self._semantic_search(query, top_k=top_k * 2)

        # 2. BM25 关键词检索
        bm25_results = self._bm25_search(query, top_k=top_k * 2)

        # 3. RRF 融合排序
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

        使用 ChromaDB 进行向量相似度检索。

        Args:
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            list[dict]: 语义检索结果列表
        """
        embedding_service = get_embedding_service()
        query_embedding = await embedding_service.get_embedding(query)

        if query_embedding is None:
            logger.error("查询 Embedding 生成失败")
            return []

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self.collection.count()) if self.collection.count() > 0 else 0,
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
            logger.warning("BM25 语料库为空，跳过关键词检索")
            return []

        tokenized_query = self._tokenize_chinese(query)
        scores = self.bm25.get_scores(tokenized_query)

        # 按分数降序排序
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
        semantic_weight: float = 0.7,
        bm25_weight: float = 0.3,
        k: int = 60,
    ) -> list[dict]:
        """
        RRF（Reciprocal Rank Fusion）融合排序

        将语义检索和 BM25 检索的结果按排名倒数加权融合，
        k 为平滑常数，防止排名靠前的结果权重过大。

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

        # 语义检索结果计分
        for result in semantic_results:
            text_key = result["text"][:200]  # 截取前200字符作为去重键
            rrf_scores[text_key] = rrf_scores.get(text_key, 0) + semantic_weight / (k + result["rank"])
            result_map[text_key] = result

        # BM25 检索结果计分
        for result in bm25_results:
            text_key = result["text"][:200]
            rrf_scores[text_key] = rrf_scores.get(text_key, 0) + bm25_weight / (k + result["rank"])
            result_map[text_key] = result

        # 按 RRF 分数降序排序
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

    实现小 chunk 检索、大 chunk 返回的策略：
    - 将文档切分为大 chunk（Parent）和小 chunk（Child）
    - 检索时匹配小 chunk（更精确的语义匹配）
    - 返回时提供对应的大 chunk（更完整的上下文）
    """

    def __init__(self, hybrid_rag: HybridRAG) -> None:
        """
        初始化 Parent-Child RAG 引擎

        Args:
            hybrid_rag: HybridRAG 实例，用于底层检索
        """
        self.hybrid_rag = hybrid_rag
        # 父子 chunk 映射：child_id -> parent_text
        self.child_to_parent: dict[str, str] = {}
        # 父 chunk 文本存储：parent_id -> parent_text
        self.parent_chunks: dict[str, str] = {}
        logger.info("ParentChildRAG 初始化完成")

    async def index_with_parent_child(
        self,
        parent_chunks: list[str],
        child_chunks_map: dict[str, list[str]],
        metadatas: Optional[list[dict]] = None,
    ) -> None:
        """
        以 Parent-Child 模式索引文档

        Args:
            parent_chunks: 父 chunk 文本列表
            child_chunks_map: 父子映射，key 为父 chunk 的 ID，value 为子 chunk 文本列表
            metadatas: 父 chunk 的元数据列表
        """
        all_child_texts = []
        all_child_metadatas = []

        for parent_id, children in child_chunks_map.items():
            # 存储父 chunk
            parent_idx = int(parent_id.split("_")[-1]) if "_" in parent_id else 0
            parent_text = parent_chunks[parent_idx] if parent_idx < len(parent_chunks) else ""
            self.parent_chunks[parent_id] = parent_text

            # 收集子 chunk
            for child_idx, child_text in enumerate(children):
                child_id = f"{parent_id}_child_{child_idx}"
                self.child_to_parent[child_id] = parent_text
                all_child_texts.append(child_text)
                child_metadata = {"parent_id": parent_id, "child_id": child_id}
                if metadatas and parent_idx < len(metadatas):
                    child_metadata.update(metadatas[parent_idx])
                all_child_metadatas.append(child_metadata)

        # 只索引子 chunk 到检索引擎
        await self.hybrid_rag.index_documents(all_child_texts, all_child_metadatas)
        logger.info(
            "Parent-Child 索引完成，父 chunk: %d，子 chunk: %d",
            len(parent_chunks),
            len(all_child_texts),
        )

    async def search_with_parent_context(self, query: str, top_k: int = 5) -> list[dict]:
        """
        检索子 chunk 并返回父 chunk 上下文

        Args:
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            list[dict]: 检索结果列表，每项包含 child_text、parent_context、metadata、score
        """
        # 先检索子 chunk
        child_results = await self.hybrid_rag.search(query, top_k=top_k)

        # 替换为父 chunk 上下文
        results_with_parent = []
        for result in child_results:
            parent_id = result.get("metadata", {}).get("parent_id", "")
            parent_context = self.parent_chunks.get(parent_id, result["text"])

            results_with_parent.append({
                "child_text": result["text"],
                "parent_context": parent_context,
                "metadata": result.get("metadata", {}),
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

        对每个引用，在法条库中检索验证其是否存在，
        并更新验证状态。

        Args:
            answer: AI 生成的回答文本
            citations: 引用列表，每项包含 law_name、article_number 等

        Returns:
            list[dict]: 更新验证状态后的引用列表
        """
        verified_citations = []

        for citation in citations:
            law_name = citation.get("law_name", "")
            article_number = citation.get("article_number", "")

            # 构造验证查询
            verify_query = f"{law_name} {article_number}"

            # 在法条库中检索
            try:
                results = await self.hybrid_rag.search(verify_query, top_k=3)

                if results and results[0].get("score", 0) > 0.5:
                    # 高置信度匹配：已验证
                    citation["verification_status"] = "已验证"
                    citation["verified_source"] = results[0].get("text", "")
                elif results and results[0].get("score", 0) > 0.3:
                    # 中等置信度：待确认
                    citation["verification_status"] = "待确认"
                else:
                    # 低置信度：无法验证
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


# 全局 RAG 引擎单例
_hybrid_rag: Optional[HybridRAG] = None
_parent_child_rag: Optional[ParentChildRAG] = None
_self_rag: Optional[SelfRAG] = None


def get_hybrid_rag() -> HybridRAG:
    """
    获取 HybridRAG 单例

    Returns:
        HybridRAG: 混合 RAG 引擎实例
    """
    global _hybrid_rag
    if _hybrid_rag is None:
        _hybrid_rag = HybridRAG()
    return _hybrid_rag


def get_parent_child_rag() -> ParentChildRAG:
    """
    获取 ParentChildRAG 单例

    Returns:
        ParentChildRAG: Parent-Child RAG 引擎实例
    """
    global _parent_child_rag
    if _parent_child_rag is None:
        _parent_child_rag = ParentChildRAG(get_hybrid_rag())
    return _parent_child_rag


def get_self_rag() -> SelfRAG:
    """
    获取 SelfRAG 单例

    Returns:
        SelfRAG: Self-RAG 引擎实例
    """
    global _self_rag
    if _self_rag is None:
        _self_rag = SelfRAG(get_hybrid_rag())
    return _self_rag
