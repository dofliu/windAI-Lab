"""SCADA 資料清洗模組測試。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data_pipeline.cleaning.scada_cleaner import clean_scada_data


@pytest.fixture()
def raw_scada_df() -> pd.DataFrame:
    """建立含異常值的合成 SCADA 資料。"""
    index = pd.date_range("2024-01-01", periods=30, freq="10min")
    rng = np.random.default_rng(42)
    ws = rng.uniform(3, 15, 30)
    power = 2050 * ((ws - 3) / (12.5 - 3)) ** 3
    power = np.clip(power, 0, 2050)
    df = pd.DataFrame(
        {
            "wind_speed_Mean": ws,
            "power_Mean": power,
        },
        index=index,
    )
    return df


class TestCleanScadaData:
    """clean_scada_data 函式測試群組。"""

    def test_returns_dataframe_and_report(self, raw_scada_df: pd.DataFrame) -> None:
        """應回傳 DataFrame 與品質報告 dict。"""
        result, report = clean_scada_data(raw_scada_df)
        assert isinstance(result, pd.DataFrame)
        assert isinstance(report, dict)

    def test_quality_report_keys(self, raw_scada_df: pd.DataFrame) -> None:
        """品質報告應包含所有必要鍵值。"""
        _, report = clean_scada_data(raw_scada_df)
        expected_keys = {
            "total_rows",
            "original_rows",
            "duplicates_removed",
            "missing_pct",
            "outliers_removed",
            "time_range",
        }
        assert expected_keys.issubset(report.keys())

    def test_removes_duplicates(self) -> None:
        """應移除重複時間戳記。"""
        idx = pd.DatetimeIndex(
            ["2024-01-01 00:00", "2024-01-01 00:00", "2024-01-01 00:10"]
        )
        df = pd.DataFrame(
            {"wind_speed_Mean": [5.0, 5.0, 8.0], "power_Mean": [200, 200, 900]},
            index=idx,
        )
        result, report = clean_scada_data(df)
        assert len(result) == 2
        assert report["duplicates_removed"] == 1

    def test_flags_negative_power_as_outlier(self) -> None:
        """高風速下的負功率應被標記為異常。"""
        idx = pd.date_range("2024-01-01", periods=5, freq="10min")
        df = pd.DataFrame(
            {
                "Wind Speed_Mean": [10.0, 10.0, 10.0, 10.0, 10.0],
                "Active Power_Mean": [1000.0, -50.0, 800.0, 900.0, 1100.0],
            },
            index=idx,
        )
        result, report = clean_scada_data(df)
        assert report["outliers_removed"] >= 1

    def test_flags_over_rated_power(self) -> None:
        """超過額定功率 110% 的資料應被標記。"""
        idx = pd.date_range("2024-01-01", periods=3, freq="10min")
        df = pd.DataFrame(
            {
                "Wind Speed_Mean": [12.0, 12.0, 12.0],
                "Active Power_Mean": [2000.0, 2500.0, 1800.0],  # 2500 > 2050*1.1
            },
            index=idx,
        )
        result, report = clean_scada_data(df)
        assert report["outliers_removed"] >= 1

    def test_preserves_row_count(self, raw_scada_df: pd.DataFrame) -> None:
        """清洗不應刪除列，只是將異常值設為 NaN。"""
        result, _ = clean_scada_data(raw_scada_df)
        assert len(result) == len(raw_scada_df)
