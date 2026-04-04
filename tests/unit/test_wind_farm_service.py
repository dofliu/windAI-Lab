"""風場運維服務測試 — Registry, Monitor, Ticket。"""

from __future__ import annotations

import os
import tempfile

import pytest

from src.services.wind_farm import (
    AlertSeverity,
    DataSourceConfig,
    DataSourceType,
    HealthLevel,
    MonitorRecord,
    ServiceTicket,
    TicketPriority,
    TicketStatus,
    TicketTrigger,
    TurbineStatus,
    WindFarm,
    WindFarmStatus,
)


# ════════════════════════════════════════════════════════════════
# 資料模型
# ════════════════════════════════════════════════════════════════


class TestDataModels:
    def test_wind_farm_defaults(self) -> None:
        farm = WindFarm(name="Test Farm")
        assert farm.name == "Test Farm"
        assert farm.status == WindFarmStatus.ONBOARDING
        assert farm.auto_diagnose is True
        assert farm.poll_interval_min == 60
        assert farm.id  # 自動生成

    def test_data_source_config(self) -> None:
        ds = DataSourceConfig(
            source_type=DataSourceType.REST_API,
            path="https://api.example.com/scada",
            auth_token="secret",
        )
        assert ds.source_type == DataSourceType.REST_API
        assert ds.auth_token == "secret"

    def test_turbine_status(self) -> None:
        ts = TurbineStatus(
            turbine_id="WT-01",
            health_score=72.5,
            health_level=HealthLevel.WARNING,
        )
        assert ts.health_score == 72.5
        assert ts.health_level == HealthLevel.WARNING

    def test_service_ticket(self) -> None:
        ticket = ServiceTicket(
            wind_farm_id="farm-1",
            title="齒輪箱溫度異常",
            priority=TicketPriority.CRITICAL,
        )
        assert ticket.status == TicketStatus.OPEN
        assert ticket.trigger == TicketTrigger.MANUAL
        assert ticket.id.startswith("TK-")

    def test_monitor_record(self) -> None:
        record = MonitorRecord(
            wind_farm_id="farm-1",
            turbine_id="WT-01",
            health_score=55.0,
            alert_severity=AlertSeverity.CRITICAL,
        )
        assert record.health_score == 55.0
        assert record.alert_severity == AlertSeverity.CRITICAL

    def test_enum_values(self) -> None:
        assert WindFarmStatus.ACTIVE == "active"
        assert HealthLevel.CRITICAL == "critical"
        assert TicketStatus.IN_PROGRESS == "in_progress"
        assert TicketTrigger.AUTO_MONITOR == "auto_monitor"
        assert AlertSeverity.WARNING == "warning"


# ════════════════════════════════════════════════════════════════
# WindFarm Registry
# ════════════════════════════════════════════════════════════════


class TestWindFarmRegistry:
    @pytest.fixture()
    def registry(self, tmp_path):
        from src.services.wind_farm.registry import WindFarmRegistry

        return WindFarmRegistry(persist_path=str(tmp_path / "farms.json"))

    def test_register(self, registry) -> None:
        farm = registry.register(
            name="海上風場A",
            location="彰化外海",
            turbine_count=20,
            rated_power_mw=120.0,
        )
        assert farm.name == "海上風場A"
        assert farm.turbine_count == 20
        assert farm.status == WindFarmStatus.ONBOARDING

    def test_get(self, registry) -> None:
        farm = registry.register(name="Test")
        fetched = registry.get(farm.id)
        assert fetched is not None
        assert fetched.name == "Test"

    def test_get_by_name(self, registry) -> None:
        registry.register(name="Farm Alpha")
        assert registry.get_by_name("Farm Alpha") is not None
        assert registry.get_by_name("Nonexistent") is None

    def test_list_all(self, registry) -> None:
        registry.register(name="A")
        registry.register(name="B")
        assert len(registry.list_all()) == 2

    def test_activate_and_pause(self, registry) -> None:
        farm = registry.register(name="Test")
        registry.activate(farm.id)
        assert registry.get(farm.id).status == WindFarmStatus.ACTIVE

        registry.pause(farm.id)
        assert registry.get(farm.id).status == WindFarmStatus.PAUSED

    def test_list_active(self, registry) -> None:
        f1 = registry.register(name="Active")
        f2 = registry.register(name="Paused")
        registry.activate(f1.id)
        assert len(registry.list_active()) == 1

    def test_remove(self, registry) -> None:
        farm = registry.register(name="ToRemove")
        assert registry.remove(farm.id) is True
        assert registry.get(farm.id) is None
        assert registry.remove("nonexistent") is False

    def test_update_turbine_health(self, registry) -> None:
        farm = registry.register(name="Test", turbine_count=5)
        level = registry.update_turbine_health(farm.id, "WT-01", 85.0, 2)
        assert level == HealthLevel.HEALTHY

        level = registry.update_turbine_health(farm.id, "WT-02", 70.0, 5)
        assert level == HealthLevel.WARNING

        level = registry.update_turbine_health(farm.id, "WT-03", 50.0, 15)
        assert level == HealthLevel.CRITICAL

    def test_summary(self, registry) -> None:
        farm = registry.register(name="Farm", turbine_count=10, rated_power_mw=50.0)
        registry.activate(farm.id)
        registry.update_turbine_health(farm.id, "WT-01", 90.0)
        registry.update_turbine_health(farm.id, "WT-02", 55.0)

        summary = registry.get_summary()
        assert summary["total_farms"] == 1
        assert summary["active_farms"] == 1
        assert summary["total_turbines"] == 10
        assert summary["monitored_turbines"] == 2
        assert summary["health_distribution"]["healthy"] == 1
        assert summary["health_distribution"]["critical"] == 1

    def test_persistence(self, tmp_path) -> None:
        from src.services.wind_farm.registry import WindFarmRegistry

        path = str(tmp_path / "farms.json")
        r1 = WindFarmRegistry(persist_path=path)
        r1.register(name="Persistent Farm", turbine_count=5)

        # 重新載入
        r2 = WindFarmRegistry(persist_path=path)
        assert len(r2.list_all()) == 1
        assert r2.list_all()[0].name == "Persistent Farm"

    def test_to_dict_list_no_secrets(self, registry) -> None:
        registry.register(name="Farm")
        dicts = registry.to_dict_list()
        assert len(dicts) == 1
        assert "auth_token" not in dicts[0].get("data_source", {})


