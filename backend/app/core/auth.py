"""
CaseWise 法律AI工具 - 用户认证模块

提供 JWT Token 生成/验证、密码哈希/校验、角色权限校验等功能。
"""

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt

from app.config import settings

logger = logging.getLogger(__name__)

_jwt_secret = os.environ.get("JWT_SECRET_KEY")
if not _jwt_secret:
    _jwt_secret = secrets.token_urlsafe(32)
    logger.warning("JWT_SECRET_KEY 未设置，已自动生成随机密钥（重启后Token将失效，生产环境请设置环境变量）")
JWT_SECRET_KEY = _jwt_secret
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24


def hash_password(password: str) -> str:
    """
    对密码进行哈希加密

    Args:
        password: 明文密码

    Returns:
        str: 哈希后的密码
    """
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=10)).decode('utf-8')


async def hash_password_async(password: str) -> str:
    """
    异步对密码进行哈希加密（在线程池中执行，避免阻塞事件循环）

    Args:
        password: 明文密码

    Returns:
        str: 哈希后的密码
    """
    import asyncio
    return await asyncio.to_thread(hash_password, password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    校验明文密码与哈希密码是否匹配

    Args:
        plain_password: 明文密码
        hashed_password: 哈希密码

    Returns:
        bool: 匹配返回 True
    """
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


async def verify_password_async(plain_password: str, hashed_password: str) -> bool:
    """
    异步校验明文密码与哈希密码是否匹配（在线程池中执行，避免阻塞事件循环）

    Args:
        plain_password: 明文密码
        hashed_password: 哈希密码

    Returns:
        bool: 匹配返回 True
    """
    import asyncio
    return await asyncio.to_thread(verify_password, plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    生成 JWT Access Token

    Args:
        data: 要编码的数据（通常包含 user_id, role）
        expires_delta: 过期时间增量，默认使用 JWT_EXPIRE_HOURS

    Returns:
        str: JWT Token 字符串
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=JWT_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """
    解码并验证 JWT Token

    Args:
        token: JWT Token 字符串

    Returns:
        Optional[dict]: 解码后的数据，无效返回 None
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT Token 已过期")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning("JWT Token 无效: %s", str(e))
        return None
