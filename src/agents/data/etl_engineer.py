"""wData:etl-engineer — ETL 工程師。

負責資料擷取、轉換與載入 (Extract-Transform-Load) pipeline 的設計與執行，
確保資料從原始來源到分析就緒狀態的可靠轉換。
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from src.agents.base import BaseAgent, TaskContext, TaskResult, TaskStatus


class EtlEngineer(BaseAgent):
    """ETL 工程代理。

    能力：
    - SCADA 資料 ETL pipeline 設計與執行
    - 資料格式轉換（CSV → Parquet）
    - 批次資料處理
    - 資料品質報告生成
    """

    def __init__(self) -> None:
        super().__init__("etl-engineer")

    @property
    def capabilities(self) -> list[str]:
        return [
            "etl_pipeline_design",
            "data_transformation",
            "format_conversion",
            "batch_processing",
            "data_quality_report",
            "pipeline_scheduling",
        ]

    async def execute(self, task: str, context: TaskContext) -> TaskResult:
        """執行 ETL 任務。"""
        params = context.parameters

        if "pipeline" in task or "轉換" in task or "etl" in task.lower():
            return await self._run_etl_pipeline(params)

        if "convert" in task or "轉檔" in task:
            return await self._convert_format(params)

        if "quality" in task or "品質" in task:
            return await self._quality_report(params)

        await self.update_progress(0.5, f"ETL 任務：{task}")
        await self.update_progress(1.0)
        return TaskResult(status=TaskStatus.SUCCESS, summary=f"ETL 任務完成：{task}")

    async def _run_etl_pipeline(self, params: dict[str, Any]) -> TaskResult:
        """執行完整 ETL pipeline：載入 → 清洗 → 特徵工程 → 輸出。"""
        turbine_id = params.get("turbine_id", "Kelmarsh_1")
        output_format = params.get("output_format", "parquet")

        await self.update_progress(0.05, f"啟動 ETL pipeline — {turbine_id}")

        try:
            from src.data_pipeline.cleaning.scada_cleaner import clean_scada_data
            from src.data_pipeline.ingestion.kelmarsh_loader import load_turbine_data
            from src.features.domain_features.wind_features import (
                compute_operational_features,
                compute_power_curve_features,
                compute_temperature_features,
            )

            loop = asyncio.get_event_loop()

            # Extract
            await self.update_progress(0.1, "Extract：載入原始 SCADA 資料")
            df = await loop.run_in_executor(None, lambda: load_turbine_data(turbine_id))
            raw_count = len(df)
            await self.update_progress(0.25, f"已載入 {raw_count} 筆原始記錄")

            # Transform — 清洗
            await self.update_progress(0.3, "Transform：資料清洗")
            df_clean, quality = await loop.run_in_executor(None, lambda: clean_scada_data(df))
            clean_count = len(df_clean)
            await self.update_progress(
                0.45, f"清洗後 {clean_count} 筆（移除 {raw_count - clean_count} 筆）"
            )

            # Transform — 特徵工程
            await self.update_progress(0.5, "Transform：特徵工程")
            df_feat = await loop.run_in_executor(
                None, lambda: compute_power_curve_features(df_clean)
            )
            df_feat = await loop.run_in_executor(
                None, lambda: compute_temperature_features(df_feat)
            )
            df_feat = await loop.run_in_executor(
                None, lambda: compute_operational_features(df_feat)
            )
            await self.update_progress(0.7, f"特徵工程完成：{len(df_feat.columns)} 欄位")

            # Load — 輸出
            await self.update_progress(0.8, "Load：儲存處理後資料")
            output_dir = Path(__file__).resolve().parents[3] / "data" / "processed"
            output_dir.mkdir(parents=True, exist_ok=True)

            if output_format == "parquet":
                output_path = output_dir / f"{turbine_id}_processed.parquet"
                await loop.run_in_executor(None, lambda: df_feat.to_parquet(output_path))
            else:
                output_path = output_dir / f"{turbine_id}_processed.csv"
                await loop.run_in_executor(None, lambda: df_feat.to_csv(output_path, index=False))

            await self.update_progress(1.0, f"ETL 完成 → {output_path.name}")

            return TaskResult(
                status=TaskStatus.SUCCESS,
                data={
                    "turbine_id": turbine_id,
                    "raw_records": raw_count,
                    "clean_records": clean_count,
                    "removed_records": raw_count - clean_count,
                    "columns": len(df_feat.columns),
                    "output_path": str(output_path),
                    "output_format": output_format,
                    "quality_report": quality,
                },
                summary=f"ETL 完成：{turbine_id} — {raw_count} → {clean_count} 筆，{len(df_feat.columns)} 欄位",
            )
        except Exception as e:
            return TaskResult(status=TaskStatus.ERROR, errors=[f"ETL pipeline 失敗：{str(e)}"])

    async def _convert_format(self, params: dict[str, Any]) -> TaskResult:
        """資料格式轉換。"""
        input_path = params.get("input_path", "")
        output_format = params.get("output_format", "parquet")

        if not input_path:
            return TaskResult(status=TaskStatus.ERROR, errors=["input_path 為必要參數"])

        await self.update_progress(0.3, f"轉換 {input_path} → {output_format}")

        try:
            import pandas as pd

            loop = asyncio.get_event_loop()
            path = Path(input_path)

            if path.suffix == ".csv":
                df = await loop.run_in_executor(None, lambda: pd.read_csv(path))
            elif path.suffix == ".parquet":
                df = await loop.run_in_executor(None, lambda: pd.read_parquet(path))
            else:
                return TaskResult(
                    status=TaskStatus.ERROR,
                    errors=[f"不支援的輸入格式：{path.suffix}"],
                )

            output_path = path.with_suffix(f".{output_format}")
            if output_format == "parquet":
                await loop.run_in_executor(None, lambda: df.to_parquet(output_path))
            else:
                await loop.run_in_executor(None, lambda: df.to_csv(output_path, index=False))

            await self.update_progress(1.0, f"轉換完成 → {output_path.name}")

            return TaskResult(
                status=TaskStatus.SUCCESS,
                data={
                    "input": str(path),
                    "output": str(output_path),
                    "rows": len(df),
                    "columns": len(df.columns),
                },
                summary=f"格式轉換完成：{path.name} → {output_path.name}",
            )
        except Exception as e:
            return TaskResult(status=TaskStatus.ERROR, errors=[f"格式轉換失敗：{str(e)}"])

    async def _quality_report(self, params: dict[str, Any]) -> TaskResult:
        """產生資料品質報告。"""
        turbine_id = params.get("turbine_id", "Kelmarsh_1")
        await self.update_progress(0.1, f"載入 {turbine_id} 資料")

        try:
            from src.data_pipeline.ingestion.kelmarsh_loader import load_turbine_data

            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, lambda: load_turbine_data(turbine_id))
            await self.update_progress(0.4, "計算品質指標")

            missing_pct = (df.isnull().sum() / len(df) * 100).to_dict()
            duplicates = int(df.duplicated().sum())
            numeric_stats = df.describe().to_dict()

            await self.update_progress(1.0, "品質報告已生成")

            return TaskResult(
                status=TaskStatus.SUCCESS,
                data={
                    "turbine_id": turbine_id,
                    "total_records": len(df),
                    "columns": len(df.columns),
                    "missing_percentage": {k: round(v, 2) for k, v in missing_pct.items()},
                    "duplicate_records": duplicates,
                    "numeric_summary": {
                        k: {
                            sk: round(sv, 3) if isinstance(sv, float) else sv
                            for sk, sv in v.items()
                        }
                        for k, v in numeric_stats.items()
                    },
                },
                summary=f"{turbine_id} 資料品質報告：{len(df)} 筆記錄，{duplicates} 筆重複",
            )
        except Exception as e:
            return TaskResult(status=TaskStatus.ERROR, errors=[f"品質報告失敗：{str(e)}"])
