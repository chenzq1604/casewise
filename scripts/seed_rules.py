"""
CaseWise 法律AI工具 - 合同审查规则导入脚本

从CSV文件导入合同审查规则到SQLite数据库。
如果表已存在则清空重建。

用法：
    conda activate casewise
    python scripts/seed_rules.py --csv-file scripts/sample_rules.csv
    python scripts/seed_rules.py --csv-file scripts/sample_rules.csv --db-path backend/data/casewise.db
"""

import argparse
import asyncio
import csv
import logging
import sys
from pathlib import Path
from typing import Optional

# 将项目根目录加入 sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

import aiosqlite

# ---------- 日志配置 ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("seed_rules")

# ---------- 建表SQL ----------
CREATE_CONTRACT_RULES_TABLE = """
CREATE TABLE IF NOT EXISTS contract_rules (
    rule_id TEXT PRIMARY KEY,
    risk_level TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    law_reference TEXT DEFAULT '',
    law_article TEXT DEFAULT '',
    suggestion TEXT DEFAULT '',
    keywords TEXT DEFAULT ''
);
"""

# 索引创建SQL
CREATE_RULES_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_rules_risk_level ON contract_rules(risk_level);",
    "CREATE INDEX IF NOT EXISTS idx_rules_category ON contract_rules(category);",
    "CREATE INDEX IF NOT EXISTS idx_rules_keywords ON contract_rules(keywords);",
]


async def init_rules_table(db: aiosqlite.Connection) -> None:
    """
    初始化合同审查规则表

    如果表已存在则清空重建，确保数据干净。
    同时创建必要的索引。

    Args:
        db: aiosqlite异步数据库连接
    """
    # 检查表是否存在
    await db.execute("DROP TABLE IF EXISTS contract_rules")
    logger.info("已清空旧的 contract_rules 表")

    # 创建表
    await db.execute(CREATE_CONTRACT_RULES_TABLE)
    logger.info("contract_rules 表创建成功")

    # 创建索引
    for index_sql in CREATE_RULES_INDEXES:
        await db.execute(index_sql)
    logger.info("索引创建成功")

    await db.commit()


