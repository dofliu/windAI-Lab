"""src.features.domain_features.wind_features 的單元測試。

測試風機領域特徵工程模組，包含功率曲線特徵計算、
溫度差異特徵計算，以及運行狀態特徵的新增。
"""

from __future__ import annotations

import pandas as pd

from src.features.domain_features.wind_features import (
    compute_operational_features,
    compute_power_curve_features,
    compute_temperature_features,
)

# ── 測試輔助函式 ──────────────────────────────────────────────────────────────


def _make_wind_df(
    n: int = 10,
    ws_col: str = "Wind Speed_Mean",
    power_col: str = "Active Power_Mean",
    ws_values: list[float] | None = None,
    pwr_values: list[float] | None = None,
) -> pd.DataFrame:
    """建立測試用的風機 SCADA DataFrame。

    Args:
        n: 資料列數。
        ws_col: 風速欄位名稱。
        power_col: 功率欄位名稱。
        ws_values: 自訂風速值；若為 None 則自動產生。
        pwr_values: 自訂功率值；若為 None 則自動產生。

    Returns:
        含 DatetimeIndex 的 DataFrame。
    """
    index = pd.date_range(start="2024-01-01", periods=n, freq="10min")
    ws = ws_values if ws_values is not None else [float(i % 15 + 2) for i in range(n)]
    pwr = pwr_values if pwr_values is not None else [min(float(w**2 * 10), 2050.0) for w in ws]
    return pd.DataFrame({ws_col: ws, power_col: pwr}, index=index)


# ── compute_power_curve_features 測試 ────────────────────────────────────────


class TestComputePowerCurveFeatures:
    """compute_power_curve_features 函式的測試。"""

    def test_adds_theoretical_power_column(self, sample_scada_df: pd.DataFrame) -> None:
        """確認新增 theoretical_power 欄位。"""
        result = compute_power_curve_features(sample_scada_df)
        assert "theoretical_power" in result.columns

    def test_adds_power_curve_deviation_column(self, sample_scada_df: pd.DataFrame) -> None:
        """確認新增 power_curve_deviation 欄位。"""
        result = compute_power_curve_features(sample_scada_df)
        assert "power_curve_deviation" in result.columns

    def test_adds_power_curve_deviation_pct_column(self, sample_scada_df: pd.DataFrame) -> None:
        """確認新增 power_curve_deviation_pct 欄位。"""
        result = compute_power_curve_features(sample_scada_df)
        assert "power_curve_deviation_pct" in result.columns

    def test_adds_capacity_factor_column(self, sample_scada_df: pd.DataFrame) -> None:
        """確認新增 capacity_factor 欄位。"""
        result = compute_power_curve_features(sample_scada_df)
        assert "capacity_factor" in result.columns

    def test_adds_normalized_power_column(self, sample_scada_df: pd.DataFrame) -> None:
        """確認新增 normalized_power 欄位。"""
        result = compute_power_curve_features(sample_scada_df)
        assert "normalized_power" in result.columns

    def test_adds_all_five_expected_columns(self, sample_scada_df: pd.DataFrame) -> None:
        """確認一次性新增全部五個功率曲線特徵欄位。"""
        result = compute_power_curve_features(sample_scada_df)
        expected_cols = [
            "theoretical_power",
            "power_curve_deviation",
            "power_curve_deviation_pct",
            "capacity_factor",
            "normalized_power",
        ]
        for col in expected_cols:
            assert col in result.columns, f"缺少欄位：{col}"

    def test_does_not_modify_original_dataframe(self, sample_scada_df: pd.DataFrame) -> None:
        """確認函式不就地修改輸入的 DataFrame。"""
        original_cols = set(sample_scada_df.columns)
        original_len = len(sample_scada_df)
        compute_power_curve_features(sample_scada_df)
        assert set(sample_scada_df.columns) == original_cols
        assert len(sample_scada_df) == original_len

    def test_theoretical_power_zero_below_cut_in(self) -> None:
        """確認風速低於切入風速（3.0 m/s）時理論功率為 0。"""
        ws = [1.0, 2.0, 2.9]
        pwr = [0.0, 0.0, 0.0]
        df = _make_wind_df(n=3, ws_values=ws, pwr_values=pwr)
        result = compute_power_curve_features(df)
        assert (result["theoretical_power"] == 0.0).all()

    def test_theoretical_power_rated_at_full_wind(self) -> None:
        """確認風速達到額定風速（>=12.5 m/s）時理論功率等於額定值。"""
        ws = [12.5, 15.0, 20.0]
        pwr = [2050.0, 2050.0, 2050.0]
        df = _make_wind_df(n=3, ws_values=ws, pwr_values=pwr)
        result = compute_power_curve_features(df)
        assert (result["theoretical_power"] == 2050.0).all()

    def test_capacity_factor_range(self, sample_scada_df: pd.DataFrame) -> None:
        """確認容量因數在合理範圍內（允許略低於 0 或略高於 1）。"""
        result = compute_power_curve_features(sample_scada_df)
        cf = result["capacity_factor"].dropna()
        assert cf.min() >= -0.5
        assert cf.max() <= 2.0

    def test_normalized_power_clipped_at_1_2(self) -> None:
        """確認 normalized_power 上限被截斷至 1.2。"""
        ws = [15.0, 15.0]
        pwr = [2050.0, 2500.0]  # 第二筆超過 2050 kW
        df = _make_wind_df(n=2, ws_values=ws, pwr_values=pwr)
        result = compute_power_curve_features(df)
        assert result["normalized_power"].max() <= 1.2

    def test_power_curve_deviation_is_actual_minus_theoretical(self) -> None:
        """確認功率曲線偏差為實際功率減去理論功率。"""
        ws = [15.0]
        pwr = [1800.0]  # 低於額定 2050 kW
        df = _make_wind_df(n=1, ws_values=ws, pwr_values=pwr)
        result = compute_power_curve_features(df)
        expected_dev = pwr[0] - result["theoretical_power"].iloc[0]
        assert abs(result["power_curve_deviation"].iloc[0] - expected_dev) < 1e-6

    def test_without_wind_or_power_column_no_new_cols(self) -> None:
        """確認輸入 DataFrame 缺少風速或功率欄位時不新增特徵欄。"""
        df = pd.DataFrame({"other_col": [1.0, 2.0, 3.0]})
        result = compute_power_curve_features(df)
        assert "theoretical_power" not in result.columns
        assert "capacity_factor" not in result.columns

    def test_custom_rated_power_used_in_calculation(self) -> None:
        """確認自訂額定功率正確影響理論功率與容量因數。"""
        ws = [15.0]
        pwr = [1000.0]
        df = _make_wind_df(n=1, ws_values=ws, pwr_values=pwr)
        result = compute_power_curve_features(df, rated_power=1000.0)
        assert result["theoretical_power"].iloc[0] == 1000.0  # 額定風速以上 = 額定功率


