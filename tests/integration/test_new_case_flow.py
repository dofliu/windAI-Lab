"""新案例處理能力驗證（規劃見 docs/routines/case-e2e-test-plan.md）。

切片 1：TC-01 / TC-02 / TC-04（告警 → 工單 → 結案 → 案例 → 相似推薦、重複結案冪等）。
切片 2：TC-05 / TC-06 / TC-07（容錯：缺欄位結案、indexer 失敗、不存在 / 缺參數）。
切片 3：TC-03（植入 3 種故障類型各 3 案例，驗證 Top-3 命中率）。
切片 4：TC-08 / TC-09 / TC-10（多風場連動、未歸屬風機、全流程耗時記錄）。
全程走 HTTP API，RAG 一律視為不可用，推薦走關鍵字降級路徑。
"""

import time
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


def _close_case_flow(
    client: TestClient, turbine_id: str = "WT-01", title: str = FAULT_TITLE
) -> tuple[str, str]:
    """告警 → 工單 → 備註 → 結案，回傳 (alert_id, order_id)。"""
    alert_id = _raise_alert(client, turbine_id, title)
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


class TestMinimalOrderClose:
    """TC-05：無 turbine_id / 無 notes 的工單結案仍建立案例。"""

    def test_close_without_turbine_or_notes(self, client: TestClient) -> None:
        resp = client.post("/api/work-orders", json={"title": "例行巡檢"})
        assert resp.status_code == 201
        order_id = resp.json()["work_order_id"]

        done = client.patch(f"/api/work-orders/{order_id}", json={"status": "completed"})
        assert done.status_code == 200

        listing = client.get("/api/cases").json()
        assert listing["total"] == 1
        case = listing["cases"][0]
        assert case["work_order_id"] == order_id
        assert not case.get("turbine_id")


class _FailingIndexer:
    """模擬向量庫寫入失敗。"""

    def add_documents(self, *args: object, **kwargs: object) -> None:
        raise RuntimeError("向量庫寫入失敗（測試）")


class TestIndexerFailure:
    """TC-06：indexer 失敗時結案仍成功，案例保存於 DB。"""

    def test_close_succeeds_when_indexer_raises(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(api_main, "_get_rag_service", lambda: _FailingIndexer())
        _, order_id = _close_case_flow(client)

        order = client.get(f"/api/work-orders/{order_id}").json()["work_order"]
        assert order["status"] == "completed"
        listing = client.get("/api/cases").json()
        assert listing["total"] == 1
        assert listing["cases"][0]["work_order_id"] == order_id


class TestInvalidRequests:
    """TC-07：不存在的資源與缺參數回傳 404 / 422。"""

    def test_unknown_case_returns_404(self, client: TestClient) -> None:
        assert client.get("/api/cases/no-such-case").status_code == 404

    def test_similar_without_alert_id_returns_422(self, client: TestClient) -> None:
        assert client.get("/api/cases/similar").status_code == 422

    def test_similar_with_unknown_alert_returns_404(self, client: TestClient) -> None:
        resp = client.get("/api/cases/similar", params={"alert_id": "no-such-alert"})
        assert resp.status_code == 404


class TestRecommendationQuality:
    """TC-03：植入 3 種故障類型各 3 案例，各類型查詢的 Top-3 命中率 ≥ 80%。"""

    FAULT_TITLES = ("齒輪箱油溫過高", "發電機軸承振動異常", "變槳系統馬達過載")

    def test_top3_hit_rate_at_least_80_percent(self, client: TestClient) -> None:
        for title in self.FAULT_TITLES:
            for turbine in ("WT-01", "WT-02", "WT-03"):
                _close_case_flow(client, turbine, title)
        cases = client.get("/api/cases", params={"limit": 100}).json()["cases"]
        assert len(cases) == 9
        fault_by_id = {c["id"]: c["fault_type"] for c in cases}

        hits = 0
        trials = 0
        for title in self.FAULT_TITLES:
            query = _raise_alert(client, "WT-01", title)
            resp = client.get("/api/cases/similar", params={"alert_id": query, "top_k": 3})
            assert resp.status_code == 200
            top3 = resp.json()["recommendations"][:3]
            trials += 1
            if top3 and all(fault_by_id.get(r["case_id"]) == title for r in top3):
                hits += 1
        assert hits / trials >= 0.8


def _create_farm_with_turbine(client: TestClient, turbine_id: str = "WT-01") -> str:
    resp = client.post("/api/farms", json={"name": "測試風場"})
    assert resp.status_code == 201
    farm_id = str(resp.json()["farm"]["id"])
    assign = client.post(f"/api/farms/{farm_id}/turbines", json={"turbine_id": turbine_id})
    assert assign.status_code == 200
    return farm_id


def _farm_overview(client: TestClient, farm_id: str) -> dict[str, int]:
    farms = client.get("/api/farms/overview").json()["farms"]
    return next(f for f in farms if f["farm_id"] == farm_id)


class TestMultiFarmLinkage:
    """TC-08：風機歸屬風場後走主流程，風場總覽 / 比較的告警與工單數即時反映。"""

    def test_overview_and_compare_follow_case_flow(self, client: TestClient) -> None:
        farm_id = _create_farm_with_turbine(client)

        alert_id = _raise_alert(client)
        row = _farm_overview(client, farm_id)
        assert (row["active_alerts"], row["critical_alerts"]) == (1, 1)

        resp = client.post(f"/api/alerts/{alert_id}/create-work-order")
        assert resp.status_code == 201
        order_id = str(resp.json()["work_order_id"])
        assert _farm_overview(client, farm_id)["open_work_orders"] == 1
        compare = client.get(f"/api/farms/{farm_id}/compare").json()["turbines"][0]
        assert compare["turbine_id"] == "WT-01"
        assert compare["open_work_orders"] == 1

        done = client.patch(f"/api/work-orders/{order_id}", json={"status": "completed"})
        assert done.status_code == 200
        assert _farm_overview(client, farm_id)["open_work_orders"] == 0


class TestUnassignedTurbine:
    """TC-09：未歸屬風機的告警不計入任何風場，且不報錯。"""

    def test_unassigned_alert_not_counted(self, client: TestClient) -> None:
        farm_id = _create_farm_with_turbine(client, "WT-01")
        _close_case_flow(client, "WT-99")
        _raise_alert(client, "WT-99")

        row = _farm_overview(client, farm_id)
        assert (row["active_alerts"], row["open_work_orders"]) == (0, 0)
        assert client.get("/api/cases").json()["total"] == 1


class TestFlowDuration:
    """TC-10：全流程計時（記錄耗時，目標 < 2 秒；以 10 秒為防退化上限避免 CI 抖動）。"""

    def test_full_flow_duration(self, client: TestClient) -> None:
        start = time.perf_counter()
        _close_case_flow(client)
        new_alert = _raise_alert(client)
        resp = client.get("/api/cases/similar", params={"alert_id": new_alert})
        elapsed = time.perf_counter() - start
        assert resp.status_code == 200
        print(f"TC-10 全流程耗時：{elapsed:.3f} 秒（目標 < 2 秒）")
        assert elapsed < 10
