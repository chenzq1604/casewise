"""
CaseWise 法律AI工具 - 配置管理模块

使用 pydantic-settings 的 BaseSettings 从 .env 文件读取所有配置项，
提供类型提示和默认值，确保敏感信息不硬编码。
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


# 项目根目录（backend/ 的绝对路径）
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """
    CaseWise 应用配置类

    所有配置项均从 .env 文件或环境变量中读取，
    敏感信息（如 API Key）绝不硬编码在源码中。
    """

    # ---------- 火山方舟 API 配置 ----------
    ARK_API_KEY: str = Field(
        default="",
        description="火山方舟 API Key，从火山方舟控制台获取"
    )
    ARK_API_URL: str = Field(
        default="https://ark.cn-beijing.volces.com/api/coding/v3",
        description="火山方舟 API 地址"
    )
    ARK_CHAT_MODEL: str = Field(
        default="ark-code-latest",
        description="对话模型名称"
    )
    ARK_EMBEDDING_MODEL: str = Field(
        default="doubao-embedding-vision",
        description="Embedding 模型名称"
    )

    # ---------- 数据库配置 ----------
    DB_PATH: str = Field(
        default=str(BASE_DIR / "data" / "casewise.db"),
        description="SQLite 数据库文件路径"
    )
    CHROMA_PERSIST_DIR: str = Field(
        default=str(BASE_DIR / "data" / "chroma_db"),
        description="ChromaDB 持久化存储目录"
    )

    # ---------- 文件存储配置 ----------
    UPLOAD_DIR: str = Field(
        default=str(BASE_DIR / "uploads"),
        description="用户上传文件目录"
    )

    # ---------- 数据采集配置 ----------
    CHROMA_CACHE_LIMIT: int = Field(
        default=256,
        description="ChromaDB内存缓存限制（MB）"
    )
    DATA_BATCH_SIZE: int = Field(
        default=10,
        description="Embedding批量大小（火山方舟API限制每次最多10条）"
    )
    EMBEDDING_RETRY_MAX: int = Field(
        default=5,
        description="Embedding限流重试次数"
    )

    # ---------- 应用配置 ----------
    ENV: str = Field(
        default="development",
        description="运行环境：development / production"
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="日志级别：DEBUG / INFO / WARNING / ERROR"
    )
    PORT: int = Field(
        default=8000,
        description="服务监听端口"
    )

    model_config = {
        "env_file": str(BASE_DIR / ".env"),
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }

    def is_production(self) -> bool:
        """判断当前是否为生产环境"""
        return self.ENV == "production"

    def ensure_directories(self) -> None:
        """确保所有必要的数据目录都存在"""
        dirs = [
            Path(self.DB_PATH).parent,
            Path(self.CHROMA_PERSIST_DIR),
            Path(self.UPLOAD_DIR),
            BASE_DIR / "logs",
            BASE_DIR / "data" / "laws",
            BASE_DIR / "data" / "cases",
            BASE_DIR / "data" / "rules",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)


# 全局配置单例
settings = Settings()