# ════════════════════════════════════════════════════════════════
# MonitorService + Tickets
# ════════════════════════════════════════════════════════════════


class TestMonitorService:
    def test_create_ticket(self) -> None:
        from src.services.wind_farm.monitor import MonitorService

        svc = MonitorService()
        ticket = svc.create_ticket(
            wind_farm_id="farm-1",
            turbine_id="WT-01",
            title="Test Ticket",
            priority="high",
        )
        assert ticket.id.startswith("TK-")
        assert ticket.priority == TicketPriority.HIGH
        assert ticket.status == TicketStatus.OPEN
        assert len(svc.tickets) == 1

    def test_get_ticket(self) -> None:
        from src.services.wind_farm.monitor import MonitorService

        svc = MonitorService()
        ticket = svc.create_ticket(wind_farm_id="f1", title="T1")
        assert svc.get_ticket(ticket.id) is not None
        assert svc.get_ticket("nonexistent") is None

    def test_update_ticket_status(self) -> None:
        from src.services.wind_farm.monitor import MonitorService

        svc = MonitorService()
        ticket = svc.create_ticket(wind_farm_id="f1", title="T1")

        svc.update_ticket_status(ticket.id, "assigned")
        assert ticket.status == TicketStatus.ASSIGNED
        assert ticket.assigned_at is not None

        svc.update_ticket_status(ticket.id, "in_progress")
        assert ticket.status == TicketStatus.IN_PROGRESS

        svc.update_ticket_status(ticket.id, "resolved", resolution="已修復")
        assert ticket.status == TicketStatus.RESOLVED
        assert ticket.resolution == "已修復"

    def test_get_open_tickets(self) -> None:
        from src.services.wind_farm.monitor import MonitorService

        svc = MonitorService()
        t1 = svc.create_ticket(wind_farm_id="f1", title="Open")
        t2 = svc.create_ticket(wind_farm_id="f1", title="Closed")
        svc.update_ticket_status(t2.id, "closed")

        open_tickets = svc.get_open_tickets()
        assert len(open_tickets) == 1
        assert open_tickets[0].id == t1.id

    def test_get_tickets_by_farm(self) -> None:
        from src.services.wind_farm.monitor import MonitorService

        svc = MonitorService()
        svc.create_ticket(wind_farm_id="farm-1", title="T1")
        svc.create_ticket(wind_farm_id="farm-2", title="T2")
        svc.create_ticket(wind_farm_id="farm-1", title="T3")

        farm1_tickets = svc.get_tickets_by_farm("farm-1")
        assert len(farm1_tickets) == 2

    def test_initial_state(self) -> None:
        from src.services.wind_farm.monitor import MonitorService

        svc = MonitorService()
        assert svc.is_running is False
        assert svc.records == []
        assert svc.tickets == []


# ════════════════════════════════════════════════════════════════
# DataConnector
# ════════════════════════════════════════════════════════════════


class TestDataConnector:
    @pytest.mark.asyncio
    async def test_load_local_csv(self, tmp_path) -> None:
        import pandas as pd

        from src.services.wind_farm import DataSourceConfig, DataSourceType
        from src.services.wind_farm.monitor import DataConnector

        # 建立測試 CSV
        df = pd.DataFrame({
            "Wind speed (m/s)_Mean": [5.0, 8.0, 12.0],
            "Active power (kW)_Mean": [100, 500, 1500],
        })
        csv_path = tmp_path / "WT01_scada.csv"
        df.to_csv(csv_path)

        farm = WindFarm(
            name="Test",
            data_source=DataSourceConfig(
                source_type=DataSourceType.LOCAL_FILE,
                path=str(csv_path),
            ),
        )
        result = await DataConnector.fetch(farm)
        assert len(result) == 1
        assert "WT01" in list(result.keys())[0]

    @pytest.mark.asyncio
    async def test_load_local_folder(self, tmp_path) -> None:
        import pandas as pd

        from src.services.wind_farm import DataSourceConfig, DataSourceType
        from src.services.wind_farm.monitor import DataConnector

        for name in ["WT01_data.csv", "WT02_data.csv"]:
            df = pd.DataFrame({"col": [1, 2, 3]})
            df.to_csv(tmp_path / name)

        farm = WindFarm(
            name="Test",
            data_source=DataSourceConfig(
                source_type=DataSourceType.LOCAL_FILE,
                path=str(tmp_path),
            ),
        )
        result = await DataConnector.fetch(farm)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_nonexistent_path(self) -> None:
        from src.services.wind_farm import DataSourceConfig, DataSourceType
        from src.services.wind_farm.monitor import DataConnector

        farm = WindFarm(
            name="Test",
            data_source=DataSourceConfig(
                source_type=DataSourceType.LOCAL_FILE,
                path="/nonexistent/path",
            ),
        )
        result = await DataConnector.fetch(farm)
        assert result == {}
