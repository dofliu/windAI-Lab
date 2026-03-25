"""wAI:experiment-tracker — 實驗追蹤師。

負責 ML 實驗的記錄、比較、版本管理與結果彙整，
整合 MLflow 進行實驗追蹤與模型登記。
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.agents.base import BaseAgent, TaskContext, TaskResult, TaskStatus

# 本地實驗記錄（MLflow 不可用時的備用方案）
_EXPERIMENT_LOG_DIR = Path(__file__).resolve().parents[3] / "data" / "experiments"


class ExperimentTracker(BaseAgent):
    """實驗追蹤代理。

    能力：
    - 實驗參數與指標記錄
    - 實驗結果比較
    - 模型版本管理
    - 最佳模型選擇
    """

    def __init__(self) -> None:
        super().__init__("experiment-tracker")

    @property
    def capabilities(self) -> list[str]:
        return [
            "experiment_logging",
            "metric_tracking",
            "model_versioning",
            "experiment_comparison",
            "best_model_selection",
            "hyperparameter_logging",
        ]

    async def execute(self, task: str, context: TaskContext) -> TaskResult:
        """執行實驗追蹤任務。"""
        params = context.parameters

        if "log" in task or "記錄" in task:
            return await self._log_experiment(params)

        if "compare" in task or "比較" in task:
            return await self._compare_experiments(params)

        if "list" in task or "列出" in task:
            return await self._list_experiments(params)

        if "best" in task or "最佳" in task:
            return await self._find_best(params)

        await self.update_progress(0.5, f"實驗追蹤：{task}")
        await self.update_progress(1.0)
        return TaskResult(status=TaskStatus.SUCCESS, summary=f"實驗追蹤任務完成：{task}")

    async def _log_experiment(self, params: dict[str, Any]) -> TaskResult:
        """記錄一次實驗。"""
        experiment_name = params.get("experiment_name", "unnamed")
        metrics = params.get("metrics", {})
        hyperparams = params.get("hyperparameters", {})
        model_type = params.get("model_type", "unknown")
        dataset = params.get("dataset", "unknown")

        await self.update_progress(0.3, f"記錄實驗：{experiment_name}")

        # 嘗試使用 MLflow
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
                mlflow.set_tag("dataset", dataset)
            mlflow_logged = True
            await self.update_progress(0.8, "MLflow 實驗已記錄")
        except Exception:
            await self.update_progress(0.5, "MLflow 不可用，使用本地記錄")

        # 本地 JSON 備份
        _EXPERIMENT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        record = {
            "experiment_name": experiment_name,
            "model_type": model_type,
            "dataset": dataset,
            "hyperparameters": hyperparams,
            "metrics": metrics,
            "timestamp": datetime.now(UTC).isoformat(),
            "mlflow_logged": mlflow_logged,
        }

        log_file = _EXPERIMENT_LOG_DIR / f"{experiment_name}.jsonl"
        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        await self.update_progress(1.0, f"實驗 '{experiment_name}' 已記錄")

        return TaskResult(
            status=TaskStatus.SUCCESS,
            data=record,
            summary=f"實驗 '{experiment_name}' 已記錄（MLflow: {'✓' if mlflow_logged else '✗'}）",
        )

    async def _compare_experiments(self, params: dict[str, Any]) -> TaskResult:
        """比較多次實驗結果。"""
        experiment_name = params.get("experiment_name", "")
        metric_key = params.get("metric", "f1_macro")

        if not experiment_name:
            return TaskResult(status=TaskStatus.ERROR, errors=["experiment_name 為必要參數"])

        await self.update_progress(0.3, f"載入 '{experiment_name}' 的實驗記錄")

        log_file = _EXPERIMENT_LOG_DIR / f"{experiment_name}.jsonl"
        if not log_file.exists():
            return TaskResult(
                status=TaskStatus.ERROR,
                errors=[f"找不到實驗 '{experiment_name}' 的記錄"],
            )

        records: list[dict[str, Any]] = []
        for line in log_file.read_text(encoding="utf-8").strip().split("\n"):
            if line:
                records.append(json.loads(line))

        if not records:
            return TaskResult(status=TaskStatus.ERROR, errors=["實驗記錄為空"])

        await self.update_progress(0.7, f"比較 {len(records)} 次實驗")

        # 依指標排序
        sorted_records = sorted(
            records,
            key=lambda r: r.get("metrics", {}).get(metric_key, 0),
            reverse=True,
        )

        await self.update_progress(1.0)
        return TaskResult(
            status=TaskStatus.SUCCESS,
            data={
                "experiment_name": experiment_name,
                "total_runs": len(records),
                "metric_key": metric_key,
                "best_run": sorted_records[0] if sorted_records else None,
                "all_runs": sorted_records[:10],
            },
            summary=f"比較 {len(records)} 次實驗，最佳 {metric_key}: "
            f"{sorted_records[0].get('metrics', {}).get(metric_key, 'N/A') if sorted_records else 'N/A'}",
        )

    async def _list_experiments(self, params: dict[str, Any]) -> TaskResult:
        """列出所有實驗。"""
        await self.update_progress(0.3, "掃描實驗記錄")

        _EXPERIMENT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        experiments: list[dict[str, Any]] = []
        for log_file in _EXPERIMENT_LOG_DIR.glob("*.jsonl"):
            line_count = sum(1 for _ in log_file.open(encoding="utf-8"))
            experiments.append(
                {
                    "name": log_file.stem,
                    "runs": line_count,
                    "file": str(log_file),
                }
            )

        await self.update_progress(1.0, f"找到 {len(experiments)} 個實驗")
        return TaskResult(
            status=TaskStatus.SUCCESS,
            data={"experiments": experiments, "total": len(experiments)},
            summary=f"共 {len(experiments)} 個實驗",
        )

    async def _find_best(self, params: dict[str, Any]) -> TaskResult:
        """找出最佳模型。"""
        experiment_name = params.get("experiment_name", "")
        metric_key = params.get("metric", "f1_macro")

        result = await self._compare_experiments(
            {"experiment_name": experiment_name, "metric": metric_key}
        )
        if result.status != TaskStatus.SUCCESS:
            return result

        best = result.data.get("best_run")
        if best:
            return TaskResult(
                status=TaskStatus.SUCCESS,
                data={"best_model": best},
                summary=f"最佳模型：{best.get('model_type', '?')} "
                f"({metric_key}={best.get('metrics', {}).get(metric_key, '?')})",
            )
        return TaskResult(status=TaskStatus.ERROR, errors=["無實驗記錄"])