# ── compute_temperature_features 測試 ────────────────────────────────────────


class TestComputeTemperatureFeatures:
    """compute_temperature_features 函式的測試。"""

    def test_adds_gear_oil_temp_delta_with_ambient_and_gear(
        self, sample_scada_df: pd.DataFrame
    ) -> None:
        """確認同時有齒輪油溫與環境溫度欄位時，新增 gear_oil_temp_delta。"""
        result = compute_temperature_features(sample_scada_df)
        assert "gear_oil_temp_delta" in result.columns

    def test_gear_oil_temp_delta_correct_value(self, sample_scada_df: pd.DataFrame) -> None:
        """確認 gear_oil_temp_delta = 齒輪油溫 - 環境溫度。"""
        result = compute_temperature_features(sample_scada_df)
        expected_delta = (
            sample_scada_df["Gear Oil Temp_Mean"] - sample_scada_df["Nacelle Ambient Temp_Mean"]
        )
        pd.testing.assert_series_equal(
            result["gear_oil_temp_delta"],
            expected_delta,
            check_names=False,
        )

    def test_adds_gear_oil_rolling_mean(self, sample_scada_df: pd.DataFrame) -> None:
        """確認有齒輪油溫欄位時，新增 gear_oil_temp_rolling_mean。"""
        result = compute_temperature_features(sample_scada_df)
        assert "gear_oil_temp_rolling_mean" in result.columns

    def test_adds_gear_oil_rolling_std(self, sample_scada_df: pd.DataFrame) -> None:
        """確認有齒輪油溫欄位時，新增 gear_oil_temp_rolling_std。"""
        result = compute_temperature_features(sample_scada_df)
        assert "gear_oil_temp_rolling_std" in result.columns

    def test_does_not_modify_original_dataframe(self, sample_scada_df: pd.DataFrame) -> None:
        """確認函式不就地修改輸入的 DataFrame。"""
        original_cols = set(sample_scada_df.columns)
        compute_temperature_features(sample_scada_df)
        assert set(sample_scada_df.columns) == original_cols

    def test_handles_missing_temperature_columns_gracefully(self) -> None:
        """確認缺少溫度欄位時不拋出例外，僅跳過對應特徵。"""
        df = pd.DataFrame({"Wind Speed_Mean": [5.0, 10.0], "Active Power_Mean": [300.0, 1200.0]})
        result = compute_temperature_features(df)
        assert isinstance(result, pd.DataFrame)
        assert "gear_oil_temp_delta" not in result.columns

    def test_handles_empty_dataframe(self) -> None:
        """確認傳入空 DataFrame 不拋出例外。"""
        df = pd.DataFrame(columns=["Wind Speed_Mean", "Active Power_Mean"])
        result = compute_temperature_features(df)
        assert isinstance(result, pd.DataFrame)

    def test_delta_dtype_is_numeric(self, sample_scada_df: pd.DataFrame) -> None:
        """確認 gear_oil_temp_delta 為數值型別。"""
        result = compute_temperature_features(sample_scada_df)
        assert pd.api.types.is_numeric_dtype(result["gear_oil_temp_delta"])

    def test_gear_oil_delta_positive_when_oil_hotter(self) -> None:
        """確認齒輪油溫高於環境溫度時，delta 為正值。"""
        index = pd.date_range("2024-01-01", periods=3, freq="10min")
        df = pd.DataFrame(
            {
                "Nacelle Ambient Temp_Mean": [10.0, 12.0, 11.0],
                "Gear Oil Temp_Mean": [50.0, 55.0, 52.0],
            },
            index=index,
        )
        result = compute_temperature_features(df)
        assert (result["gear_oil_temp_delta"] > 0).all()


