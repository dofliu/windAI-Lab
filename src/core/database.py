"""WindAI Lab 持久化儲存模組。

使用 Python 內建 sqlite3 實現任務記錄、工作日誌與分析結果的持久化儲存。
不引入額外依賴（SQLAlchemy），保持系統輕量。
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.config import get_settings
from src.utils.logger import get_logger

logger = get_logger("core.database")

# ── Schema 定義 ──────────────────────────────────────────────────

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    command TEXT NOT NULL,
    parameters TEXT DEFAULT '{}',
    description TEXT DEFAULT '',
    status TEXT DEFAULT 'running',
    started_at TEXT NOT NULL,
    completed_at TEXT,
    duration_ms INTEGER DEFAULT 0,
    agent_ids TEXT DEFAULT '[]',
    agent_names TEXT DEFAULT '[]',
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS work_logs (
    id TEXT PRIMARY KEY,
    task_id TEXT,
    timestamp TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT DEFAULT 'info',
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

CREATE TABLE IF NOT EXISTS analysis_results (
    id TEXT PRIMARY KEY,
    task_id TEXT,
    chart_type TEXT NOT NULL,
    title TEXT NOT NULL,
    data TEXT DEFAULT '[]',
    metadata TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

CREATE INDEX IF NOT EXISTS idx_work_logs_task_id ON work_logs(task_id);
CREATE INDEX IF NOT EXISTS idx_work_logs_timestamp ON work_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_analysis_results_task_id ON analysis_results(task_id);
CREATE INDEX IF NOT EXISTS idx_tasks_started_at ON tasks(started_at);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
"""


# ── 資料庫管理器 ─────────────────────────────────────────────────


