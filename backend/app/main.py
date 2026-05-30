"""
CaseWise 法律AI工具 - FastAPI 应用入口

负责创建 FastAPI 应用实例、配置 CORS、注册路由、
管理应用生命周期（启动时初始化数据库，关闭时释放资源）。
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings, BASE_DIR
from app.db.database import init_db, close_db
from app.api import chat, contract, data, review, auth, admin, report, document

# 确保日志目录存在
(BASE_DIR / "logs").mkdir(parents=True, exist_ok=True)

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            str(BASE_DIR / "logs" / "app.log"),
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    启动时：确保目录存在、初始化数据库
    关闭时：关闭数据库连接
    """
    # 启动阶段
    logger.info("CaseWise 法律AI工具启动中...")
    settings.ensure_directories()
    await init_db()
    logger.info("数据库初始化完成")

    # 检查 API Key 配置
    if not settings.ARK_API_KEY:
        logger.warning("ARK_API_KEY 未配置，LLM 相关功能将不可用")

    yield

    # 关闭阶段
    logger.info("CaseWise 法律AI工具关闭中...")
    await close_db()
    logger.info("数据库连接已关闭")


# 创建 FastAPI 应用实例
app = FastAPI(
    title="CaseWise 法律AI工具",
    description="基于 RAG 的法律AI助手系统，提供法律问答、合同审查、复核反馈等功能",
    version="0.1.0",
    lifespan=lifespan,
)


# 配置 CORS（跨域资源共享）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"] if not settings.is_production() else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 注册 API 路由
app.include_router(chat.router)
app.include_router(contract.router)
app.include_router(review.router)
app.include_router(data.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(report.router)
app.include_router(document.router)


@app.get("/", tags=["健康检查"])
async def root():
    """
    根路径健康检查接口

    返回应用基本信息和运行状态。

    Returns:
        dict: 应用名称、版本和状态
    """
    return {
        "name": "CaseWise 法律AI工具",
        "version": "0.1.0",
        "status": "running",
        "environment": settings.ENV,
    }


@app.get("/health", tags=["健康检查"])
async def health_check():
    """
    健康检查接口

    用于负载均衡器或监控系统检查服务是否正常运行。

    Returns:
        dict: 健康状态
    """
    return {"status": "healthy"}
