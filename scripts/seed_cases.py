"""
CaseWise 法律AI工具 - 案例数据导入脚本

从CAIL2018等数据集的JSON文件导入案例到ChromaDB，同时建立BM25索引。
支持脱敏处理（去除当事人姓名、身份证号等个人信息）和断点续传。

用法：
    conda activate casewise
    python scripts/seed_cases.py --data-dir backend/data/cases --limit 100
    python scripts/seed_cases.py --data-dir backend/data/cases --filter-type civil --limit 0
"""

import argparse
import json
import logging
import os
import pickle
import re
import sys
import time
from pathlib import Path
from typing import Optional

# 将项目根目录加入 sys.path，以便导入 backend 模块
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

import chromadb
from openai import OpenAI
from rank_bm25 import BM25Okapi
from tqdm import tqdm

# ---------- 日志配置 ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("seed_cases")

# ---------- 常量 ----------
BATCH_SIZE = 50
MAX_RETRIES = 5
RETRY_BASE_DELAY = 2
COLLECTION_CASES = "cases"

# ---------- 脱敏正则 ----------
# 身份证号模式：18位或15位数字+X
RE_ID_CARD = re.compile(r"\b\d{6}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b")
# 15位身份证号
RE_ID_CARD_15 = re.compile(r"\b\d{6}\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}\b")
# 手机号模式：1开头11位数字
RE_PHONE = re.compile(r"\b1[3-9]\d{9}\b")
# 银行卡号模式：16-19位连续数字
RE_BANK_CARD = re.compile(r"\b\d{16,19}\b")
# 姓名模式：原告/被告/第三人 + 姓名（2-4个中文字符）
RE_PLAINTIFF_NAME = re.compile(r"(?:原告|上诉人|申请人|申诉人)[：:]\s*([^\s，,。.；;]{2,4})")
RE_DEFENDANT_NAME = re.compile(r"(?:被告|被上诉人|被申请人|被申诉人)[：:]\s*([^\s，,。.；;]{2,4})")


def get_embedding_client() -> OpenAI:
    """
    创建火山方舟Embedding API的OpenAI兼容客户端

    从环境变量 ARK_API_KEY 读取API密钥。

    Returns:
        OpenAI: 配置好的OpenAI客户端实例

    Raises:
        ValueError: 当环境变量 ARK_API_KEY 未设置时抛出
    """
    api_key = os.environ.get("ARK_API_KEY", "")
    if not api_key:
        raise ValueError("环境变量 ARK_API_KEY 未设置，请先设置后再运行")
    base_url = os.environ.get(
        "ARK_API_URL", "https://ark.cn-beijing.volces.com/api/coding/v3"
    )
    client = OpenAI(base_url=base_url, api_key=api_key)
    logger.info("Embedding客户端初始化完成，base_url=%s", base_url)
    return client


def get_chroma_client(persist_dir: str) -> chromadb.PersistentClient:
    """
    创建ChromaDB持久化客户端

    Args:
        persist_dir: ChromaDB数据持久化目录路径

    Returns:
        chromadb.PersistentClient: ChromaDB持久化客户端实例
    """
    Path(persist_dir).mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=persist_dir)
    logger.info("ChromaDB客户端初始化完成，路径: %s", persist_dir)
    return client


