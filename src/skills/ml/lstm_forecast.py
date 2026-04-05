"""LSTM 時序預測技能 — 包裝 LSTMForecaster 為可重用技能。

支援：
- 風速/功率/溫度時序預測
- 自動降級至 Ridge AR（PyTorch 不可用時）
- MLflow + JSONL 實驗記錄
- 模型持久化（儲存/載入）
- R² 指標輸出（跨模型對比用）
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.skills.base import BaseSkill, ProgressCallback, SkillInput, SkillOutput, SkillStatus

_EXPERIMENT_LOG_DIR = Path(__file__).resolve().parents[3] / "data" / "experiments"
_MODEL_SAVE_DIR = Path(__file__).resolve().parents[3] / "models" / "lstm"


class LSTMForecastSkill(BaseSkill):
    """LSTM 風速/功率短期時序預測。"""

    skill_id = "lstm_forecast"
    display_name = "LSTM 時序預測"
    description = "使用 LSTM 進行風速或功率短期預測，支援降級至 Ridge AR，含實驗追蹤與模型持久化"
    version = "2.0.0"

    async def execute(
        self,
        inp: SkillInput,
        progress_cb: ProgressCallback = None,
    ) -> SkillOutput:
        """執行 LSTM 時序預測。

        Parameters（透過 inp.parameters）:
            turbine_id: 風機 ID
            target: 預測目標（"wind_speed" / "power" / "temperature"），預設 "wind_speed"
            sequence_length: 輸入序列長度（預設 48）
            forecast_horizon: 預測步數（預設 12）
            epochs: 訓練 epoch 數（預設 50）
            save_model: 是否儲存模型（預設 True）
            experiment_name: 實驗名稱（預設 "lstm_forecast"）
        """
        df = inp.dataframe if inp.dataframe is not None else inp.data
        if df is None:
            return SkillOutput(status=SkillStatus.ERROR, errors=["未收到輸入資料"])

        import pandas as pd

        if not isinstance(df, pd.DataFrame) or df.empty:
            return SkillOutput(status=SkillStatus.ERROR, errors=["輸入資料為空"])

        # ── 參數解析 ──
        turbine_id = inp.parameters.get("turbine_id", "未知")
        target = inp.parameters.get("target", "wind_speed")
        seq_len = inp.parameters.get("sequence_length", 48)
        horizon = inp.parameters.get("forecast_horizon", 12)
        epochs = inp.parameters.get("epochs", 50)
        save_model = inp.parameters.get("save_model", True)
        experiment_name = inp.parameters.get("experiment_name", "lstm_forecast")

        if progress_cb:
            await progress_cb(0.05, f"準備 {target} 時序資料...")

        loop = asyncio.get_event_loop()

        try:
            from src.models.degradation.lstm_forecaster import LSTMForecaster

            # ── 1. 找目標欄位 ──
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
                await progress_cb(0.10, f"資料就緒：{len(series)} 筆，目標欄位 {target_col}")

            # ── 2. 初始化模型 ──
            if progress_cb:
                await progress_cb(0.15, "初始化 LSTMForecaster...")

            forecaster = LSTMForecaster(
                sequence_length=seq_len,
                forecast_horizon=horizon,
            )

            # ── 3. 訓練與預測 ──
            if progress_cb:
                await progress_cb(0.20, f"開始訓練（{epochs} epochs）...")

            result = await loop.run_in_executor(
                None,
                lambda: forecaster.fit_and_predict(series, epochs=epochs),
            )

            if progress_cb:
                await progress_cb(0.75, f"訓練完成 | {result.model_type} | RMSE={result.rmse:.3f}")

            # ── 4. 模型持久化 ──
            model_path: str | None = None
            if save_model and forecaster._model is not None:
                if progress_cb:
                    await progress_cb(0.80, "儲存模型...")
                timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
                model_dir = _MODEL_SAVE_DIR / f"{turbine_id}_{target}_{timestamp}"
                await loop.run_in_executor(None, lambda: forecaster.save(model_dir))
                model_path = str(model_dir)

            # ── 5. 實驗記錄 ──
            if progress_cb:
                await progress_cb(0.88, "記錄實驗結果...")

            hyperparams = {
                "sequence_length": seq_len,
                "forecast_horizon": horizon,
                "epochs": epochs,
                "hidden_dim": forecaster._hidden_dim,
                "num_layers": forecaster._num_layers,
                "dropout": forecaster._dropout,
            }
            metrics = {
                "rmse": result.rmse,
                "mae": result.mae,
                "r2": result.r2,
                "train_loss": result.train_loss,
                "val_loss": result.val_loss,
            }
            await loop.run_in_executor(
                None,
                lambda: _log_experiment(
                    experiment_name=experiment_name,
                    model_type=result.model_type,
                    turbine_id=turbine_id,
                    target=target,
                    hyperparams=hyperparams,
                    metrics=metrics,
                    data_points=len(series),
                    model_path=model_path,
                ),
            )

            if progress_cb:
                await progress_cb(1.0, "預測完成，結果已記錄")

            # ── 組裝輸出 ──
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
                    "r2": result.r2,
                    "sequence_length": result.sequence_length,
                    "epochs_trained": result.epochs_trained,
                    "data_points_used": len(series),
                    "model_path": model_path,
                    "experiment_name": experiment_name,
                },
                summary=(
                    f"{target} LSTM 預測 | "
                    f"model={result.model_type} | "
                    f"RMSE={result.rmse:.3f} | MAE={result.mae:.3f} | R²={result.r2:.4f} | "
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
        "temperature": ["gear oil temp", "bearing temp", "generator bearing temp"],
    }
    keywords = target_keywords.get(target, [target])
    for kw in keywords:
        for col in df.columns:
            if kw.lower() in col.lower():
                return col
    return None


def _log_experiment(
    experiment_name: str,
    model_type: str,
    turbine_id: str,
    target: str,
    hyperparams: dict[str, Any],
    metrics: dict[str, float],
    data_points: int,
    model_path: str | None,
) -> None:
    """記錄實驗至 JSONL + 可選 MLflow。"""
    # MLflow（可選）
    mlflow_logged = False
    try:
        import mlflow

        mlflow.set_experiment(experiment_name)
        with mlflow.start_run(
            run_name=f"{model_type}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
        ):
            mlflow.log_params(hyperparams)
            mlflow.log_metrics(metrics)
            mlflow.set_tag("model_type", model_type)
            mlflow.set_tag("turbine_id", turbine_id)
            mlflow.set_tag("target", target)
            if model_path:
                mlflow.set_tag("model_path", model_path)
        mlflow_logged = True
    except Exception:
        pass

    # JSONL 本地記錄（始終執行）
    _EXPERIMENT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "experiment_name": experiment_name,
        "model_type": model_type,
        "turbine_id": turbine_id,
        "target": target,
        "hyperparameters": hyperparams,
        "metrics": metrics,
        "data_points": data_points,
        "model_path": model_path,
        "mlflow_logged": mlflow_logged,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    log_file = _EXPERIMENT_LOG_DIR / f"{experiment_name}.jsonl"
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
