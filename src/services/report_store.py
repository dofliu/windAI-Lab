"""報告暫存區 — 記憶體快取 + SQLite 持久化。

儲存由 ReportGeneratorSkill 產出的 Markdown 報告，供 API 端點提供下載。
記憶體層用於快取，DB 層確保後端重啟後仍可取回。
DB 不可用時（如測試環境）自動降級為純記憶體模式。
"""

from __future__ import annotations

import contextlib
from datetime import datetime
from typing import Any

_store: dict[str, dict[str, Any]] = {}


def _get_db() -> Any:
    try:
        from src.core.database import get_database

        return get_database()
    except Exception:
        return None


def save_report(report_id: str, title: str, markdown: str) -> None:
    """儲存報告至記憶體與 DB。"""
    _store[report_id] = {
        "id": report_id,
        "title": title,
        "markdown": markdown,
        "created_at": datetime.now().isoformat(),
    }
    db = _get_db()
    if db is not None:
        with contextlib.suppress(Exception):
            db.save_report(report_id, title, markdown)


def get_report(report_id: str) -> dict[str, Any] | None:
    """取得報告：優先從記憶體，未命中時 fallback 至 DB。"""
    if report_id in _store:
        return _store[report_id]
    db = _get_db()
    if db is not None:
        with contextlib.suppress(Exception):
            return db.get_report(report_id)
    return None


def list_reports() -> list[dict[str, Any]]:
    """列出所有報告：優先從 DB（可跨 session），DB 不可用則回傳記憶體內容。"""
    db = _get_db()
    if db is not None:
        with contextlib.suppress(Exception):
            return db.list_reports()
    return [
        {"id": rid, "title": r.get("title", ""), "created_at": r.get("created_at", "")}
        for rid, r in _store.items()
    ]
