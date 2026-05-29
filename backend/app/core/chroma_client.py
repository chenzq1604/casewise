"""
CaseWise 法律AI工具 - ChromaDB 客户端管理模块

提供全局 ChromaDB PersistentClient 单例，
避免同一目录创建多个不同配置的客户端实例导致冲突。
"""

import logging
from typing import Optional

import chromadb

from app.config import settings

logger = logging.getLogger(__name__)

"""全局 ChromaDB 客户端单例"""
_chroma_client: Optional[chromadb.PersistentClient] = None


def get_chroma_client() -> chromadb.PersistentClient:
    """
    获取 ChromaDB PersistentClient 全局单例

    确保整个应用生命周期内只创建一个客户端实例，
    避免同一目录创建多个不同配置的客户端导致冲突。

    Returns:
        chromadb.PersistentClient: ChromaDB 持久化客户端实例
    """
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
        )
        logger.info("ChromaDB 客户端初始化完成，路径: %s", settings.CHROMA_PERSIST_DIR)
    return _chroma_client
