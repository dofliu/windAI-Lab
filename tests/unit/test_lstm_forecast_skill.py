"""LSTM 時序預測技能測試。"""

from __future__ import annotations

import pytest

from src.skills.base import SkillInput, SkillStatus


class TestLSTMForecastSkill:
    """LSTMForecastSkill 單元測試。"""

    def test_import_and_metadata(self) -> None:
        from src.skills.ml.lstm_forecast import LSTMForecastSkill

        skill = LSTMForecastSkill()
        assert skill.skill_id == "lstm_forecast"
        assert skill.display_name == "LSTM 時序預測"
        assert skill.version == "2.0.0"

    @pytest.mark.asyncio
    async def test_no_input_returns_error(self) -> None:
        from src.skills.ml.lstm_forecast import LSTMForecastSkill

        skill = LSTMForecastSkill()
        inp = SkillInput(parameters={})
        result = await skill.execute(inp)
        assert result.status == SkillStatus.ERROR
        assert any("未收到" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_empty_dataframe_returns_error(self) -> None:
        import pandas as pd

        from src.skills.ml.lstm_forecast import LSTMForecastSkill

        skill = LSTMForecastSkill()
        inp = SkillInput(parameters={}, dataframe=pd.DataFrame())
        result = await skill.execute(inp)
        assert result.status == SkillStatus.ERROR

    @pytest.mark.asyncio
    async def test_insufficient_data_returns_error(self) -> None:
        import numpy as np
        import pandas as pd

        from src.skills.ml.lstm_forecast import LSTMForecastSkill

        df = pd.DataFrame({"Wind speed (m/s)_Mean": np.random.uniform(3, 15, 20)})
        skill = LSTMForecastSkill()
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

        from src.skills.ml.lstm_forecast import LSTMForecastSkill

        df = pd.DataFrame({"unrelated_col": np.random.uniform(0, 1, 200)})
        skill = LSTMForecastSkill()
        inp = SkillInput(
            parameters={"target": "wind_speed"},
            dataframe=df,
        )
        result = await skill.execute(inp)
        assert result.status == SkillStatus.ERROR
        assert any("未找到" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_with_valid_data(self) -> None:
        """以模擬風速資料測試完整 LSTM pipeline。"""
        import numpy as np
        import pandas as pd

        from src.skills.ml.lstm_forecast import LSTMForecastSkill

        np.random.seed(42)
        n = 200
        t = np.arange(n)
        wind_speed = 8.0 + 3.0 * np.sin(2 * np.pi * t / 144) + np.random.normal(0, 0.5, n)

        df = pd.DataFrame({"Wind speed (m/s)_Mean": wind_speed})
        df.index = pd.date_range("2024-01-01", periods=n, freq="10min")

        skill = LSTMForecastSkill()
        inp = SkillInput(
            parameters={
                "turbine_id": "TEST-01",
                "target": "wind_speed",
                "sequence_length": 24,
                "forecast_horizon": 6,
                "epochs": 5,
                "save_model": False,
                "experiment_name": "test_lstm_run",
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
        assert result.data["model_type"] in ("lstm", "ridge_ar")
        assert len(result.data["predictions"]) == 6
        assert result.data["rmse"] >= 0
        assert result.data["mae"] >= 0
        assert "r2" in result.data
        assert "epochs_trained" in result.data
        assert "experiment_name" in result.data
        assert "R²=" in result.summary

        # 驗證進度回報有多個 checkpoint
        assert len(progress_calls) >= 5
        assert progress_calls[-1][0] == 1.0

    @pytest.mark.asyncio
    async def test_power_target(self) -> None:
        """測試功率目標欄位。"""
        import numpy as np
        import pandas as pd

        from src.skills.ml.lstm_forecast import LSTMForecastSkill

        np.random.seed(123)
        n = 150
        power = np.random.uniform(100, 2000, n)

        df = pd.DataFrame({"Active power (kW)_Mean": power})
        skill = LSTMForecastSkill()
        inp = SkillInput(
            parameters={
                "target": "power",
                "sequence_length": 24,
                "forecast_horizon": 6,
                "epochs": 3,
                "save_model": False,
            },
            dataframe=df,
        )
        result = await skill.execute(inp)
        assert result.status == SkillStatus.SUCCESS
        assert result.data["target"] == "power"


class TestLSTMForecasterModel:
    """LSTMForecaster 模型層測試。"""

    def test_r2_in_result(self) -> None:
        """驗證 LSTMForecastResult 包含 r2 欄位。"""
        from src.models.degradation.lstm_forecaster import LSTMForecastResult

        result = LSTMForecastResult()
        assert hasattr(result, "r2")
        assert result.r2 == 0.0
        assert hasattr(result, "epochs_trained")

    def test_fit_and_predict_with_synthetic_data(self) -> None:
        """用合成資料測試 fit_and_predict。"""
        import numpy as np

        from src.models.degradation.lstm_forecaster import LSTMForecaster

        np.random.seed(42)
        series = 10.0 + np.sin(np.linspace(0, 20, 200)) + np.random.normal(0, 0.1, 200)

        forecaster = LSTMForecaster(sequence_length=24, forecast_horizon=6)
        result = forecaster.fit_and_predict(series, epochs=3)

        assert len(result.predictions) == 6
        assert result.rmse >= 0
        assert result.mae >= 0
        assert result.r2 <= 1.0
        assert result.model_type in ("lstm", "ridge_ar")
        assert result.sequence_length == 24
        assert result.horizon_steps == 6

    def test_save_and_load(self, tmp_path: str) -> None:
        """測試模型儲存與載入。"""
        import numpy as np

        from src.models.degradation.lstm_forecaster import LSTMForecaster

        np.random.seed(42)
        series = np.random.uniform(5, 15, 200).astype(np.float32)

        forecaster = LSTMForecaster(sequence_length=24, forecast_horizon=6)
        original_result = forecaster.fit_and_predict(series, epochs=3)

        # 儲存
        save_dir = tmp_path / "test_model"
        forecaster.save(save_dir)

        # 載入
        loaded = LSTMForecaster.load(save_dir)
        assert loaded._seq_len == 24
        assert loaded._horizon == 6
        assert loaded._model is not None
        assert loaded._scaler is not None

    def test_insufficient_data(self) -> None:
        """資料不足時應回傳 insufficient_data 類型。"""
        import numpy as np

        from src.models.degradation.lstm_forecaster import LSTMForecaster

        forecaster = LSTMForecaster(sequence_length=48, forecast_horizon=12)
        result = forecaster.fit_and_predict(np.array([1.0, 2.0, 3.0]))
        assert result.model_type == "insufficient_data"
        assert len(result.predictions) == 0


class TestFindTargetCol:
    """_find_target_col 輔助函式測試。"""

    def test_wind_speed_match(self) -> None:
        import pandas as pd

        from src.skills.ml.lstm_forecast import _find_target_col

        df = pd.DataFrame({"Wind speed (m/s)_Mean": [1], "Other": [2]})
        assert _find_target_col(df, "wind_speed") == "Wind speed (m/s)_Mean"

    def test_power_match(self) -> None:
        import pandas as pd

        from src.skills.ml.lstm_forecast import _find_target_col

        df = pd.DataFrame({"Active power (kW)_Mean": [1]})
        assert _find_target_col(df, "power") == "Active power (kW)_Mean"

    def test_no_match(self) -> None:
        import pandas as pd

        from src.skills.ml.lstm_forecast import _find_target_col

        df = pd.DataFrame({"unrelated": [1]})
        assert _find_target_col(df, "wind_speed") is None

    def test_temperature_match(self) -> None:
        import pandas as pd

        from src.skills.ml.lstm_forecast import _find_target_col

        df = pd.DataFrame({"Gear oil temp (°C)_Mean": [1]})
        assert _find_target_col(df, "temperature") == "Gear oil temp (°C)_Mean"
