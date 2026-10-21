"""案例學習服務測試（Epic A #47）。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from src.core.database import Database
from src.services.case_learning import (
    CASE_COLLECTION,
    UNCLASSIFIED_FAULT,
    CaseLearningService,
    extract_case,
)

if TYPE_CHECKING:
    from pathlib import Path

    from src.services.rag_service import Document


class FakeIndexer:
    """記錄寫入內容的假向量知識庫。"""

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[tuple[list[Document], str | None]] = []

    def add_documents(
        self, documents: list[Document], collection_name: str | None = None
    ) -> dict[str, Any]:
        if self.fail:
            raise RuntimeError("chromadb not installed")
        self.calls.append((documents, collection_name))
        return {"added": len(documents)}


@pytest.fixture
def db(tmp_path: Path) -> Database:
    database = Database(str(tmp_path / "cases.db"))
    database.initialize()
    return database


def _closed_order_with_alert(db: Database) -> str:
    alert_id = db.create_alert(
        source="alert_rule_engine",
        severity="critical",
        title="齒輪箱油溫過高",
        description="gearbox_oil_temp 連續 30 分鐘超過 80°C",
        turbine_id="WT-07",
        tags=["gearbox_overheat"],
        metrics={"gearbox_oil_temp": 86.2},
    )
    order_id = db.create_work_order(
        title="WT-07 齒輪箱檢修",
        turbine_id="WT-07",
        alert_id=alert_id,
        priority="high",
    )
    db.add_work_order_note(order_id, "tech-a", "更換冷卻風扇")
    db.add_work_order_note(order_id, "tech-a", "清潔油冷器")
    db.update_work_order(order_id, status="in_progress", started_at="2026-10-01T08:00:00")
    db.update_work_order(order_id, status="completed", completed_at="2026-10-01T11:30:00")
    return order_id


class TestExtractCase:
    def test_extracts_from_alert_and_notes(self) -> None:
        work_order = {
            "id": "WO-1",
            "title": "檢修",
            "turbine_id": "WT-01",
            "alert_id": "ALT-1",
            "priority": "high",
            "notes": [{"text": "更換感測器"}, {"text": " "}],
            "metadata": {},
            "created_at": "2026-10-01T00:00:00",
            "started_at": "2026-10-01T02:00:00",
            "completed_at": "2026-10-01T05:00:00",
        }
        alert = {
            "title": "振動異常",
            "description": "主軸振動 RMS 偏高",
            "severity": "warning",
            "tags": ["vibration_high"],
            "metrics": {"vib_rms": 7.1},
            "metadata": {},
        }
        case = extract_case(work_order, alert)
        assert case.fault_type == "vibration_high"
        assert case.symptoms == "振動異常；主軸振動 RMS 偏高；指標：vib_rms=7.1"
        assert case.solution == "更換感測器"
        assert case.resolution_hours == 3.0
        assert case.severity == "warning"

    def test_fault_type_priority(self) -> None:
        alert = {"tags": ["rule_x"], "metadata": {"fault_type_zh": "變槳故障"}, "source": "s"}
        assert extract_case({"id": "WO", "metadata": {}}, alert).fault_type == "變槳故障"
        explicit = {"id": "WO", "metadata": {"fault_type": "發電機軸承"}}
        assert extract_case(explicit, alert).fault_type == "發電機軸承"
        assert extract_case({"id": "WO"}, {"source": "windguard"}).fault_type == "windguard"
        assert extract_case({"id": "WO"}).fault_type == UNCLASSIFIED_FAULT

    def test_generic_source_falls_back_to_title(self) -> None:
        """手動建立的告警（source=manual）以告警標題當故障類型，而非 'manual'。"""
        alert = {"source": "manual", "title": "齒輪箱油溫過高"}
        assert extract_case({"id": "WO"}, alert).fault_type == "齒輪箱油溫過高"
        assert extract_case({"id": "WO"}, {"source": "manual"}).fault_type == UNCLASSIFIED_FAULT

    def test_without_alert_falls_back_to_work_order(self) -> None:
        work_order = {
            "id": "WO-2",
            "description": "葉片前緣侵蝕",
            "metadata": {"resolution": "前緣保護膠帶修補"},
            "completed_at": "not-a-date",
        }
        case = extract_case(work_order)
        assert case.symptoms == "葉片前緣侵蝕"
        assert case.solution == "前緣保護膠帶修補"
        assert case.resolution_hours is None

    def test_summary_template_fields(self) -> None:
        summary = extract_case({"id": "WO-3", "turbine_id": "WT-03"}).to_summary()
        for label in ("故障類型：", "風機：WT-03", "症狀描述：", "解決方案：", "處理時間：未知"):
            assert label in summary


class TestCaseLearningService:
    def test_record_case_writes_sqlite_and_vector_store(self, db: Database) -> None:
        order_id = _closed_order_with_alert(db)
        indexer = FakeIndexer()
        result = CaseLearningService(db, indexer).record_case(order_id)

        assert result is not None
        assert result["created"] is True
        assert result["indexed"] is True
        case = db.get_case(result["case_id"])
        assert case is not None
        assert case["work_order_id"] == order_id
        assert case["fault_type"] == "gearbox_overheat"
        assert case["turbine_id"] == "WT-07"
        assert case["solution"] == "更換冷卻風扇；清潔油冷器"
        assert case["resolution_hours"] == 3.5
        assert case["indexed"] is True
        assert case["metadata"]["severity"] == "critical"

        docs, collection = indexer.calls[0]
        assert collection == CASE_COLLECTION
        assert docs[0].doc_id == result["case_id"]
        assert docs[0].metadata["fault_type"] == "gearbox_overheat"
        assert all(v is not None for v in docs[0].metadata.values())

    def test_record_case_is_idempotent(self, db: Database) -> None:
        order_id = _closed_order_with_alert(db)
        indexer = FakeIndexer()
        service = CaseLearningService(db, indexer)
        first = service.record_case(order_id)
        second = service.record_case(order_id)

        assert first is not None and second is not None
        assert second["created"] is False
        assert second["case_id"] == first["case_id"]
        assert len(indexer.calls) == 1
        assert len(db.list_cases()) == 1

    def test_skips_unfinished_or_missing_work_order(self, db: Database) -> None:
        order_id = db.create_work_order(title="未結案工單")
        service = CaseLearningService(db, FakeIndexer())
        assert service.record_case(order_id) is None
        assert service.record_case("WO-does-not-exist") is None
        db.update_work_order(order_id, status="cancelled")
        assert service.record_case(order_id) is None
        assert db.list_cases() == []

    def test_indexer_failure_keeps_sqlite_record(self, db: Database) -> None:
        order_id = _closed_order_with_alert(db)
        result = CaseLearningService(db, FakeIndexer(fail=True)).record_case(order_id)

        assert result is not None
        assert result["created"] is True
        assert result["indexed"] is False
        case = db.get_case_by_work_order(order_id)
        assert case is not None and case["indexed"] is False

    def test_without_indexer(self, db: Database) -> None:
        order_id = _closed_order_with_alert(db)
        result = CaseLearningService(db).record_case(order_id)
        assert result is not None and result["indexed"] is False


class TestCaseQueries:
    def test_list_cases_filters(self, db: Database) -> None:
        db.create_case("WO-a", "gearbox_overheat", "s1", turbine_id="WT-01")
        db.create_case("WO-b", "pitch_fault", "s2", turbine_id="WT-01")
        db.create_case("WO-c", "pitch_fault", "s3", turbine_id="WT-02")

        assert len(db.list_cases()) == 3
        assert len(db.list_cases(fault_type="pitch_fault")) == 2
        assert len(db.list_cases(turbine_id="WT-01")) == 2
        assert len(db.list_cases(fault_type="pitch_fault", turbine_id="WT-02")) == 1
        assert len(db.list_cases(limit=1)) == 1

    def test_create_case_idempotent_per_work_order(self, db: Database) -> None:
        first = db.create_case("WO-a", "x", "s")
        assert db.create_case("WO-a", "y", "t") == first
        case = db.get_case(first)
        assert case is not None and case["fault_type"] == "x"
        assert db.get_case("CASE-missing") is None
        assert db.mark_case_indexed("CASE-missing") is False


class TestCountCases:
    """count_cases 與 list_cases 篩選一致（A3-1 分頁 total）。"""

    def test_count_matches_filters(self, db: Database) -> None:
        db.create_case("WO-a", "gearbox_overheat", "s1", turbine_id="WT-01")
        db.create_case("WO-b", "pitch_fault", "s2", turbine_id="WT-01")
        db.create_case("WO-c", "pitch_fault", "s3", turbine_id="WT-02")
        assert db.count_cases() == 3
        assert db.count_cases(fault_type="pitch_fault") == 2
        assert db.count_cases(turbine_id="WT-01") == 2
        assert db.count_cases(fault_type="pitch_fault", turbine_id="WT-02") == 1
        assert db.count_cases(fault_type="none") == 0

    def test_pagination_total_independent_of_limit(self, db: Database) -> None:
        for i in range(5):
            db.create_case(f"WO-{i}", "pitch_fault", f"s{i}")
        assert len(db.list_cases(limit=2, offset=0)) == 2
        assert db.count_cases() == 5
