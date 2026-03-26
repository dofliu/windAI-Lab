"""自動實驗技能 — 自動規劃、執行、比較多輪 ML 實驗。

給定一個研究問題（如「功率曲線預測」「故障診斷」），AutoExperimentSkill 會：
1. 根據問題類型規劃實驗矩陣（哪些模型 × 哪些超參數組合）
2. 自動逐輪執行實驗（訓練 + 評估）
3. 記錄每輪結果（串接 ExperimentTracker 的 JSONL 格式）
4. 比較所有實驗結果，選出最佳配置
5. 產出實驗總結報告

支援的實驗類型：
- power_curve_nbm：功率曲線正常行為模型（GBR，調整 n_estimators / max_depth / lr）
- fault_classifier：故障分類器（RF，調整 n_estimators / max_depth）
- model_comparison：在同一資料上比較多種模型

使用方式：
    inp.parameters = {
        "experiment_type": "power_curve_nbm",  # 或 "fault_classifier" / "model_comparison"
        "experiment_name": "my_experiment",     # 實驗名稱（用於記錄）
        "n_trials": 5,                         # 實驗輪數
    }
    inp.dataframe = df  # 已清洗 + 特徵工程後的 SCADA DataFrame
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from itertools import product
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.skills.base import BaseSkill, ProgressCallback, SkillInput, SkillOutput, SkillStatus

# 實驗記錄目錄（與 ExperimentTracker 共用）
_EXPERIMENT_LOG_DIR = Path(__file__).resolve().parents[3] / "data" / "experiments"


# ── 實驗結果資料結構 ──────────────────────────────────────────


@dataclass
class TrialResult:
    """單次實驗結果。"""

    trial_id: int
    model_type: str
    hyperparameters: dict[str, Any]
    metrics: dict[str, float]
    duration_seconds: float
    error: str | None = None


@dataclass
class ExperimentReport:
    """實驗總結報告。"""

    experiment_name: str
    experiment_type: str
    total_trials: int
    successful_trials: int
    failed_trials: int
    best_trial: TrialResult | None
    primary_metric: str
    all_trials: list[TrialResult] = field(default_factory=list)
    total_duration_seconds: float = 0.0


# ── 實驗配置 ──────────────────────────────────────────────────

# 每種實驗類型的搜尋空間
_SEARCH_SPACES: dict[str, dict[str, list[Any]]] = {
    "power_curve_nbm": {
        "n_estimators": [100, 200, 300],
        "max_depth": [3, 5, 7],
        "learning_rate": [0.05, 0.1, 0.2],
    },
    "fault_classifier": {
        "n_estimators": [50, 100, 200],
        "max_depth": [4, 6, 8],
    },
}

# 主要評估指標
_PRIMARY_METRICS: dict[str, str] = {
    "power_curve_nbm": "r2",
    "fault_classifier": "f1_macro",
    "model_comparison": "r2",
}


class AutoExperimentSkill(BaseSkill):
    """自動規劃並執行多輪 ML 實驗，比較結果並選出最佳配置。"""

    skill_id = "auto_experiment"
    display_name = "自動實驗"
    description = "自動規劃、執行、比較多輪 ML 實驗，找出最佳模型配置"
    version = "1.0.0"

    async def execute(
        self,
        inp: SkillInput,
        progress_cb: ProgressCallback = None,
    ) -> SkillOutput:
        """執行自動實驗。

        Parameters (inp.parameters):
            experiment_type: str — 實驗類型
                "power_curve_nbm" / "fault_classifier" / "model_comparison"
            experiment_name: str — 實驗名稱（預設自動產生）
            n_trials: int | None — 限制實驗輪數（None = 跑完所有組合）
            custom_search_space: dict | None — 自訂搜尋空間（覆蓋預設）
        Input (inp.dataframe or inp.data):
            已清洗 + 特徵工程後的 SCADA DataFrame
        """
        import asyncio

        df = inp.dataframe if inp.dataframe is not None else inp.data
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            return SkillOutput(status=SkillStatus.ERROR, errors=["未收到輸入資料"])

        experiment_type = inp.parameters.get("experiment_type", "power_curve_nbm")
        experiment_name = inp.parameters.get(
            "experiment_name",
            f"auto_{experiment_type}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
        )
        n_trials = inp.parameters.get("n_trials")
        custom_space = inp.parameters.get("custom_search_space")

        if progress_cb:
            await progress_cb(0.05, f"規劃實驗：{experiment_type}...")

        # ── Step 1：規劃實驗矩陣 ──
        if experiment_type == "model_comparison":
            trial_configs = _plan_model_comparison()
        else:
            search_space = custom_space or _SEARCH_SPACES.get(experiment_type, {})
            trial_configs = _plan_grid_search(experiment_type, search_space, n_trials)

        if not trial_configs:
            return SkillOutput(
                status=SkillStatus.ERROR,
                errors=[f"無法規劃實驗：不支援的類型 '{experiment_type}'"],
            )

        total = len(trial_configs)
        primary_metric = _PRIMARY_METRICS.get(experiment_type, "r2")

        if progress_cb:
            await progress_cb(0.1, f"共 {total} 組實驗，開始執行...")

        # ── Step 2：逐輪執行實驗 ──
        loop = asyncio.get_event_loop()
        results: list[TrialResult] = []
        start_time = time.monotonic()

        for i, config in enumerate(trial_configs):
            trial_start = time.monotonic()
            model_type = config["model_type"]
            hyperparams = config["hyperparameters"]

            try:
                metrics = await loop.run_in_executor(
                    None,
                    lambda mt=model_type, hp=hyperparams: _run_single_trial(df, mt, hp),
                )
                trial = TrialResult(
                    trial_id=i + 1,
                    model_type=model_type,
                    hyperparameters=hyperparams,
                    metrics=metrics,
                    duration_seconds=round(time.monotonic() - trial_start, 2),
                )
            except Exception as e:
                trial = TrialResult(
                    trial_id=i + 1,
                    model_type=model_type,
                    hyperparameters=hyperparams,
                    metrics={},
                    duration_seconds=round(time.monotonic() - trial_start, 2),
                    error=str(e),
                )

            results.append(trial)

            # ── Step 3：記錄每輪結果 ──
            _log_trial(experiment_name, trial)

            if progress_cb and (i + 1) % max(1, total // 10) == 0:
                pct = 0.1 + 0.8 * (i + 1) / total
                best_so_far = _find_best(results, primary_metric)
                best_val = best_so_far.metrics.get(primary_metric, 0) if best_so_far else 0
                await progress_cb(
                    pct, f"已完成 {i + 1}/{total}，最佳 {primary_metric}={best_val:.4f}"
                )

        total_duration = round(time.monotonic() - start_time, 2)

        # ── Step 4：比較並選出最佳 ──
        successful = [r for r in results if r.error is None]
        best = _find_best(successful, primary_metric)

        report = ExperimentReport(
            experiment_name=experiment_name,
            experiment_type=experiment_type,
            total_trials=total,
            successful_trials=len(successful),
            failed_trials=total - len(successful),
            best_trial=best,
            primary_metric=primary_metric,
            all_trials=results,
            total_duration_seconds=total_duration,
        )

        if progress_cb:
            await progress_cb(1.0, "實驗完成")

        # ── Step 5：產出報告 ──
        report_data = _build_report_data(report)

        best_val = best.metrics.get(primary_metric, 0) if best else 0
        summary = (
            f"自動實驗完成：{len(successful)}/{total} 成功，"
            f"最佳 {primary_metric}={best_val:.4f}"
        )
        if best:
            summary += f"（{best.model_type}, {best.hyperparameters}）"

        return SkillOutput(
            status=SkillStatus.SUCCESS if successful else SkillStatus.ERROR,
            data=report_data,
            summary=summary,
            dataframe=df,
            errors=[r.error for r in results if r.error is not None],
        )


# ── 實驗規劃 ──────────────────────────────────────────────────


def _plan_grid_search(
    model_type: str,
    search_space: dict[str, list[Any]],
    max_trials: int | None = None,
) -> list[dict[str, Any]]:
    """從搜尋空間產生網格組合。"""
    if not search_space:
        return []

    keys = list(search_space.keys())
    values = list(search_space.values())
    combos = list(product(*values))

    # 限制試驗數
    if max_trials and len(combos) > max_trials:
        rng = np.random.default_rng(42)
        indices = rng.choice(len(combos), size=max_trials, replace=False)
        combos = [combos[i] for i in sorted(indices)]

    return [
        {
            "model_type": model_type,
            "hyperparameters": dict(zip(keys, combo, strict=True)),
        }
        for combo in combos
    ]


def _plan_model_comparison() -> list[dict[str, Any]]:
    """規劃多模型比較實驗。"""
    return [
        {
            "model_type": "power_curve_nbm",
            "hyperparameters": {"n_estimators": 200, "max_depth": 5, "learning_rate": 0.1},
        },
        {
            "model_type": "power_curve_nbm",
            "hyperparameters": {"n_estimators": 100, "max_depth": 3, "learning_rate": 0.1},
        },
        {
            "model_type": "power_curve_nbm",
            "hyperparameters": {"n_estimators": 300, "max_depth": 7, "learning_rate": 0.05},
        },
        {
            "model_type": "fault_classifier",
            "hyperparameters": {"n_estimators": 100, "max_depth": 8},
        },
        {
            "model_type": "fault_classifier",
            "hyperparameters": {"n_estimators": 200, "max_depth": 6},
        },
    ]


# ── 實驗執行 ──────────────────────────────────────────────────


def _run_single_trial(
    df: pd.DataFrame,
    model_type: str,
    hyperparams: dict[str, Any],
) -> dict[str, float]:
    """執行單次實驗，回傳指標。"""
    if model_type == "power_curve_nbm":
        return _train_nbm(df, hyperparams)
    if model_type == "fault_classifier":
        return _train_fault_classifier(df, hyperparams)
    raise ValueError(f"不支援的模型類型：{model_type}")


def _train_nbm(df: pd.DataFrame, hyperparams: dict[str, Any]) -> dict[str, float]:
    """訓練一次 NBM 並回傳指標。"""
    from src.models.nbm.power_curve_nbm import PowerCurveNBM

    nbm = PowerCurveNBM(
        n_estimators=hyperparams.get("n_estimators", 200),
        max_depth=hyperparams.get("max_depth", 5),
        learning_rate=hyperparams.get("learning_rate", 0.1),
    )
    result = nbm.train(df)
    return {
        "r2": round(result.r2, 6),
        "mae": round(result.mae, 2),
        "rmse": round(result.rmse, 2),
    }


def _train_fault_classifier(df: pd.DataFrame, hyperparams: dict[str, Any]) -> dict[str, float]:
    """訓練一次 FaultClassifier 並回傳指標。"""
    from src.models.classification.fault_classifier import FaultClassifier

    clf = FaultClassifier(
        n_estimators=hyperparams.get("n_estimators", 100),
        max_depth=hyperparams.get("max_depth", 8),
    )
    result = clf.train(df)
    return {
        "f1_macro": round(result.f1_macro, 6),
        "n_train": result.n_train,
        "n_test": result.n_test,
    }


# ── 結果記錄與比較 ────────────────────────────────────────────


def _log_trial(experiment_name: str, trial: TrialResult) -> None:
    """將單次實驗記錄寫入 JSONL（與 ExperimentTracker 格式相容）。"""
    _EXPERIMENT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "experiment_name": experiment_name,
        "trial_id": trial.trial_id,
        "model_type": trial.model_type,
        "dataset": "auto_experiment",
        "hyperparameters": trial.hyperparameters,
        "metrics": trial.metrics,
        "duration_seconds": trial.duration_seconds,
        "error": trial.error,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    log_file = _EXPERIMENT_LOG_DIR / f"{experiment_name}.jsonl"
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _find_best(trials: list[TrialResult], metric: str) -> TrialResult | None:
    """從成功的實驗中找出指標最佳的一輪。"""
    valid = [t for t in trials if t.error is None and metric in t.metrics]
    if not valid:
        return None
    return max(valid, key=lambda t: t.metrics[metric])


def _build_report_data(report: ExperimentReport) -> dict[str, Any]:
    """將 ExperimentReport 轉為可序列化的 dict。"""
    data: dict[str, Any] = {
        "experiment_name": report.experiment_name,
        "experiment_type": report.experiment_type,
        "total_trials": report.total_trials,
        "successful_trials": report.successful_trials,
        "failed_trials": report.failed_trials,
        "primary_metric": report.primary_metric,
        "total_duration_seconds": report.total_duration_seconds,
    }

    if report.best_trial:
        data["best_trial"] = {
            "trial_id": report.best_trial.trial_id,
            "model_type": report.best_trial.model_type,
            "hyperparameters": report.best_trial.hyperparameters,
            "metrics": report.best_trial.metrics,
        }

    # 排行榜（前 10 名）
    successful = [t for t in report.all_trials if t.error is None]
    ranked = sorted(
        successful,
        key=lambda t: t.metrics.get(report.primary_metric, 0),
        reverse=True,
    )
    data["leaderboard"] = [
        {
            "rank": i + 1,
            "trial_id": t.trial_id,
            "model_type": t.model_type,
            "hyperparameters": t.hyperparameters,
            "metrics": t.metrics,
            "duration_seconds": t.duration_seconds,
        }
        for i, t in enumerate(ranked[:10])
    ]

    return data
