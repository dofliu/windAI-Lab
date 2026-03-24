"""核心模組測試。"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.config import Settings, get_settings
from src.core.constants import AGENT_NAMESPACES, AGENT_TIERS, DEFAULT_RATED_POWER_KW
from src.core.exceptions import (
    AgentBusyError,
    AgentNotFoundError,
    DataLoadError,
    WindAIError,
    WorkflowNotFoundError,
)


class TestSettings:
    """Settings 設定模組測試群組。"""

    def test_default_host(self, app_settings: Settings) -> None:
        """預設 host 應為 0.0.0.0。"""
        assert app_settings.host == "0.0.0.0"

    def test_default_port(self, app_settings: Settings) -> None:
        """預設 port 應為 8000。"""
        assert app_settings.port == 8000

    def test_data_root_is_path(self, app_settings: Settings) -> None:
        """data_root 應為 Path 物件。"""
        assert isinstance(app_settings.data_root, Path)

    def test_data_subdirectories(self, app_settings: Settings) -> None:
        """data_raw/processed/features 應為 data_root 的子目錄。"""
        assert app_settings.data_raw == app_settings.data_root / "raw"
        assert app_settings.data_processed == app_settings.data_root / "processed"
        assert app_settings.data_features == app_settings.data_root / "features"

    def test_get_settings_returns_same_instance(self) -> None:
        """get_settings 應回傳快取的單例。"""
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2


class TestConstants:
    """常數定義測試群組。"""

    def test_agent_namespaces_count(self) -> None:
        """應有 6 個代理命名空間。"""
        assert len(AGENT_NAMESPACES) == 6

    def test_all_namespaces_start_with_w(self) -> None:
        """所有 namespace 應以 w 開頭。"""
        for ns in AGENT_NAMESPACES:
            assert ns.startswith("w")

    def test_agent_tiers_count(self) -> None:
        """應有 6 個代理層級。"""
        assert len(AGENT_TIERS) == 6

    def test_rated_power_value(self) -> None:
        """額定功率預設值應為 2050 kW。"""
        assert DEFAULT_RATED_POWER_KW == 2050.0


class TestExceptions:
    """自定義例外測試群組。"""

    def test_windai_error_message(self) -> None:
        """基礎例外應包含預設訊息。"""
        err = WindAIError()
        assert "未預期" in str(err)

    def test_agent_not_found_error(self) -> None:
        """代理未找到例外應包含 agent_id。"""
        err = AgentNotFoundError("test-agent")
        assert err.agent_id == "test-agent"
        assert "test-agent" in str(err)

    def test_agent_busy_error(self) -> None:
        """代理忙碌例外應包含 agent_id。"""
        err = AgentBusyError("test-agent")
        assert err.agent_id == "test-agent"

    def test_workflow_not_found_error(self) -> None:
        """工作流程未找到例外應包含 workflow_name。"""
        err = WorkflowNotFoundError("test-wf")
        assert err.workflow_name == "test-wf"

    def test_data_load_error(self) -> None:
        """資料載入例外應包含來源與原因。"""
        err = DataLoadError("file.csv", "file not found")
        assert err.source == "file.csv"
        assert err.reason == "file not found"

    def test_exception_inheritance(self) -> None:
        """所有自定義例外應繼承自 WindAIError。"""
        assert issubclass(AgentNotFoundError, WindAIError)
        assert issubclass(AgentBusyError, WindAIError)
        assert issubclass(WorkflowNotFoundError, WindAIError)
        assert issubclass(DataLoadError, WindAIError)
