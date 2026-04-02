"""LSTM 時序預測技能 — 包裝 LSTMForecaster 為可重用技能。"""

from __future__ import annotations

import asyncio
from typing import Any

from src.skills.base import BaseSkill, ProgressCallback, SkillInput, SkillOutput, SkillStatus


class LSTMForecastSkill(BaseSkill):
    """LSTM 風速/功率短期時序預測。"""

    skill_id = "lstm_forecast"
    display_name = "LSTM 時序預測"
    description = "使用 LSTM 進行風速或功率短期預測，支援降級至 Ridge AR"
    version = "1.0.0"

    async def execute(
        self,
        inp: SkillInput,
        progress_cb: ProgressCallback = None,
    ) -> SkillOutput:
        """執行 LSTM 時序預測。

        Parameters（透過 inp.parameters）:
            turbine_id: 風機 ID
            target: 預測目標（"wind_speed" / "power"），預設 "wind_speed"
            sequence_length: 輸入序列長度（預設 48）
            forecast_horizon: 預測步數（預設 12）
            epochs: 訓練 epoch 數（預設 50）
        """
        df = inp.dataframe if inp.dataframe is not None else inp.data
        if df is None:
            return SkillOutput(status=SkillStatus.ERROR, errors=["未收到輸入資料"])

        import pandas as pd

        if not isinstance(df, pd.DataFrame) or df.empty:
            return SkillOutput(status=SkillStatus.ERROR, errors=["輸入資料為空"])

        turbine_id = inp.parameters.get("turbine_id", "未知")
        target = inp.parameters.get("target", "wind_speed")
        seq_len = inp.parameters.get("sequence_length", 48)
        horizon = inp.parameters.get("forecast_horizon", 12)
        epochs = inp.parameters.get("epochs", 50)

        if progress_cb:
            await progress_cb(0.05, f"準備 {target} 時序資料...")

        loop = asyncio.get_event_loop()

        try:
            from src.models.degradation.lstm_forecaster import LSTMForecaster

            # 找目標欄位
            target_col = _find_target_col(df, target)
            if target_col is None:
                return SkillOutput(
                    status=SkillStatus.ERROR,
                    errors=[f"未找到 {target} 相關欄位"],
                )

            series = df[target_col].dropna().values

            if len(series) < seq_len + horizon + 10:
                return SkillOutput(
                    status=SkillStatus.ERROR,
                    errors=[f"資料量不足（需 >= {seq_len + horizon + 10}，實際 {len(series)}）"],
                )

            if progress_cb:
                await progress_cb(0.2, f"訓練 LSTM 模型（{epochs} epochs）...")

            forecaster = LSTMForecaster(
                sequence_length=seq_len,
                forecast_horizon=horizon,
            )

            result = await loop.run_in_executor(
                None,
                lambda: forecaster.fit_and_predict(series, epochs=epochs),
            )

            if progress_cb:
                await progress_cb(1.0, "預測完成")

            # 預測步數對應的時間（假設 10 分鐘採樣）
            interval_min = inp.parameters.get("sampling_interval", 600) // 60
            forecast_minutes = horizon * interval_min

            return SkillOutput(
                status=SkillStatus.SUCCESS,
                data={
                    "turbine_id": turbine_id,
                    "target": target,
                    "target_column": target_col,
                    "model_type": result.model_type,
                    "predictions": result.predictions,
                    "horizon_steps": result.horizon_steps,
                    "forecast_minutes": forecast_minutes,
                    "train_loss": result.train_loss,
                    "val_loss": result.val_loss,
                    "rmse": result.rmse,
                    "mae": result.mae,
                    "sequence_length": result.sequence_length,
                    "data_points_used": len(series),
                },
                summary=(
                    f"{target} LSTM 預測 | "
                    f"model={result.model_type} | "
                    f"RMSE={result.rmse:.2f} | MAE={result.mae:.2f} | "
                    f"預測 {forecast_minutes} 分鐘"
                ),
                dataframe=df,
            )

        except Exception as e:
            return SkillOutput(
                status=SkillStatus.ERROR,
                errors=[f"LSTM 預測失敗：{e}"],
            )


def _find_target_col(df: Any, target: str) -> str | None:
    """搜尋目標欄位。"""
    target_keywords: dict[str, list[str]] = {
        "wind_speed": ["wind speed", "windspeed", "ws"],
        "power": ["power", "active power"],
        "temperature": ["gear oil temp", "bearing temp"],
    }
    keywords = target_keywords.get(target, [target])
    for kw in keywords:
        for col in df.columns:
            if kw.lower() in col.lower():
                return col
    return None
