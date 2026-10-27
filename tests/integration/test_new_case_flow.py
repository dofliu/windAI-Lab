"""新案例處理能力驗證（規劃見 docs/routines/case-e2e-test-plan.md）。

切片 1：TC-01 / TC-02 / TC-04（告警 → 工單 → 結案 → 案例 → 相似推薦、重複結案冪等）。
全程走 HTTP API，RAG 一律視為不可用，推薦走關鍵字降級路徑。
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import src.core.database as database_module
from src.api import main as api_main
from src.core.database import Database

FAULT_TITLE = "齒輪箱油溫過高"


@pytest.fixture
def db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Database:
    """以暫存 SQLite 取代全域資料庫單例。"""
    database = Database(str(tmp_path / "flow.db"))
    database.initialize()
    monkeypatch.setattr(database_module, "_db_instance", database)
    return database


@pytest.fixture
def client(db: Database, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """不啟動 lifespan 的 TestClient；RAG 不可用。"""

    def _no_rag() -> None:
        raise RuntimeError("RAG 不可用（測試）")

    monkeypatch.setattr(api_main, "_get_rag_service", _no_rag)
    yield TestClient(api_main.app)


def _raise_alert(client: TestClient, turbine_id: str = "WT-01", title: str = FAULT_TITLE) -> str:
    resp = client.post(
        "/api/alerts",
        json={
            "source": "manual",
            "severity": "critical",
            "title": title,
            "description": "油溫 92°C，持續升高",
            "turbine_id": turbine_id,
        },
    )
    assert resp.status_code == 201
    return str(resp.json()["alert_id"])


def _close_case_flow(client: TestClient, turbine_id: str = "WT-01") -> tuple[str, str]:
    """告警 → 工單 → 備註 → 結案，回傳 (alert_id, order_id)。"""
    alert_id = _raise_alert(client, turbine_id)
    resp = client.post(f"/api/alerts/{alert_id}/create-work-order")
    assert resp.status_code == 201
    order_id = str(resp.json()["work_order_id"])
    note = client.post(
        f"/api/work-orders/{order_id}/notes",
        json={"author": "技師", "text": "更換油冷卻器濾網"},
    )
    assert note.status_code in (200, 201)
    done = client.patch(f"/api/work-orders/{order_id}", json={"status": "completed"})
    assert done.status_code == 200
    return alert_id, order_id


class TestMainFlow:
    """TC-01：告警 → 工單 → 結案 → 案例。"""

    def test_close_creates_case_with_turbine_and_fault_type(self, client: TestClient) -> None:
        before = client.get("/api/cases").json()["total"]
        _, order_id = _close_case_flow(client)

        order = client.get(f"/api/work-orders/{order_id}").json()["work_order"]
        assert order["status"] == "completed"

        listing = client.get("/api/cases").json()
        assert listing["total"] == before + 1
        case = listing["cases"][0]
        assert case["turbine_id"] == "WT-01"
        assert case["fault_type"] == FAULT_TITLE
        assert client.get(f"/api/cases/{case['id']}").status_code == 200


class TestSimilarRecommendation:
    """TC-02：結案後同風機同類型新告警能推薦到該案例。"""

    def test_new_alert_recommends_closed_case(self, client: TestClient) -> None:
        _close_case_flow(client)
        case_id = client.get("/api/cases").json()["cases"][0]["id"]

        new_alert = _raise_alert(client)
        resp = client.get("/api/cases/similar", params={"alert_id": new_alert, "top_k": 5})
        assert resp.status_code == 200
        recs = resp.json()["recommendations"]
        assert len(recs) <= 5
        assert case_id in {r["case_id"] for r in recs}


class TestIdempotentClose:
    """TC-04：同一工單重複結案不產生重複案例。"""

    def test_repeated_close_keeps_single_case(self, client: TestClient) -> None:
        _, order_id = _close_case_flow(client)
        for _ in range(2):
            resp = client.patch(f"/api/work-orders/{order_id}", json={"status": "completed"})
            assert resp.status_code == 200
        assert client.get("/api/cases").json()["total"] == 1
