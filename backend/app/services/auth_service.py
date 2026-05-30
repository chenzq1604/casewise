"""
CaseWise 法律AI工具 - 用户认证业务逻辑模块

处理用户注册、登录、Token验证等业务逻辑。
"""

import logging
from typing import Optional

import aiosqlite
from app.core.auth import hash_password, verify_password, verify_password_async, create_access_token, decode_access_token, hash_password_async
from app.db.database import get_db
from app.models.user import (
    LoginRequest,
    RegisterRequest,
    LoginResponse,
    UserInfo,
    UserRecord,
    UserRole,
)

logger = logging.getLogger(__name__)


class AuthService:
    """
    用户认证业务服务

    处理用户注册、登录、Token验证等业务逻辑。
    """

    def __init__(self) -> None:
        """初始化认证服务"""
        logger.info("AuthService 初始化完成")

    async def register(self, request: RegisterRequest) -> LoginResponse:
        """
        用户注册

        创建新用户，自动登录并返回Token。

        Args:
            request: 注册请求

        Returns:
            LoginResponse: 登录响应（含Token和用户信息）

        Raises:
            ValueError: 用户名已存在或角色无效
        """
        if request.role not in (UserRole.ADMIN, UserRole.LAWYER, UserRole.CLIENT):
            raise ValueError(f"无效的角色: {request.role}")

        db = await get_db()

        cursor = await db.execute(
            "SELECT id FROM users WHERE username = ?",
            (request.username,),
        )
        if await cursor.fetchone():
            raise ValueError("用户名已存在")

        password_hash = await hash_password_async(request.password)
        display_name = request.display_name or request.username

        cursor = await db.execute(
            """INSERT INTO users (username, password_hash, role, display_name)
               VALUES (?, ?, ?, ?)""",
            (request.username, password_hash, request.role, display_name),
        )
        await db.commit()
        user_id = cursor.lastrowid

        token = create_access_token({"user_id": user_id, "role": request.role, "username": request.username})

        logger.info("用户注册成功: %s (角色: %s)", request.username, request.role)

        return LoginResponse(
            access_token=token,
            user=UserInfo(
                id=user_id,
                username=request.username,
                role=request.role,
                display_name=display_name,
            ),
        )

    async def login(self, request: LoginRequest) -> LoginResponse:
        """
        用户登录

        验证用户名密码，返回JWT Token。

        Args:
            request: 登录请求

        Returns:
            LoginResponse: 登录响应（含Token和用户信息）

        Raises:
            ValueError: 用户名或密码错误
        """
        db = await get_db()
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            "SELECT id, username, password_hash, role, display_name, is_active FROM users WHERE username = ?",
            (request.username,),
        )
        row = await cursor.fetchone()

        if not row:
            raise ValueError("用户名或密码错误")

        if not row["is_active"]:
            raise ValueError("账号已被禁用")

        if not await verify_password_async(request.password, row["password_hash"]):
            raise ValueError("用户名或密码错误")

        token = create_access_token({"user_id": row["id"], "role": row["role"], "username": row["username"]})

        logger.info("用户登录成功: %s (角色: %s)", row["username"], row["role"])

        return LoginResponse(
            access_token=token,
            user=UserInfo(
                id=row["id"],
                username=row["username"],
                role=row["role"],
                display_name=row["display_name"] or row["username"],
            ),
        )

    async def get_current_user(self, token: str) -> Optional[UserInfo]:
        """
        根据Token获取当前用户信息

        Args:
            token: JWT Token

        Returns:
            Optional[UserInfo]: 用户信息，无效返回None
        """
        payload = decode_access_token(token)
        if not payload:
            return None

        user_id = payload.get("user_id")
        if not user_id:
            return None

        db = await get_db()
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            "SELECT id, username, role, display_name, is_active FROM users WHERE id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()

        if not row or not row["is_active"]:
            return None

        return UserInfo(
            id=row["id"],
            username=row["username"],
            role=row["role"],
            display_name=row["display_name"] or row["username"],
        )

    async def list_users(self) -> list[dict]:
        """
        获取用户列表（管理员功能）

        Returns:
            list[dict]: 用户列表
        """
        db = await get_db()
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            "SELECT id, username, role, display_name, is_active, created_at FROM users ORDER BY id"
        )
        rows = await cursor.fetchall()

        return [
            {
                "id": row["id"],
                "username": row["username"],
                "role": row["role"],
                "display_name": row["display_name"],
                "is_active": bool(row["is_active"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    async def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """
        修改用户密码（需验证旧密码）

        Args:
            user_id: 用户ID
            old_password: 旧密码
            new_password: 新密码

        Returns:
            bool: 修改是否成功

        Raises:
            ValueError: 旧密码错误或用户不存在
        """
        db = await get_db()
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            "SELECT id, password_hash FROM users WHERE id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()

        if not row:
            raise ValueError("用户不存在")

        if not await verify_password_async(old_password, row["password_hash"]):
            raise ValueError("旧密码错误")

        new_hash = await hash_password_async(new_password)
        await db.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_hash, user_id),
        )
        await db.commit()

        logger.info("用户 %d 修改密码成功", user_id)
        return True

    async def reset_password(self, user_id: int, new_password: str) -> bool:
        """
        重置用户密码（管理员操作，无需旧密码）

        Args:
            user_id: 目标用户ID
            new_password: 新密码

        Returns:
            bool: 重置是否成功

        Raises:
            ValueError: 用户不存在
        """
        db = await get_db()
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            "SELECT id FROM users WHERE id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()

        if not row:
            raise ValueError("用户不存在")

        new_hash = await hash_password_async(new_password)
        await db.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_hash, user_id),
        )
        await db.commit()

        logger.info("管理员重置用户 %d 密码成功", user_id)
        return True

    async def toggle_user_active(self, user_id: int, is_active: bool) -> bool:
        """
        启用/禁用用户（管理员功能）

        Args:
            user_id: 用户ID
            is_active: 是否启用

        Returns:
            bool: 操作是否成功
        """
        try:
            db = await get_db()
            await db.execute(
                "UPDATE users SET is_active = ? WHERE id = ?",
                (1 if is_active else 0, user_id),
            )
            await db.commit()
            return True
        except Exception as e:
            logger.error("切换用户状态失败: %s", str(e))
            return False


_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """
    获取认证服务单例

    Returns:
        AuthService: 认证服务实例
    """
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
