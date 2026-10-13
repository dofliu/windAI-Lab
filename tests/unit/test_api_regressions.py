"""API 層回歸測試：2026-10-13 實機 UI 測試發現的缺陷。

- `/api/agents/available` 被 `/api/agents/{agent_id}` 遮蔽而回 404
- 工單結案（PATCH status=completed）未自動建立維修案例（Epic A1-2）
- `/api/scada/turbines` 列出不存在的 Kelmarsh 風機、拉取檔每分鐘一份全部列出
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import src.core.database as database_module
from src.api import main as api_main
from src.core.database import Database


@pytest.fixture
def db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Database:
    """以暫存 SQLite 取代全域資料庫單例。"""
    database = Database(str(tmp_path / "api.db"))
    database.initialize()
    monkeypatch.setattr(database_module, "_db_instance", database)
    return database


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """不啟動 lifespan（背景連接器 / 排程）的 TestClient；RAG 一律視為不可用。"""

    def _no_rag() -> None:
        raise RuntimeError("RAG 不可用（測試）")

    monkeypatch.setattr(api_main, "_get_rag_service", _no_rag)
    yield TestClient(api_main.app)


def _open_order(db: Database) -> str:
    alert_id = db.create_alert(
        source="manual",
        severity="critical",
        title="齒輪箱油溫過高",
        description="油溫 92°C",
        turbine_id="WT-01",
    )
    order_id = db.create_work_order(title="[CRITICAL] 齒輪箱油溫過高", alert_id=alert_id)
    db.add_work_order_note(order_id, author="技師", text="更換油冷卻器濾網")
    return order_id


class TestAgentsAvailableRoute:
    """`/api/agents/available` 不可被 `{agent_id}` 路由遮蔽。"""

    def test_available_returns_200(self, client: TestClient) -> None:
        resp = client.get("/api/agents/available")
        assert resp.status_code == 200
        body = resp.json()
        assert "agents" in body and body["total"] == len(body["agents"])

    def test_unknown_agent_still_404(self, client: TestClient) -> None:
        assert client.get("/api/agents/no-such-agent").status_code == 404


class TestWorkOrderCloseRecordsCase:
    """工單結案自動建立案例（Epic A1-2）。"""

    def test_completed_creates_case(self, client: TestClient, db: Database) -> None:
        order_id = _open_order(db)
        resp = client.patch(f"/api/work-orders/{order_id}", json={"status": "completed"})
        assert resp.status_code == 200
        case = db.get_case_by_work_order(order_id)
        assert case is not None
        assert case["fault_type"] == "齒輪箱油溫過高"
        assert "更換油冷卻器濾網" in case["solution"]

    def test_close_is_idempotent(self, client: TestClient, db: Database) -> None:
        order_id = _open_order(db)
        client.patch(f"/api/work-orders/{order_id}", json={"status": "completed"})
        client.patch(f"/api/work-orders/{order_id}", json={"status": "completed"})
        assert db.count_cases() == 1

    def test_non_completed_status_creates_no_case(self, client: TestClient, db: Database) -> None:
        order_id = _open_order(db)
        client.patch(f"/api/work-orders/{order_id}", json={"status": "in_progress"})
        assert db.get_case_by_work_order(order_id) is None

    def test_case_failure_does_not_fail_update(
        self, client: TestClient, db: Database, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _boom(*_args: object, **_kwargs: object) -> str:
            raise RuntimeError("寫入案例失敗")

        monkeypatch.setattr(db, "create_case", _boom)
        order_id = _open_order(db)
        resp = client.patch(f"/api/work-orders/{order_id}", json={"status": "completed"})
        assert resp.status_code == 200
        assert resp.json()["work_order"]["status"] == "completed"


class TestScanTurbines:
    """`_scan_turbines` 只列出實際可載入的資料。"""

    def test_no_kelmarsh_without_zip(self, tmp_path: Path) -> None:
        (tmp_path / "raw").mkdir()
        (tmp_path / "raw" / "WT-09.csv").write_text("a\n1\n")
        assert api_main._scan_turbines(tmp_path) == ["WT-09"]

    def test_kelmarsh_listed_when_zip_exists(self, tmp_path: Path) -> None:
        (tmp_path / "external").mkdir()
        (tmp_path / "external" / "Kelmarsh_SCADA_2016.zip").write_bytes(b"")
        turbines = api_main._scan_turbines(tmp_path)
        assert [t for t in turbines if t.startswith("Kelmarsh_")] == [
            f"Kelmarsh_{i}" for i in range(1, 7)
        ]

    def test_fetched_files_collapse_to_latest(self, tmp_path: Path) -> None:
        raw = tmp_path / "raw"
        raw.mkdir()
        for ts in ("20261013_142101", "20261013_142201", "20261013_142301"):
            (raw / f"WT-01_api_fetched_{ts}.csv").write_text("a\n1\n")
        assert api_main._scan_turbines(tmp_path) == ["WT-01_api_fetched_20261013_142301"]
