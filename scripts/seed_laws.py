"""
CaseWise 法律AI工具 - 法条数据导入脚本

从JSON格式的法条语料库导入到ChromaDB，同时建立BM25索引。
支持Parent-Child结构：child是法条的一款，parent是完整法条。
支持断点续传（已导入的跳过）。

用法：
    conda activate casewise
    python scripts/seed_laws.py --data-dir backend/data/laws --limit 100
    python scripts/seed_laws.py --data-dir backend/data/laws --limit 0   # 全量导入
"""

import argparse
import json
import logging
import os
import pickle
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
logger = logging.getLogger("seed_laws")

# ---------- 常量 ----------
# 每批embedding的条数
BATCH_SIZE = 50
# embedding限流重试最大次数
MAX_RETRIES = 5
# 限流重试基础等待秒数
RETRY_BASE_DELAY = 2
# ChromaDB collection名称
COLLECTION_CHILD = "laws_child"
COLLECTION_PARENT = "laws_parent"


def get_embedding_client() -> OpenAI:
    """
    创建火山方舟Embedding API的OpenAI兼容客户端

    从环境变量 ARK_API_KEY 读取API密钥，
    使用火山方舟的兼容接口地址。

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
    生产环境建议替换为jieba等专业分词工具。

    Args:
        text: 待分词的文本

    Returns:
        list[str]: 分词结果列表
    """
    tokens = []
    current_word = ""
    for char in text:
        if "\u4e00" <= char <= "\u9fff":
            # 中文字符：先提交当前英文词，再将中文字符作为独立token
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


