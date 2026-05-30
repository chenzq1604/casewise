"""
CaseWise 法律AI工具 - 数据管理API路由

提供法条数据采集和管理的HTTP接口：
- POST /api/data/collect     — 启动数据采集（admin/lawyer）
- GET  /api/data/progress    — 查询采集进度
- GET  /api/data/status      — 查询ChromaDB当前数据状态
- GET  /api/data/categories  — 获取可用的法律类型列表
- POST /api/data/cancel      — 取消正在运行的采集任务（admin/lawyer）
"""

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.models.user import UserInfo, UserRole
from app.api.auth import get_current_user, require_role
from app.core.data_collector import get_data_collector, LAW_CATEGORIES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/data", tags=["数据管理"])


class CollectRequest(BaseModel):
    """数据采集请求模型"""
    categories: list[str] = Field(
        default=["civil"],
        description="要采集的法律类型列表，如 ['civil', 'labor']"
    )
    limit: int = Field(
        default=0,
        description="每类法条限制条数，0表示不限制"
    )


class CollectResponse(BaseModel):
    """数据采集响应模型"""
    task_id: str = Field(description="采集任务ID")
    message: str = Field(description="响应消息")


class CancelResponse(BaseModel):
    """取消任务响应模型"""
    message: str = Field(description="响应消息")


@router.post("/collect", response_model=CollectResponse, summary="启动数据采集")
async def start_collect(
    request: CollectRequest,
    operator: UserInfo = Depends(require_role(UserRole.ADMIN, UserRole.LAWYER)),
) -> CollectResponse:
    """
    启动法条数据采集任务，仅管理员和律师可操作

    根据选择的法律类型，在后台异步执行数据采集流程：
    获取数据 -> 解析 -> 生成向量 -> 写入ChromaDB -> 构建BM25索引。
    同一时间只能运行一个采集任务。

    Args:
        request: 采集请求，包含 categories 和 limit
        operator: 当前操作用户（admin/lawyer）

    Returns:
        CollectResponse: 包含 task_id 和启动消息

    Raises:
        HTTPException: 当已有任务运行中或参数无效时返回相应错误
    """
    collector = get_data_collector()

    if collector.progress.status == "running":
        raise HTTPException(
            status_code=409,
            detail=f"已有采集任务正在运行，任务ID: {collector.progress.task_id}"
        )

    invalid_categories = [c for c in request.categories if c not in LAW_CATEGORIES]
    if invalid_categories:
        raise HTTPException(
            status_code=400,
            detail=f"无效的法律类型: {invalid_categories}，可用类型: {list(LAW_CATEGORIES.keys())}"
        )

    async def _run_collect() -> None:
        """后台运行采集任务的内部函数"""
        await collector.collect(
            categories=request.categories,
            limit=request.limit,
        )

    asyncio.create_task(_run_collect())

    await asyncio.sleep(0.1)

    task_id = collector.progress.task_id
    logger.info("数据采集任务 %s 已启动，类别: %s，操作人: %s", task_id, request.categories, operator.username)

    return CollectResponse(
        task_id=task_id,
        message="采集任务已启动",
    )


@router.get("/progress", summary="查询采集进度")
async def get_progress(
    current_user: UserInfo = Depends(get_current_user),
) -> dict:
    """
    查询当前数据采集任务的进度

    Args:
        current_user: 当前登录用户

    Returns:
        dict: 采集进度信息
    """
    collector = get_data_collector()
    return collector.get_progress()


@router.get("/status", summary="查询数据状态")
async def get_status(
    current_user: UserInfo = Depends(get_current_user),
) -> dict:
    """
    查询 ChromaDB 当前数据状态

    Args:
        current_user: 当前登录用户

    Returns:
        dict: 包含 laws_count、cases_count、collections、last_updated
    """
    collector = get_data_collector()
    return collector.get_status()


@router.get("/categories", summary="获取法律类型列表")
async def get_categories(
    current_user: UserInfo = Depends(get_current_user),
) -> dict:
    """
    获取可用的法律类型列表

    Args:
        current_user: 当前登录用户

    Returns:
        dict: LAW_CATEGORIES 完整结构
    """
    return LAW_CATEGORIES


@router.post("/cancel", response_model=CancelResponse, summary="取消采集任务")
async def cancel_collect(
    operator: UserInfo = Depends(require_role(UserRole.ADMIN, UserRole.LAWYER)),
) -> CancelResponse:
    """
    取消正在运行的数据采集任务，仅管理员和律师可操作

    Args:
        operator: 当前操作用户（admin/lawyer）

    Returns:
        CancelResponse: 包含取消消息

    Raises:
        HTTPException: 当没有正在运行的任务时返回 400 错误
    """
    collector = get_data_collector()

    if collector.progress.status != "running":
        raise HTTPException(
            status_code=400,
            detail="当前没有正在运行的采集任务"
        )

    success = collector.cancel()
    if success:
        return CancelResponse(message="任务已取消")
    else:
        raise HTTPException(
            status_code=500,
            detail="取消任务失败"
        )
