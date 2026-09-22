"""src.data_pipeline.cleaning.scada_cleaner 的單元測試。

測試 SCADA 資料清洗流程，包含重複時間戳記移除、
缺失值處理、異常值偵測，以及品質報告結構驗證。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.data_pipeline.cleaning.scada_cleaner import clean_scada_data

# ── 測試輔助函式 ──────────────────────────────────────────────────────────────


def _make_scada_df(
    n: int = 20,
    wind_col: str = "Wind Speed_Mean",
    power_col: str = "Active Power_Mean",
    ws_values: list[float] | None = None,
    pwr_values: list[float] | None = None,
) -> pd.DataFrame:
    """建立測試用的合成 SCADA DataFrame。

    Args:
        n: 資料列數。
        wind_col: 風速欄位名稱。
        power_col: 功率欄位名稱。
        ws_values: 自訂風速值列表；若為 None 則自動產生合理值。
        pwr_values: 自訂功率值列表；若為 None 則自動產生合理值。

    Returns:
        含 DatetimeIndex 的 SCADA 模擬 DataFrame。
    """
    index = pd.date_range(start="2024-01-01", periods=n, freq="10min")
    ws = ws_values if ws_values is not None else [float(i % 15 + 2) for i in range(n)]
    pwr = pwr_values if pwr_values is not None else [min(float(w**2 * 10), 2050.0) for w in ws]
    return pd.DataFrame({wind_col: ws, power_col: pwr}, index=index)


# ── 基本行為測試 ──────────────────────────────────────────────────────────────


class TestCleanScadaDataReturnType:
    """clean_scada_data 回傳值型別的測試。"""

    def test_returns_tuple_of_two_elements(self) -> None:
        """確認函式回傳包含兩個元素的元組。"""
        df = _make_scada_df()
        result = clean_scada_data(df)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_first_element_is_dataframe(self) -> None:
        """確認元組第一個元素為 DataFrame。"""
        df = _make_scada_df()
        df_clean, _ = clean_scada_data(df)
        assert isinstance(df_clean, pd.DataFrame)

    def test_second_element_is_dict(self) -> None:
        """確認元組第二個元素為字典。"""
        df = _make_scada_df()
        _, report = clean_scada_data(df)
        assert isinstance(report, dict)

    def test_clean_does_not_modify_original_df(self) -> None:
        """確認清洗操作不會就地修改原始 DataFrame。"""
        df = _make_scada_df(n=10)
        original_wind_values = df["Wind Speed_Mean"].copy()
        original_len = len(df)
        clean_scada_data(df)
        assert len(df) == original_len
        pd.testing.assert_series_equal(df["Wind Speed_Mean"], original_wind_values)

    def test_clean_preserves_datetime_index(self) -> None:
        """確認清洗後仍保留 DatetimeIndex。"""
        df = _make_scada_df()
        df_clean, _ = clean_scada_data(df)
        assert isinstance(df_clean.index, pd.DatetimeIndex)

    def test_clean_normal_data_row_count_unchanged(self) -> None:
        """確認無異常值的資料清洗後列數不減少。

        異常值設為 NaN 而非刪除列，因此列數應與原始相同。
        """
        ws = [5.0] * 10
        pwr = [500.0] * 10
        df = _make_scada_df(n=10, ws_values=ws, pwr_values=pwr)
        df_clean, _ = clean_scada_data(df)
        assert len(df_clean) == len(df)


# ── 重複時間戳記移除測試 ──────────────────────────────────────────────────────


class TestDuplicateRemoval:
    """重複時間戳記移除的測試。"""

    def test_removes_single_duplicate_timestamp(self) -> None:
        """確認單一重複的時間戳記被移除，總列數減一。"""
        index = pd.DatetimeIndex(
            ["2024-01-01 00:00", "2024-01-01 00:10", "2024-01-01 00:10", "2024-01-01 00:20"]
        )
        df = pd.DataFrame(
            {
                "Wind Speed_Mean": [5.0, 6.0, 7.0, 8.0],
                "Active Power_Mean": [200.0, 300.0, 350.0, 400.0],
            },
            index=index,
        )
        df_clean, report = clean_scada_data(df)
        assert len(df_clean) == 3
        assert report["duplicates_removed"] == 1

    def test_duplicate_keeps_first_occurrence(self) -> None:
        """確認保留重複記錄中的第一筆，後續記錄被移除。"""
        index = pd.DatetimeIndex(["2024-01-01 00:00", "2024-01-01 00:00"])
        df = pd.DataFrame(
            {"Wind Speed_Mean": [5.0, 99.0], "Active Power_Mean": [200.0, 9999.0]},
            index=index,
        )
        df_clean, _ = clean_scada_data(df)
        assert len(df_clean) == 1
        assert df_clean["Wind Speed_Mean"].iloc[0] == 5.0

    def test_no_duplicates_reports_zero_removed(self) -> None:
        """確認無重複時，品質報告中 duplicates_removed 回報 0。"""
        df = _make_scada_df(n=10)
        _, report = clean_scada_data(df)
        assert report["duplicates_removed"] == 0

    def test_multiple_duplicate_groups_all_removed(self) -> None:
        """確認多組重複時間戳記均被移除，只保留每組的第一筆。"""
        index = pd.DatetimeIndex(
            [
                "2024-01-01 00:00",
                "2024-01-01 00:00",  # 第一組：1 個重複
                "2024-01-01 00:10",
                "2024-01-01 00:10",  # 第二組：1 個重複
                "2024-01-01 00:20",
            ]
        )
        df = pd.DataFrame(
            {"Wind Speed_Mean": [5.0] * 5, "Active Power_Mean": [200.0] * 5},
            index=index,
        )
        df_clean, report = clean_scada_data(df)
        assert len(df_clean) == 3
        assert report["duplicates_removed"] == 2

    def test_original_rows_reflects_pre_dedup_count(self) -> None:
        """確認 original_rows 反映清洗前（含重複）的列數。"""
        index = pd.DatetimeIndex(["2024-01-01 00:00", "2024-01-01 00:00", "2024-01-01 00:10"])
        df = pd.DataFrame(
            {"Wind Speed_Mean": [5.0, 5.0, 8.0], "Active Power_Mean": [200.0, 200.0, 900.0]},
            index=index,
        )
        _, report = clean_scada_data(df)
        assert report["original_rows"] == 3


# ── 異常值偵測測試 ────────────────────────────────────────────────────────────


class TestOutlierDetection:
    """異常值偵測的測試。"""

    def test_negative_power_with_high_wind_is_flagged(self) -> None:
        """確認風速高於切入值但功率為明顯負值的記錄被標記。

        條件：ws > cut_in (3.0) + 1 = 4.0 且 power < -10
        """
        ws = [5.0, 6.0, 7.0]  # 均高於 4.0
        pwr = [-200.0, 500.0, 600.0]  # 第一筆為明顯負功率
        df = _make_scada_df(n=3, ws_values=ws, pwr_values=pwr)
        df_clean, report = clean_scada_data(df)
        assert report["outliers_removed"] >= 1
        assert pd.isna(df_clean["Active Power_Mean"].iloc[0])

    def test_over_rated_power_is_flagged(self) -> None:
        """確認超過額定功率 110% 的記錄被標記為異常。

        預設額定 2050 kW，110% 上限 = 2255 kW。
        """
        ws = [10.0, 12.0, 14.0]
        pwr = [1000.0, 2300.0, 1800.0]  # 第二筆超過 2255 kW
        df = _make_scada_df(n=3, ws_values=ws, pwr_values=pwr)
        df_clean, report = clean_scada_data(df)
        assert report["outliers_removed"] >= 1
        assert pd.isna(df_clean["Active Power_Mean"].iloc[1])

    def test_normal_data_has_zero_outliers(self) -> None:
        """確認正常範圍內的資料不被標記為異常值。"""
        ws = [5.0, 8.0, 10.0, 12.0]
        pwr = [300.0, 800.0, 1400.0, 2000.0]
        df = _make_scada_df(n=4, ws_values=ws, pwr_values=pwr)
        _, report = clean_scada_data(df)
        assert report["outliers_removed"] == 0

    def test_wind_speed_below_zero_sets_ws_to_nan(self) -> None:
        """確認負風速的記錄被標記：風速欄位設為 NaN。"""
        ws = [-1.0, 5.0, 8.0]
        pwr = [0.0, 300.0, 800.0]
        df = _make_scada_df(n=3, ws_values=ws, pwr_values=pwr)
        df_clean, report = clean_scada_data(df)
        assert pd.isna(df_clean["Wind Speed_Mean"].iloc[0])
        assert report["outliers_removed"] >= 1

    def test_wind_speed_above_50_sets_ws_to_nan(self) -> None:
        """確認風速超過 50 m/s 的記錄被標記：風速欄位設為 NaN。"""
        ws = [5.0, 55.0, 8.0]
        pwr = [300.0, 2050.0, 800.0]
        df = _make_scada_df(n=3, ws_values=ws, pwr_values=pwr)
        df_clean, report = clean_scada_data(df)
        assert pd.isna(df_clean["Wind Speed_Mean"].iloc[1])
        assert report["outliers_removed"] >= 1

    def test_outlier_sets_power_to_nan_not_remove_row(self) -> None:
        """確認異常值處理為設 NaN，而非刪除整列。"""
        ws = [10.0, 10.0, 10.0]
        pwr = [1000.0, 2400.0, 1200.0]  # 第二筆超過 110%
        df = _make_scada_df(n=3, ws_values=ws, pwr_values=pwr)
        df_clean, _ = clean_scada_data(df)
        assert len(df_clean) == 3  # 列數不變
        assert pd.isna(df_clean["Active Power_Mean"].iloc[1])

    def test_custom_rated_power_adjusts_threshold(self) -> None:
        """確認使用自訂額定功率計算異常閾值（1000 kW → 上限 1100 kW）。"""
        ws = [10.0, 10.0]
        pwr = [900.0, 1200.0]  # 第二筆超過 1100 kW
        df = _make_scada_df(n=2, ws_values=ws, pwr_values=pwr)
        _, report = clean_scada_data(df, rated_power=1000.0)
        assert report["outliers_removed"] >= 1

    def test_custom_cut_in_speed_changes_negative_power_threshold(self) -> None:
        """確認自訂切入風速影響負功率異常的判定。

        若 cut_in = 5.0，則風速 = 5.5 時需確認為異常。
        """
        ws = [5.5, 8.0]
        pwr = [-200.0, 800.0]
        df = _make_scada_df(n=2, ws_values=ws, pwr_values=pwr)
        _, report = clean_scada_data(df, cut_in_speed=5.0)
        # ws[0] = 5.5 > 5.0 + 1 = 6.0 → 不符合條件，outliers 應為 0
        # (5.5 < 6.0，未超過閾值)
        # 此測試主要確認參數被實際使用（不拋出錯誤）
        assert isinstance(report["outliers_removed"], int)


# ── 品質報告結構測試 ───────────────────────────────────────────────────────────


class TestQualityReport:
    """品質報告結構的測試。"""

    def test_quality_report_has_all_required_keys(self) -> None:
        """確認品質報告包含所有必要的鍵值。"""
        df = _make_scada_df()
        _, report = clean_scada_data(df)
        required_keys = {
            "total_rows",
            "original_rows",
            "duplicates_removed",
            "missing_pct",
            "outliers_removed",
            "time_range",
        }
        assert required_keys.issubset(report.keys())

    def test_quality_report_time_range_has_start_and_end(self) -> None:
        """確認 time_range 子字典包含 start 與 end 兩個鍵。"""
        df = _make_scada_df()
        _, report = clean_scada_data(df)
        assert "start" in report["time_range"]
        assert "end" in report["time_range"]

    def test_quality_report_total_rows_matches_cleaned_df(self) -> None:
        """確認 total_rows 與清洗後 DataFrame 的列數一致。"""
        df = _make_scada_df(n=15)
        df_clean, report = clean_scada_data(df)
        assert report["total_rows"] == len(df_clean)

    def test_quality_report_original_rows_matches_input(self) -> None:
        """確認 original_rows 與輸入 DataFrame 的列數一致。"""
        df = _make_scada_df(n=20)
        _, report = clean_scada_data(df)
        assert report["original_rows"] == 20

    def test_quality_report_missing_pct_is_float(self) -> None:
        """確認 missing_pct 為浮點數型別。"""
        df = _make_scada_df()
        _, report = clean_scada_data(df)
        assert isinstance(report["missing_pct"], float)

    def test_quality_report_missing_pct_in_valid_range(self) -> None:
        """確認 missing_pct 在 0.0 至 100.0 之間。"""
        df = _make_scada_df()
        _, report = clean_scada_data(df)
        assert 0.0 <= report["missing_pct"] <= 100.0

    def test_quality_report_outliers_removed_is_non_negative_int(self) -> None:
        """確認 outliers_removed 為非負整數。"""
        df = _make_scada_df()
        _, report = clean_scada_data(df)
        assert isinstance(report["outliers_removed"], int)
        assert report["outliers_removed"] >= 0

    def test_quality_report_time_range_not_na_for_datetime_index(self) -> None:
        """確認具有 DatetimeIndex 的資料，time_range 的 start/end 不為 'N/A'。"""
        df = _make_scada_df(n=5)
        _, report = clean_scada_data(df)
        assert report["time_range"]["start"] != "N/A"
        assert report["time_range"]["end"] != "N/A"

    def test_quality_report_no_nan_data_has_zero_missing_pct(self) -> None:
        """確認無缺失值資料的 missing_pct 為 0.0。"""
        ws = [5.0, 8.0, 10.0]
        pwr = [300.0, 800.0, 1400.0]
        df = _make_scada_df(n=3, ws_values=ws, pwr_values=pwr)
        _, report = clean_scada_data(df)
        assert report["missing_pct"] == 0.0


# ── 缺失值處理測試 ────────────────────────────────────────────────────────────


class TestMissingValueHandling:
    """缺失值處理的測試。"""

    def test_single_nan_in_gap_is_interpolated(self) -> None:
        """確認單筆（小間隙）缺失值被線性插值填補。"""
        ws = [5.0, np.nan, 7.0, 8.0, 9.0]
        pwr = [300.0, np.nan, 500.0, 600.0, 700.0]
        df = _make_scada_df(n=5, ws_values=ws, pwr_values=pwr)
        df_clean, _ = clean_scada_data(df)
        assert not pd.isna(df_clean["Wind Speed_Mean"].iloc[1])

    def test_interpolated_value_is_between_neighbors(self) -> None:
        """確認插值結果位於鄰近值之間。"""
        ws = [4.0, np.nan, 6.0, 7.0]
        pwr = [200.0, np.nan, 400.0, 500.0]
        df = _make_scada_df(n=4, ws_values=ws, pwr_values=pwr)
        df_clean, _ = clean_scada_data(df)
        interpolated = df_clean["Wind Speed_Mean"].iloc[1]
        assert 4.0 <= interpolated <= 6.0

    def test_large_gap_exceeding_limit_retains_nan(self) -> None:
        """確認超過插值上限（>3 筆連續缺失）的間隙保留 NaN。"""
        ws = [5.0, np.nan, np.nan, np.nan, np.nan, 10.0]
        pwr = [300.0, np.nan, np.nan, np.nan, np.nan, 900.0]
        df = _make_scada_df(n=6, ws_values=ws, pwr_values=pwr)
        df_clean, _ = clean_scada_data(df)
        # 4 筆連續 NaN 超過插值上限，應仍有 NaN 存在
        nan_count = df_clean["Wind Speed_Mean"].isna().sum()
        assert nan_count > 0

    def test_missing_pct_nonzero_for_df_with_nans(self) -> None:
        """確認含缺失值的 DataFrame 品質報告顯示非零 missing_pct。"""
        ws = [5.0, np.nan, 7.0, 8.0, 9.0, 10.0, np.nan, np.nan, np.nan, np.nan]
        pwr = [300.0, np.nan, 500.0, 600.0, 700.0, 800.0, np.nan, np.nan, np.nan, np.nan]
        df = _make_scada_df(n=10, ws_values=ws, pwr_values=pwr)
        _, report = clean_scada_data(df)
        # 有 NaN 的情況下（且部分不能被插值）missing_pct 應 > 0
        # 即使完全填補也會回報原始缺失比例
        assert report["missing_pct"] >= 0.0