def load_rules_from_csv(csv_path: str) -> list[dict]:
    """
    从CSV文件加载合同审查规则

    CSV格式：rule_id, risk_level, category, description,
             law_reference, law_article, suggestion, keywords

    Args:
        csv_path: CSV文件路径

    Returns:
        list[dict]: 规则数据列表，每项为字段名到值的映射
    """
    csv_file = Path(csv_path)
    if not csv_file.exists():
        logger.error("CSV文件不存在: %s", csv_path)
        return []

    rules = []
    try:
        with open(csv_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 确保必要字段存在
                rule = {
                    "rule_id": row.get("rule_id", "").strip(),
                    "risk_level": row.get("risk_level", "").strip(),
                    "category": row.get("category", "").strip(),
                    "description": row.get("description", "").strip(),
                    "law_reference": row.get("law_reference", "").strip(),
                    "law_article": row.get("law_article", "").strip(),
                    "suggestion": row.get("suggestion", "").strip(),
                    "keywords": row.get("keywords", "").strip(),
                }
                # 跳过空行
                if not rule["rule_id"] or not rule["description"]:
                    continue
                rules.append(rule)

        logger.info("从 %s 加载了 %d 条规则", csv_path, len(rules))
    except Exception as e:
        logger.error("加载CSV文件 %s 失败: %s", csv_path, str(e))
        return []

    return rules


async def insert_rules(db: aiosqlite.Connection, rules: list[dict]) -> int:
    """
    批量插入规则到数据库

    使用事务批量插入，遇到重复rule_id则跳过。

    Args:
        db: aiosqlite异步数据库连接
        rules: 规则数据列表

    Returns:
        int: 成功插入的规则数量
    """
    if not rules:
        logger.warning("规则列表为空，跳过插入")
        return 0

    insert_sql = """
    INSERT OR IGNORE INTO contract_rules
        (rule_id, risk_level, category, description, law_reference, law_article, suggestion, keywords)
    VALUES
        (:rule_id, :risk_level, :category, :description, :law_reference, :law_article, :suggestion, :keywords)
    """

    inserted = 0
    try:
        await db.executemany(insert_sql, rules)
        await db.commit()
        inserted = len(rules)
        logger.info("成功插入 %d 条规则", inserted)
    except Exception as e:
        logger.error("插入规则失败: %s", str(e))
        await db.rollback()

    return inserted


async def verify_rules(db: aiosqlite.Connection) -> dict:
    """
    验证规则导入结果，返回统计信息

    Args:
        db: aiosqlite异步数据库连接

    Returns:
        dict: 统计信息，包含总数、各级别数量、各类别数量
    """
    stats = {}

    # 总数
    async with db.execute("SELECT COUNT(*) FROM contract_rules") as cursor:
        row = await cursor.fetchone()
        stats["total"] = row[0]

    # 按风险级别统计
    async with db.execute(
        "SELECT risk_level, COUNT(*) FROM contract_rules GROUP BY risk_level"
    ) as cursor:
        stats["by_risk_level"] = {}
        async for row in cursor:
            stats["by_risk_level"][row[0]] = row[1]

    # 按类别统计
    async with db.execute(
        "SELECT category, COUNT(*) FROM contract_rules GROUP BY category"
    ) as cursor:
        stats["by_category"] = {}
        async for row in cursor:
            stats["by_category"][row[0]] = row[1]

    return stats


async def seed_rules(
    csv_file: str = "scripts/sample_rules.csv",
    db_path: str = "backend/data/casewise.db",
) -> None:
    """
    合同审查规则导入主函数

    从CSV文件加载规则，清空重建SQLite表，批量插入规则数据。

    Args:
        csv_file: CSV规则文件路径
        db_path: SQLite数据库文件路径
    """
    # 转换为绝对路径
    if not Path(csv_file).is_absolute():
        csv_file = str(PROJECT_ROOT / csv_file)
    if not Path(db_path).is_absolute():
        db_path = str(PROJECT_ROOT / db_path)

    logger.info("=" * 60)
    logger.info("开始合同审查规则导入")
    logger.info("CSV文件: %s", csv_file)
    logger.info("数据库路径: %s", db_path)
    logger.info("=" * 60)

    # 1. 加载CSV规则
    rules = load_rules_from_csv(csv_file)
    if not rules:
        logger.warning("未找到规则数据，退出")
        return

    # 2. 确保数据库目录存在
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    # 3. 连接数据库并操作
    db = await aiosqlite.connect(str(db_file))
    # 启用WAL模式
    await db.execute("PRAGMA journal_mode=WAL;")
    await db.execute("PRAGMA foreign_keys=ON;")

    try:
        # 初始化表（清空重建）
        await init_rules_table(db)

        # 批量插入规则
        inserted = await insert_rules(db, rules)

        # 验证结果
        stats = await verify_rules(db)

        # 输出统计
        logger.info("=" * 60)
        logger.info("合同审查规则导入完成")
        logger.info("总计: %d 条规则", stats["total"])
        logger.info("按风险级别: %s", stats["by_risk_level"])
        logger.info("按类别: %s", stats["by_category"])
        logger.info("=" * 60)
    finally:
        await db.close()


def main() -> None:
    """
    脚本入口函数

    解析命令行参数并异步调用规则导入主函数。
    """
    parser = argparse.ArgumentParser(description="合同审查规则导入脚本")
    parser.add_argument(
        "--csv-file",
        type=str,
        default="scripts/sample_rules.csv",
        help="CSV规则文件路径（默认: scripts/sample_rules.csv）",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="backend/data/casewise.db",
        help="SQLite数据库路径（默认: backend/data/casewise.db）",
    )
    args = parser.parse_args()

    asyncio.run(seed_rules(csv_file=args.csv_file, db_path=args.db_path))


if __name__ == "__main__":
    main()
