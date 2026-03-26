"""wData:quality-checker — 資料品質檢核員。

負責驗證資料品質指標，包含完整度、一致性、
感測器範圍檢查、品質標記 (quality flag) 管理。
"""

from __future__ import annotations

import asyncio
from typing import Any

from src.agents.base import BaseAgent, TaskContext, TaskResult, TaskStatus


class QualityChecker(BaseAgent):
    """資料品質檢核代理，驗證 SCADA 資料品質。"""

    def __init__(self) -> None:
        super().__init__("quality-checker")

    @property
    def capabilities(self) -> list[str]:
        return [
            "data_quality_assessment",
            "completeness_check",
            "range_validation",
            "consistency_check",
            "quality_flag_management",
        ]

    async def execute(self, task: str, context: TaskContext) -> TaskResult:
        """執行資料品質檢核任務。"""
        params = context.parameters
        data = params.get("dataframe")

        if data is None:
            # 嘗試從 context results 取得上游資料
            return await self._validate_from_source(params)

        return await self._validate_dataframe(data)

    async def _validate_from_source(self, params: dict[str, Any]) -> TaskResult:
        """載入並驗證資料來源。"""
        turbine_id = params.get("turbine_id", "WT-01")
        await self.update_progress(0.2, f"載入 {turbine_id} 資料進行品質檢核")

        try:
            from src.data_pipeline.ingestion.kelmarsh_loader import load_turbine_data

            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, lambda: load_turbine_data(turbine_id))

            return await self._validate_dataframe(df)
        except Exception as e:
            return TaskResult(
                status=TaskStatus.ERROR,
                errors=[f"品質檢核失敗：{str(e)}"],
            )

    async def _validate_dataframe(self, df: Any) -> TaskResult:
        """驗證 DataFrame 品質。"""
        import pandas as pd

        if not isinstance(df, pd.DataFrame):
            return TaskResult(
                status=TaskStatus.ERROR,
                errors=["輸入資料格式錯誤，預期為 pandas DataFrame"],
            )

        await self.update_progress(0.3, "檢查資料完整度")

        total_rows = len(df)
        total_cells = df.size
        missing_cells = int(df.isnull().sum().sum())
        missing_pct = (missing_cells / total_cells * 100) if total_cells > 0 else 0.0

        await self.update_progress(0.6, "檢查數值範圍與一致性")

        # 基本範圍檢查
        warnings: list[str] = []
        if "wind_speed" in df.columns:
            ws = df["wind_speed"]
            if ws.max() > 50:
                warnings.append(f"風速最大值異常：{ws.max():.1f} m/s")
            if ws.min() < 0:
                warnings.append(f"風速存在負值：{ws.min():.1f} m/s")

        if "power_output" in df.columns:
            po = df["power_output"]
            if po.min() < -100:
                warnings.append(f"功率存在異常負值：{po.min():.1f} kW")

        await self.update_progress(1.0, "品質檢核完成")

        quality_score = max(0, 100 - missing_pct * 2 - len(warnings) * 5)

        status = TaskStatus.SUCCESS if quality_score >= 70 else TaskStatus.PARTIAL
        return TaskResult(
            status=status,
            data={
                "total_rows": total_rows,
                "missing_pct": round(missing_pct, 2),
                "quality_score": round(quality_score, 1),
                "warnings": warnings,
            },
            summary=f"品質分數：{quality_score:.1f}/100（缺失率 {missing_pct:.1f}%）",
        )
