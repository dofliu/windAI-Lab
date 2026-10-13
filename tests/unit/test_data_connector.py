"""資料連接器與斷線告警整合測試。"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from src.services.data_connector import (
    ConnectorManager,
    MQTTConnector,
    _prune_fetched_files,
)


class TestMQTTConnector:
    """MQTTConnector 雙軌與數據流測試。"""

    @pytest.mark.asyncio
    async def test_mqtt_connector_fallback_stream(self) -> None:
        """測試 MQTTConnector 在沒有 paho-mqtt 下的回落與隨機數據緩衝提取。"""
        config = {
            "host": "localhost",
            "port": 1883,
            "topic": "test/topic",
            "turbine_id": "WT-01",
        }

        # 使用 patch 將 HAS_PAHO 設為 False 模擬無依賴環境
        with patch("src.services.data_connector.HAS_PAHO", False):
            conn = MQTTConnector("test_mqtt", "MQTT 測試連線", 5, config)
            try:
                success = await conn.connect()
                assert success is True
                assert conn.is_connected is True

                # 測試 fetch_data (會隨機返回一筆數據以供定時輪詢)
                df = await conn.fetch_data()
                assert df is not None
                assert len(df) == 1
                assert "Wind_speed" in df.columns
                assert "Active_power" in df.columns
            finally:
                await conn.disconnect()
                assert conn.is_connected is False


class TestConnectorManagerHealth:
    """ConnectorManager 連線健康與斷線告警整合測試。"""

    @pytest.mark.asyncio
    async def test_connector_failure_triggers_alert(self, tmp_path) -> None:
        """測試當連接器拉取資料連續失敗達 3 次時，是否觸發離線告警。"""
        configs_dir = tmp_path / "connectors"
        configs_dir.mkdir()

        conn_yaml = {
            "id": "bad_connector",
            "name": "故障資料源",
            "type": "mock",
            "enabled": True,
            "interval_seconds": 1,
            "config": {"turbine_id": "WT-01"},
        }
        with open(configs_dir / "bad_connector.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump(conn_yaml, f)

        # 建立 Manager 實例
        manager = ConnectorManager(configs_dir=configs_dir)
        manager.load_connectors()

        conn = manager.connectors["bad_connector"]
        conn.fetch_data = AsyncMock(return_value=None)

        engine_mock = MagicMock()
        engine_mock.evaluate = MagicMock()

        with patch("src.services.alert_engine.get_alert_rule_engine", return_value=engine_mock):
            # 1. 第一次失敗
            manager._handle_fetch_fail(conn)
            assert manager.fail_counts["bad_connector"] == 1
            engine_mock.evaluate.assert_not_called()

            # 2. 第二次失敗
            manager._handle_fetch_fail(conn)
            assert manager.fail_counts["bad_connector"] == 2
            engine_mock.evaluate.assert_not_called()

            # 3. 第三次失敗 -> 應觸發評估離線指標
            manager._handle_fetch_fail(conn)
            assert manager.fail_counts["bad_connector"] == 3

            engine_mock.evaluate.assert_called_once()
            called_args = engine_mock.evaluate.call_args[0][0]
            assert called_args["connector_online_status"] == 0.0
            assert called_args["connector_id"] == "bad_connector"


class TestPruneFetchedFiles:
    """連接器拉取檔保留上限，避免 data/raw 無限增長。"""

    def test_keeps_latest_n(self, tmp_path: Path) -> None:
        for i in range(5):
            (tmp_path / f"WT-01_api_fetched_20261013_14{i:02d}00.csv").write_text("x")
        (tmp_path / "WT-02_api_fetched_20261013_140000.csv").write_text("x")
        (tmp_path / "WT-01.csv").write_text("x")

        removed = _prune_fetched_files(tmp_path, "WT-01", keep=2)

        assert len(removed) == 3
        left = sorted(p.name for p in tmp_path.iterdir())
        assert left == [
            "WT-01.csv",
            "WT-01_api_fetched_20261013_140300.csv",
            "WT-01_api_fetched_20261013_140400.csv",
            "WT-02_api_fetched_20261013_140000.csv",
        ]

    def test_under_limit_removes_nothing(self, tmp_path: Path) -> None:
        (tmp_path / "WT-01_api_fetched_20261013_140000.csv").write_text("x")
        assert _prune_fetched_files(tmp_path, "WT-01", keep=10) == []