class Database:
    """SQLite 持久化儲存管理器。"""

    def __init__(self, db_path: str | None = None) -> None:
        if db_path is None:
            settings = get_settings()
            url = settings.database_url
            # 從 sqlite:///path 格式提取路徑
            if url.startswith("sqlite:///"):
                db_path = url.replace("sqlite:///", "")
            else:
                db_path = "windai.db"
        self._db_path = db_path
        self._initialized = False

    @contextmanager
    def _connect(self) -> Any:
        """取得資料庫連線的 context manager。"""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        """建立資料表（如果不存在）。"""
        if self._initialized:
            return
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA_SQL)
        self._initialized = True
        logger.info(f"資料庫已初始化：{self._db_path}")

    # ── Task CRUD ────────────────────────────────────────────────

    def create_task(
        self,
        command: str,
        parameters: dict[str, Any] | None = None,
        description: str = "",
    ) -> str:
        """建立新任務記錄，回傳 task_id。"""
        self.initialize()
        task_id = f"WLAB-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO tasks (id, command, parameters, description, status, started_at) "
                "VALUES (?, ?, ?, ?, 'running', ?)",
                (
                    task_id,
                    command,
                    json.dumps(parameters or {}),
                    description,
                    datetime.now().isoformat(),
                ),
            )
        logger.debug(f"任務已建立：{task_id} ({command})")
        return task_id

    def complete_task(
        self,
        task_id: str,
        status: str = "completed",
        error_message: str | None = None,
        agent_ids: list[str] | None = None,
        agent_names: list[str] | None = None,
    ) -> None:
        """標記任務完成或失敗。"""
        self.initialize()
        with self._connect() as conn:
            # 計算耗時
            row = conn.execute("SELECT started_at FROM tasks WHERE id = ?", (task_id,)).fetchone()
            duration_ms = 0
            if row:
                started = datetime.fromisoformat(row["started_at"])
                duration_ms = int((datetime.now() - started).total_seconds() * 1000)
            conn.execute(
                "UPDATE tasks SET status = ?, completed_at = ?, duration_ms = ?, "
                "error_message = ?, agent_ids = ?, agent_names = ? WHERE id = ?",
                (
                    status,
                    datetime.now().isoformat(),
                    duration_ms,
                    error_message,
                    json.dumps(agent_ids or []),
                    json.dumps(agent_names or []),
                    task_id,
                ),
            )
        logger.debug(f"任務已完成：{task_id} ({status})")

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        """取得單一任務記錄。"""
        self.initialize()
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if row is None:
                return None
            return _row_to_task(row)

    def list_tasks(
        self,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """查詢任務記錄列表（最新在前）。"""
        self.initialize()
        with self._connect() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM tasks WHERE status = ? ORDER BY started_at DESC LIMIT ? OFFSET ?",
                    (status, limit, offset),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM tasks ORDER BY started_at DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                ).fetchall()
            return [_row_to_task(r) for r in rows]

    def count_tasks(self, status: str | None = None) -> int:
        """計算任務總數。"""
        self.initialize()
        with self._connect() as conn:
            if status:
                row = conn.execute(
                    "SELECT COUNT(*) as cnt FROM tasks WHERE status = ?", (status,)
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) as cnt FROM tasks").fetchone()
            return row["cnt"] if row else 0

    # ── WorkLog CRUD ─────────────────────────────────────────────

    def save_work_log(
        self,
        agent_id: str,
        agent_name: str,
        message: str,
        log_type: str = "info",
        task_id: str | None = None,
    ) -> str:
        """儲存工作日誌。"""
        self.initialize()
        log_id = uuid.uuid4().hex[:12]
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO work_logs (id, task_id, timestamp, agent_id, agent_name, message, type) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    log_id,
                    task_id,
                    datetime.now().isoformat(),
                    agent_id,
                    agent_name,
                    message,
                    log_type,
                ),
            )
        return log_id

    def get_task_logs(self, task_id: str, limit: int = 200) -> list[dict[str, Any]]:
        """取得指定任務的工作日誌。"""
        self.initialize()
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM work_logs WHERE task_id = ? ORDER BY timestamp ASC LIMIT ?",
                (task_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_recent_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        """取得最近的工作日誌。"""
        self.initialize()
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM work_logs ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    # ── AnalysisResult CRUD ──────────────────────────────────────

    def save_analysis_result(
        self,
        task_id: str,
        chart_type: str,
        title: str,
        data: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """儲存分析結果。"""
        self.initialize()
        result_id = uuid.uuid4().hex[:12]
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO analysis_results (id, task_id, chart_type, title, data, metadata, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    result_id,
                    task_id,
                    chart_type,
                    title,
                    json.dumps(data or [], default=_json_fallback),
                    json.dumps(metadata or {}, default=_json_fallback),
                    datetime.now().isoformat(),
                ),
            )
        return result_id

    def get_task_results(self, task_id: str) -> list[dict[str, Any]]:
        """取得指定任務的分析結果。"""
        self.initialize()
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM analysis_results WHERE task_id = ? ORDER BY created_at ASC",
                (task_id,),
            ).fetchall()
            return [_row_to_result(r) for r in rows]

    # ── 統計 ─────────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """取得資料庫統計資訊。"""
        self.initialize()
        with self._connect() as conn:
            tasks_total = conn.execute("SELECT COUNT(*) as c FROM tasks").fetchone()["c"]
            tasks_completed = conn.execute(
                "SELECT COUNT(*) as c FROM tasks WHERE status = 'completed'"
            ).fetchone()["c"]
            logs_total = conn.execute("SELECT COUNT(*) as c FROM work_logs").fetchone()["c"]
            results_total = conn.execute("SELECT COUNT(*) as c FROM analysis_results").fetchone()[
                "c"
            ]
            return {
                "tasks_total": tasks_total,
                "tasks_completed": tasks_completed,
                "tasks_error": tasks_total - tasks_completed,
                "work_logs_total": logs_total,
                "analysis_results_total": results_total,
            }


# ── 輔助函式 ─────────────────────────────────────────────────────


def _json_fallback(obj: Any) -> Any:
    """JSON 序列化 fallback：處理 float('nan') 等特殊值。"""
    import math

    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return str(obj)


def _row_to_task(row: sqlite3.Row) -> dict[str, Any]:
    """將 sqlite3.Row 轉為 task dict，解析 JSON 欄位。"""
    d = dict(row)
    d["parameters"] = json.loads(d.get("parameters") or "{}")
    d["agent_ids"] = json.loads(d.get("agent_ids") or "[]")
    d["agent_names"] = json.loads(d.get("agent_names") or "[]")
    return d


def _row_to_result(row: sqlite3.Row) -> dict[str, Any]:
    """將 sqlite3.Row 轉為 analysis_result dict，解析 JSON 欄位。"""
    d = dict(row)
    d["data"] = json.loads(d.get("data") or "[]")
    d["metadata"] = json.loads(d.get("metadata") or "{}")
    return d


# ── 全域單例 ─────────────────────────────────────────────────────

_db_instance: Database | None = None


def get_database() -> Database:
    """取得全域資料庫單例。"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
        _db_instance.initialize()
    return _db_instance
