"""wData:scada-processor — SCADA 資料處理員。

負責 SCADA 資料的匯入、預處理與格式轉換，
整合既有的 kelmarsh_loader 與 scada_cleaner 模組。
"""

from __future__ import annotations

import asyncio
from typing import Any

from src.agents.base import BaseAgent, TaskContext, TaskResult, TaskStatus


class ScadaProcessor(BaseAgent):
    """SCADA 資料處理代理，橋接資料匯入管線。"""

    def __init__(self) -> None:
        super().__init__("scada-processor")

    @property
    def capabilities(self) -> list[str]:
        return [
            "scada_ingestion",
            "data_preprocessing",
            "format_conversion",
            "data_alignment",
            "batch_processing",
        ]

    async def execute(self, task: str, context: TaskContext) -> TaskResult:
        """執行 SCADA 資料處理任務。"""
        params = context.parameters

        if "load" in task or "載入" in task or "匯入" in task:
            return await self._load_scada(params)

        if "clean" in task or "清洗" in task:
            return await self._clean_scada(params)

        return TaskResult(
            status=TaskStatus.ERROR,
            errors=[f"未知的 SCADA 處理任務：{task}"],
        )

    async def _load_scada(self, params: dict[str, Any]) -> TaskResult:
        """載入 SCADA 資料。"""
        turbine_id = params.get("turbine_id", "WT-01")
        year = params.get("year", 2016)

        await self.update_progress(0.1, f"連線至 {turbine_id} 資料來源")

        try:
            from src.data_pipeline.ingestion.kelmarsh_loader import load_turbine_data

            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, lambda: load_turbine_data(turbine_id, year))

            row_count = len(df)
            col_count = len(df.columns)

            await self.update_progress(0.8, f"已載入 {row_count} 筆記錄")
            await self.update_progress(1.0, "SCADA 資料載入完成")

            return TaskResult(
                status=TaskStatus.SUCCESS,
                data={
                    "turbine_id": turbine_id,
                    "row_count": row_count,
                    "col_count": col_count,
                    "columns": list(df.columns[:20]),
                },
                summary=f"{turbine_id} SCADA 資料載入完成：{row_count} 筆 × {col_count} 欄",
            )
        except Exception as e:
            return TaskResult(
                status=TaskStatus.ERROR,
                errors=[f"SCADA 資料載入失敗：{str(e)}"],
            )

    async def _clean_scada(self, params: dict[str, Any]) -> TaskResult:
        """清洗 SCADA 資料。"""
        await self.update_progress(0.2, "執行資料品質檢查")

        try:
            from src.data_pipeline.cleaning.scada_cleaner import clean_scada_data
            from src.data_pipeline.ingestion.kelmarsh_loader import load_turbine_data

            turbine_id = params.get("turbine_id", "WT-01")

            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, lambda: load_turbine_data(turbine_id))

            await self.update_progress(0.5, "清洗中：去重、插補、異常值過濾")

            df_clean, quality = await loop.run_in_executor(None, lambda: clean_scada_data(df))

            await self.update_progress(1.0, "資料清洗完成")

            return TaskResult(
                status=TaskStatus.SUCCESS,
                data={
                    "quality_report": quality,
                    "clean_row_count": len(df_clean),
                },
                summary=(
                    f"資料清洗完成 — 總筆數: {quality['total_rows']}, "
                    f"缺失率: {quality['missing_pct']:.1f}%"
                ),
            )
        except Exception as e:
            return TaskResult(
                status=TaskStatus.ERROR,
                errors=[f"資料清洗失敗：{str(e)}"],
            )
