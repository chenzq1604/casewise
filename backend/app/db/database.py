"""
CaseWise 法律AI工具 - SQLite 数据库连接和初始化模块

使用 aiosqlite 异步操作 SQLite 数据库，
启用 WAL 模式以提升并发读写性能，
初始化 chat_history、contract_reviews、review_feedback 三张核心表。
"""

import aiosqlite
from pathlib import Path
from typing import Optional

from app.config import settings


# 全局数据库连接对象
_db_connection: Optional[aiosqlite.Connection] = None


# ========== 建表 SQL ==========

CREATE_CHAT_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    citations_json TEXT DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_CONTRACT_REVIEWS_TABLE = """
CREATE TABLE IF NOT EXISTS contract_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id TEXT NOT NULL,
    filename TEXT DEFAULT '',
    contract_type TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    risks_json TEXT DEFAULT '[]',
    overall_risk_level TEXT DEFAULT '低',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_REVIEW_FEEDBACK_TABLE = """
CREATE TABLE IF NOT EXISTS review_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,
    source_id INTEGER NOT NULL,
    original_output TEXT NOT NULL,
    feedback_type TEXT NOT NULL,
    corrected_content TEXT,
    comment TEXT DEFAULT '',
    reviewer TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# 索引创建 SQL
CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_chat_history_session ON chat_history(session_id);",
    "CREATE INDEX IF NOT EXISTS idx_chat_history_created ON chat_history(created_at);",
    "CREATE INDEX IF NOT EXISTS idx_contract_reviews_file_id ON contract_reviews(file_id);",
    "CREATE INDEX IF NOT EXISTS idx_review_feedback_source ON review_feedback(source_type, source_id);",
    "CREATE INDEX IF NOT EXISTS idx_review_feedback_type ON review_feedback(feedback_type);",
]


async def get_db() -> aiosqlite.Connection:
    """
    获取数据库连接（单例模式）

    如果连接不存在则创建新连接，启用 WAL 模式和外键约束。

    Returns:
        aiosqlite.Connection: 异步 SQLite 数据库连接
    """
    global _db_connection
    if _db_connection is None:
        # 确保数据库目录存在
        db_path = Path(settings.DB_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        _db_connection = await aiosqlite.connect(str(db_path))
        # 启用 WAL 模式，提升并发读写性能
        await _db_connection.execute("PRAGMA journal_mode=WAL;")
        # 启用外键约束
        await _db_connection.execute("PRAGMA foreign_keys=ON;")
        # 设置递归触发器
        await _db_connection.execute("PRAGMA recursive_triggers=ON;")
    return _db_connection


async def init_db() -> None:
    """
    初始化数据库表结构

    创建 chat_history、contract_reviews、review_feedback 三张核心表，
    并创建必要的索引。如果表已存在则跳过。
    """
    db = await get_db()

    # 创建所有表
    await db.execute(CREATE_CHAT_HISTORY_TABLE)
    await db.execute(CREATE_CONTRACT_REVIEWS_TABLE)
    await db.execute(CREATE_REVIEW_FEEDBACK_TABLE)

    # 创建索引
    for index_sql in CREATE_INDEXES:
        await db.execute(index_sql)

    await db.commit()


async def close_db() -> None:
    """
    关闭数据库连接

    在应用关闭时调用，确保所有未提交的事务已提交，
    并安全关闭数据库连接。
    """
    global _db_connection
    if _db_connection is not None:
        await _db_connection.close()
        _db_connection = None
