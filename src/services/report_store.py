"""報告暫存區 — 獨立模組，避免循環匯入。

儲存由 ReportGeneratorSkill 產出的 Markdown 報告，
供 API 端點提供下載。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

_store: dict[str, dict[str, Any]] = {}


def save_report(report_id: str, title: str, markdown: str) -> None:
    """儲存報告至暫存區。"""
    _store[report_id] = {
        "id": report_id,
        "title": title,
        "markdown": markdown,
        "created_at": datetime.now().isoformat(),
    }


def get_report(report_id: str) -> dict[str, Any] | None:
    """取得報告。"""
    return _store.get(report_id)


def list_reports() -> list[dict[str, Any]]:
    """列出所有報告。"""
    return [
        {"id": rid, "title": r.get("title", ""), "created_at": r.get("created_at", "")}
        for rid, r in _store.items()
    ]
