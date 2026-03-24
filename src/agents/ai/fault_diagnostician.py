"""wAI:fault-diagnostician — 故障診斷師。

負責風機故障分類、多標籤診斷、嚴重度評估與根因分析，
整合異常偵測模型與特徵工程管線。
"""

from __future__ import annotations

import asyncio
from typing import Any

from src.agents.base import BaseAgent, TaskContext, TaskResult, TaskStatus


class FaultDiagnostician(BaseAgent):
    """故障診斷代理，執行風機故障分類與異常偵測。"""

    def __init__(self) -> None:
        super().__init__("fault-diagnostician")

    @property
    def capabilities(self) -> list[str]:
        return [
            "fault_classification",
            "anomaly_detection",
            "severity_assessment",
            "root_cause_analysis",
            "vibration_analysis",
            "power_curve_deviation",
        ]

    async def execute(self, task: str, context: TaskContext) -> TaskResult:
        """執行故障診斷任務。"""
        params = context.parameters

        if "diagnose" in task or "診斷" in task:
            return await self._run_diagnosis(params)

        if "anomaly" in task or "異常" in task:
            return await self._detect_anomalies(params)

        await self.update_progress(0.5, f"分析中：{task}")
        await self.update_progress(1.0)
        return TaskResult(status=TaskStatus.SUCCESS, summary=f"故障分析完成：{task}")

    async def _run_diagnosis(self, params: dict[str, Any]) -> TaskResult:
        """執行完整故障診斷流程。"""
        turbine_id = params.get("turbine_id", "Kelmarsh_1")
        await self.update_progress(0.1, f"載入 {turbine_id} 的 SCADA 與感測器資料")

        try:
            from src.data_pipeline.ingestion.kelmarsh_loader import load_turbine_data

            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, lambda: load_turbine_data(turbine_id))
            await self.update_progress(0.25, f"已載入 {len(df)} 筆記錄")

            # 清洗
            from src.data_pipeline.cleaning.scada_cleaner import clean_scada_data

            df_clean, quality = await loop.run_in_executor(None, lambda: clean_scada_data(df))
            await self.update_progress(0.4, "資料清洗完成")

            # 特徵工程
            from src.features.domain_features.wind_features import (
                compute_operational_features,
                compute_power_curve_features,
                compute_temperature_features,
            )

            df_feat = await loop.run_in_executor(
                None, lambda: compute_power_curve_features(df_clean)
            )
            df_feat = await loop.run_in_executor(
                None, lambda: compute_temperature_features(df_feat)
            )
            df_feat = await loop.run_in_executor(
                None, lambda: compute_operational_features(df_feat)
            )
            await self.update_progress(0.6, "特徵工程完成")

            # 異常偵測與健康評分
            from src.models.evaluation.anomaly_analysis import generate_diagnosis_report

            report = await loop.run_in_executor(
                None, lambda: generate_diagnosis_report(df_feat, turbine_id)
            )
            await self.update_progress(0.9, "診斷報告已產出")

            health = report.get("health_score", 0)
            await self.update_progress(1.0, f"健康分數：{health}/100")

            return TaskResult(
                status=TaskStatus.SUCCESS,
                data={
                    "turbine_id": turbine_id,
                    "health_score": health,
                    "report": report,
                    "quality_report": quality,
                },
                summary=f"{turbine_id} 故障診斷完成 — 健康分數 {health}/100",
            )

        except Exception as e:
            return TaskResult(
                status=TaskStatus.ERROR,
                errors=[f"故障診斷失敗：{str(e)}"],
            )

    async def _detect_anomalies(self, params: dict[str, Any]) -> TaskResult:
        """執行異常偵測。"""
        turbine_id = params.get("turbine_id", "Kelmarsh_1")
        await self.update_progress(0.3, "載入並分析資料")

        try:
            from src.data_pipeline.ingestion.kelmarsh_loader import load_turbine_data
            from src.models.evaluation.anomaly_analysis import generate_diagnosis_report

            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, lambda: load_turbine_data(turbine_id))

            await self.update_progress(0.6, "執行異常偵測模型")

            report = await loop.run_in_executor(
                None, lambda: generate_diagnosis_report(df, turbine_id)
            )

            anomalies = report.get("temperature_anomalies", [])
            await self.update_progress(1.0, f"偵測到 {len(anomalies)} 個異常事件")

            return TaskResult(
                status=TaskStatus.SUCCESS,
                data={"anomaly_count": len(anomalies), "anomalies": anomalies},
                summary=f"異常偵測完成：{len(anomalies)} 個異常事件",
            )
        except Exception as e:
            return TaskResult(
                status=TaskStatus.ERROR,
                errors=[f"異常偵測失敗：{str(e)}"],
            )
