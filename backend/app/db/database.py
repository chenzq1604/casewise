"""
CaseWise 法律AI工具 - SQLite 数据库连接和初始化模块

使用 aiosqlite 异步操作 SQLite 数据库，
启用 WAL 模式以提升并发读写性能，
初始化 chat_history、contract_reviews、review_feedback 三张核心表。
"""

import aiosqlite
import logging
from pathlib import Path
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


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
    contract_text TEXT DEFAULT '',
    analyzed_at TIMESTAMP,
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

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'client',
    display_name TEXT DEFAULT '',
    is_active INTEGER DEFAULT 1,
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
    "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);",
    "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);",
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
        await _db_connection.execute("PRAGMA journal_mode=WAL;")
        await _db_connection.execute("PRAGMA foreign_keys=ON;")
        await _db_connection.execute("PRAGMA recursive_triggers=ON;")
        await _db_connection.execute("PRAGMA busy_timeout = 5000;")
    return _db_connection


async def init_db() -> None:
    """
    初始化数据库表结构

    创建 chat_history、contract_reviews、review_feedback 三张核心表，
    并创建必要的索引。如果表已存在则跳过。
    同时执行必要的表结构迁移。
    """
    db = await get_db()

    # 创建所有表
    await db.execute(CREATE_CHAT_HISTORY_TABLE)
    await db.execute(CREATE_CONTRACT_REVIEWS_TABLE)
    await db.execute(CREATE_REVIEW_FEEDBACK_TABLE)
    await db.execute(CREATE_USERS_TABLE)

    # 创建索引
    for index_sql in CREATE_INDEXES:
        await db.execute(index_sql)

    # 表结构迁移：为 contract_reviews 添加新字段
    await _migrate_contract_reviews(db)

    # 初始化默认用户
    await _seed_default_users(db)

    await db.commit()


async def _migrate_contract_reviews(db: aiosqlite.Connection) -> None:
    """
    合同审查表结构迁移

    检查并添加 contract_text 和 analyzed_at 字段。
    SQLite 不支持 IF NOT EXISTS 用于 ALTER TABLE，
    所以用 try/except 处理字段已存在的情况。
    """
    migrations = [
        "ALTER TABLE contract_reviews ADD COLUMN contract_text TEXT DEFAULT '';",
        "ALTER TABLE contract_reviews ADD COLUMN analyzed_at TIMESTAMP;",
    ]
    for sql in migrations:
        try:
            await db.execute(sql)
        except Exception:
            pass


async def _seed_default_users(db: aiosqlite.Connection) -> None:
    """
    初始化默认用户账号

    首次启动时创建3个默认用户（管理员/律师/客户），
    如果用户名已存在则跳过。
    """
    try:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        row = await cursor.fetchone()
        if row and row[0] > 0:
            logger.info("用户表已有 %d 条记录，跳过默认用户创建", row[0])
            return

        from app.core.auth import hash_password_async

        default_users = [
            ("admin", "admin123", "admin", "系统管理员"),
            ("lawyer", "lawyer123", "lawyer", "律师"),
            ("client", "client123", "client", "客户"),
        ]

        for username, password, role, display_name in default_users:
            password_hash = await hash_password_async(password)
            await db.execute(
                "INSERT INTO users (username, password_hash, role, display_name) VALUES (?, ?, ?, ?)",
                (username, password_hash, role, display_name),
            )
            logger.info("默认用户已创建: %s (角色: %s)", username, role)
        logger.warning("已创建默认用户，请在生产环境中修改默认密码！")
    except Exception as e:
        logger.warning("初始化默认用户失败（可忽略）: %s", str(e))


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
