"""
CaseWise 法律AI工具 - 用户认证API路由

提供用户注册、登录、获取当前用户信息等接口。
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel

from app.models.user import LoginRequest, RegisterRequest, LoginResponse, UserInfo, UserRole
from app.services.auth_service import get_auth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["用户认证"])


async def get_current_user(authorization: Optional[str] = Header(None)) -> UserInfo:
    """
    从请求头中提取并验证当前用户

    作为FastAPI依赖注入使用，需要认证的接口可引用此函数。

    Args:
        authorization: Authorization 请求头

    Returns:
        UserInfo: 当前用户信息

    Raises:
        HTTPException: 未提供Token或Token无效
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证Token")

    token = authorization[7:]
    auth_service = get_auth_service()
    user = await auth_service.get_current_user(token)

    if not user:
        raise HTTPException(status_code=401, detail="Token无效或已过期")

    return user


def require_role(*allowed_roles: str):
    """
    创建角色权限校验依赖

    用法: current_user: UserInfo = Depends(require_role("admin", "lawyer"))

    Args:
        allowed_roles: 允许的角色列表

    Returns:
        依赖函数
    """
    async def _check_role(current_user: UserInfo = Depends(get_current_user)) -> UserInfo:
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="权限不足")
        return current_user

    return _check_role


@router.post("/register", response_model=LoginResponse, summary="用户注册")
async def register(request: RegisterRequest) -> LoginResponse:
    """
    用户注册接口

    自助注册仅允许创建客户角色，管理员/律师账号需由管理员创建。

    Args:
        request: 注册请求

    Returns:
        LoginResponse: 登录响应
    """
    if request.role not in (UserRole.CLIENT,):
        raise HTTPException(status_code=403, detail="自助注册仅允许客户角色，其他角色请联系管理员创建")
    try:
        auth_service = get_auth_service()
        return await auth_service.register(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("注册接口异常: %s", str(e))
        raise HTTPException(status_code=500, detail="注册服务异常")


@router.post("/login", response_model=LoginResponse, summary="用户登录")
async def login(request: LoginRequest) -> LoginResponse:
    """
    用户登录接口

    验证用户名密码，返回JWT Token。

    Args:
        request: 登录请求

    Returns:
        LoginResponse: 登录响应
    """
    try:
        auth_service = get_auth_service()
        return await auth_service.login(request)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error("登录接口异常: %s", str(e))
        raise HTTPException(status_code=500, detail="登录服务异常")


@router.get("/me", response_model=UserInfo, summary="获取当前用户信息")
async def get_me(current_user: UserInfo = Depends(get_current_user)) -> UserInfo:
    """
    获取当前登录用户信息

    需要在请求头中携带 Bearer Token。

    Returns:
        UserInfo: 当前用户信息
    """
    return current_user


@router.get("/users", summary="获取用户列表（管理员）")
async def list_users(admin: UserInfo = Depends(require_role(UserRole.ADMIN))) -> list[dict]:
    """
    获取用户列表，仅管理员可访问

    Args:
        admin: 当前管理员用户（通过依赖注入校验）

    Returns:
        list[dict]: 用户列表
    """
    auth_service = get_auth_service()
    return await auth_service.list_users()


class ToggleActiveRequest(BaseModel):
    """切换用户启用状态请求"""
    is_active: bool


@router.post("/users/{user_id}/toggle", summary="启用/禁用用户（管理员）")
async def toggle_user(
    user_id: int,
    request: ToggleActiveRequest,
    admin: UserInfo = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    """
    启用或禁用用户账号，仅管理员可操作

    Args:
        user_id: 目标用户ID
        request: 启用/禁用请求
        admin: 当前管理员用户

    Returns:
        dict: 操作结果
    """
    auth_service = get_auth_service()
    success = await auth_service.toggle_user_active(user_id, request.is_active)
    if success:
        return {"message": f"用户已{'启用' if request.is_active else '禁用'}"}
    raise HTTPException(status_code=500, detail="操作失败")
