"""Phase 15：多風場階層資料模型（風場 → 風機群組 → 單機）測試。"""

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
    database = Database(str(tmp_path / "farms.db"))
    database.initialize()
    monkeypatch.setattr(database_module, "_db_instance", database)
    return database


@pytest.fixture
def client(db: Database) -> Iterator[TestClient]:
    """不啟動 lifespan 的 TestClient。"""
    yield TestClient(api_main.app)


def test_hierarchy_groups_and_ungrouped(db: Database) -> None:
    farm_id = db.create_wind_farm("北風場", customer="A 公司", capacity_mw=30.0)
    group_id = db.create_turbine_group(farm_id, "A 區")
    db.assign_turbine(farm_id, "WT-01", group_id=group_id, rated_power_kw=2000)
    db.assign_turbine(farm_id, "WT-02")

    farm = db.get_farm_hierarchy(farm_id)
    assert farm is not None
    assert farm["turbine_count"] == 2
    assert [t["turbine_id"] for t in farm["groups"][0]["turbines"]] == ["WT-01"]
    assert [t["turbine_id"] for t in farm["ungrouped"]] == ["WT-02"]


def test_duplicate_names_rejected(db: Database) -> None:
    farm_id = db.create_wind_farm("北風場")
    with pytest.raises(ValueError):
        db.create_wind_farm("北風場")
    db.create_turbine_group(farm_id, "A 區")
    with pytest.raises(ValueError):
        db.create_turbine_group(farm_id, "A 區")


def test_group_must_belong_to_same_farm(db: Database) -> None:
    farm_a = db.create_wind_farm("A 場")
    farm_b = db.create_wind_farm("B 場")
    group_b = db.create_turbine_group(farm_b, "B 區")
    with pytest.raises(ValueError):
        db.assign_turbine(farm_a, "WT-01", group_id=group_b)


def test_reassign_turbine_moves_between_farms(db: Database) -> None:
    farm_a = db.create_wind_farm("A 場")
    farm_b = db.create_wind_farm("B 場")
    db.assign_turbine(farm_a, "WT-01")
    db.assign_turbine(farm_b, "WT-01")
    assert db.get_farm_hierarchy(farm_a)["turbine_count"] == 0  # type: ignore[index]
    assert db.get_farm_hierarchy(farm_b)["turbine_count"] == 1  # type: ignore[index]


def test_delete_farm_cascades(db: Database) -> None:
    farm_id = db.create_wind_farm("北風場")
    group_id = db.create_turbine_group(farm_id, "A 區")
    db.assign_turbine(farm_id, "WT-01", group_id=group_id)
    assert db.delete_wind_farm(farm_id) is True
    assert db.get_wind_farm(farm_id) is None
    assert db.delete_wind_farm(farm_id) is False
    with db._connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM farm_turbines").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM turbine_groups").fetchone()[0] == 0


def test_list_farms_counts(db: Database) -> None:
    farm_id = db.create_wind_farm("北風場")
    db.create_turbine_group(farm_id, "A 區")
    db.assign_turbine(farm_id, "WT-01")
    farms = db.list_wind_farms()
    assert farms[0]["turbine_count"] == 1
    assert farms[0]["group_count"] == 1


def test_api_flow(client: TestClient) -> None:
    resp = client.post("/api/farms", json={"name": "北風場", "capacity_mw": 30})
    assert resp.status_code == 201
    farm_id = resp.json()["farm"]["id"]
    assert client.post("/api/farms", json={"name": "北風場"}).status_code == 409

    group = client.post(f"/api/farms/{farm_id}/groups", json={"name": "A 區"})
    assert group.status_code == 201
    group_id = group.json()["group_id"]

    assigned = client.post(
        f"/api/farms/{farm_id}/turbines", json={"turbine_id": "WT-01", "group_id": group_id}
    )
    assert assigned.status_code == 200
    assert assigned.json()["farm"]["groups"][0]["turbines"][0]["turbine_id"] == "WT-01"

    assert client.get("/api/farms").json()["total"] == 1
    assert client.get(f"/api/farms/{farm_id}").json()["farm"]["turbine_count"] == 1
    assert client.delete(f"/api/farms/{farm_id}").status_code == 200
    assert client.get(f"/api/farms/{farm_id}").status_code == 404


def test_api_errors(client: TestClient) -> None:
    assert client.post("/api/farms/NOPE/groups", json={"name": "x"}).status_code == 404
    assert client.post("/api/farms/NOPE/turbines", json={"turbine_id": "WT"}).status_code == 404
    farm_id = client.post("/api/farms", json={"name": "F"}).json()["farm"]["id"]
    bad = client.post(
        f"/api/farms/{farm_id}/turbines", json={"turbine_id": "WT", "group_id": "GRP-x"}
    )
    assert bad.status_code == 400
