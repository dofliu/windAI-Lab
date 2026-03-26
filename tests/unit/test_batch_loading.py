"""DataInspectorSkill 與 BatchLoadSkill 的單元測試。

使用臨時資料夾與合成 CSV 檔案驗證：
- 資料夾掃描與檔案統計
- 取樣頻率推斷
- 載入策略推薦邏輯
- 直接合併、降頻聚合、逐檔處理三種策略
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.skills.data.data_inspector import (
    DataInspectorSkill,
    _format_interval,
    _format_size,
    _infer_sampling_interval,
    _recommend_strategy,
    _scan_folder,
    _sample_files,
)
from src.skills.data.batch_load import (
    BatchLoadSkill,
    _concat_dataframes,
    _ensure_datetime_index,
    _read_file,
    _resample_aggregate,
)


# ── 測試用合成資料 ──────────────────────────────────────────────


def _make_csv_files(
    folder: Path,
    n_files: int = 5,
    rows_per_file: int = 100,
    interval_seconds: int = 1,
    seed: int = 42,
) -> list[Path]:
    """在指定資料夾中產生合成 CSV 檔案。"""
    rng = np.random.default_rng(seed)
    files: list[Path] = []

    for i in range(n_files):
        start = pd.Timestamp("2024-01-01") + pd.Timedelta(
            seconds=i * rows_per_file * interval_seconds
        )
        timestamps = pd.date_range(start, periods=rows_per_file, freq=f"{interval_seconds}s")

        wind_speed = rng.weibull(2.0, rows_per_file) * 7 + 1
        power = np.clip(wind_speed ** 3 * 0.5, 0, 2050)

        df = pd.DataFrame(
            {
                "Timestamp": timestamps,
                "Wind Speed_Mean": wind_speed,
                "Active Power_Mean": power,
                "Ambient Temperature_Mean": 15 + rng.normal(0, 2, rows_per_file),
            }
        )

        filepath = folder / f"data_segment_{i:04d}.csv"
        df.to_csv(filepath, index=False)
        files.append(filepath)

    return files


# ── DataInspectorSkill 測試 ─────────────────────────────────────


class TestScanFolder:
    """_scan_folder 函式的測試。"""

    def test_counts_csv_files(self, tmp_path: Path) -> None:
        """確認正確計算 CSV 檔案數。"""
        _make_csv_files(tmp_path, n_files=3)
        report = _scan_folder(tmp_path)
        assert report["file_count"] == 3
        assert report["total_size_bytes"] > 0
        assert ".csv" in report["format_distribution"]

    def test_ignores_hidden_files(self, tmp_path: Path) -> None:
        """確認忽略隱藏檔案。"""
        _make_csv_files(tmp_path, n_files=2)
        (tmp_path / ".hidden.csv").write_text("a,b\n1,2\n")
        report = _scan_folder(tmp_path)
        assert report["file_count"] == 2

    def test_empty_folder(self, tmp_path: Path) -> None:
        """確認空資料夾回傳 0 檔案。"""
        report = _scan_folder(tmp_path)
        assert report["file_count"] == 0

    def test_subdirectory_scan(self, tmp_path: Path) -> None:
        """確認可遞迴掃描子目錄。"""
        sub = tmp_path / "sub"
        sub.mkdir()
        _make_csv_files(sub, n_files=2)
        _make_csv_files(tmp_path, n_files=1)
        report = _scan_folder(tmp_path)
        assert report["file_count"] == 3


class TestSampleFiles:
    """_sample_files 函式的測試。"""

    def test_detects_sampling_interval(self, tmp_path: Path) -> None:
        """確認正確推斷 1 秒取樣頻率。"""
        _make_csv_files(tmp_path, n_files=2, interval_seconds=1)
        report = _scan_folder(tmp_path)
        sample = _sample_files(report["files"])
        assert sample["sampling_interval_seconds"] is not None
        assert abs(sample["sampling_interval_seconds"] - 1.0) < 0.5

    def test_schema_consistency(self, tmp_path: Path) -> None:
        """確認偵測一致的欄位結構。"""
        _make_csv_files(tmp_path, n_files=3)
        report = _scan_folder(tmp_path)
        sample = _sample_files(report["files"])
        assert sample["schema_consistent"] is True

    def test_detects_wind_speed_field(self, tmp_path: Path) -> None:
        """確認偵測到風速欄位。"""
        _make_csv_files(tmp_path, n_files=1)
        report = _scan_folder(tmp_path)
        sample = _sample_files(report["files"])
        assert len(sample["detected_fields"]) > 0


class TestRecommendStrategy:
    """_recommend_strategy 函式的測試。"""

    def test_few_files_recommends_direct_concat(self) -> None:
        """少量檔案應推薦直接合併。"""
        strategy = _recommend_strategy(
            file_report={"file_count": 5, "total_size_bytes": 10 * 1024 * 1024},
            sample_report={"sampling_interval_seconds": 600},
            analysis_purpose="fault_diagnosis",
        )
        assert strategy["strategy"] == "direct_concat"

    def test_many_high_freq_files_recommends_aggregate(self) -> None:
        """大量高頻檔案應推薦降頻聚合。"""
        strategy = _recommend_strategy(
            file_report={"file_count": 1000, "total_size_bytes": 2000 * 1024 * 1024},
            sample_report={"sampling_interval_seconds": 1},
            analysis_purpose="power_curve",
        )
        assert strategy["strategy"] == "aggregate_then_merge"

    def test_vibration_analysis_recommends_per_file(self) -> None:
        """振動分析應推薦逐檔處理。"""
        strategy = _recommend_strategy(
            file_report={"file_count": 100, "total_size_bytes": 500 * 1024 * 1024},
            sample_report={"sampling_interval_seconds": 0.001},
            analysis_purpose="vibration_analysis",
        )
        assert strategy["strategy"] == "per_file_processing"

    def test_turbulence_includes_aggregation_params(self) -> None:
        """紊流分析應包含 turbulence_intensity 額外特徵。"""
        strategy = _recommend_strategy(
            file_report={"file_count": 500, "total_size_bytes": 1000 * 1024 * 1024},
            sample_report={"sampling_interval_seconds": 1},
            analysis_purpose="turbulence_analysis",
        )
        assert strategy["strategy"] == "aggregate_then_merge"
        assert "turbulence_intensity" in strategy.get("extra_features", [])


# ── BatchLoadSkill 輔助函式測試 ─────────────────────────────────


class TestConcatDataframes:
    """_concat_dataframes 函式的測試。"""

    def test_merges_and_sorts(self) -> None:
        """確認合併後按時間排序。"""
        idx1 = pd.date_range("2024-01-01", periods=3, freq="10min")
        idx2 = pd.date_range("2024-01-01 00:05", periods=3, freq="10min")
        df1 = pd.DataFrame({"val": [1, 2, 3]}, index=idx1)
        df2 = pd.DataFrame({"val": [4, 5, 6]}, index=idx2)

        merged = _concat_dataframes([df1, df2])
        assert len(merged) == 6
        assert merged.index.is_monotonic_increasing

    def test_removes_duplicates(self) -> None:
        """確認去除重複時間戳。"""
        idx = pd.date_range("2024-01-01", periods=3, freq="10min")
        df1 = pd.DataFrame({"val": [1, 2, 3]}, index=idx)
        df2 = pd.DataFrame({"val": [10, 20, 30]}, index=idx)

        merged = _concat_dataframes([df1, df2], remove_duplicates=True)
        assert len(merged) == 3


class TestResampleAggregate:
    """_resample_aggregate 函式的測試。"""

    def test_downsamples_1s_to_10min(self) -> None:
        """確認 1 秒資料可降頻至 10 分鐘。"""
        idx = pd.date_range("2024-01-01", periods=1200, freq="1s")  # 20 分鐘
        df = pd.DataFrame(
            {"wind_speed": np.random.randn(1200), "power": np.random.randn(1200)},
            index=idx,
        )
        result = _resample_aggregate(df, "600s", ["mean", "std"])
        assert result is not None
        # 20 分鐘的資料以 10 分鐘聚合，應有 2~3 個 bin
        assert 1 <= len(result) <= 3
        # 應有 wind_speed (mean) 與 wind_speed_std 欄位
        assert "wind_speed" in result.columns
        assert "wind_speed_std" in result.columns

    def test_non_datetime_index_returns_none(self) -> None:
        """非時間索引應回傳 None。"""
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = _resample_aggregate(df, "600s", ["mean"])
        assert result is None


class TestEnsureDatetimeIndex:
    """_ensure_datetime_index 函式的測試。"""

    def test_converts_timestamp_column_to_index(self) -> None:
        """確認能將 Timestamp 欄位轉為 DatetimeIndex。"""
        df = pd.DataFrame({
            "Timestamp": pd.date_range("2024-01-01", periods=5, freq="1min"),
            "value": [1, 2, 3, 4, 5],
        })
        result = _ensure_datetime_index(df)
        assert isinstance(result.index, pd.DatetimeIndex)

    def test_keeps_existing_datetime_index(self) -> None:
        """已有 DatetimeIndex 的 DataFrame 不變。"""
        idx = pd.date_range("2024-01-01", periods=5, freq="1min")
        df = pd.DataFrame({"value": [1, 2, 3, 4, 5]}, index=idx)
        result = _ensure_datetime_index(df)
        assert isinstance(result.index, pd.DatetimeIndex)
        assert len(result) == 5


class TestReadFile:
    """_read_file 函式的測試。"""

    def test_reads_csv(self, tmp_path: Path) -> None:
        """確認可讀取 CSV。"""
        filepath = tmp_path / "test.csv"
        pd.DataFrame({"a": [1, 2], "b": [3, 4]}).to_csv(filepath, index=False)
        df = _read_file(filepath)
        assert df is not None
        assert len(df) == 2

    def test_reads_parquet(self, tmp_path: Path) -> None:
        """確認可讀取 Parquet。"""
        pytest.importorskip("pyarrow")
        filepath = tmp_path / "test.parquet"
        pd.DataFrame({"a": [1, 2], "b": [3, 4]}).to_parquet(filepath)
        df = _read_file(filepath)
        assert df is not None
        assert len(df) == 2


# ── 格式化工具函式測試 ──────────────────────────────────────────


class TestFormatters:
    """格式化工具函式的測試。"""

    def test_format_size_bytes(self) -> None:
        assert _format_size(500) == "500 B"

    def test_format_size_kb(self) -> None:
        assert _format_size(2048) == "2.0 KB"

    def test_format_size_mb(self) -> None:
        assert _format_size(5 * 1024 * 1024) == "5.0 MB"

    def test_format_interval_seconds(self) -> None:
        assert _format_interval(1) == "1s"

    def test_format_interval_minutes(self) -> None:
        assert _format_interval(600) == "10min"

    def test_format_interval_none(self) -> None:
        assert _format_interval(None) == "未知"

    def test_format_interval_ms(self) -> None:
        assert _format_interval(0.001) == "1ms"


class TestInferSamplingInterval:
    """_infer_sampling_interval 函式的測試。"""

    def test_detects_1_second(self) -> None:
        """確認偵測 1 秒取樣。"""
        df = pd.DataFrame({
            "Timestamp": pd.date_range("2024-01-01", periods=100, freq="1s"),
            "value": range(100),
        })
        interval = _infer_sampling_interval(df)
        assert interval is not None
        assert abs(interval - 1.0) < 0.1

    def test_detects_10_minutes(self) -> None:
        """確認偵測 10 分鐘取樣。"""
        df = pd.DataFrame({
            "DateTime": pd.date_range("2024-01-01", periods=100, freq="10min"),
            "value": range(100),
        })
        interval = _infer_sampling_interval(df)
        assert interval is not None
        assert abs(interval - 600.0) < 1.0

    def test_no_time_column_returns_none(self) -> None:
        """無時間欄位應回傳 None。"""
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        interval = _infer_sampling_interval(df)
        assert interval is None
