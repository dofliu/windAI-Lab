"""wAI:predictive-modeler — 預測模型師。

負責剩餘使用壽命預測 (RUL)、退化建模、
預測性維護排程建議，使用真實退化曲線擬合。
"""

from __future__ import annotations

import asyncio
from typing import Any

from src.agents.base import BaseAgent, TaskContext, TaskResult, TaskStatus


class PredictiveModeler(BaseAgent):
    """預測模型代理，負責 RUL 預測與退化建模。"""

    def __init__(self) -> None:
        super().__init__("predictive-modeler")

    @property
    def capabilities(self) -> list[str]:
        return [
            "rul_prediction",
            "degradation_modeling",
            "survival_analysis",
            "predictive_maintenance",
            "trend_forecasting",
        ]

    async def execute(self, task: str, context: TaskContext) -> TaskResult:
        """執行預測建模任務。"""
        params = context.parameters

        if "rul" in task.lower() or "壽命" in task:
            return await self._predict_rul(params)

        if "trend" in task or "趨勢" in task or "退化" in task:
            return await self._analyze_trend(params)

        await self.update_progress(0.5, f"預測分析中：{task}")
        await self.update_progress(1.0)
        return TaskResult(status=TaskStatus.SUCCESS, summary=f"預測分析完成：{task}")

    async def _predict_rul(self, params: dict[str, Any]) -> TaskResult:
        """使用退化模型預測剩餘使用壽命。"""
        turbine_id = params.get("turbine_id", "WT-01")
        component = params.get("component", "gearbox")

        await self.update_progress(0.1, f"載入 {turbine_id} 資料")

        try:
            from src.data_pipeline.cleaning.scada_cleaner import clean_scada_data
            from src.data_pipeline.ingestion.kelmarsh_loader import load_turbine_data
            from src.features.domain_features.wind_features import (
                compute_operational_features,
                compute_power_curve_features,
                compute_temperature_features,
            )
            from src.models.degradation.rul_model import RULModel, compute_health_index

            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, lambda: load_turbine_data(turbine_id))
            await self.update_progress(0.2, f"已載入 {len(df)} 筆記錄")

            # 清洗與特徵工程
            df_clean, _ = await loop.run_in_executor(None, lambda: clean_scada_data(df))
            df_feat = await loop.run_in_executor(
                None, lambda: compute_power_curve_features(df_clean)
            )
            df_feat = await loop.run_in_executor(
                None, lambda: compute_temperature_features(df_feat)
            )
            df_feat = await loop.run_in_executor(
                None, lambda: compute_operational_features(df_feat)
            )
            await self.update_progress(0.4, "特徵工程完成")

            # 計算每日健康指標
            await self.update_progress(0.5, "計算每日健康指標")
            hi_df = await loop.run_in_executor(None, lambda: compute_health_index(df_feat))
            await self.update_progress(0.6, f"取得 {len(hi_df)} 天健康指標")

            # 擬合退化模型
            await self.update_progress(0.7, "擬合退化曲線模型")
            rul_model = RULModel()
            deg_analysis = await loop.run_in_executor(None, lambda: rul_model.fit(hi_df))
            await self.update_progress(
                0.8,
                f"退化模型：{deg_analysis.model_type}, "
                f"趨勢={deg_analysis.trend}, R²={deg_analysis.r_squared:.4f}",
            )

            # 預測 RUL
            await self.update_progress(0.9, "計算剩餘使用壽命與信賴區間")
            rul_pred = await loop.run_in_executor(None, lambda: rul_model.predict_rul())

            ci = rul_pred.confidence_interval
            await self.update_progress(
                1.0,
                f"RUL 預測：{rul_pred.rul_days:.0f} 天 "
                f"（95% CI: {ci['lower']:.0f}~{ci['upper']:.0f} 天）",
            )

            return TaskResult(
                status=TaskStatus.SUCCESS,
                data={
                    "turbine_id": turbine_id,
                    "component": component,
                    "rul_days": rul_pred.rul_days,
                    "confidence_interval": rul_pred.confidence_interval,
                    "confidence_level": rul_pred.confidence_level,
                    "degradation_model": rul_pred.degradation_model,
                    "model_r_squared": rul_pred.model_r_squared,
                    "current_health_index": rul_pred.current_health_index,
                    "trend": rul_pred.trend,
                    "daily_degradation_rate": rul_pred.daily_degradation_rate,
                    "degradation_analysis": {
                        "model_type": deg_analysis.model_type,
                        "r_squared": deg_analysis.r_squared,
                        "days_analyzed": len(hi_df),
                        "model_params": deg_analysis.model_params,
                    },
                },
                summary=(
                    f"{turbine_id} {component} RUL 預測：{rul_pred.rul_days:.0f} 天 "
                    f"（{ci['lower']:.0f}~{ci['upper']:.0f} 天, 95% CI）— "
                    f"趨勢：{rul_pred.trend}"
                ),
            )

        except Exception as e:
            return TaskResult(
                status=TaskStatus.ERROR,
                errors=[f"RUL 預測失敗：{str(e)}"],
            )

    async def _analyze_trend(self, params: dict[str, Any]) -> TaskResult:
        """分析退化趨勢。"""
        turbine_id = params.get("turbine_id", "WT-01")

        await self.update_progress(0.1, f"載入 {turbine_id} 退化資料")

        try:
            from src.data_pipeline.cleaning.scada_cleaner import clean_scada_data
            from src.data_pipeline.ingestion.kelmarsh_loader import load_turbine_data
            from src.features.domain_features.wind_features import (
                compute_operational_features,
                compute_power_curve_features,
                compute_temperature_features,
            )
            from src.models.degradation.rul_model import RULModel, compute_health_index

            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, lambda: load_turbine_data(turbine_id))
            df_clean, _ = await loop.run_in_executor(None, lambda: clean_scada_data(df))
            df_feat = await loop.run_in_executor(
                None, lambda: compute_power_curve_features(df_clean)
            )
            df_feat = await loop.run_in_executor(
                None, lambda: compute_temperature_features(df_feat)
            )
            df_feat = await loop.run_in_executor(
                None, lambda: compute_operational_features(df_feat)
            )
            await self.update_progress(0.5, "計算健康指標")

            hi_df = await loop.run_in_executor(None, lambda: compute_health_index(df_feat))
            rul_model = RULModel()
            deg_analysis = await loop.run_in_executor(None, lambda: rul_model.fit(hi_df))

            await self.update_progress(1.0, "趨勢分析完成")

            return TaskResult(
                status=TaskStatus.SUCCESS,
                data={
                    "turbine_id": turbine_id,
                    "trend": deg_analysis.trend,
                    "degradation_rate": deg_analysis.degradation_rate,
                    "model_type": deg_analysis.model_type,
                    "r_squared": deg_analysis.r_squared,
                    "health_index_series": deg_analysis.health_index_series[:30],
                },
                summary=(
                    f"{turbine_id} 退化趨勢分析完成 — "
                    f"趨勢：{deg_analysis.trend}, "
                    f"日退化率：{deg_analysis.degradation_rate:.4f}"
                ),
            )

        except Exception as e:
            return TaskResult(
                status=TaskStatus.ERROR,
                errors=[f"趨勢分析失敗：{str(e)}"],
            )
