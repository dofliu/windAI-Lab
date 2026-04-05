"""模型對比實驗框架測試。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.skills.base import SkillInput, SkillStatus


def _make_scada_df(n: int = 300, seed: int = 42) -> pd.DataFrame:
    """產生模擬 SCADA 資料。"""
    rng = np.random.RandomState(seed)
    wind_speed = rng.uniform(3, 25, n)
    power = np.where(
        wind_speed < 3,
        0,
        np.where(wind_speed > 25, 0, wind_speed**3 * 0.13 + rng.normal(0, 10, n)),
    )
    gear_temp = 40 + power / 100 + rng.normal(0, 2, n)
    rotor_speed = wind_speed * 0.8 + rng.normal(0, 0.5, n)

    df = pd.DataFrame(
        {
            "Wind speed (m/s)_Mean": wind_speed,
            "Active power (kW)_Mean": power,
            "Gear oil temp (°C)_Mean": gear_temp,
            "Rotor speed (rpm)_Mean": rotor_speed,
        }
    )
    df.index = pd.date_range("2024-01-01", periods=n, freq="10min")
    return df


class TestModelBenchmark:
    """ModelBenchmark 核心測試。"""

    def test_benchmark_lstm_only(self) -> None:
        """只跑 LSTM 的基本流程。"""
        from src.models.benchmark.model_benchmark import ModelBenchmark

        df = _make_scada_df(200)
        benchmark = ModelBenchmark(
            df=df,
            target="power",
            test_ratio=0.2,
            sequence_length=24,
            forecast_horizon=6,
        )
        report = benchmark.run_all(
            epochs=3,
            include_nbm=False,
            include_lstm=True,
            include_patch_tst=False,
        )

        assert len(report.results) == 1
        assert report.results[0].model_name == "LSTM"
        assert report.results[0].model_type in ("lstm", "ridge_ar")
        assert report.comparison_table is not None
        assert len(report.comparison_table) == 1
        assert report.best_model == "LSTM"

    def test_benchmark_patch_tst_only(self) -> None:
        """只跑 PatchTST。"""
        from src.models.benchmark.model_benchmark import ModelBenchmark

        df = _make_scada_df(200)
        benchmark = ModelBenchmark(
            df=df,
            target="power",
            test_ratio=0.2,
            sequence_length=24,
            forecast_horizon=6,
        )
        report = benchmark.run_all(
            epochs=3,
            include_nbm=False,
            include_lstm=False,
            include_patch_tst=True,
            patch_length=6,
            stride=6,
        )

        assert len(report.results) == 1
        assert report.results[0].model_name == "PatchTST"

    def test_benchmark_lstm_vs_patch_tst(self) -> None:
        """LSTM vs PatchTST 對比。"""
        from src.models.benchmark.model_benchmark import ModelBenchmark

        df = _make_scada_df(200)
        benchmark = ModelBenchmark(
            df=df,
            target="power",
            test_ratio=0.2,
            sequence_length=24,
            forecast_horizon=6,
        )
        report = benchmark.run_all(
            epochs=3,
            include_nbm=False,
            include_lstm=True,
            include_patch_tst=True,
            patch_length=6,
            stride=6,
        )

        assert len(report.results) == 2
        model_names = {r.model_name for r in report.results}
        assert "LSTM" in model_names
        assert "PatchTST" in model_names

        # 表格應按 R² 排序
        table = report.comparison_table
        assert len(table) == 2
        assert table.iloc[0]["R²"] >= table.iloc[1]["R²"]

        # 最佳模型應該是 R² 最高的
        assert report.best_model == table.iloc[0]["Model"]

    def test_latex_output(self) -> None:
        """驗證 LaTeX 表格輸出。"""
        from src.models.benchmark.model_benchmark import ModelBenchmark

        df = _make_scada_df(200)
        benchmark = ModelBenchmark(df=df, target="power", sequence_length=24, forecast_horizon=6)
        report = benchmark.run_all(
            epochs=3, include_nbm=False, include_lstm=True, include_patch_tst=False
        )

        assert "\\begin{table}" in report.latex_table
        assert "\\end{table}" in report.latex_table
        assert "LSTM" in report.latex_table
        assert "R$^2$" in report.latex_table

    def test_dataset_info(self) -> None:
        """驗證資料集資訊。"""
        from src.models.benchmark.model_benchmark import ModelBenchmark

        df = _make_scada_df(200)
        benchmark = ModelBenchmark(
            df=df,
            target="power",
            test_ratio=0.2,
            sequence_length=24,
            forecast_horizon=6,
        )
        report = benchmark.run_all(
            epochs=3, include_nbm=False, include_lstm=True, include_patch_tst=False
        )

        info = report.dataset_info
        assert info["target"] == "power"
        assert info["total_samples"] == 200
        assert info["test_ratio"] == 0.2
        assert info["sequence_length"] == 24
        assert info["forecast_horizon"] == 6

    def test_missing_target_raises(self) -> None:
        """目標欄位不存在應拋出 ValueError。"""
        from src.models.benchmark.model_benchmark import ModelBenchmark

        df = pd.DataFrame({"unrelated": np.random.uniform(0, 1, 100)})

        with pytest.raises(ValueError, match="未找到"):
            ModelBenchmark(df=df, target="power")

    def test_wind_speed_target(self) -> None:
        """驗證可切換目標為 wind_speed。"""
        from src.models.benchmark.model_benchmark import ModelBenchmark

        df = _make_scada_df(200)
        benchmark = ModelBenchmark(
            df=df, target="wind_speed", sequence_length=24, forecast_horizon=6
        )
        report = benchmark.run_all(
            epochs=3, include_nbm=False, include_lstm=True, include_patch_tst=False
        )

        assert report.dataset_info["target"] == "wind_speed"
        assert report.results[0].rmse >= 0


class TestBenchmarkResult:
    """BenchmarkResult 資料類測試。"""

    def test_default_values(self) -> None:
        from src.models.benchmark.model_benchmark import BenchmarkResult

        r = BenchmarkResult()
        assert r.model_name == ""
        assert r.rmse == 0.0
        assert r.r2 == 0.0
        assert r.extra == {}

    def test_with_values(self) -> None:
        from src.models.benchmark.model_benchmark import BenchmarkResult

        r = BenchmarkResult(
            model_name="LSTM",
            model_type="lstm",
            rmse=1.23,
            mae=0.98,
            r2=0.95,
            train_time_sec=5.0,
        )
        assert r.model_name == "LSTM"
        assert r.r2 == 0.95


class TestComputeMetrics:
    """_compute_metrics 輔助函式測試。"""

    def test_perfect_prediction(self) -> None:
        from src.models.benchmark.model_benchmark import _compute_metrics

        y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        rmse, mae, r2 = _compute_metrics(y, y)
        assert rmse == 0.0
        assert mae == 0.0
        assert r2 == 1.0

    def test_known_values(self) -> None:
        from src.models.benchmark.model_benchmark import _compute_metrics

        y_true = np.array([1.0, 2.0, 3.0])
        y_pred = np.array([1.1, 2.1, 2.9])
        rmse, mae, r2 = _compute_metrics(y_true, y_pred)
        assert rmse > 0
        assert mae > 0
        assert r2 > 0


class TestModelBenchmarkSkill:
    """ModelBenchmarkSkill 技能測試。"""

    def test_import_and_metadata(self) -> None:
        from src.skills.ml.model_benchmark import ModelBenchmarkSkill

        skill = ModelBenchmarkSkill()
        assert skill.skill_id == "model_benchmark"
        assert skill.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_no_input_returns_error(self) -> None:
        from src.skills.ml.model_benchmark import ModelBenchmarkSkill

        skill = ModelBenchmarkSkill()
        inp = SkillInput(parameters={})
        result = await skill.execute(inp)
        assert result.status == SkillStatus.ERROR

    @pytest.mark.asyncio
    async def test_with_valid_data(self) -> None:
        """完整技能流程測試（LSTM only 避免超時）。"""
        from src.skills.ml.model_benchmark import ModelBenchmarkSkill

        df = _make_scada_df(200)
        skill = ModelBenchmarkSkill()
        inp = SkillInput(
            parameters={
                "target": "power",
                "epochs": 3,
                "include_nbm": False,
                "include_lstm": True,
                "include_patch_tst": False,
                "sequence_length": 24,
                "forecast_horizon": 6,
                "experiment_name": "test_benchmark",
            },
            dataframe=df,
        )

        progress_calls: list[tuple[float, str]] = []

        async def track_progress(p: float, msg: str) -> None:
            progress_calls.append((p, msg))

        result = await skill.execute(inp, progress_cb=track_progress)

        assert result.status == SkillStatus.SUCCESS
        assert "results" in result.data
        assert "best_model" in result.data
        assert "latex_table" in result.data
        assert "comparison_table" in result.data
        assert len(result.data["results"]) == 1
        assert len(progress_calls) >= 4