def tokenize_chinese(text: str) -> list[str]:
    """
    中文文本分词（简易字符级分词）

    对中文文本按字符切分，同时保留英文单词的完整性。

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


def batch_embed(
    client: OpenAI,
    texts: list[str],
    model: str = "doubao-embedding-vision",
) -> Optional[list[list[float]]]:
    """
    批量获取文本向量，遇到限流自动重试

    Args:
        client: OpenAI兼容客户端
        texts: 需要向量化的文本列表
        model: 使用的embedding模型名称

    Returns:
        list[list[float]] | None: 文本向量列表，失败时返回None
    """
    for attempt in range(MAX_RETRIES):
        try:
            response = client.embeddings.create(model=model, input=texts)
            embeddings = [item.embedding for item in response.data]
            logger.debug("批量Embedding成功，数量: %d", len(embeddings))
            return embeddings
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "rate" in error_str.lower():
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning(
                    "Embedding限流，第%d次重试，等待%d秒...", attempt + 1, delay
                )
                time.sleep(delay)
            else:
                logger.error("Embedding生成失败: %s", error_str)
                return None
    logger.error("Embedding生成失败：已达最大重试次数 %d", MAX_RETRIES)
    return None


def desensitize_text(text: str) -> str:
    """
    脱敏处理：去除当事人姓名、身份证号、手机号等个人信息

    替换规则：
    - 身份证号 -> ***
    - 手机号 -> ***
    - 银行卡号 -> ***
    - 原告/被告姓名 -> 张三/李四

    Args:
        text: 原始文本

    Returns:
        str: 脱敏后的文本
    """
    if not text:
        return text

    # 替换身份证号
    text = RE_ID_CARD.sub("***", text)
    text = RE_ID_CARD_15.sub("***", text)

    # 替换手机号
    text = RE_PHONE.sub("***", text)

    # 替换银行卡号（注意不要误替换短数字）
    text = RE_BANK_CARD.sub("***", text)

    # 替换原告姓名
    text = RE_PLAINTIFF_NAME.sub(lambda m: m.group(0).replace(m.group(1), "张三"), text)

    # 替换被告姓名
    text = RE_DEFENDANT_NAME.sub(lambda m: m.group(0).replace(m.group(1), "李四"), text)

    return text


def load_case_files(data_dir: str, filter_type: str = "all") -> list[dict]:
    """
    从指定目录加载所有案例JSON文件

    递归扫描data_dir下的所有.json文件，
    支持按案例类型筛选。

    Args:
        data_dir: 案例JSON文件所在目录
        filter_type: 筛选类型，可选 civil/contract/construction/finance/all

    Returns:
        list[dict]: 筛选后的案例数据列表
    """
    data_path = Path(data_dir)
    if not data_path.exists():
        logger.error("案例数据目录不存在: %s", data_dir)
        return []

    # 类型映射：筛选参数 -> 案例类型关键词
    type_keywords = {
        "civil": ["民事", "civil"],
        "contract": ["合同", "contract"],
        "construction": ["建设工程", "construction"],
        "finance": ["金融", "借款", "finance"],
    }

    all_cases = []
    json_files = list(data_path.rglob("*.json"))
    logger.info("在 %s 下找到 %d 个JSON文件", data_dir, len(json_files))

    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 支持两种格式：直接列表 或 {"cases": [...]} 包装
            if isinstance(data, list):
                cases = data
            elif isinstance(data, dict) and "cases" in data:
                cases = data["cases"]
            else:
                cases = [data]  # 单条案例

            # 按类型筛选
            if filter_type != "all" and filter_type in type_keywords:
                keywords = type_keywords[filter_type]
                filtered = []
                for case in cases:
                    case_type = case.get("case_type", "")
                    title = case.get("title", "")
                    # 在case_type和title中搜索关键词
                    search_text = f"{case_type} {title}".lower()
                    if any(kw.lower() in search_text for kw in keywords):
                        filtered.append(case)
                cases = filtered

            all_cases.extend(cases)
            logger.info("从 %s 加载了 %d 条案例", json_file.name, len(cases))
        except Exception as e:
            logger.error("加载文件 %s 失败: %s", json_file, str(e))

    return all_cases


def format_case_text(case: dict) -> str:
    """
    将案例数据格式化为可检索的文本

    将案例的各字段拼接为一段完整文本，
    用于向量化和BM25索引。

    Args:
        case: 案例数据字典

    Returns:
        str: 格式化后的案例文本
    """
    title = case.get("title", "")
    case_type = case.get("case_type", "")
    fact = case.get("fact_description", "")
    judgment = case.get("judgment", "")
    court = case.get("court", "")
    date = case.get("date", "")

    parts = []
    if title:
        parts.append(f"案例标题：{title}")
    if case_type:
        parts.append(f"案件类型：{case_type}")
    if fact:
        parts.append(f"案件事实：{fact}")
    if judgment:
        parts.append(f"裁判结果：{judgment}")
    if court:
        parts.append(f"审理法院：{court}")
    if date:
        parts.append(f"裁判日期：{date}")

    return "\n".join(parts)


def get_existing_ids(collection: chromadb.Collection) -> set[str]:
    """
    获取collection中已存在的所有文档ID，用于断点续传

    Args:
        collection: ChromaDB集合

    Returns:
        set[str]: 已存在的文档ID集合
    """
    count = collection.count()
    if count == 0:
        return set()

    existing_ids = set()
    batch_size = 5000
    offset = 0
    while offset < count:
        results = collection.get(include=[], limit=batch_size, offset=offset)
        existing_ids.update(results["ids"])
        offset += batch_size

    logger.info("Collection '%s' 已有 %d 条记录", collection.name, len(existing_ids))
    return existing_ids


def build_bm25_index(corpus: list[str], output_path: str) -> None:
    """
    构建BM25索引并序列化保存到文件

    Args:
        corpus: 文档文本列表
        output_path: BM25索引保存路径
    """
    if not corpus:
        logger.warning("语料库为空，跳过BM25索引构建")
        return

    logger.info("开始构建BM25索引，语料数量: %d", len(corpus))
    tokenized_corpus = [tokenize_chinese(text) for text in tqdm(corpus, desc="分词中")]
    bm25 = BM25Okapi(tokenized_corpus)

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "wb") as f:
        pickle.dump(
            {
                "bm25": bm25,
                "corpus": corpus,
            },
            f,
        )
    logger.info("BM25索引已保存到: %s", output_path)


def seed_cases(
    data_dir: str = "backend/data/cases",
    chroma_dir: str = "backend/data/chroma_db",
    bm25_path: str = "backend/data/cases/bm25_index.pkl",
    limit: int = 0,
    filter_type: str = "all",
) -> None:
    """
    案例数据导入主函数

    从JSON文件加载案例数据，进行脱敏处理后生成向量并导入ChromaDB，
    同时构建BM25索引。支持断点续传。

    Args:
        data_dir: 案例JSON文件目录
        chroma_dir: ChromaDB持久化目录
        bm25_path: BM25索引保存路径
        limit: 导入数量限制，0表示全量导入
        filter_type: 筛选案例类型，可选 civil/contract/construction/finance/all
    """
    # 转换为绝对路径
    if not Path(data_dir).is_absolute():
        data_dir = str(PROJECT_ROOT / data_dir)
    if not Path(chroma_dir).is_absolute():
        chroma_dir = str(PROJECT_ROOT / chroma_dir)
    if not Path(bm25_path).is_absolute():
        bm25_path = str(PROJECT_ROOT / bm25_path)

    logger.info("=" * 60)
    logger.info("开始案例数据导入")
    logger.info("数据目录: %s", data_dir)
    logger.info("ChromaDB目录: %s", chroma_dir)
    logger.info("BM25索引路径: %s", bm25_path)
    logger.info("导入数量限制: %s", "全量" if limit == 0 else str(limit))
    logger.info("筛选类型: %s", filter_type)
    logger.info("=" * 60)

    # 1. 加载案例数据
    cases = load_case_files(data_dir, filter_type)
    if not cases:
        logger.warning("未找到案例数据，退出")
        return

    # 限制导入数量
    if limit > 0:
        cases = cases[:limit]
        logger.info("限制导入数量为: %d", limit)

    logger.info("共加载 %d 条案例", len(cases))

    # 2. 初始化客户端
    embedding_client = get_embedding_client()
    chroma_client = get_chroma_client(chroma_dir)

    # 获取或创建collection
    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_CASES,
        metadata={"description": "案例向量索引，用于相似案例检索"},
    )

    # 3. 获取已导入的ID（断点续传）
    existing_ids = get_existing_ids(collection)

    # 4. 脱敏处理并准备导入数据
    all_texts = []
    all_metas = []
    all_ids = []

    for case in tqdm(cases, desc="脱敏处理"):
        case_id = case.get("case_id", "")
        doc_id = f"case_{case_id}"

        # 跳过已导入的
        if doc_id in existing_ids:
            continue

        # 脱敏处理
        fact = desensitize_text(case.get("fact_description", ""))
        judgment = desensitize_text(case.get("judgment", ""))

        # 构建脱敏后的案例对象
        sanitized_case = {
            **case,
            "fact_description": fact,
            "judgment": judgment,
        }

        # 格式化为可检索文本
        text = format_case_text(sanitized_case)

        # 构建元数据
        metadata = {
            "case_id": case_id,
            "case_type": case.get("case_type", ""),
            "court": case.get("court", ""),
            "date": case.get("date", ""),
            "type": "case",
        }

        # 关联法条信息
        law_articles = case.get("law_articles", [])
        if law_articles:
            if isinstance(law_articles, list):
                metadata["law_articles"] = json.dumps(
                    law_articles, ensure_ascii=False
                )
            else:
                metadata["law_articles"] = str(law_articles)

        all_texts.append(text)
        all_metas.append(metadata)
        all_ids.append(doc_id)

    logger.info("待导入: %d 条案例（已跳过 %d 条）", len(all_texts), len(cases) - len(all_texts))

    if not all_texts:
        logger.info("所有案例已导入，无需更新")
        return

    # 5. 批量生成Embedding并导入ChromaDB
    logger.info("开始导入案例到ChromaDB...")
    for i in tqdm(
        range(0, len(all_texts), BATCH_SIZE),
        desc="导入案例",
    ):
        batch_texts = all_texts[i : i + BATCH_SIZE]
        batch_metas = all_metas[i : i + BATCH_SIZE]
        batch_ids = all_ids[i : i + BATCH_SIZE]

        embeddings = batch_embed(embedding_client, batch_texts)
        if embeddings is None:
            logger.error("案例 batch %d Embedding失败，跳过", i // BATCH_SIZE)
            continue

        collection.add(
            ids=batch_ids,
            embeddings=embeddings,
            documents=batch_texts,
            metadatas=batch_metas,
        )

    logger.info("案例导入完成，总计: %d", len(all_texts))

    # 6. 构建BM25索引
    all_bm25_corpus = []

    # 获取所有已存在的文档文本
    case_count = collection.count()
    if case_count > 0:
        batch_size = 5000
        offset = 0
        while offset < case_count:
            results = collection.get(
                include=["documents"], limit=batch_size, offset=offset
            )
            all_bm25_corpus.extend(results["documents"])
            offset += batch_size

    build_bm25_index(all_bm25_corpus, bm25_path)

    # 7. 输出统计
    logger.info("=" * 60)
    logger.info("案例数据导入完成")
    logger.info("Collection '%s': %d 条", COLLECTION_CASES, collection.count())
    logger.info("BM25索引语料数: %d", len(all_bm25_corpus))
    logger.info("=" * 60)


def main() -> None:
    """
    脚本入口函数

    解析命令行参数并调用案例导入主函数。
    """
    parser = argparse.ArgumentParser(description="案例数据导入脚本")
    parser.add_argument(
        "--data-dir",
        type=str,
        default="backend/data/cases",
        help="案例JSON文件目录（默认: backend/data/cases）",
    )
    parser.add_argument(
        "--chroma-dir",
        type=str,
        default="backend/data/chroma_db",
        help="ChromaDB持久化目录（默认: backend/data/chroma_db）",
    )
    parser.add_argument(
        "--bm25-path",
        type=str,
        default="backend/data/cases/bm25_index.pkl",
        help="BM25索引保存路径（默认: backend/data/cases/bm25_index.pkl）",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="导入数量限制，0表示全量导入（默认: 0）",
    )
    parser.add_argument(
        "--filter-type",
        type=str,
        default="all",
        choices=["civil", "contract", "construction", "finance", "all"],
        help="筛选案例类型（默认: all）",
    )
    args = parser.parse_args()

    seed_cases(
        data_dir=args.data_dir,
        chroma_dir=args.chroma_dir,
        bm25_path=args.bm25_path,
        limit=args.limit,
        filter_type=args.filter_type,
    )


if __name__ == "__main__":
    main()
