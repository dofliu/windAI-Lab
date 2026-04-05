"""模型對比實驗技能 — 一鍵執行 NBM vs LSTM vs PatchTST 對比評估。

支援：
- 統一時序 train/test 分割
- 多模型並行評估（NBM、LSTM、PatchTST）
- 對比表格 + LaTeX 輸出
- 結果記錄至 JSONL + MLflow
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.skills.base import BaseSkill, ProgressCallback, SkillInput, SkillOutput, SkillStatus

_EXPERIMENT_LOG_DIR = Path(__file__).resolve().parents[3] / "data" / "experiments"


class ModelBenchmarkSkill(BaseSkill):
    """模型對比實驗技能。"""

    skill_id = "model_benchmark"
    display_name = "模型對比實驗"
    description = "一鍵執行 NBM vs LSTM vs PatchTST 對比評估，產出統一指標表格與 LaTeX"
    version = "1.0.0"

    async def execute(
        self,
        inp: SkillInput,
        progress_cb: ProgressCallback = None,
    ) -> SkillOutput:
        """執行模型對比實驗。

        Parameters（透過 inp.parameters）:
            target: 預測目標（"power" / "wind_speed"），預設 "power"
            test_ratio: 測試集比例（預設 0.2）
            sequence_length: 時序模型輸入長度（預設 48）
            forecast_horizon: 預測步數（預設 12）
            epochs: LSTM/PatchTST 訓練 epoch 數（預設 50）
            include_nbm: 是否包含 NBM（預設 True）
            include_lstm: 是否包含 LSTM（預設 True）
            include_patch_tst: 是否包含 PatchTST（預設 True）
            patch_length: PatchTST patch 長度（預設 8）
            experiment_name: 實驗名稱（預設 "model_benchmark"）
        """
        df = inp.dataframe if inp.dataframe is not None else inp.data
        if df is None:
            return SkillOutput(status=SkillStatus.ERROR, errors=["未收到輸入資料"])

        import pandas as pd

        if not isinstance(df, pd.DataFrame) or df.empty:
            return SkillOutput(status=SkillStatus.ERROR, errors=["輸入資料為空"])

        # ── 參數解析 ──
        target = inp.parameters.get("target", "power")
        test_ratio = inp.parameters.get("test_ratio", 0.2)
        seq_len = inp.parameters.get("sequence_length", 48)
        horizon = inp.parameters.get("forecast_horizon", 12)
        epochs = inp.parameters.get("epochs", 50)
        include_nbm = inp.parameters.get("include_nbm", True)
        include_lstm = inp.parameters.get("include_lstm", True)
        include_patch_tst = inp.parameters.get("include_patch_tst", True)
        patch_length = inp.parameters.get("patch_length", 8)
        stride = inp.parameters.get("stride", 8)
        experiment_name = inp.parameters.get("experiment_name", "model_benchmark")

        if progress_cb:
            await progress_cb(0.05, "初始化對比實驗框架...")

        loop = asyncio.get_event_loop()

        try:
            from src.models.benchmark.model_benchmark import ModelBenchmark

            # ── 1. 初始化 ──
            if progress_cb:
                await progress_cb(0.10, f"資料準備：target={target}, test_ratio={test_ratio}")

            benchmark = ModelBenchmark(
                df=df,
                target=target,
                test_ratio=test_ratio,
                sequence_length=seq_len,
                forecast_horizon=horizon,
            )

            # ── 2. 執行對比 ──
            models_to_run = []
            if include_nbm:
                models_to_run.append("NBM")
            if include_lstm:
                models_to_run.append("LSTM")
            if include_patch_tst:
                models_to_run.append("PatchTST")

            if progress_cb:
                await progress_cb(0.15, f"開始對比：{' vs '.join(models_to_run)}")

            report = await loop.run_in_executor(
                None,
                lambda: benchmark.run_all(
                    epochs=epochs,
                    include_nbm=include_nbm,
                    include_lstm=include_lstm,
                    include_patch_tst=include_patch_tst,
                    patch_length=patch_length,
                    stride=stride,
                ),
            )

            if progress_cb:
                await progress_cb(0.85, f"對比完成，最佳模型：{report.best_model}")

            # ── 3. 記錄實驗 ──
            if progress_cb:
                await progress_cb(0.90, "記錄實驗結果...")

            results_data = []
            for r in report.results:
                results_data.append(
                    {
                        "model_name": r.model_name,
                        "model_type": r.model_type,
                        "rmse": r.rmse,
                        "mae": r.mae,
                        "r2": r.r2,
                        "train_time_sec": r.train_time_sec,
                        "predict_time_sec": r.predict_time_sec,
                        "n_train": r.n_train,
                        "n_test": r.n_test,
                    }
                )

            await loop.run_in_executor(
                None,
                lambda: _log_benchmark(
                    experiment_name=experiment_name,
                    results=results_data,
                    dataset_info=report.dataset_info,
                    best_model=report.best_model,
                ),
            )

            if progress_cb:
                await progress_cb(1.0, "對比實驗完成")

            # ── 組裝輸出 ──
            comparison_text = report.comparison_table.to_string(index=False)

            summary_parts = [f"模型對比實驗 | target={target}"]
            for r in report.results:
                summary_parts.append(f"{r.model_name}: R²={r.r2:.4f} RMSE={r.rmse:.4f}")
            summary_parts.append(f"最佳: {report.best_model}")

            return SkillOutput(
                status=SkillStatus.SUCCESS,
                data={
                    "results": results_data,
                    "dataset_info": report.dataset_info,
                    "best_model": report.best_model,
                    "comparison_table": comparison_text,
                    "latex_table": report.latex_table,
                    "experiment_name": experiment_name,
                },
                summary=" | ".join(summary_parts),
                dataframe=df,
            )

        except Exception as e:
            return SkillOutput(
                status=SkillStatus.ERROR,
                errors=[f"對比實驗失敗：{e}"],
            )


def _log_benchmark(
    experiment_name: str,
    results: list[dict[str, Any]],
    dataset_info: dict[str, Any],
    best_model: str,
) -> None:
    """記錄對比實驗至 JSONL + 可選 MLflow。"""
    mlflow_logged = False
    try:
        import mlflow

        mlflow.set_experiment(experiment_name)
        with mlflow.start_run(run_name=f"benchmark_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"):
            for r in results:
                mlflow.log_metric(f"{r['model_name']}_rmse", r["rmse"])
                mlflow.log_metric(f"{r['model_name']}_mae", r["mae"])
                mlflow.log_metric(f"{r['model_name']}_r2", r["r2"])
            mlflow.set_tag("best_model", best_model)
            mlflow.set_tag("models_compared", ",".join(r["model_name"] for r in results))
        mlflow_logged = True
    except Exception:
        pass

    _EXPERIMENT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "experiment_name": experiment_name,
        "results": results,
        "dataset_info": dataset_info,
        "best_model": best_model,
        "mlflow_logged": mlflow_logged,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    log_file = _EXPERIMENT_LOG_DIR / f"{experiment_name}.jsonl"
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