def batch_embed(
    client: OpenAI,
    texts: list[str],
    model: str = "doubao-embedding-vision",
) -> Optional[list[list[float]]]:
    """
    批量获取文本向量，遇到限流自动重试

    每次调用最多处理BATCH_SIZE条文本，
    遇到429限流错误时自动退避重试。

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
                # 限流：指数退避重试
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


def load_law_files(data_dir: str) -> list[dict]:
    """
    从指定目录加载所有法条JSON文件

    递归扫描data_dir下的所有.json文件，
    每个文件应包含一个法条列表（JSON数组）。

    Args:
        data_dir: 法条JSON文件所在目录

    Returns:
        list[dict]: 所有法条数据的列表
    """
    data_path = Path(data_dir)
    if not data_path.exists():
        logger.error("法条数据目录不存在: %s", data_dir)
        return []

    all_laws = []
    json_files = list(data_path.rglob("*.json"))
    logger.info("在 %s 下找到 %d 个JSON文件", data_dir, len(json_files))

    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 支持两种格式：直接列表 或 {"laws": [...]} 包装
            if isinstance(data, list):
                laws = data
            elif isinstance(data, dict) and "laws" in data:
                laws = data["laws"]
            else:
                logger.warning("文件 %s 格式不识别，跳过", json_file)
                continue
            all_laws.extend(laws)
            logger.info("从 %s 加载了 %d 条法条", json_file.name, len(laws))
        except Exception as e:
            logger.error("加载文件 %s 失败: %s", json_file, str(e))

    return all_laws


def split_law_to_parent_child(law: dict) -> tuple[str, list[str], dict]:
    """
    将一条法条拆分为Parent-Child结构

    Parent是完整法条文本，Child是法条的各款内容。
    如果法条没有分款，则整条作为一个Child。

    Args:
        law: 法条数据字典，包含 law_id, title, content 等字段

    Returns:
        tuple: (parent_text, child_texts_list, metadata)
            - parent_text: 完整法条文本
            - child_texts_list: 各款文本列表
            - metadata: 法条元数据
    """
    law_id = law.get("law_id", "")
    title = law.get("title", "")
    content = law.get("content", "")
    chapter = law.get("chapter", "")
    section = law.get("section", "")
    effective_date = law.get("effective_date", "")

    # 构建完整法条文本（Parent）
    parent_text = f"{title}\n{content}" if title else content

    # 构建元数据
    metadata = {
        "law_id": law_id,
        "title": title,
        "chapter": chapter,
        "section": section,
        "effective_date": effective_date,
        "type": "law",
    }

    # 拆分为Child（按款拆分）
    # 尝试按常见分款模式拆分：数字+顿号开头，如"一、""二、"
    # 或者按换行+数字编号拆分
    child_texts = []

    # 先尝试按"数字、"格式拆分（如"一、""二、""三、"）
    import re

    # 匹配中文数字序号分款
    clause_pattern = re.compile(r"[一二三四五六七八九十]+、")
    clauses = clause_pattern.split(content)

    if len(clauses) > 1:
        # 有分款
        matches = clause_pattern.findall(content)
        for i, clause in enumerate(clauses[1:]):  # 跳过第一个（分款前的内容）
            prefix = matches[i] if i < len(matches) else ""
            child_text = f"{title} {prefix}{clause.strip()}" if title else f"{prefix}{clause.strip()}"
            child_texts.append(child_text)
    else:
        # 尝试按阿拉伯数字+点号拆分（如"1.""2."）
        digit_pattern = re.compile(r"(?=\n\d+[\.\、])")
        parts = digit_pattern.split(content)
        if len(parts) > 1:
            for part in parts:
                part = part.strip()
                if part:
                    child_text = f"{title} {part}" if title else part
                    child_texts.append(child_text)
        else:
            # 无法拆分，整条作为一个Child
            child_text = f"{title} {content}" if title else content
            child_texts.append(child_text)

    return parent_text, child_texts, metadata


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

    # 分批获取所有ID
    existing_ids = set()
    batch_size = 5000
    offset = 0
    while offset < count:
        results = collection.get(
            include=[], limit=batch_size, offset=offset
        )
        existing_ids.update(results["ids"])
        offset += batch_size

    logger.info("Collection '%s' 已有 %d 条记录", collection.name, len(existing_ids))
    return existing_ids


def build_bm25_index(
    corpus: list[str],
    output_path: str,
) -> None:
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

    # 保存索引
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


def seed_laws(
    data_dir: str = "backend/data/laws",
    chroma_dir: str = "backend/data/chroma_db",
    bm25_path: str = "backend/data/laws/bm25_index.pkl",
    limit: int = 0,
) -> None:
    """
    法条数据导入主函数

    从JSON文件加载法条数据，生成向量并导入ChromaDB，
    同时构建BM25索引。支持Parent-Child结构和断点续传。

    Args:
        data_dir: 法条JSON文件目录
        chroma_dir: ChromaDB持久化目录
        bm25_path: BM25索引保存路径
        limit: 导入数量限制，0表示全量导入
    """
    # 转换为绝对路径
    if not Path(data_dir).is_absolute():
        data_dir = str(PROJECT_ROOT / data_dir)
    if not Path(chroma_dir).is_absolute():
        chroma_dir = str(PROJECT_ROOT / chroma_dir)
    if not Path(bm25_path).is_absolute():
        bm25_path = str(PROJECT_ROOT / bm25_path)

    logger.info("=" * 60)
    logger.info("开始法条数据导入")
    logger.info("数据目录: %s", data_dir)
    logger.info("ChromaDB目录: %s", chroma_dir)
    logger.info("BM25索引路径: %s", bm25_path)
    logger.info("导入数量限制: %s", "全量" if limit == 0 else str(limit))
    logger.info("=" * 60)

    # 1. 加载法条数据
    laws = load_law_files(data_dir)
    if not laws:
        logger.warning("未找到法条数据，退出")
        return

    # 限制导入数量
    if limit > 0:
        laws = laws[:limit]
        logger.info("限制导入数量为: %d", limit)

    logger.info("共加载 %d 条法条", len(laws))

    # 2. 初始化客户端
    embedding_client = get_embedding_client()
    chroma_client = get_chroma_client(chroma_dir)

    # 获取或创建collection
    collection_child = chroma_client.get_or_create_collection(
        name=COLLECTION_CHILD,
        metadata={"description": "法条子chunk（款级别），用于精确检索"},
    )
    collection_parent = chroma_client.get_or_create_collection(
        name=COLLECTION_PARENT,
        metadata={"description": "法条父chunk（完整法条），用于提供上下文"},
    )

    # 3. 获取已导入的ID（断点续传）
    existing_child_ids = get_existing_ids(collection_child)
    existing_parent_ids = get_existing_ids(collection_parent)

    # 4. 拆分Parent-Child并过滤已导入的
    all_parent_texts = []
    all_parent_metas = []
    all_parent_ids = []
    all_child_texts = []
    all_child_metas = []
    all_child_ids = []

    for law in laws:
        law_id = law.get("law_id", "")
        parent_text, child_texts, metadata = split_law_to_parent_child(law)

        # Parent
        parent_doc_id = f"law_parent_{law_id}"
        if parent_doc_id not in existing_parent_ids:
            all_parent_texts.append(parent_text)
            all_parent_metas.append(metadata)
            all_parent_ids.append(parent_doc_id)

        # Children
        for idx, child_text in enumerate(child_texts):
            child_doc_id = f"law_child_{law_id}_{idx}"
            if child_doc_id not in existing_child_ids:
                child_meta = {**metadata, "parent_id": parent_doc_id, "child_index": idx}
                all_child_texts.append(child_text)
                all_child_metas.append(child_meta)
                all_child_ids.append(child_doc_id)

    logger.info(
        "待导入: %d 条Parent, %d 条Child",
        len(all_parent_texts),
        len(all_child_texts),
    )

    if not all_parent_texts and not all_child_texts:
        logger.info("所有法条已导入，无需更新")
        return

    # 5. 批量生成Embedding并导入ChromaDB
    # 导入Parent chunks
    if all_parent_texts:
        logger.info("开始导入Parent chunks...")
        for i in tqdm(
            range(0, len(all_parent_texts), BATCH_SIZE),
            desc="导入Parent",
        ):
            batch_texts = all_parent_texts[i : i + BATCH_SIZE]
            batch_metas = all_parent_metas[i : i + BATCH_SIZE]
            batch_ids = all_parent_ids[i : i + BATCH_SIZE]

            embeddings = batch_embed(embedding_client, batch_texts)
            if embeddings is None:
                logger.error("Parent batch %d Embedding失败，跳过", i // BATCH_SIZE)
                continue

            collection_parent.add(
                ids=batch_ids,
                embeddings=embeddings,
                documents=batch_texts,
                metadatas=batch_metas,
            )

        logger.info("Parent chunks导入完成，总计: %d", len(all_parent_texts))

    # 导入Child chunks
    if all_child_texts:
        logger.info("开始导入Child chunks...")
        for i in tqdm(
            range(0, len(all_child_texts), BATCH_SIZE),
            desc="导入Child",
        ):
            batch_texts = all_child_texts[i : i + BATCH_SIZE]
            batch_metas = all_child_metas[i : i + BATCH_SIZE]
            batch_ids = all_child_ids[i : i + BATCH_SIZE]

            embeddings = batch_embed(embedding_client, batch_texts)
            if embeddings is None:
                logger.error("Child batch %d Embedding失败，跳过", i // BATCH_SIZE)
                continue

            collection_child.add(
                ids=batch_ids,
                embeddings=embeddings,
                documents=batch_texts,
                metadatas=batch_metas,
            )

        logger.info("Child chunks导入完成，总计: %d", len(all_child_texts))

    # 6. 构建BM25索引（使用Child chunks的文本）
    # 获取所有已存在的child文档文本
    all_bm25_corpus = []

    # 先获取已有的文档
    child_count = collection_child.count()
    if child_count > 0:
        batch_size = 5000
        offset = 0
        while offset < child_count:
            results = collection_child.get(
                include=["documents"], limit=batch_size, offset=offset
            )
            all_bm25_corpus.extend(results["documents"])
            offset += batch_size

    build_bm25_index(all_bm25_corpus, bm25_path)

    # 7. 输出统计
    logger.info("=" * 60)
    logger.info("法条数据导入完成")
    logger.info("Parent collection '%s': %d 条", COLLECTION_PARENT, collection_parent.count())
    logger.info("Child collection '%s': %d 条", COLLECTION_CHILD, collection_child.count())
    logger.info("BM25索引语料数: %d", len(all_bm25_corpus))
    logger.info("=" * 60)


def main() -> None:
    """
    脚本入口函数

    解析命令行参数并调用法条导入主函数。
    """
    parser = argparse.ArgumentParser(description="法条数据导入脚本")
    parser.add_argument(
        "--data-dir",
        type=str,
        default="backend/data/laws",
        help="法条JSON文件目录（默认: backend/data/laws）",
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
        default="backend/data/laws/bm25_index.pkl",
        help="BM25索引保存路径（默认: backend/data/laws/bm25_index.pkl）",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="导入数量限制，0表示全量导入（默认: 0）",
    )
    args = parser.parse_args()

    seed_laws(
        data_dir=args.data_dir,
        chroma_dir=args.chroma_dir,
        bm25_path=args.bm25_path,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