# ── compute_operational_features 測試 ────────────────────────────────────────


class TestComputeOperationalFeatures:
    """compute_operational_features 函式的測試。"""

    def test_adds_operating_state_column(self, sample_scada_df: pd.DataFrame) -> None:
        """確認新增 operating_state 欄位。"""
        result = compute_operational_features(sample_scada_df)
        assert "operating_state" in result.columns

    def test_operating_state_values_are_valid_categories(
        self, sample_scada_df: pd.DataFrame
    ) -> None:
        """確認所有 operating_state 值均為預定義的合法類別。"""
        result = compute_operational_features(sample_scada_df)
        valid_states = {"idle", "partial", "full", "shutdown", "unknown"}
        actual_states = set(result["operating_state"].unique())
        assert actual_states.issubset(valid_states)

    def test_does_not_modify_original_dataframe(self, sample_scada_df: pd.DataFrame) -> None:
        """確認函式不就地修改輸入的 DataFrame。"""
        original_cols = set(sample_scada_df.columns)
        compute_operational_features(sample_scada_df)
        assert set(sample_scada_df.columns) == original_cols

    def test_low_wind_speed_results_in_idle_state(self) -> None:
        """確認風速低於切入風速（3.0 m/s）時運行狀態為 'idle'。"""
        ws = [1.0, 2.0, 2.5]
        pwr = [0.0, 0.0, 0.0]
        df = _make_wind_df(n=3, ws_values=ws, pwr_values=pwr)
        result = compute_operational_features(df)
        assert (result["operating_state"] == "idle").all()

    def test_full_power_results_in_full_state(self) -> None:
        """確認功率 >= 95% 額定功率（>=1947.5 kW）時狀態為 'full'。"""
        ws = [15.0, 18.0, 20.0]
        pwr = [2050.0, 2050.0, 2050.0]
        df = _make_wind_df(n=3, ws_values=ws, pwr_values=pwr)
        result = compute_operational_features(df)
        assert (result["operating_state"] == "full").all()

    def test_partial_power_results_in_partial_state(self) -> None:
        """確認切入風速以上且功率 < 95% 額定時狀態為 'partial'。"""
        ws = [5.0, 7.0, 9.0]
        pwr = [200.0, 500.0, 900.0]
        df = _make_wind_df(n=3, ws_values=ws, pwr_values=pwr)
        result = compute_operational_features(df)
        assert (result["operating_state"] == "partial").all()

    def test_handles_missing_wind_or_power_column(self) -> None:
        """確認缺少風速或功率欄位時不拋出例外。"""
        df = pd.DataFrame({"other_col": [1.0, 2.0, 3.0]})
        result = compute_operational_features(df)
        assert isinstance(result, pd.DataFrame)
        assert "operating_state" not in result.columns

    def test_adds_tip_speed_ratio_with_rotor_column(self) -> None:
        """確認同時有風速與轉子轉速欄位時，新增 tip_speed_ratio。"""
        index = pd.date_range("2024-01-01", periods=4, freq="10min")
        df = pd.DataFrame(
            {
                "Wind Speed_Mean": [5.0, 8.0, 10.0, 12.0],
                "Active Power_Mean": [300.0, 800.0, 1400.0, 2000.0],
                "Rotor Speed_Mean": [8.0, 12.0, 14.0, 16.0],
            },
            index=index,
        )
        result = compute_operational_features(df)
        assert "tip_speed_ratio" in result.columns

    def test_operating_state_column_dtype_is_object(self, sample_scada_df: pd.DataFrame) -> None:
        """確認 operating_state 欄位為字串型別。"""
        result = compute_operational_features(sample_scada_df)
        assert pd.api.types.is_string_dtype(result["operating_state"])

    def test_sample_df_contains_multiple_states(self, sample_scada_df: pd.DataFrame) -> None:
        """確認合成 SCADA 資料（含多種風速）產生多種運行狀態。"""
        result = compute_operational_features(sample_scada_df)
        unique_states = result["operating_state"].unique()
        # 20 筆風速從 1.0 到 22.0 m/s，應出現超過一種狀態
        assert len(unique_states) > 1
