"""AutoExperimentSkill 的單元測試。

測試實驗規劃、單次執行、結果比較、記錄格式等。
使用合成 SCADA 資料（無需外部檔案）。
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.skills.ml.auto_experiment import (
    ExperimentReport,
    TrialResult,
    _build_report_data,
    _find_best,
    _log_trial,
    _plan_grid_search,
    _plan_model_comparison,
    _run_single_trial,
)

# ── 合成資料 ──────────────────────────────────────────────────


def _make_scada_df(n: int = 2000, seed: int = 42) -> pd.DataFrame:
    """產生含特徵工程欄位的合成 SCADA 資料。"""
    rng = np.random.default_rng(seed)
    timestamps = pd.date_range("2024-01-01", periods=n, freq="10min")

    wind_speed = rng.weibull(2.0, n) * 7 + 1
    wind_speed = np.clip(wind_speed, 0, 30)

    rated_power = 2050
    cut_in = 3.0
    rated_wind = 12.5
    power = np.where(
        wind_speed < cut_in,
        0,
        np.where(
            wind_speed < rated_wind,
            rated_power * ((wind_speed - cut_in) / (rated_wind - cut_in)) ** 3,
            rated_power,
        ),
    )
    power = power + rng.normal(0, 30, n)
    power = np.clip(power, -10, rated_power * 1.1)

    ambient_temp = 10 + 5 * np.sin(np.linspace(0, 4 * np.pi, n)) + rng.normal(0, 2, n)
    gear_oil_temp = 45 + power / rated_power * 20 + rng.normal(0, 2, n)
    gen_front = 50 + power / rated_power * 15 + rng.normal(0, 1.5, n)
    rotor_speed = np.where(wind_speed < cut_in, 0, 8 + wind_speed * 0.5 + rng.normal(0, 0.3, n))
    blade_pitch = np.where(wind_speed < rated_wind, 0, (wind_speed - rated_wind) * 2)

    df = pd.DataFrame(
        {
            "Wind Speed_Mean": wind_speed,
            "Active Power_Mean": power,
            "Ambient Temperature_Mean": ambient_temp,
            "Gear Oil Temperature_Mean": gear_oil_temp,
            "Generator Bearing Front Temperature_Mean": gen_front,
            "Rotor Speed_Mean": rotor_speed,
            "Blade Pitch Angle_Mean": blade_pitch,
        },
        index=timestamps,
    )
    df.index.name = "Timestamp"

    # 加入特徵工程欄位（模擬 domain_feature_extraction 的輸出）
    df["capacity_factor"] = power / rated_power
    df["normalized_power"] = np.clip(power / rated_power, 0, 1.2)
    df["gear_oil_temp_delta"] = gear_oil_temp - ambient_temp
    df["gear_oil_temp_rolling_std"] = (
        pd.Series(gear_oil_temp, index=timestamps).rolling(144, min_periods=72).std()
    )

    return df


# ── 實驗規劃測試 ──────────────────────────────────────────────


class TestPlanGridSearch:
    """_plan_grid_search 函式的測試。"""

    def test_generates_all_combinations(self) -> None:
        """確認產生完整的網格組合。"""
        space = {"a": [1, 2], "b": [10, 20]}
        configs = _plan_grid_search("test_model", space)
        assert len(configs) == 4  # 2 × 2

    def test_limits_trials(self) -> None:
        """確認 max_trials 限制試驗數。"""
        space = {"a": [1, 2, 3], "b": [10, 20, 30]}
        configs = _plan_grid_search("test_model", space, max_trials=3)
        assert len(configs) == 3

    def test_empty_space_returns_empty(self) -> None:
        """空搜尋空間回傳空列表。"""
        configs = _plan_grid_search("test_model", {})
        assert configs == []

    def test_config_structure(self) -> None:
        """確認每個 config 包含 model_type 和 hyperparameters。"""
        space = {"lr": [0.1]}
        configs = _plan_grid_search("nbm", space)
        assert len(configs) == 1
        assert configs[0]["model_type"] == "nbm"
        assert configs[0]["hyperparameters"] == {"lr": 0.1}


class TestPlanModelComparison:
    """_plan_model_comparison 函式的測試。"""

    def test_returns_multiple_configs(self) -> None:
        """確認回傳多個模型配置。"""
        configs = _plan_model_comparison()
        assert len(configs) >= 2

    def test_includes_different_model_types(self) -> None:
        """確認包含不同的模型類型。"""
        configs = _plan_model_comparison()
        types = {c["model_type"] for c in configs}
        assert len(types) >= 2


# ── 單次實驗執行測試 ──────────────────────────────────────────


class TestRunSingleTrial:
    """_run_single_trial 函式的測試。"""

    def test_nbm_returns_r2(self) -> None:
        """確認 NBM 實驗回傳 R² 指標。"""
        df = _make_scada_df()
        metrics = _run_single_trial(df, "power_curve_nbm", {"n_estimators": 50, "max_depth": 3})
        assert "r2" in metrics
        assert metrics["r2"] > 0

    def test_fault_classifier_returns_f1(self) -> None:
        """確認故障分類實驗回傳 F1 指標。"""
        df = _make_scada_df()
        metrics = _run_single_trial(df, "fault_classifier", {"n_estimators": 50, "max_depth": 4})
        assert "f1_macro" in metrics

    def test_unsupported_model_raises(self) -> None:
        """不支援的模型類型應拋出 ValueError。"""
        df = _make_scada_df()
        with pytest.raises(ValueError, match="不支援"):
            _run_single_trial(df, "unknown_model", {})


# ── 結果比較測試 ──────────────────────────────────────────────


class TestFindBest:
    """_find_best 函式的測試。"""

    def test_finds_highest_metric(self) -> None:
        """確認找出指標最高的實驗。"""
        trials = [
            TrialResult(1, "a", {}, {"r2": 0.8}, 1.0),
            TrialResult(2, "b", {}, {"r2": 0.95}, 1.0),
            TrialResult(3, "c", {}, {"r2": 0.9}, 1.0),
        ]
        best = _find_best(trials, "r2")
        assert best is not None
        assert best.trial_id == 2

    def test_skips_failed_trials(self) -> None:
        """確認跳過失敗的實驗。"""
        trials = [
            TrialResult(1, "a", {}, {"r2": 0.8}, 1.0),
            TrialResult(2, "b", {}, {}, 1.0, error="failed"),
        ]
        best = _find_best(trials, "r2")
        assert best is not None
        assert best.trial_id == 1

    def test_returns_none_if_all_failed(self) -> None:
        """全部失敗時回傳 None。"""
        trials = [
            TrialResult(1, "a", {}, {}, 1.0, error="e1"),
            TrialResult(2, "b", {}, {}, 1.0, error="e2"),
        ]
        best = _find_best(trials, "r2")
        assert best is None

    def test_empty_list_returns_none(self) -> None:
        """空列表回傳 None。"""
        assert _find_best([], "r2") is None


# ── 記錄格式測試 ──────────────────────────────────────────────


class TestLogTrial:
    """_log_trial 函式的測試。"""

    def test_creates_jsonl_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """確認建立 JSONL 記錄檔。"""
        monkeypatch.setattr(
            "src.skills.ml.auto_experiment._EXPERIMENT_LOG_DIR", tmp_path
        )
        trial = TrialResult(1, "nbm", {"lr": 0.1}, {"r2": 0.95}, 2.5)
        _log_trial("test_exp", trial)

        log_file = tmp_path / "test_exp.jsonl"
        assert log_file.exists()

        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1

        record = json.loads(lines[0])
        assert record["experiment_name"] == "test_exp"
        assert record["trial_id"] == 1
        assert record["metrics"]["r2"] == 0.95

    def test_appends_multiple_trials(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """確認多次實驗追加寫入。"""
        monkeypatch.setattr(
            "src.skills.ml.auto_experiment._EXPERIMENT_LOG_DIR", tmp_path
        )
        _log_trial("exp2", TrialResult(1, "a", {}, {"r2": 0.8}, 1.0))
        _log_trial("exp2", TrialResult(2, "b", {}, {"r2": 0.9}, 1.0))

        lines = (tmp_path / "exp2.jsonl").read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2


# ── 報告產出測試 ──────────────────────────────────────────────


class TestBuildReportData:
    """_build_report_data 函式的測試。"""

    def test_contains_leaderboard(self) -> None:
        """確認報告包含排行榜。"""
        best = TrialResult(2, "nbm", {"lr": 0.1}, {"r2": 0.95}, 2.5)
        report = ExperimentReport(
            experiment_name="test",
            experiment_type="power_curve_nbm",
            total_trials=3,
            successful_trials=3,
            failed_trials=0,
            best_trial=best,
            primary_metric="r2",
            all_trials=[
                TrialResult(1, "nbm", {}, {"r2": 0.8}, 1.0),
                best,
                TrialResult(3, "nbm", {}, {"r2": 0.9}, 1.0),
            ],
        )
        data = _build_report_data(report)
        assert "leaderboard" in data
        assert len(data["leaderboard"]) == 3
        # 排行榜應按 r2 降序
        assert data["leaderboard"][0]["metrics"]["r2"] == 0.95

    def test_best_trial_in_report(self) -> None:
        """確認最佳實驗包含在報告中。"""
        best = TrialResult(1, "nbm", {"n": 100}, {"r2": 0.99}, 1.0)
        report = ExperimentReport(
            experiment_name="t",
            experiment_type="nbm",
            total_trials=1,
            successful_trials=1,
            failed_trials=0,
            best_trial=best,
            primary_metric="r2",
            all_trials=[best],
        )
        data = _build_report_data(report)
        assert data["best_trial"]["metrics"]["r2"] == 0.99
