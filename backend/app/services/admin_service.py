"""
CaseWise 法律AI工具 - 系统管理业务逻辑模块

处理系统配置读取/更新、数据库备份等管理功能。
"""

import logging
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.config import BASE_DIR, settings

logger = logging.getLogger(__name__)

# 需要脱敏的配置键（包含 KEY、SECRET、PASSWORD 等敏感词）
_SENSITIVE_KEY_PATTERNS = re.compile(r"(KEY|SECRET|PASSWORD)", re.IGNORECASE)

# 备份目录
BACKUP_DIR = BASE_DIR / "backups"


class AdminService:
    """
    系统管理业务服务

    处理系统配置读取/更新、数据库备份等管理功能。
    """

    def __init__(self) -> None:
        """初始化系统管理服务"""
        logger.info("AdminService 初始化完成")

    async def get_config(self) -> dict:
        """
        获取系统配置（脱敏后返回）

        从 .env 文件读取配置项，对敏感字段进行脱敏处理。

        Returns:
            dict: 脱敏后的配置字典
        """
        env_path = BASE_DIR / ".env"
        config = {}

        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip()
                    if _SENSITIVE_KEY_PATTERNS.search(key):
                        value = self._mask_value(value)
                    config[key] = value

        # 补充 settings 中的默认配置项
        settings_items = {
            "ARK_API_KEY": settings.ARK_API_KEY,
            "ARK_API_URL": settings.ARK_API_URL,
            "ARK_CHAT_MODEL": settings.ARK_CHAT_MODEL,
            "ARK_EMBEDDING_MODEL": settings.ARK_EMBEDDING_MODEL,
            "DB_PATH": settings.DB_PATH,
            "CHROMA_PERSIST_DIR": settings.CHROMA_PERSIST_DIR,
            "UPLOAD_DIR": settings.UPLOAD_DIR,
            "ENV": settings.ENV,
            "LOG_LEVEL": settings.LOG_LEVEL,
            "PORT": str(settings.PORT),
        }

        for key, value in settings_items.items():
            if key not in config:
                if _SENSITIVE_KEY_PATTERNS.search(key):
                    config[key] = self._mask_value(value)
                else:
                    config[key] = value

        return config

    async def update_config(self, key: str, value: str) -> bool:
        """
        更新系统配置项

        将配置写入 .env 文件，如果键已存在则更新，否则追加。

        Args:
            key: 配置键名
            value: 配置值

        Returns:
            bool: 更新是否成功
        """
        env_path = BASE_DIR / ".env"

        try:
            lines = []
            found = False

            if env_path.exists():
                with open(env_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

            for i, line in enumerate(lines):
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if "=" not in stripped:
                    continue
                existing_key, _, _ = stripped.partition("=")
                if existing_key.strip() == key:
                    lines[i] = f"{key}={value}\n"
                    found = True
                    break

            if not found:
                if lines and not lines[-1].endswith("\n"):
                    lines.append("\n")
                lines.append(f"{key}={value}\n")

            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

            logger.info("配置项已更新: %s", key)
            return True
        except Exception as e:
            logger.error("更新配置项失败: %s", str(e))
            return False

    async def create_backup(self) -> Optional[str]:
        """
        创建数据库备份

        将 SQLite 数据库文件复制到 backups 目录，文件名包含时间戳。

        Returns:
            Optional[str]: 备份文件名，失败返回 None
        """
        try:
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)

            db_path = Path(settings.DB_PATH)
            if not db_path.exists():
                logger.error("数据库文件不存在: %s", db_path)
                return None

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"casewise_{timestamp}.db"
            backup_path = BACKUP_DIR / backup_filename

            shutil.copy2(str(db_path), str(backup_path))

            logger.info("数据库备份成功: %s", backup_filename)
            return backup_filename
        except Exception as e:
            logger.error("数据库备份失败: %s", str(e))
            return None

    async def list_backups(self) -> list[dict]:
        """
        获取备份文件列表

        Returns:
            list[dict]: 备份文件列表，按时间倒序排列
        """
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

        backups = []
        for f in BACKUP_DIR.iterdir():
            if f.is_file() and f.suffix == ".db":
                stat = f.stat()
                backups.append({
                    "filename": f.name,
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
                })

        backups.sort(key=lambda x: x["created_at"], reverse=True)
        return backups

    @staticmethod
    def _mask_value(value: str) -> str:
        """
        对敏感值进行脱敏处理

        保留前3位和后3位，中间用星号替代。

        Args:
            value: 原始值

        Returns:
            str: 脱敏后的值
        """
        if len(value) <= 6:
            return "***" + value[-3:] if len(value) > 3 else "***"
        return value[:3] + "***" + value[-3:]


_admin_service: Optional[AdminService] = None


def get_admin_service() -> AdminService:
    """
    获取系统管理服务单例

    Returns:
        AdminService: 系统管理服务实例
    """
    global _admin_service
    if _admin_service is None:
        _admin_service = AdminService()
    return _admin_service
