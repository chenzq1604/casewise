"""
CaseWise 法律AI工具 - 用户数据模型

定义用户相关的请求、响应和数据库记录模型。
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class UserRole:
    """用户角色常量"""
    ADMIN = "admin"
    LAWYER = "lawyer"
    CLIENT = "client"


class LoginRequest(BaseModel):
    """
    登录请求模型

    Attributes:
        username: 用户名
        password: 密码
    """
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码")


class RegisterRequest(BaseModel):
    """
    注册请求模型

    Attributes:
        username: 用户名
        password: 密码
        role: 角色（admin/lawyer/client）
        display_name: 显示名称
    """
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    role: str = Field(default=UserRole.CLIENT, description="角色：admin/lawyer/client")
    display_name: str = Field(default="", max_length=100, description="显示名称")


class LoginResponse(BaseModel):
    """
    登录响应模型

    Attributes:
        access_token: JWT Token
        token_type: Token 类型
        user: 用户信息
    """
    access_token: str = Field(..., description="JWT Access Token")
    token_type: str = Field(default="bearer", description="Token 类型")
    user: "UserInfo" = Field(..., description="用户信息")


class UserInfo(BaseModel):
    """
    用户信息模型

    Attributes:
        id: 用户ID
        username: 用户名
        role: 角色
        display_name: 显示名称
    """
    id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    role: str = Field(..., description="角色")
    display_name: str = Field(default="", description="显示名称")


class UserRecord(BaseModel):
    """
    用户数据库记录模型

    Attributes:
        id: 用户ID
        username: 用户名
        password_hash: 密码哈希
        role: 角色
        display_name: 显示名称
        is_active: 是否启用
        created_at: 创建时间
    """
    id: Optional[int] = None
    username: str = ""
    password_hash: str = ""
    role: str = UserRole.CLIENT
    display_name: str = ""
    is_active: int = 1
    created_at: str = ""


LoginResponse.model_rebuild()
