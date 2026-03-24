"""風機領域特徵工程模組測試。"""

from __future__ import annotations

import pandas as pd
import pytest

from src.features.domain_features.wind_features import (
    compute_operational_features,
    compute_power_curve_features,
    compute_temperature_features,
)


class TestComputePowerCurveFeatures:
    """compute_power_curve_features 測試群組。"""

    def test_adds_expected_columns(self, sample_scada_df: pd.DataFrame) -> None:
        """應新增理論功率、偏差等欄位。"""
        result = compute_power_curve_features(sample_scada_df)
        expected_cols = [
            "theoretical_power",
            "power_curve_deviation",
            "power_curve_deviation_pct",
            "capacity_factor",
            "normalized_power",
        ]
        for col in expected_cols:
            assert col in result.columns, f"缺少欄位 {col}"

    def test_does_not_modify_original(self, sample_scada_df: pd.DataFrame) -> None:
        """不應修改原始 DataFrame。"""
        original_cols = set(sample_scada_df.columns)
        compute_power_curve_features(sample_scada_df)
        assert set(sample_scada_df.columns) == original_cols

    def test_capacity_factor_range(self, sample_scada_df: pd.DataFrame) -> None:
        """容量因數應在合理範圍。"""
        result = compute_power_curve_features(sample_scada_df)
        cf = result["capacity_factor"].dropna()
        assert cf.min() >= -0.1
        assert cf.max() <= 1.5


class TestComputeTemperatureFeatures:
    """compute_temperature_features 測試群組。"""

    def test_adds_gear_oil_delta(self, sample_scada_df: pd.DataFrame) -> None:
        """含齒輪箱油溫與環境溫度時應新增 delta 欄位。"""
        result = compute_temperature_features(sample_scada_df)
        assert "gear_oil_temp_delta" in result.columns

    def test_handles_missing_columns(self) -> None:
        """缺少溫度欄位時不應報錯。"""
        df = pd.DataFrame({"wind_speed_Mean": [5.0, 10.0]})
        result = compute_temperature_features(df)
        assert isinstance(result, pd.DataFrame)


class TestComputeOperationalFeatures:
    """compute_operational_features 測試群組。"""

    def test_adds_operating_state(self, sample_scada_df: pd.DataFrame) -> None:
        """應新增 operating_state 欄位。"""
        result = compute_operational_features(sample_scada_df)
        assert "operating_state" in result.columns

    def test_state_values(self, sample_scada_df: pd.DataFrame) -> None:
        """運行狀態值應為預定義類別。"""
        result = compute_operational_features(sample_scada_df)
        valid_states = {"idle", "partial", "full", "shutdown", "unknown"}
        actual_states = set(result["operating_state"].unique())
        assert actual_states.issubset(valid_states)
