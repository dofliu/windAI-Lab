"""WindAI Lab 全域設定模組。

使用 pydantic-settings 管理環境變數與應用程式設定，
支援從 .env 檔案載入設定值，並提供單一進入點取得設定實例。
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 專案根目錄
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """應用程式設定，優先從環境變數讀取，其次使用預設值。"""

    model_config = SettingsConfigDict(
        env_prefix="WINDAI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    # ── 伺服器 ──
    host: str = Field(default="0.0.0.0", description="API 伺服器綁定位址")
    port: int = Field(default=8000, description="API 伺服器埠號")
    debug: bool = Field(default=False, description="偵錯模式")

    # ── 資料路徑 ──
    data_root: Path = Field(
        default=PROJECT_ROOT / "data",
        description="資料根目錄",
    )
    model_registry: Path = Field(
        default=PROJECT_ROOT / "models" / "registry",
        description="模型註冊表路徑",
    )

    # ── MLflow ──
    mlflow_tracking_uri: str = Field(
        default="http://localhost:5000",
        validation_alias="MLFLOW_TRACKING_URI",
        description="MLflow tracking server URI",
    )

    # ── 資料庫（Phase 2 預留） ──
    database_url: str = Field(
        default="sqlite:///windai.db",
        description="主資料庫連線字串",
    )

    # ── 應用程式 ──
    app_name: str = "WindAI Lab"
    app_version: str = "0.2.0"
    log_level: str = Field(default="DEBUG", description="日誌等級")

    @property
    def data_raw(self) -> Path:
        """原始資料目錄。"""
        return self.data_root / "raw"

    @property
    def data_processed(self) -> Path:
        """處理後資料目錄。"""
        return self.data_root / "processed"

    @property
    def data_features(self) -> Path:
        """特徵工程輸出目錄。"""
        return self.data_root / "features"

    @property
    def data_external(self) -> Path:
        """外部資料目錄。"""
        return self.data_root / "external"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """取得全域設定單例。"""
    return Settings()
