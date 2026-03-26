"""SCADA 資料載入技能 — 包裝 smart_loader，支援任意格式自動辨識。"""

from __future__ import annotations

import asyncio
from pathlib import Path

from src.skills.base import BaseSkill, ProgressCallback, SkillInput, SkillOutput, SkillStatus


class ScadaIngestionSkill(BaseSkill):
    """智慧載入 SCADA 資料：自動偵測格式、欄位映射、時間戳記解析。"""

    skill_id = "scada_ingestion"
    display_name = "SCADA 資料載入"
    description = "從 CSV/Parquet/ZIP 自動載入風場 SCADA 資料，智慧辨識欄位映射"
    version = "1.0.0"

    async def execute(
        self,
        inp: SkillInput,
        progress_cb: ProgressCallback = None,
    ) -> SkillOutput:
        """載入資料。

        Parameters (inp.parameters):
            turbine_id: str — 風機 ID（如 "Kelmarsh_1"）
            file_path: str | None — 指定檔案路徑（可選）
        """
        turbine_id = inp.parameters.get("turbine_id", "Kelmarsh_1")
        file_path = inp.parameters.get("file_path")

        if progress_cb:
            await progress_cb(0.1, f"載入 {turbine_id} 的資料...")

        loop = asyncio.get_event_loop()

        try:
            if file_path:
                from src.data_pipeline.ingestion.smart_loader import (
                    detect_columns,
                    smart_load,
                )

                df = await loop.run_in_executor(
                    None, lambda: smart_load(Path(file_path), turbine_id=turbine_id)
                )
            else:
                # 先嘗試 Kelmarsh 專用 loader
                try:
                    from src.data_pipeline.ingestion.kelmarsh_loader import (
                        load_turbine_data,
                    )

                    df = await loop.run_in_executor(None, lambda: load_turbine_data(turbine_id))
                except (FileNotFoundError, ValueError):
                    from src.data_pipeline.ingestion.smart_loader import smart_load

                    # Fallback: 在 data/ 目錄搜尋
                    project_root = Path(__file__).resolve().parents[3]
                    found = False
                    for sub in ["raw", "external", "processed"]:
                        d = project_root / "data" / sub
                        if not d.exists():
                            continue
                        for f in d.iterdir():
                            if f.is_file() and turbine_id.lower() in f.stem.lower():
                                df = await loop.run_in_executor(
                                    None, lambda fp=f: smart_load(fp, turbine_id=turbine_id)
                                )
                                found = True
                                break
                        if found:
                            break
                    if not found:
                        return SkillOutput(
                            status=SkillStatus.ERROR,
                            errors=[f"找不到 {turbine_id} 的資料"],
                        )

            if progress_cb:
                await progress_cb(0.8, f"已載入 {len(df)} 筆資料")

            # 偵測欄位映射
            from src.data_pipeline.ingestion.smart_loader import detect_columns

            mapping = detect_columns(df)
            detected = {k: v for k, v in mapping.items() if v is not None}

            if progress_cb:
                await progress_cb(1.0, "資料載入完成")

            return SkillOutput(
                status=SkillStatus.SUCCESS,
                data={
                    "turbine_id": turbine_id,
                    "row_count": len(df),
                    "col_count": len(df.columns),
                    "columns": list(df.columns),
                    "detected_fields": detected,
                },
                summary=f"已載入 {turbine_id}：{len(df)} 筆 × {len(df.columns)} 欄",
                dataframe=df,
            )

        except Exception as e:
            return SkillOutput(
                status=SkillStatus.ERROR,
                errors=[str(e)],
                summary=f"載入失敗：{e}",
            )
