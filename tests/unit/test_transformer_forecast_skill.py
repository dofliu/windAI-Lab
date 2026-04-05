"""PatchTST 時序預測技能與模型測試。"""

from __future__ import annotations

import pytest

from src.skills.base import SkillInput, SkillStatus


class TestTransformerForecastSkill:
    """TransformerForecastSkill 單元測試。"""

    def test_import_and_metadata(self) -> None:
        from src.skills.ml.transformer_forecast import TransformerForecastSkill

        skill = TransformerForecastSkill()
        assert skill.skill_id == "transformer_forecast"
        assert skill.display_name == "PatchTST 時序預測"
        assert skill.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_no_input_returns_error(self) -> None:
        from src.skills.ml.transformer_forecast import TransformerForecastSkill

        skill = TransformerForecastSkill()
        inp = SkillInput(parameters={})
        result = await skill.execute(inp)
        assert result.status == SkillStatus.ERROR
        assert any("未收到" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_empty_dataframe_returns_error(self) -> None:
        import pandas as pd

        from src.skills.ml.transformer_forecast import TransformerForecastSkill

        skill = TransformerForecastSkill()
        inp = SkillInput(parameters={}, dataframe=pd.DataFrame())
        result = await skill.execute(inp)
        assert result.status == SkillStatus.ERROR

    @pytest.mark.asyncio
    async def test_insufficient_data_returns_error(self) -> None:
        import numpy as np
        import pandas as pd

        from src.skills.ml.transformer_forecast import TransformerForecastSkill

        df = pd.DataFrame({"Wind speed (m/s)_Mean": np.random.uniform(3, 15, 20)})
        skill = TransformerForecastSkill()
        inp = SkillInput(
            parameters={"target": "wind_speed", "sequence_length": 48, "forecast_horizon": 12},
            dataframe=df,
        )
        result = await skill.execute(inp)
        assert result.status == SkillStatus.ERROR
        assert any("資料量不足" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_missing_target_column_returns_error(self) -> None:
        import numpy as np
        import pandas as pd

        from src.skills.ml.transformer_forecast import TransformerForecastSkill

        df = pd.DataFrame({"unrelated_col": np.random.uniform(0, 1, 200)})
        skill = TransformerForecastSkill()
        inp = SkillInput(
            parameters={"target": "wind_speed"},
            dataframe=df,
        )
        result = await skill.execute(inp)
        assert result.status == SkillStatus.ERROR
        assert any("未找到" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_with_valid_data(self) -> None:
        """以模擬風速資料測試完整 PatchTST pipeline。"""
        import numpy as np
        import pandas as pd

        from src.skills.ml.transformer_forecast import TransformerForecastSkill

        np.random.seed(42)
        n = 200
        t = np.arange(n)
        wind_speed = 8.0 + 3.0 * np.sin(2 * np.pi * t / 144) + np.random.normal(0, 0.5, n)

        df = pd.DataFrame({"Wind speed (m/s)_Mean": wind_speed})
        df.index = pd.date_range("2024-01-01", periods=n, freq="10min")

        skill = TransformerForecastSkill()
        inp = SkillInput(
            parameters={
                "turbine_id": "TEST-01",
                "target": "wind_speed",
                "sequence_length": 24,
                "forecast_horizon": 6,
                "patch_length": 6,
                "stride": 6,
                "d_model": 32,
                "n_heads": 2,
                "n_layers": 1,
                "epochs": 5,
                "save_model": False,
                "experiment_name": "test_patchtst_run",
            },
            dataframe=df,
        )

        progress_calls: list[tuple[float, str]] = []

        async def track_progress(p: float, msg: str) -> None:
            progress_calls.append((p, msg))

        result = await skill.execute(inp, progress_cb=track_progress)

        assert result.status == SkillStatus.SUCCESS
        assert result.data["turbine_id"] == "TEST-01"
        assert result.data["target"] == "wind_speed"
        assert result.data["model_type"] in ("patch_tst", "ridge_ar")
        assert len(result.data["predictions"]) == 6
        assert result.data["rmse"] >= 0
        assert result.data["mae"] >= 0
        assert "r2" in result.data
        assert "patch_length" in result.data
        assert "num_patches" in result.data
        assert "epochs_trained" in result.data
        assert "experiment_name" in result.data
        assert "R²=" in result.summary
        assert "PatchTST" in result.summary

        # 驗證進度回報有多個 checkpoint
        assert len(progress_calls) >= 5
        assert progress_calls[-1][0] == 1.0

    @pytest.mark.asyncio
    async def test_power_target(self) -> None:
        """測試功率目標欄位。"""
        import numpy as np
        import pandas as pd

        from src.skills.ml.transformer_forecast import TransformerForecastSkill

        np.random.seed(123)
        n = 150
        power = np.random.uniform(100, 2000, n)

        df = pd.DataFrame({"Active power (kW)_Mean": power})
        skill = TransformerForecastSkill()
        inp = SkillInput(
            parameters={
                "target": "power",
                "sequence_length": 24,
                "forecast_horizon": 6,
                "patch_length": 6,
                "stride": 6,
                "d_model": 32,
                "n_heads": 2,
                "n_layers": 1,
                "epochs": 3,
                "save_model": False,
            },
            dataframe=df,
        )
        result = await skill.execute(inp)
        assert result.status == SkillStatus.SUCCESS
        assert result.data["target"] == "power"


class TestPatchTSTForecasterModel:
    """PatchTSTForecaster 模型層測試。"""

    def test_result_dataclass_fields(self) -> None:
        """驗證 PatchTSTForecastResult 包含所有必要欄位。"""
        from src.models.degradation.patch_tst_forecaster import PatchTSTForecastResult

        result = PatchTSTForecastResult()
        assert hasattr(result, "r2")
        assert hasattr(result, "patch_length")
        assert hasattr(result, "num_patches")
        assert hasattr(result, "epochs_trained")
        assert result.model_type == "patch_tst"

    def test_fit_and_predict_with_synthetic_data(self) -> None:
        """用合成資料測試 fit_and_predict。"""
        import numpy as np

        from src.models.degradation.patch_tst_forecaster import PatchTSTForecaster

        np.random.seed(42)
        series = 10.0 + np.sin(np.linspace(0, 20, 200)) + np.random.normal(0, 0.1, 200)

        forecaster = PatchTSTForecaster(
            sequence_length=24,
            forecast_horizon=6,
            patch_length=6,
            stride=6,
            d_model=32,
            n_heads=2,
            n_layers=1,
        )
        result = forecaster.fit_and_predict(series, epochs=3)

        assert len(result.predictions) == 6
        assert result.rmse >= 0
        assert result.mae >= 0
        assert result.r2 <= 1.0
        assert result.model_type in ("patch_tst", "ridge_ar")
        assert result.sequence_length == 24
        assert result.horizon_steps == 6
        assert result.patch_length == 6

    def test_num_patches_calculation(self) -> None:
        """驗證 patch 數量計算正確。"""
        from src.models.degradation.patch_tst_forecaster import PatchTSTForecaster

        # seq_len=48, patch_len=8, stride=8 → (48-8)//8 + 1 = 6
        f1 = PatchTSTForecaster(sequence_length=48, patch_length=8, stride=8)
        assert f1._num_patches == 6

        # seq_len=24, patch_len=6, stride=6 → (24-6)//6 + 1 = 4
        f2 = PatchTSTForecaster(sequence_length=24, patch_length=6, stride=6)
        assert f2._num_patches == 4

        # seq_len=48, patch_len=8, stride=4 → (48-8)//4 + 1 = 11 (重疊 patches)
        f3 = PatchTSTForecaster(sequence_length=48, patch_length=8, stride=4)
        assert f3._num_patches == 11

    def test_save_and_load(self, tmp_path: str) -> None:
        """測試模型儲存與載入。"""
        import numpy as np

        from src.models.degradation.patch_tst_forecaster import PatchTSTForecaster

        np.random.seed(42)
        series = np.random.uniform(5, 15, 200).astype(np.float32)

        forecaster = PatchTSTForecaster(
            sequence_length=24,
            forecast_horizon=6,
            patch_length=6,
            stride=6,
            d_model=32,
            n_heads=2,
            n_layers=1,
        )
        forecaster.fit_and_predict(series, epochs=3)

        save_dir = tmp_path / "test_patch_tst"
        forecaster.save(save_dir)

        loaded = PatchTSTForecaster.load(save_dir)
        assert loaded._seq_len == 24
        assert loaded._horizon == 6
        assert loaded._patch_len == 6
        assert loaded._model is not None
        assert loaded._scaler is not None

    def test_insufficient_data(self) -> None:
        """資料不足時應回傳 insufficient_data 類型。"""
        import numpy as np

        from src.models.degradation.patch_tst_forecaster import PatchTSTForecaster

        forecaster = PatchTSTForecaster(sequence_length=48, forecast_horizon=12)
        result = forecaster.fit_and_predict(np.array([1.0, 2.0, 3.0]))
        assert result.model_type == "insufficient_data"
        assert len(result.predictions) == 0


class TestTransformerFindTargetCol:
    """_find_target_col 輔助函式測試。"""

    def test_wind_speed_match(self) -> None:
        import pandas as pd

        from src.skills.ml.transformer_forecast import _find_target_col

        df = pd.DataFrame({"Wind speed (m/s)_Mean": [1], "Other": [2]})
        assert _find_target_col(df, "wind_speed") == "Wind speed (m/s)_Mean"

    def test_power_match(self) -> None:
        import pandas as pd

        from src.skills.ml.transformer_forecast import _find_target_col

        df = pd.DataFrame({"Active power (kW)_Mean": [1]})
        assert _find_target_col(df, "power") == "Active power (kW)_Mean"

    def test_no_match(self) -> None:
        import pandas as pd

        from src.skills.ml.transformer_forecast import _find_target_col

        df = pd.DataFrame({"unrelated": [1]})
        assert _find_target_col(df, "wind_speed") is None
