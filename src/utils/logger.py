"""WindAI Lab 日誌設定模組。

使用 loguru 建立結構化日誌系統，支援控制台與檔案輸出，
並提供代理上下文資訊的綁定功能。
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

# 日誌檔案存放路徑
_LOG_DIR = Path("logs")
_LOG_DIR.mkdir(exist_ok=True)

# 移除預設處理器
logger.remove()

# 控制台輸出：彩色格式，顯示時間、層級、模組與訊息
logger.add(
    sys.stderr,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{extra[agent_id]:>20}</cyan> | "
        "<white>{message}</white>"
    ),
    level="DEBUG",
    filter=lambda record: "agent_id" in record["extra"],
)

# 控制台輸出：無代理上下文的一般日誌
logger.add(
    sys.stderr,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan> | "
        "<white>{message}</white>"
    ),
    level="DEBUG",
    filter=lambda record: "agent_id" not in record["extra"],
)

# 檔案輸出：JSON 格式結構化日誌，每日輪替
logger.add(
    _LOG_DIR / "windai_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} | {message}",
    level="DEBUG",
    rotation="00:00",
    retention="30 days",
    compression="gz",
    encoding="utf-8",
)

# 錯誤專用日誌檔
logger.add(
    _LOG_DIR / "windai_error_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} | {message}",
    level="ERROR",
    rotation="00:00",
    retention="90 days",
    compression="gz",
    encoding="utf-8",
)


def get_agent_logger(agent_id: str, agent_name: str) -> logger:
    """取得綁定代理上下文的日誌記錄器。

    Args:
        agent_id: 代理唯一識別碼
        agent_name: 代理顯示名稱

    Returns:
        綁定代理上下文資訊的 loguru logger 實例
    """
    return logger.bind(agent_id=agent_id, agent_name=agent_name)


def get_logger(module_name: str) -> logger:
    """取得綁定模組名稱的日誌記錄器。

    Args:
        module_name: 模組名稱

    Returns:
        loguru logger 實例
    """
    return logger.bind(module=module_name)
