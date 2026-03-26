"""SCADA 資料清洗技能 — 包裝 scada_cleaner，執行去重、插值、異常過濾。"""

from __future__ import annotations

import asyncio

from src.skills.base import BaseSkill, ProgressCallback, SkillInput, SkillOutput, SkillStatus


class ScadaCleaningSkill(BaseSkill):
    """自動清洗 SCADA 資料：去重、缺失值處理、異常值過濾、品質報告。"""

    skill_id = "scada_cleaning"
    display_name = "SCADA 資料清洗"
    description = "執行去重、小間隙插值、異常值過濾，產出資料品質報告"
    version = "1.0.0"

    async def execute(
        self,
        inp: SkillInput,
        progress_cb: ProgressCallback = None,
    ) -> SkillOutput:
        """清洗資料。

        Parameters (inp.parameters):
            rated_power: float — 額定功率 kW（預設 2050）
        Input (inp.dataframe or inp.data):
            上游傳入的 DataFrame
        """
        df = inp.dataframe if hasattr(inp, "dataframe") and inp.dataframe is not None else inp.data
        if df is None:
            return SkillOutput(status=SkillStatus.ERROR, errors=["未收到輸入資料"])

        # 從 turbine_profiler 推斷的參數自動注入（若無則用全域預設值）
        from src.core.constants import TurbineProfile

        _defaults = TurbineProfile()
        rated_power = inp.parameters.get("rated_power", _defaults.rated_power_kw)
        cut_in = inp.parameters.get("cut_in_speed", _defaults.cut_in_speed_ms)
        cut_out = inp.parameters.get("cut_out_speed", _defaults.cut_out_speed_ms)

        if progress_cb:
            await progress_cb(0.1, f"開始清洗（額定 {rated_power:.0f} kW）...")

        loop = asyncio.get_event_loop()

        try:
            from src.data_pipeline.cleaning.scada_cleaner import clean_scada_data

            df_clean, quality_report = await loop.run_in_executor(
                None,
                lambda: clean_scada_data(
                    df,
                    rated_power=rated_power,
                    cut_in_speed=cut_in,
                    cut_out_speed=cut_out,
                ),
            )

            if progress_cb:
                await progress_cb(1.0, "清洗完成")

            return SkillOutput(
                status=SkillStatus.SUCCESS,
                data={
                    "quality_report": quality_report,
                    "rows_before": quality_report.get("total_rows", len(df)),
                    "rows_after": len(df_clean),
                    "missing_pct": quality_report.get("missing_pct", 0),
                },
                summary=(
                    f"清洗完成：{len(df)} → {len(df_clean)} 筆，"
                    f"缺失率 {quality_report.get('missing_pct', 0):.1f}%"
                ),
                dataframe=df_clean,
            )

        except Exception as e:
            return SkillOutput(status=SkillStatus.ERROR, errors=[str(e)])
