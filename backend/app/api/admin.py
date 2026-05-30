"""
CaseWise 法律AI工具 - 系统管理API路由

提供系统配置管理、数据库备份等管理员接口。
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.models.user import UserInfo, UserRole
from app.api.auth import require_role
from app.services.admin_service import get_admin_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["系统管理"])


class BatchUpdateConfigRequest(BaseModel):
    """批量更新配置请求"""
    items: dict[str, str] = Field(..., description="配置键值对")


@router.get("/config", summary="获取系统配置")
async def get_config(
    admin: UserInfo = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    """
    获取系统配置（脱敏后返回），仅管理员可访问

    Args:
        admin: 当前管理员用户

    Returns:
        dict: 脱敏后的系统配置
    """
    admin_service = get_admin_service()
    config = await admin_service.get_config()
    return config


@router.put("/config", summary="批量更新系统配置")
async def update_config(
    request: BatchUpdateConfigRequest,
    admin: UserInfo = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    """
    批量更新系统配置项，仅管理员可操作

    Args:
        request: 批量更新配置请求，items为键值对字典
        admin: 当前管理员用户

    Returns:
        dict: 操作结果
    """
    admin_service = get_admin_service()
    updated_keys = []
    for key, value in request.items.items():
        success = await admin_service.update_config(key, value)
        if success:
            updated_keys.append(key)
    return {"message": f"已更新 {len(updated_keys)} 个配置项", "updated_keys": updated_keys}


@router.post("/backup", summary="触发数据库备份")
async def create_backup(
    admin: UserInfo = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    """
    触发数据库备份，仅管理员可操作

    Args:
        admin: 当前管理员用户

    Returns:
        dict: 备份结果，包含备份文件名
    """
    admin_service = get_admin_service()
    backup_filename = await admin_service.create_backup()
    if backup_filename:
        return {"message": "备份成功", "filename": backup_filename}
    raise HTTPException(status_code=500, detail="数据库备份失败")


@router.get("/backups", summary="获取备份列表")
async def list_backups(
    admin: UserInfo = Depends(require_role(UserRole.ADMIN)),
) -> list[dict]:
    """
    获取数据库备份文件列表，仅管理员可访问

    Args:
        admin: 当前管理员用户

    Returns:
        list[dict]: 备份文件列表
    """
    admin_service = get_admin_service()
    backups = await admin_service.list_backups()
    return backups
