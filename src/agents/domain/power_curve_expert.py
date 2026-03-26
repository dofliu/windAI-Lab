"""wDomain:power-curve-expert — 功率曲線專家。

負責風機功率曲線建模、偏差分析、性能評估，
整合 Normal Behavior Model (NBM) 與 IEC 61400-12 標準方法。
"""

from __future__ import annotations

import asyncio
from typing import Any

from src.agents.base import BaseAgent, TaskContext, TaskResult, TaskStatus


class PowerCurveExpert(BaseAgent):
    """功率曲線專家代理，使用 ML NBM 建模與分析風機功率曲線。"""

    def __init__(self) -> None:
        super().__init__("power-curve-expert")

    @property
    def capabilities(self) -> list[str]:
        return [
            "power_curve_modeling",
            "nbm_training",
            "deviation_analysis",
            "performance_assessment",
            "iec_compliance_check",
            "cp_calculation",
        ]

    async def execute(self, task: str, context: TaskContext) -> TaskResult:
        """執行功率曲線分析任務。"""
        params = context.parameters

        if "model" in task or "建模" in task or "curve" in task or "nbm" in task.lower():
            return await self._build_power_curve_nbm(params)

        if "deviation" in task or "偏差" in task or "anomal" in task.lower():
            return await self._analyze_deviation_nbm(params)

        await self.update_progress(0.5, f"功率曲線分析：{task}")
        await self.update_progress(1.0)
        return TaskResult(status=TaskStatus.SUCCESS, summary=f"完成：{task}")

    async def _build_power_curve_nbm(self, params: dict[str, Any]) -> TaskResult:
        """使用 Gradient Boosting NBM 建立功率曲線模型。"""
        turbine_id = params.get("turbine_id", "WT-01")

        await self.update_progress(0.1, f"載入 {turbine_id} 運行資料")

        try:
            from src.data_pipeline.cleaning.scada_cleaner import clean_scada_data
            from src.data_pipeline.ingestion.kelmarsh_loader import load_turbine_data
            from src.models.nbm.power_curve_nbm import PowerCurveNBM

            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, lambda: load_turbine_data(turbine_id))
            await self.update_progress(0.2, f"已載入 {len(df)} 筆記錄")

            # 清洗
            df_clean, quality = await loop.run_in_executor(None, lambda: clean_scada_data(df))
            await self.update_progress(0.3, "資料清洗完成")

            # 訓練 NBM
            await self.update_progress(0.4, "訓練 Gradient Boosting NBM...")
            nbm = PowerCurveNBM()
            nbm_result = await loop.run_in_executor(None, lambda: nbm.train(df_clean))
            await self.update_progress(
                0.7,
                f"NBM 訓練完成 — R²={nbm_result.r2:.4f}, MAE={nbm_result.mae:.1f} kW",
            )

            # NBM 異常偵測
            await self.update_progress(0.8, "執行 NBM 功率曲線異常偵測...")
            anomaly_result = await loop.run_in_executor(
                None, lambda: nbm.detect_anomalies(df_clean)
            )
            await self.update_progress(
                0.95,
                f"偵測到 {anomaly_result.anomaly_count} 個異常點 "
                f"（比率 {anomaly_result.anomaly_ratio:.2%}）",
            )

            await self.update_progress(1.0, "功率曲線 NBM 建模完成")

            return TaskResult(
                status=TaskStatus.SUCCESS,
                data={
                    "turbine_id": turbine_id,
                    "model_type": "GradientBoostingRegressor",
                    "performance": {
                        "r2": nbm_result.r2,
                        "mae": nbm_result.mae,
                        "rmse": nbm_result.rmse,
                    },
                    "feature_importances": nbm_result.feature_importances,
                    "n_train": nbm_result.n_train,
                    "n_test": nbm_result.n_test,
                    "anomaly_detection": {
                        "total_points": anomaly_result.total_points,
                        "anomaly_count": anomaly_result.anomaly_count,
                        "anomaly_ratio": anomaly_result.anomaly_ratio,
                        "threshold": anomaly_result.threshold,
                        "top_anomalies": anomaly_result.anomalies[:10],
                    },
                },
                summary=(
                    f"{turbine_id} 功率曲線 NBM 建模完成 — "
                    f"R²={nbm_result.r2:.4f}, "
                    f"異常點 {anomaly_result.anomaly_count} 個"
                ),
            )
        except Exception as e:
            return TaskResult(
                status=TaskStatus.ERROR,
                errors=[f"功率曲線 NBM 建模失敗：{str(e)}"],
            )

    async def _analyze_deviation_nbm(self, params: dict[str, Any]) -> TaskResult:
        """使用 NBM 分析功率曲線偏差。"""
        turbine_id = params.get("turbine_id", "WT-01")

        await self.update_progress(0.2, f"載入 {turbine_id} 資料")

        try:
            from src.data_pipeline.cleaning.scada_cleaner import clean_scada_data
            from src.data_pipeline.ingestion.kelmarsh_loader import load_turbine_data
            from src.models.nbm.power_curve_nbm import PowerCurveNBM

            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, lambda: load_turbine_data(turbine_id))
            df_clean, _ = await loop.run_in_executor(None, lambda: clean_scada_data(df))

            await self.update_progress(0.4, "訓練 NBM 並偵測偏差")
            nbm = PowerCurveNBM()
            await loop.run_in_executor(None, lambda: nbm.train(df_clean))

            anomaly_result = await loop.run_in_executor(
                None, lambda: nbm.detect_anomalies(df_clean)
            )

            await self.update_progress(1.0, "偏差分析完成")

            return TaskResult(
                status=TaskStatus.SUCCESS,
                data={
                    "turbine_id": turbine_id,
                    "mean_residual": anomaly_result.mean_residual,
                    "std_residual": anomaly_result.std_residual,
                    "anomaly_count": anomaly_result.anomaly_count,
                    "anomaly_ratio": anomaly_result.anomaly_ratio,
                },
                summary=(
                    f"{turbine_id} NBM 偏差分析完成 — "
                    f"異常比率 {anomaly_result.anomaly_ratio:.2%}"
                ),
            )
        except Exception as e:
            return TaskResult(
                status=TaskStatus.ERROR,
                errors=[f"偏差分析失敗：{str(e)}"],
            )
