"""
CaseWise 法律AI工具 - Embedding 服务模块

使用 OpenAI 兼容格式调用火山方舟的 doubao-embedding-vision 模型，
提供单条和批量文本向量化接口。
"""

import logging
from typing import Optional

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Embedding 服务

    封装火山方舟 Embedding API 的调用逻辑，
    提供单条和批量文本向量化能力，用于 RAG 检索的语义向量化。
    """

    def __init__(self) -> None:
        """
        初始化 Embedding 服务

        使用 .env 中的 ARK_API_URL 和 ARK_API_KEY 创建异步 OpenAI 客户端，
        模型使用 ARK_EMBEDDING_MODEL 配置的 doubao-embedding-vision。
        """
        self.client = AsyncOpenAI(
            base_url=settings.ARK_API_URL,
            api_key=settings.ARK_API_KEY,
        )
        self.model = settings.ARK_EMBEDDING_MODEL
        logger.info("Embedding 服务初始化完成，模型: %s", self.model)

    async def get_embedding(self, text: str) -> Optional[list[float]]:
        """
        获取单条文本的向量表示

        Args:
            text: 需要向量化的文本内容

        Returns:
            list[float]: 文本的向量表示，失败时返回 None
        """
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
            )
            embedding = response.data[0].embedding
            logger.debug(
                "Embedding 生成完成，维度: %d，token 用量: %s",
                len(embedding),
                response.usage,
            )
            return embedding
        except Exception as e:
            logger.error("Embedding 生成失败: %s", str(e))
            return None

    async def get_embeddings(self, texts: list[str]) -> Optional[list[list[float]]]:
        """
        批量获取文本的向量表示

        适用于批量索引文档的场景，减少 API 调用次数。

        Args:
            texts: 需要向量化的文本列表

        Returns:
            list[list[float]]: 文本向量列表，与输入顺序一致，失败时返回 None
        """
        if not texts:
            logger.warning("批量 Embedding 请求为空")
            return []

        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts,
            )
            embeddings = [item.embedding for item in response.data]
            logger.debug(
                "批量 Embedding 生成完成，数量: %d，token 用量: %s",
                len(embeddings),
                response.usage,
            )
            return embeddings
        except Exception as e:
            logger.error("批量 Embedding 生成失败: %s", str(e))
            return None


# 全局 Embedding 服务单例
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """
    获取 Embedding 服务单例

    Returns:
        EmbeddingService: Embedding 服务实例
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
