"""src.core 模組的單元測試。

測試應用程式設定（config）、自定義例外（exceptions）
與全域常數（constants）的正確性。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.config import Settings, get_settings
from src.core.constants import (
    AGENT_NAMESPACES,
    AGENT_TIERS,
    DEFAULT_AIR_DENSITY_KGM3,
    DEFAULT_CUT_IN_SPEED_MS,
    DEFAULT_CUT_OUT_SPEED_MS,
    DEFAULT_RATED_POWER_KW,
    DEFAULT_RATED_WIND_SPEED_MS,
    DEFAULT_ROTOR_DIAMETER_M,
    SCADA_REQUIRED_COLUMNS,
    SCADA_SAMPLING_INTERVAL_MIN,
    STATUS_COLORS,
    TASK_ID_PREFIX,
    WS_MESSAGE_TYPES,
    TurbineProfile,
)
from src.core.exceptions import (
    AgentBusyError,
    AgentNotFoundError,
    DataLoadError,
    DataValidationError,
    ModelNotFoundError,
    ModelTrainingError,
    WindAIError,
    WorkflowExecutionError,
    WorkflowNotFoundError,
)


# ── Settings 設定測試 ─────────────────────────────────────────────────────────


class TestSettings:
    """Settings 設定模組的測試。"""

    def test_default_host_is_0000(self, app_settings: Settings) -> None:
        """確認預設 host 為 '0.0.0.0'。"""
        assert app_settings.host == "0.0.0.0"

    def test_default_port_is_5800(self, app_settings: Settings) -> None:
        """確認預設 port 為 5800。"""
        assert app_settings.port == 5800

    def test_default_debug_is_false(self, app_settings: Settings) -> None:
        """確認預設 debug 模式為 False。"""
        assert app_settings.debug is False

    def test_default_log_level_is_debug(self, app_settings: Settings) -> None:
        """確認預設日誌等級為 'DEBUG'。"""
        assert app_settings.log_level == "DEBUG"

    def test_default_app_name(self, app_settings: Settings) -> None:
        """確認預設應用程式名稱為 'WindAI Lab'。"""
        assert app_settings.app_name == "WindAI Lab"

    def test_default_app_version(self, app_settings: Settings) -> None:
        """確認應用程式版本為 '0.2.0'。"""
        assert app_settings.app_version == "0.2.0"

    def test_default_database_url_is_sqlite(self, app_settings: Settings) -> None:
        """確認預設資料庫連線字串為 SQLite。"""
        assert app_settings.database_url.startswith("sqlite:")

    def test_data_root_is_path_instance(self, app_settings: Settings) -> None:
        """確認 data_root 為 Path 物件。"""
        assert isinstance(app_settings.data_root, Path)

    def test_model_registry_is_path_instance(self, app_settings: Settings) -> None:
        """確認 model_registry 為 Path 物件。"""
        assert isinstance(app_settings.model_registry, Path)

    def test_data_raw_is_subdir_of_data_root(self, app_settings: Settings) -> None:
        """確認 data_raw 為 data_root 的 raw 子目錄。"""
        assert app_settings.data_raw == app_settings.data_root / "raw"

    def test_data_processed_is_subdir_of_data_root(self, app_settings: Settings) -> None:
        """確認 data_processed 為 data_root 的 processed 子目錄。"""
        assert app_settings.data_processed == app_settings.data_root / "processed"

    def test_data_features_is_subdir_of_data_root(self, app_settings: Settings) -> None:
        """確認 data_features 為 data_root 的 features 子目錄。"""
        assert app_settings.data_features == app_settings.data_root / "features"

    def test_data_external_is_subdir_of_data_root(self, app_settings: Settings) -> None:
        """確認 data_external 為 data_root 的 external 子目錄。"""
        assert app_settings.data_external == app_settings.data_root / "external"

    def test_mlflow_tracking_uri_default(self, app_settings: Settings) -> None:
        """確認 MLflow tracking URI 預設為 localhost:5000。"""
        assert app_settings.mlflow_tracking_uri == "http://localhost:5000"

    def test_get_settings_returns_singleton(self) -> None:
        """確認 get_settings 回傳快取的單例（兩次呼叫回傳同一物件）。"""
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_settings_can_be_instantiated_without_env_file(self) -> None:
        """確認在無 .env 檔案的環境下仍可建立 Settings 實例。"""
        settings = Settings()
        assert settings is not None
        assert isinstance(settings, Settings)


# ── 例外類別測試 ──────────────────────────────────────────────────────────────


class TestWindAIError:
    """WindAIError 基礎例外的測試。"""

    def test_default_message_contains_unexpected_error(self) -> None:
        """確認基礎例外的預設訊息包含「未預期」。"""
        err = WindAIError()
        assert "未預期" in str(err)

    def test_custom_message_is_used(self) -> None:
        """確認自訂訊息正確設定。"""
        err = WindAIError("自訂錯誤訊息")
        assert "自訂錯誤訊息" in str(err)
        assert err.message == "自訂錯誤訊息"

    def test_is_exception_subclass(self) -> None:
        """確認 WindAIError 繼承自 Exception。"""
        assert issubclass(WindAIError, Exception)

    def test_can_be_raised_and_caught(self) -> None:
        """確認 WindAIError 可以被正常拋出與捕捉。"""
        with pytest.raises(WindAIError):
            raise WindAIError("測試拋出")


class TestAgentNotFoundError:
    """AgentNotFoundError 的測試。"""

    def test_agent_id_attribute_is_set(self) -> None:
        """確認 agent_id 屬性正確設定。"""
        err = AgentNotFoundError("test-agent")
        assert err.agent_id == "test-agent"

    def test_message_contains_agent_id(self) -> None:
        """確認錯誤訊息包含代理 ID。"""
        err = AgentNotFoundError("my-agent")
        assert "my-agent" in str(err)

    def test_is_windai_error_subclass(self) -> None:
        """確認 AgentNotFoundError 繼承自 WindAIError。"""
        assert issubclass(AgentNotFoundError, WindAIError)

    def test_can_be_caught_as_windai_error(self) -> None:
        """確認可以用 WindAIError 類型捕捉 AgentNotFoundError。"""
        with pytest.raises(WindAIError):
            raise AgentNotFoundError("agent-xyz")


class TestAgentBusyError:
    """AgentBusyError 的測試。"""

    def test_agent_id_attribute_is_set(self) -> None:
        """確認 agent_id 屬性正確設定。"""
        err = AgentBusyError("busy-agent")
        assert err.agent_id == "busy-agent"

    def test_message_contains_agent_id(self) -> None:
        """確認錯誤訊息包含代理 ID。"""
        err = AgentBusyError("busy-agent")
        assert "busy-agent" in str(err)

    def test_is_windai_error_subclass(self) -> None:
        """確認 AgentBusyError 繼承自 WindAIError。"""
        assert issubclass(AgentBusyError, WindAIError)


class TestWorkflowErrors:
    """工作流程例外的測試。"""

    def test_workflow_not_found_error_workflow_name(self) -> None:
        """確認 WorkflowNotFoundError 正確設定 workflow_name 屬性。"""
        err = WorkflowNotFoundError("run-diagnosis")
        assert err.workflow_name == "run-diagnosis"

    def test_workflow_not_found_error_message_contains_name(self) -> None:
        """確認 WorkflowNotFoundError 訊息包含工作流程名稱。"""
        err = WorkflowNotFoundError("run-diagnosis")
        assert "run-diagnosis" in str(err)

    def test_workflow_execution_error_attributes(self) -> None:
        """確認 WorkflowExecutionError 正確設定 workflow_name 與 reason 屬性。"""
        err = WorkflowExecutionError("data-pipeline", "連線逾時")
        assert err.workflow_name == "data-pipeline"
        assert err.reason == "連線逾時"

    def test_workflow_execution_error_message(self) -> None:
        """確認 WorkflowExecutionError 訊息包含工作流程名稱與原因。"""
        err = WorkflowExecutionError("data-pipeline", "連線逾時")
        assert "data-pipeline" in str(err)
        assert "連線逾時" in str(err)

    def test_both_inherit_from_windai_error(self) -> None:
        """確認工作流程例外均繼承自 WindAIError。"""
        assert issubclass(WorkflowNotFoundError, WindAIError)
        assert issubclass(WorkflowExecutionError, WindAIError)


class TestDataErrors:
    """資料相關例外的測試。"""

    def test_data_load_error_source_and_reason(self) -> None:
        """確認 DataLoadError 正確設定 source 與 reason 屬性。"""
        err = DataLoadError("data/raw/file.csv", "檔案不存在")
        assert err.source == "data/raw/file.csv"
        assert err.reason == "檔案不存在"

    def test_data_load_error_message_contains_both(self) -> None:
        """確認 DataLoadError 訊息同時包含來源與原因。"""
        err = DataLoadError("file.parquet", "格式錯誤")
        assert "file.parquet" in str(err)
        assert "格式錯誤" in str(err)

    def test_data_validation_error_field_and_reason(self) -> None:
        """確認 DataValidationError 正確設定 field 與 reason 屬性。"""
        err = DataValidationError("wind_speed", "數值超出合理範圍")
        assert err.field == "wind_speed"
        assert err.reason == "數值超出合理範圍"

    def test_data_validation_error_message(self) -> None:
        """確認 DataValidationError 訊息包含欄位名稱與原因。"""
        err = DataValidationError("power_output", "包含負值")
        assert "power_output" in str(err)
        assert "包含負值" in str(err)

    def test_both_inherit_from_windai_error(self) -> None:
        """確認資料例外均繼承自 WindAIError。"""
        assert issubclass(DataLoadError, WindAIError)
        assert issubclass(DataValidationError, WindAIError)


class TestModelErrors:
    """模型相關例外的測試。"""

    def test_model_not_found_error_model_name(self) -> None:
        """確認 ModelNotFoundError 正確設定 model_name 屬性。"""
        err = ModelNotFoundError("xgboost-v1")
        assert err.model_name == "xgboost-v1"

    def test_model_not_found_error_message(self) -> None:
        """確認 ModelNotFoundError 訊息包含模型名稱。"""
        err = ModelNotFoundError("random-forest-v2")
        assert "random-forest-v2" in str(err)

    def test_model_training_error_attributes(self) -> None:
        """確認 ModelTrainingError 正確設定 model_name 與 reason 屬性。"""
        err = ModelTrainingError("xgboost-v1", "記憶體不足")
        assert err.model_name == "xgboost-v1"
        assert err.reason == "記憶體不足"

    def test_both_inherit_from_windai_error(self) -> None:
        """確認模型例外均繼承自 WindAIError。"""
        assert issubclass(ModelNotFoundError, WindAIError)
        assert issubclass(ModelTrainingError, WindAIError)


# ── 常數定義測試 ──────────────────────────────────────────────────────────────


class TestAgentNamespacesConstant:
    """AGENT_NAMESPACES 常數的測試。"""

    def test_has_six_namespaces(self) -> None:
        """確認代理命名空間數量為 6。"""
        assert len(AGENT_NAMESPACES) == 6

    def test_all_keys_start_with_w(self) -> None:
        """確認所有命名空間鍵值均以 'w' 開頭。"""
        for ns in AGENT_NAMESPACES:
            assert ns.startswith("w"), f"命名空間 '{ns}' 未以 'w' 開頭"

    def test_contains_expected_namespaces(self) -> None:
        """確認包含所有預期的命名空間鍵值。"""
        expected = {"wLab", "wData", "wAI", "wDomain", "wEng", "wRes"}
        assert expected == set(AGENT_NAMESPACES.keys())

    def test_values_are_strings(self) -> None:
        """確認所有命名空間值為非空字串。"""
        for key, value in AGENT_NAMESPACES.items():
            assert isinstance(value, str)
            assert len(value) > 0


class TestAgentTiersConstant:
    """AGENT_TIERS 常數的測試。"""

    def test_has_six_tiers(self) -> None:
        """確認代理層級數量為 6。"""
        assert len(AGENT_TIERS) == 6

    def test_tier_numbers_are_sequential(self) -> None:
        """確認層級編號為 1 到 6 的連續整數。"""
        tier_numbers = set(AGENT_TIERS.values())
        assert tier_numbers == {1, 2, 3, 4, 5, 6}

    def test_leadership_is_tier_1(self) -> None:
        """確認 leadership 為第一層級。"""
        assert AGENT_TIERS["leadership"] == 1

    def test_research_is_tier_6(self) -> None:
        """確認 research 為第六層級。"""
        assert AGENT_TIERS["research"] == 6


class TestWindTurbineConstants:
    """風機運行參數常數的測試。"""

    def test_rated_power_is_2050_kw(self) -> None:
        """確認額定功率預設值為 2050.0 kW。"""
        assert DEFAULT_RATED_POWER_KW == 2050.0

    def test_rotor_diameter_is_92_m(self) -> None:
        """確認轉子直徑預設值為 92.0 m。"""
        assert DEFAULT_ROTOR_DIAMETER_M == 92.0

    def test_cut_in_speed_is_3_ms(self) -> None:
        """確認切入風速預設值為 3.0 m/s。"""
        assert DEFAULT_CUT_IN_SPEED_MS == 3.0

    def test_rated_wind_speed_is_12_5_ms(self) -> None:
        """確認額定風速預設值為 12.5 m/s。"""
        assert DEFAULT_RATED_WIND_SPEED_MS == 12.5

    def test_cut_out_speed_is_25_ms(self) -> None:
        """確認切出風速預設值為 25.0 m/s。"""
        assert DEFAULT_CUT_OUT_SPEED_MS == 25.0

    def test_air_density_is_1_225(self) -> None:
        """確認空氣密度預設值為 1.225 kg/m³（海平面標準值）。"""
        assert DEFAULT_AIR_DENSITY_KGM3 == 1.225


class TestTurbineProfile:
    """TurbineProfile 資料類別的測試。"""

    def test_default_values(self) -> None:
        """確認 TurbineProfile 預設值與全域常數一致。"""
        p = TurbineProfile()
        assert p.rated_power_kw == DEFAULT_RATED_POWER_KW
        assert p.cut_in_speed_ms == DEFAULT_CUT_IN_SPEED_MS
        assert p.cut_out_speed_ms == DEFAULT_CUT_OUT_SPEED_MS
        assert p.rated_wind_speed_ms == DEFAULT_RATED_WIND_SPEED_MS
        assert p.rotor_diameter_m == DEFAULT_ROTOR_DIAMETER_M

    def test_custom_values(self) -> None:
        """確認可建立自訂風機參數的 TurbineProfile。"""
        p = TurbineProfile(rated_power_kw=3000, rotor_diameter_m=110)
        assert p.rated_power_kw == 3000
        assert p.rotor_diameter_m == 110

    def test_from_profiler_dict(self) -> None:
        """確認可從 TurbineProfilerSkill 輸出建構 TurbineProfile。"""
        d = {
            "rated_power_kw": 4200,
            "cut_in_speed_ms": 3.5,
            "rated_wind_speed_ms": 13.0,
            "cut_out_speed_ms": 28.0,
            "rotor_diameter_m": 136.0,
        }
        p = TurbineProfile.from_profiler_dict(d)
        assert p.rated_power_kw == 4200
        assert p.cut_in_speed_ms == 3.5
        assert p.rated_wind_speed_ms == 13.0
        assert p.rotor_diameter_m == 136.0


class TestScadaConstants:
    """SCADA 相關常數的測試。"""

    def test_sampling_interval_is_10_min(self) -> None:
        """確認 SCADA 取樣間隔預設值為 10 分鐘。"""
        assert SCADA_SAMPLING_INTERVAL_MIN == 10

    def test_required_columns_is_list(self) -> None:
        """確認 SCADA 必要欄位為列表型別。"""
        assert isinstance(SCADA_REQUIRED_COLUMNS, list)

    def test_required_columns_contains_wind_speed(self) -> None:
        """確認必要欄位包含 wind_speed。"""
        assert "wind_speed" in SCADA_REQUIRED_COLUMNS

    def test_required_columns_contains_power_output(self) -> None:
        """確認必要欄位包含 power_output。"""
        assert "power_output" in SCADA_REQUIRED_COLUMNS

    def test_required_columns_count(self) -> None:
        """確認必要欄位總數為 5。"""
        assert len(SCADA_REQUIRED_COLUMNS) == 5


class TestStatusColorsConstant:
    """STATUS_COLORS 常數的測試。"""

    def test_has_six_status_colors(self) -> None:
        """確認狀態顏色定義涵蓋全部 6 個代理狀態。"""
        assert len(STATUS_COLORS) == 6

    def test_all_colors_start_with_hash(self) -> None:
        """確認所有顏色值為合法十六進位色碼格式（以 # 開頭）。"""
        for status, color in STATUS_COLORS.items():
            assert color.startswith("#"), f"狀態 '{status}' 的顏色 '{color}' 格式錯誤"

    def test_contains_idle_status_color(self) -> None:
        """確認包含 idle 狀態的顏色定義。"""
        assert "idle" in STATUS_COLORS

    def test_contains_error_status_color(self) -> None:
        """確認包含 error 狀態的顏色定義。"""
        assert "error" in STATUS_COLORS


class TestMiscConstants:
    """其他常數的測試。"""

    def test_task_id_prefix_is_wlab(self) -> None:
        """確認任務 ID 前綴為 'WLAB'。"""
        assert TASK_ID_PREFIX == "WLAB"

    def test_ws_message_types_is_dict(self) -> None:
        """確認 WebSocket 訊息類型為字典型別。"""
        assert isinstance(WS_MESSAGE_TYPES, dict)

    def test_ws_message_types_contains_initial_state(self) -> None:
        """確認 WebSocket 訊息類型包含 INITIAL_STATE。"""
        assert "INITIAL_STATE" in WS_MESSAGE_TYPES

    def test_ws_message_types_contains_agent_status_update(self) -> None:
        """確認 WebSocket 訊息類型包含 AGENT_STATUS_UPDATE。"""
        assert "AGENT_STATUS_UPDATE" in WS_MESSAGE_TYPES
