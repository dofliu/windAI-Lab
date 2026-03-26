"""AlarmProcessorSkill 的單元測試。

測試警報欄位偵測、事件正規化、時間序列轉換、MTBF 計算等。
使用合成警報事件清單（無需外部檔案）。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.skills.data.alarm_processor import (
    AlarmProcessorSkill,
    _compute_alarm_summary,
    _compute_mtbf,
    _detect_alarm_columns,
    _events_to_timeseries,
    _normalize_events,
)


# ── 合成警報資料 ──────────────────────────────────────────────


def _make_alarm_df(n: int = 100, seed: int = 42) -> pd.DataFrame:
    """產生合成警報事件清單。"""
    rng = np.random.default_rng(seed)
    base = pd.Timestamp("2024-01-01")
    timestamps = [base + pd.Timedelta(hours=rng.integers(0, 24 * 90)) for _ in range(n)]
    timestamps.sort()

    codes = rng.choice(
        ["E001", "E002", "E003", "W001", "W002", "A001", "A002", "F001"],
        size=n,
    )
    descriptions = [
        {
            "E001": "Gearbox overtemperature",
            "E002": "Generator bearing high vibration",
            "E003": "Yaw motor fault",
            "W001": "Grid frequency deviation",
            "W002": "Pitch battery low",
            "A001": "Wind speed sensor error",
            "A002": "Nacelle temperature high",
            "F001": "Emergency stop activated",
        }.get(c, "Unknown alarm")
        for c in codes
    ]
    severities = rng.choice(["info", "warning", "high", "critical"], size=n, p=[0.2, 0.4, 0.3, 0.1])
    components = rng.choice(
        ["Gearbox", "Generator", "Yaw System", "Pitch System", "Grid", "Sensors"],
        size=n,
    )
    durations = rng.exponential(1800, size=n)  # 平均 30 分鐘

    return pd.DataFrame(
        {
            "Timestamp": timestamps,
            "Alarm Code": codes,
            "Description": descriptions,
            "Severity": severities,
            "Component": components,
            "Duration (s)": durations.astype(int),
        }
    )


def _make_minimal_alarm_df() -> pd.DataFrame:
    """產生最小化的警報清單（只有時間和警報碼）。"""
    return pd.DataFrame(
        {
            "event_time": pd.date_range("2024-01-01", periods=10, freq="6h"),
            "error_code": ["E1", "E2", "E1", "E3", "E1", "E2", "E1", "E3", "E2", "E1"],
        }
    )


def _make_start_end_alarm_df() -> pd.DataFrame:
    """產生含開始/結束時間的警報清單。"""
    starts = pd.date_range("2024-01-01", periods=5, freq="12h")
    ends = starts + pd.Timedelta(minutes=45)
    return pd.DataFrame(
        {
            "Start Time": starts,
            "End Time": ends,
            "Fault Code": ["F001", "F002", "F001", "F003", "F002"],
            "Level": ["high", "critical", "medium", "high", "warning"],
        }
    )


# ── 欄位偵測測試 ──────────────────────────────────────────────


class TestDetectAlarmColumns:
    """_detect_alarm_columns 函式的測試。"""

    def test_detects_standard_columns(self) -> None:
        """確認偵測標準警報欄位。"""
        df = _make_alarm_df()
        col_map = _detect_alarm_columns(df)
        assert col_map["timestamp"] == "Timestamp"
        assert col_map["alarm_code"] == "Alarm Code"
        assert col_map["description"] == "Description"
        assert col_map["severity"] == "Severity"
        assert col_map["component"] == "Component"

    def test_detects_minimal_columns(self) -> None:
        """確認偵測最小化欄位。"""
        df = _make_minimal_alarm_df()
        col_map = _detect_alarm_columns(df)
        assert col_map["timestamp"] is not None  # event_time
        assert col_map["alarm_code"] is not None  # error_code

    def test_detects_start_end_time(self) -> None:
        """確認偵測開始/結束時間欄位。"""
        df = _make_start_end_alarm_df()
        col_map = _detect_alarm_columns(df)
        assert col_map["timestamp"] is not None
        assert col_map["end_time"] is not None
        assert col_map["alarm_code"] is not None


# ── 事件正規化測試 ────────────────────────────────────────────


class TestNormalizeEvents:
    """_normalize_events 函式的測試。"""

    def test_normalizes_full_events(self) -> None:
        """確認完整警報清單正規化。"""
        df = _make_alarm_df(50)
        col_map = _detect_alarm_columns(df)
        events = _normalize_events(df, col_map)

        assert "timestamp" in events.columns
        assert "alarm_code" in events.columns
        assert "severity" in events.columns
        assert "duration_seconds" in events.columns
        assert len(events) == 50
        assert events["timestamp"].is_monotonic_increasing

    def test_normalizes_minimal_events(self) -> None:
        """確認最小化警報清單正規化。"""
        df = _make_minimal_alarm_df()
        col_map = _detect_alarm_columns(df)
        events = _normalize_events(df, col_map)

        assert len(events) == 10
        assert events["alarm_code"].iloc[0] == "E1"
        assert events["severity"].iloc[0] == 2  # 預設 medium

    def test_computes_duration_from_start_end(self) -> None:
        """確認從開始/結束時間計算持續時間。"""
        df = _make_start_end_alarm_df()
        col_map = _detect_alarm_columns(df)
        events = _normalize_events(df, col_map)

        # 每筆都是 45 分鐘 = 2700 秒
        assert all(events["duration_seconds"] == 2700.0)

    def test_severity_mapping(self) -> None:
        """確認嚴重度正規化。"""
        df = _make_alarm_df(20, seed=123)
        col_map = _detect_alarm_columns(df)
        events = _normalize_events(df, col_map)
        # 嚴重度應為 0-4 的整數
        assert events["severity"].between(0, 4).all()


# ── 統計摘要測試 ──────────────────────────────────────────────


class TestComputeAlarmSummary:
    """_compute_alarm_summary 函式的測試。"""

    def test_summary_structure(self) -> None:
        """確認摘要包含所有必要欄位。"""
        df = _make_alarm_df(100)
        col_map = _detect_alarm_columns(df)
        events = _normalize_events(df, col_map)
        summary = _compute_alarm_summary(events)

        assert "total_events" in summary
        assert "unique_codes" in summary
        assert "top_alarm_codes" in summary
        assert "severity_distribution" in summary
        assert "top_components" in summary
        assert "duration_stats" in summary
        assert "peak_hour" in summary
        assert summary["total_events"] == 100

    def test_top_codes_sorted_by_count(self) -> None:
        """確認 top 警報碼按次數降序。"""
        df = _make_alarm_df(200)
        col_map = _detect_alarm_columns(df)
        events = _normalize_events(df, col_map)
        summary = _compute_alarm_summary(events)

        top = summary["top_alarm_codes"]
        for i in range(len(top) - 1):
            assert top[i]["count"] >= top[i + 1]["count"]


# ── 時間序列轉換測試 ──────────────────────────────────────────


class TestEventsToTimeseries:
    """_events_to_timeseries 函式的測試。"""

    def test_daily_timeseries(self) -> None:
        """確認每日時間序列產出。"""
        df = _make_alarm_df(100)
        col_map = _detect_alarm_columns(df)
        events = _normalize_events(df, col_map)
        ts = _events_to_timeseries(events, freq="1D")

        assert isinstance(ts.index, pd.DatetimeIndex)
        assert "alarm_count" in ts.columns
        assert "alarm_duration_hours" in ts.columns
        assert "alarm_severity_mean" in ts.columns
        assert "alarm_high_severity_count" in ts.columns
        assert "alarm_unique_codes" in ts.columns
        assert ts["alarm_count"].sum() == 100

    def test_hourly_timeseries(self) -> None:
        """確認每小時時間序列產出。"""
        df = _make_alarm_df(50)
        col_map = _detect_alarm_columns(df)
        events = _normalize_events(df, col_map)
        ts = _events_to_timeseries(events, freq="1h")

        assert isinstance(ts.index, pd.DatetimeIndex)
        assert ts["alarm_count"].sum() == 50

    def test_onehot_alarm_codes(self) -> None:
        """確認 one-hot 編碼欄位。"""
        df = _make_alarm_df(100)
        col_map = _detect_alarm_columns(df)
        events = _normalize_events(df, col_map)
        ts = _events_to_timeseries(events, freq="1D", top_n_codes=5)

        alarm_cols = [c for c in ts.columns if c.startswith("alarm_") and c != "alarm_count"
                      and c != "alarm_duration_hours" and c != "alarm_severity_mean"
                      and c != "alarm_severity_max" and c != "alarm_unique_codes"
                      and c != "alarm_high_severity_count"]
        assert len(alarm_cols) > 0

    def test_component_columns(self) -> None:
        """確認元件別警報欄位。"""
        df = _make_alarm_df(100)
        col_map = _detect_alarm_columns(df)
        events = _normalize_events(df, col_map)
        ts = _events_to_timeseries(events, freq="1D")

        comp_cols = [c for c in ts.columns if c.startswith("comp_")]
        assert len(comp_cols) > 0


# ── MTBF 計算測試 ─────────────────────────────────────────────


class TestComputeMtbf:
    """_compute_mtbf 函式的測試。"""

    def test_mtbf_calculation(self) -> None:
        """確認 MTBF 計算。"""
        events = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=5, freq="24h"),
                "severity": [3, 3, 3, 3, 3],
            }
        )
        mtbf = _compute_mtbf(events)
        assert mtbf["mtbf_hours"] == 24.0
        assert mtbf["total_failures"] == 5

    def test_mtbf_single_event(self) -> None:
        """單一事件的 MTBF 應為 None。"""
        events = pd.DataFrame(
            {
                "timestamp": [pd.Timestamp("2024-01-01")],
                "severity": [3],
            }
        )
        mtbf = _compute_mtbf(events)
        assert mtbf["mtbf_hours"] is None

    def test_mtbf_filters_high_severity(self) -> None:
        """確認 MTBF 優先計算高嚴重度事件。"""
        events = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=10, freq="6h"),
                "severity": [1, 3, 1, 1, 3, 1, 1, 3, 1, 1],
            }
        )
        mtbf = _compute_mtbf(events)
        # 高嚴重度事件在 index 1, 4, 7 → 間隔 18h
        assert mtbf["total_failures"] == 3
        assert mtbf["mtbf_hours"] == 18.0
