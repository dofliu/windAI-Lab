"""檔案監控服務 — 定期掃描資料目錄，偵測新檔案並自動觸發工作流程。

當使用者將新的 CSV / Parquet / Excel / ZIP 檔案放入 data/raw/ 或 data/external/ 時，
系統會自動：
1. 偵測到新檔案 → WebSocket 廣播通知
2. 呼叫 smart_load 載入資料
3. 自動偵測欄位映射
4. 執行特徵分析
5. 廣播分析結果至前端

使用方式：
    watcher = FileWatcherService()
    await watcher.start()   # 啟動背景掃描
    await watcher.stop()    # 停止掃描
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("windailab.file_watcher")

# 專案根目錄
_PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 預設監控目錄
DEFAULT_WATCH_DIRS = [
    _PROJECT_ROOT / "data" / "raw",
    _PROJECT_ROOT / "data" / "external",
]

# 支援的副檔名
SUPPORTED_EXTENSIONS = {".csv", ".parquet", ".xlsx", ".xls", ".zip", ".tsv"}


@dataclass
class FileEvent:
    """檔案事件記錄。"""

    filename: str
    path: str
    size_bytes: int
    detected_at: float
    event_type: str  # "detected" | "processed" | "error"
    turbine_id: str | None = None
    detected_fields: dict[str, str] | None = None
    total_records: int = 0
    analysis_summary: dict[str, Any] | None = None
    error_message: str | None = None


@dataclass
class FileWatcherService:
    """定期掃描資料目錄，偵測新檔案並自動觸發分析工作流程。

    Attributes
    ----------
    watch_dirs : list[Path]
        要監控的目錄列表。
    scan_interval : int
        掃描間隔秒數。
    auto_analyze : bool
        是否自動執行特徵分析（否則只偵測欄位）。
    """

    watch_dirs: list[Path] = field(default_factory=lambda: list(DEFAULT_WATCH_DIRS))
    scan_interval: int = 30
    auto_analyze: bool = True

    # 內部狀態
    _running: bool = field(default=False, init=False)
    _task: asyncio.Task[None] | None = field(default=None, init=False)
    _known_files: dict[str, float] = field(default_factory=dict, init=False)
    _history: list[FileEvent] = field(default_factory=list, init=False)
    _scan_count: int = field(default=0, init=False)
    _broadcast_fn: Any = field(default=None, init=False)  # WebSocket 廣播回呼
    _dispatch_workflow_fn: Any = field(default=None, init=False)  # 工作流程派任回呼

    def set_broadcast(self, fn: Any) -> None:
        """設定 WebSocket 廣播函式。"""
        self._broadcast_fn = fn

    def set_workflow_dispatcher(self, fn: Any) -> None:
        """設定工作流程派任函式（連接 orchestration engine）。"""
        self._dispatch_workflow_fn = fn

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def history(self) -> list[FileEvent]:
        return list(self._history)

    @property
    def status(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "scan_interval": self.scan_interval,
            "watch_dirs": [str(d) for d in self.watch_dirs],
            "known_files": len(self._known_files),
            "processed_count": len(self._history),
            "scan_count": self._scan_count,
        }

    async def start(self) -> None:
        """啟動背景掃描任務。"""
        if self._running:
            logger.info("FileWatcher 已在運行中")
            return

        # 初始掃描：記錄現有檔案（不觸發處理）
        await self._initialize_known_files()

        self._running = True
        self._task = asyncio.create_task(self._scan_loop())
        logger.info(
            f"FileWatcher 已啟動（間隔 {self.scan_interval}s，"
            f"監控 {len(self.watch_dirs)} 個目錄，"
            f"已知 {len(self._known_files)} 個檔案）"
        )

    async def stop(self) -> None:
        """停止背景掃描任務。"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("FileWatcher 已停止")

    async def force_scan(self, path: str | None = None) -> list[dict[str, Any]]:
        """強制掃描並處理指定檔案或所有未處理的檔案。

        Parameters
        ----------
        path : str | None
            指定要處理的檔案路徑。為 None 時掃描所有未處理的檔案。

        Returns
        -------
        list[dict]
            處理結果列表。
        """
        results: list[dict[str, Any]] = []

        if path:
            # 處理指定檔案
            file_path = Path(path) if Path(path).is_absolute() else _PROJECT_ROOT / path
            if file_path.exists():
                await self._process_new_file(file_path)
                key = self._file_key(file_path)
                self._known_files[key] = file_path.stat().st_mtime
                results.append({"file": str(file_path.name), "status": "processed"})
        else:
            # 掃描所有目錄，處理所有未在歷史中的檔案
            processed_paths = {e.path for e in self._history}
            for directory in self.watch_dirs:
                if not directory.exists():
                    continue
                for file_path in self._iter_data_files(directory):
                    rel_path = str(file_path.relative_to(_PROJECT_ROOT))
                    if rel_path not in processed_paths:
                        await self._process_new_file(file_path)
                        results.append({"file": file_path.name, "status": "processed"})

        return results

    async def _initialize_known_files(self) -> None:
        """初始掃描：記錄所有現有檔案，不觸發任何處理。"""
        for directory in self.watch_dirs:
            if not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)
                continue
            for file_path in self._iter_data_files(directory):
                key = self._file_key(file_path)
                self._known_files[key] = file_path.stat().st_mtime

    async def _scan_loop(self) -> None:
        """主掃描迴圈。"""
        while self._running:
            try:
                await asyncio.sleep(self.scan_interval)
                if not self._running:
                    break
                new_files = await self._scan_once()
                for file_path in new_files:
                    await self._process_new_file(file_path)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("FileWatcher 掃描異常")
                await asyncio.sleep(5)

    async def _scan_once(self) -> list[Path]:
        """掃描一次所有監控目錄，回傳新檔案列表。"""
        self._scan_count += 1
        new_files: list[Path] = []

        for directory in self.watch_dirs:
            if not directory.exists():
                continue
            for file_path in self._iter_data_files(directory):
                key = self._file_key(file_path)
                mtime = file_path.stat().st_mtime

                # 新檔案或已修改的檔案
                if key not in self._known_files or self._known_files[key] < mtime:
                    # 確保檔案不是正在寫入中（等最後修改超過 5 秒）
                    if time.time() - mtime > 5:
                        self._known_files[key] = mtime
                        new_files.append(file_path)

        if new_files:
            logger.info(f"偵測到 {len(new_files)} 個新檔案")

        return new_files

    async def _process_new_file(self, file_path: Path) -> None:
        """處理新偵測到的檔案：載入 → 偵測欄位 → 分析 → 廣播。"""
        filename = file_path.name
        size = file_path.stat().st_size
        turbine_id = file_path.stem

        logger.info(f"處理新檔案：{filename}（{size / 1024:.1f} KB）")

        # Step 1: 廣播「偵測到新檔案」
        event = FileEvent(
            filename=filename,
            path=str(file_path.relative_to(_PROJECT_ROOT)),
            size_bytes=size,
            detected_at=time.time(),
            event_type="detected",
            turbine_id=turbine_id,
        )
        await self._broadcast_event(event)

        # Step 2: 嘗試載入並分析
        try:
            loop = asyncio.get_event_loop()

            # 載入資料
            from src.data_pipeline.ingestion.smart_loader import (
                detect_columns,
                smart_load,
            )

            df = await loop.run_in_executor(None, lambda: smart_load(file_path))
            event.total_records = len(df)

            # 偵測欄位
            mapping = detect_columns(df)
            event.detected_fields = {k: v for k, v in mapping.items() if v is not None}

            # Step 3: 自動特徵分析（可選）
            if self.auto_analyze:
                from src.features.auto_feature_analysis import analyze_features

                report = await loop.run_in_executor(None, lambda: analyze_features(df))
                event.analysis_summary = {
                    "numeric_columns": report.get("numeric_columns", 0),
                    "target_column": report.get("target_column"),
                    "top_features": [
                        f["column"]
                        for f in report.get("feature_importance", [])[:5]
                    ],
                    "anomaly_columns": report.get("anomalies", {}).get(
                        "total_columns_with_outliers", 0
                    ),
                    "recommendations_count": len(
                        report.get("recommendations", [])
                    ),
                }

            # Step 4: 廣播「處理完成」
            event.event_type = "processed"
            await self._broadcast_event(event)

            logger.info(
                f"檔案處理完成：{filename}，"
                f"{event.total_records} 筆，"
                f"偵測到 {len(event.detected_fields or {})} 個欄位"
            )

            # Step 5: 自動派任代理工作流程
            if self._dispatch_workflow_fn and event.detected_fields:
                try:
                    await self._dispatch_workflow_fn(turbine_id, event)
                except Exception:
                    logger.debug(f"自動派任工作流程失敗：{turbine_id}")

        except Exception as e:
            event.event_type = "error"
            event.error_message = str(e)
            await self._broadcast_event(event)
            logger.error(f"檔案處理失敗：{filename} — {e}")

        self._history.append(event)

    async def _broadcast_event(self, event: FileEvent) -> None:
        """透過 WebSocket 廣播檔案事件。"""
        if self._broadcast_fn is None:
            return

        payload = {
            "filename": event.filename,
            "path": event.path,
            "size_bytes": event.size_bytes,
            "size_display": _format_size(event.size_bytes),
            "turbine_id": event.turbine_id,
            "total_records": event.total_records,
            "detected_fields": event.detected_fields,
            "analysis_summary": event.analysis_summary,
            "error_message": event.error_message,
        }

        message = {
            "type": f"file_{event.event_type}",
            "timestamp": _iso_now(),
            "payload": payload,
        }

        try:
            await self._broadcast_fn(message)
        except Exception:
            logger.debug("WebSocket 廣播失敗（可能無連線）")

    @staticmethod
    def _iter_data_files(directory: Path):
        """迭代目錄中的資料檔案（不遞迴進子目錄太深）。"""
        for item in directory.iterdir():
            if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS:
                if not item.name.startswith(".") and not item.name.startswith("~"):
                    yield item
            # 只進入一層子目錄
            elif item.is_dir() and not item.name.startswith("."):
                for sub_item in item.iterdir():
                    if (
                        sub_item.is_file()
                        and sub_item.suffix.lower() in SUPPORTED_EXTENSIONS
                    ):
                        yield sub_item

    @staticmethod
    def _file_key(path: Path) -> str:
        """產生檔案唯一鍵（路徑+大小）。"""
        try:
            return f"{path.resolve()}:{path.stat().st_size}"
        except OSError:
            return str(path.resolve())


def _format_size(size_bytes: int) -> str:
    """格式化檔案大小。"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def _iso_now() -> str:
    """取得 ISO 8601 時間戳記。"""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
