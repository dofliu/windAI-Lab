"""案例學習服務（Epic A #47 — 案例自動記錄）。

工單結案（status=completed）時，從工單與其關聯告警提取故障類型、症狀、
解決方案與處理時間，產生結構化案例摘要：

- 結構化 metadata 寫入 SQLite `cases` 表（可篩選、可統計）
- 案例摘要寫入 ChromaDB `maintenance_cases` 集合（供 #48 語意搜尋推薦）

向量知識庫為選用依賴：未注入或寫入失敗時，案例仍會保存在 SQLite，
`indexed` 欄位維持 False，待日後補寫。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from src.services.rag_service import Document
from src.utils.logger import get_logger

logger = get_logger("service.case_learning")

CASE_COLLECTION = "maintenance_cases"
UNCLASSIFIED_FAULT = "未分類"
_CLOSED_STATUS = "completed"
_MAX_METRICS_IN_SYMPTOMS = 8


class CaseStore(Protocol):
    """案例服務所需的資料庫介面（`src.core.database.Database` 的子集）。"""

    def get_work_order(self, order_id: str) -> dict[str, Any] | None: ...

    def get_alert(self, alert_id: str) -> dict[str, Any] | None: ...

    def get_case_by_work_order(self, work_order_id: str) -> dict[str, Any] | None: ...

    def create_case(
        self,
        work_order_id: str,
        fault_type: str,
        summary: str,
        symptoms: str = "",
        solution: str = "",
        alert_id: str | None = None,
        turbine_id: str | None = None,
        resolution_hours: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str: ...

    def mark_case_indexed(self, case_id: str) -> bool: ...


class CaseIndexer(Protocol):
    """向量知識庫寫入介面（`RAGService.add_documents` 的子集）。"""

    def add_documents(
        self,
        documents: list[Document],
        collection_name: str | None = None,
    ) -> dict[str, Any]: ...


@dataclass
class CaseRecord:
    """從已結案工單提取的維修案例。"""

    work_order_id: str
    fault_type: str
    symptoms: str
    solution: str
    turbine_id: str | None = None
    alert_id: str | None = None
    resolution_hours: float | None = None
    severity: str | None = None
    title: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_summary(self) -> str:
        """依案例摘要模板產生文字（故障類型 / 風機 / 症狀 / 解決方案 / 處理時間）。

        Returns:
            供嵌入與人工閱讀的案例摘要。
        """
        hours = (
            f"{self.resolution_hours:.1f} 小時" if self.resolution_hours is not None else "未知"
        )
        lines = [
            f"案例標題：{self.title or self.work_order_id}",
            f"故障類型：{self.fault_type}",
            f"風機：{self.turbine_id or '未指定'}",
            f"嚴重度：{self.severity or '未知'}",
            f"症狀描述：{self.symptoms or '無'}",
            f"解決方案：{self.solution or '無'}",
            f"處理時間：{hours}",
        ]
        return "\n".join(lines)


def _parse_iso(value: object) -> datetime | None:
    """解析 ISO 8601 字串，失敗回傳 None。"""
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _resolution_hours(work_order: dict[str, Any]) -> float | None:
    """計算處理時間（小時）：completed_at − (started_at 或 created_at)。"""
    end = _parse_iso(work_order.get("completed_at"))
    start = _parse_iso(work_order.get("started_at")) or _parse_iso(work_order.get("created_at"))
    if end is None or start is None:
        return None
    if (end.tzinfo is None) != (start.tzinfo is None):
        return None
    hours = (end - start).total_seconds() / 3600
    return round(hours, 2) if hours >= 0 else None


def _infer_fault_type(work_order: dict[str, Any], alert: dict[str, Any] | None) -> str:
    """推斷故障類型。

    優先序：工單 metadata.fault_type → 告警 metadata.fault_type_zh / fault_type
    → 告警第一個 tag（規則 ID）→ 告警 source → 「未分類」。
    """
    wo_meta = work_order.get("metadata") or {}
    if wo_meta.get("fault_type"):
        return str(wo_meta["fault_type"])
    if alert:
        alert_meta = alert.get("metadata") or {}
        for key in ("fault_type_zh", "fault_type"):
            if alert_meta.get(key):
                return str(alert_meta[key])
        tags = alert.get("tags") or []
        if tags:
            return str(tags[0])
        if alert.get("source"):
            return str(alert["source"])
    return UNCLASSIFIED_FAULT


def _build_symptoms(work_order: dict[str, Any], alert: dict[str, Any] | None) -> str:
    """組合症狀描述：告警標題 / 描述 / 指標值，缺告警時退回工單描述。"""
    parts: list[str] = []
    if alert:
        if alert.get("title"):
            parts.append(str(alert["title"]))
        if alert.get("description"):
            parts.append(str(alert["description"]))
        metrics = alert.get("metrics") or {}
        if metrics:
            items = list(metrics.items())[:_MAX_METRICS_IN_SYMPTOMS]
            parts.append("指標：" + ", ".join(f"{k}={v}" for k, v in items))
    if not parts and work_order.get("description"):
        parts.append(str(work_order["description"]))
    return "；".join(parts)


def _build_solution(work_order: dict[str, Any]) -> str:
    """組合解決方案：工單 metadata.resolution 優先，否則串接工單備註。"""
    wo_meta = work_order.get("metadata") or {}
    if wo_meta.get("resolution"):
        return str(wo_meta["resolution"])
    notes = work_order.get("notes") or []
    texts = [str(n.get("text", "")).strip() for n in notes if isinstance(n, dict)]
    return "；".join(t for t in texts if t)


def extract_case(work_order: dict[str, Any], alert: dict[str, Any] | None = None) -> CaseRecord:
    """從工單（與關聯告警）提取案例。純函式，不碰資料庫。

    Args:
        work_order: 工單 dict（`Database.get_work_order` 的回傳格式）。
        alert: 關聯告警 dict，可為 None。

    Returns:
        提取出的案例。
    """
    return CaseRecord(
        work_order_id=str(work_order["id"]),
        fault_type=_infer_fault_type(work_order, alert),
        symptoms=_build_symptoms(work_order, alert),
        solution=_build_solution(work_order),
        turbine_id=work_order.get("turbine_id") or (alert or {}).get("turbine_id"),
        alert_id=work_order.get("alert_id"),
        resolution_hours=_resolution_hours(work_order),
        severity=(alert or {}).get("severity"),
        title=str(work_order.get("title") or ""),
        metadata={"priority": work_order.get("priority")},
    )


class CaseLearningService:
    """工單結案 → 案例記錄 → 向量知識庫的協調服務。"""

    def __init__(self, store: CaseStore, indexer: CaseIndexer | None = None) -> None:
        """初始化服務。

        Args:
            store: 資料庫（需提供工單、告警與案例 CRUD）。
            indexer: 向量知識庫，None 表示只寫 SQLite。
        """
        self._store = store
        self._indexer = indexer

    def record_case(self, work_order_id: str) -> dict[str, Any] | None:
        """為已結案工單建立案例紀錄（冪等）。

        Args:
            work_order_id: 工單 ID。

        Returns:
            案例資訊 dict（含 `case_id`、`created`、`indexed`）；
            工單不存在或尚未結案時回傳 None。
        """
        work_order = self._store.get_work_order(work_order_id)
        if work_order is None or work_order.get("status") != _CLOSED_STATUS:
            return None

        existing = self._store.get_case_by_work_order(work_order_id)
        if existing:
            return {
                "case_id": existing["id"],
                "created": False,
                "indexed": bool(existing.get("indexed")),
            }

        alert_id = work_order.get("alert_id")
        alert = self._store.get_alert(alert_id) if alert_id else None
        case = extract_case(work_order, alert)
        summary = case.to_summary()
        case_id = self._store.create_case(
            work_order_id=case.work_order_id,
            fault_type=case.fault_type,
            summary=summary,
            symptoms=case.symptoms,
            solution=case.solution,
            alert_id=case.alert_id,
            turbine_id=case.turbine_id,
            resolution_hours=case.resolution_hours,
            metadata={**case.metadata, "severity": case.severity},
        )
        indexed = self._index_case(case_id, case, summary)
        logger.info(f"案例已記錄：{case_id}（工單 {work_order_id}，向量索引={indexed}）")
        return {"case_id": case_id, "created": True, "indexed": indexed}

    def _index_case(self, case_id: str, case: CaseRecord, summary: str) -> bool:
        """將案例摘要寫入向量知識庫；失敗不影響 SQLite 紀錄。"""
        if self._indexer is None:
            return False
        # ChromaDB metadata 只接受 str/int/float/bool，None 一律轉空字串
        meta: dict[str, Any] = {
            "case_id": case_id,
            "work_order_id": case.work_order_id,
            "fault_type": case.fault_type,
            "turbine_id": case.turbine_id or "",
            "alert_id": case.alert_id or "",
            "severity": case.severity or "",
            "source": "case_learning",
        }
        if case.resolution_hours is not None:
            meta["resolution_hours"] = case.resolution_hours
        try:
            self._indexer.add_documents(
                [Document(content=summary, metadata=meta, doc_id=case_id)],
                collection_name=CASE_COLLECTION,
            )
        except Exception as exc:  # 向量庫不可用（未安裝 chromadb 等）時降級
            logger.warning(f"案例 {case_id} 向量索引失敗，僅保存於 SQLite：{exc}")
            return False
        return self._store.mark_case_indexed(case_id)
