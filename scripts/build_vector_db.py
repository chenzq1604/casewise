"""
CaseWise 法律AI工具 - 一键构建向量库

顺序调用 seed_laws、seed_cases、seed_rules 三个脚本，
一键完成所有数据的导入和索引构建。
支持跳过某步骤和限制导入数量。

用法：
    conda activate casewise
    python scripts/build_vector_db.py --limit 1000
    python scripts/build_vector_db.py --limit 0 --skip-cases
    python scripts/build_vector_db.py --skip-laws --skip-cases --skip-rules  # 什么都不做
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# 将项目根目录加入 sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

# 导入各子模块
from scripts.seed_laws import seed_laws
from scripts.seed_cases import seed_cases
from scripts.seed_rules import seed_rules

# ---------- 日志配置 ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("build_vector_db")


def run_step(
    step_name: str,
    step_func,
    skip: bool,
    **kwargs,
) -> float:
    """
    执行单个导入步骤并计时

    Args:
        step_name: 步骤名称，用于日志显示
        step_func: 步骤执行函数
        skip: 是否跳过此步骤
        **kwargs: 传递给步骤函数的参数

    Returns:
        float: 步骤耗时（秒），跳过时返回0
    """
    if skip:
        logger.info("[跳过] %s", step_name)
        return 0.0

    logger.info("-" * 60)
    logger.info("[开始] %s", step_name)
    start_time = time.time()

    try:
        step_func(**kwargs)
    except Exception as e:
        logger.error("[失败] %s: %s", step_name, str(e))
        return time.time() - start_time

    elapsed = time.time() - start_time
    logger.info("[完成] %s，耗时: %.2f 秒", step_name, elapsed)
    return elapsed


def build_all(
    limit: int = 1000,
    skip_laws: bool = False,
    skip_cases: bool = False,
    skip_rules: bool = False,
    data_dir_laws: str = "backend/data/laws",
    data_dir_cases: str = "backend/data/cases",
    csv_file_rules: str = "scripts/sample_rules.csv",
    chroma_dir: str = "backend/data/chroma_db",
    db_path: str = "backend/data/casewise.db",
    filter_type: str = "all",
) -> None:
    """
    一键构建向量库主函数

    顺序执行法条导入、案例导入、规则导入三个步骤，
    显示总体进度和耗时统计。

    Args:
        limit: 导入数量限制，0表示全量导入
        skip_laws: 是否跳过法条导入
        skip_cases: 是否跳过案例导入
        skip_rules: 是否跳过规则导入
        data_dir_laws: 法条数据目录
        data_dir_cases: 案例数据目录
        csv_file_rules: 规则CSV文件路径
        chroma_dir: ChromaDB持久化目录
        db_path: SQLite数据库路径
        filter_type: 案例筛选类型
    """
    total_start = time.time()

    logger.info("=" * 60)
    logger.info("CaseWise 向量库一键构建")
    logger.info("导入数量限制: %s", "全量" if limit == 0 else str(limit))
    logger.info("跳过法条: %s", "是" if skip_laws else "否")
    logger.info("跳过案例: %s", "是" if skip_cases else "否")
    logger.info("跳过规则: %s", "是" if skip_rules else "否")
    logger.info("=" * 60)

    # 步骤1：法条导入
    laws_time = run_step(
        step_name="法条数据导入",
        step_func=seed_laws,
        skip=skip_laws,
        data_dir=data_dir_laws,
        chroma_dir=chroma_dir,
        bm25_path="backend/data/laws/bm25_index.pkl",
        limit=limit,
    )

    # 步骤2：案例导入
    cases_time = run_step(
        step_name="案例数据导入",
        step_func=seed_cases,
        skip=skip_cases,
        data_dir=data_dir_cases,
        chroma_dir=chroma_dir,
        bm25_path="backend/data/cases/bm25_index.pkl",
        limit=limit,
        filter_type=filter_type,
    )

    # 步骤3：规则导入
    rules_time = run_step(
        step_name="合同审查规则导入",
        step_func=seed_rules,
        skip=skip_rules,
        csv_file=csv_file_rules,
        db_path=db_path,
    )

    # 总体统计
    total_elapsed = time.time() - total_start
    logger.info("=" * 60)
    logger.info("向量库构建完成 - 总体统计")
    logger.info("-" * 40)
    logger.info("法条导入耗时: %.2f 秒%s", laws_time, " (已跳过)" if skip_laws else "")
    logger.info("案例导入耗时: %.2f 秒%s", cases_time, " (已跳过)" if skip_cases else "")
    logger.info("规则导入耗时: %.2f 秒%s", rules_time, " (已跳过)" if skip_rules else "")
    logger.info("-" * 40)
    logger.info("总耗时: %.2f 秒", total_elapsed)
    logger.info("=" * 60)


def main() -> None:
    """
    脚本入口函数

    解析命令行参数并调用一键构建主函数。
    """
    parser = argparse.ArgumentParser(description="一键构建向量库")
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="导入数量限制，0表示全量导入（默认: 1000）",
    )
    parser.add_argument(
        "--skip-laws",
        action="store_true",
        default=False,
        help="跳过法条导入",
    )
    parser.add_argument(
        "--skip-cases",
        action="store_true",
        default=False,
        help="跳过案例导入",
    )
    parser.add_argument(
        "--skip-rules",
        action="store_true",
        default=False,
        help="跳过规则导入",
    )
    parser.add_argument(
        "--data-dir-laws",
        type=str,
        default="backend/data/laws",
        help="法条数据目录（默认: backend/data/laws）",
    )
    parser.add_argument(
        "--data-dir-cases",
        type=str,
        default="backend/data/cases",
        help="案例数据目录（默认: backend/data/cases）",
    )
    parser.add_argument(
        "--csv-file-rules",
        type=str,
        default="scripts/sample_rules.csv",
        help="规则CSV文件路径（默认: scripts/sample_rules.csv）",
    )
    parser.add_argument(
        "--chroma-dir",
        type=str,
        default="backend/data/chroma_db",
        help="ChromaDB持久化目录（默认: backend/data/chroma_db）",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="backend/data/casewise.db",
        help="SQLite数据库路径（默认: backend/data/casewise.db）",
    )
    parser.add_argument(
        "--filter-type",
        type=str,
        default="all",
        choices=["civil", "contract", "construction", "finance", "all"],
        help="案例筛选类型（默认: all）",
    )
    args = parser.parse_args()

    build_all(
        limit=args.limit,
        skip_laws=args.skip_laws,
        skip_cases=args.skip_cases,
        skip_rules=args.skip_rules,
        data_dir_laws=args.data_dir_laws,
        data_dir_cases=args.data_dir_cases,
        csv_file_rules=args.csv_file_rules,
        chroma_dir=args.chroma_dir,
        db_path=args.db_path,
        filter_type=args.filter_type,
    )


if __name__ == "__main__":
    main()
