"""RUL 預測技能 — 包裝 RULModel，預測剩餘使用壽命。"""

from __future__ import annotations

import asyncio

from src.skills.base import BaseSkill, ProgressCallback, SkillInput, SkillOutput, SkillStatus


class RulPredictionSkill(BaseSkill):
    """預測風機組件的剩餘使用壽命 (Remaining Useful Life)。"""

    skill_id = "rul_prediction"
    display_name = "RUL 壽命預測"
    description = "計算健康指標、擬合退化曲線並推估剩餘使用壽命"
    version = "1.0.0"

    async def execute(
        self,
        inp: SkillInput,
        progress_cb: ProgressCallback = None,
    ) -> SkillOutput:
        df = inp.dataframe if inp.dataframe is not None else inp.data
        if df is None:
            return SkillOutput(status=SkillStatus.ERROR, errors=["未收到輸入資料"])

        if progress_cb:
            await progress_cb(0.1, "計算健康指標...")

        loop = asyncio.get_event_loop()

        try:
            from src.models.degradation.rul_model import RULModel, compute_health_index

            # Step 1: 計算健康指標
            hi_df = await loop.run_in_executor(None, lambda: compute_health_index(df))

            if progress_cb:
                await progress_cb(0.5, "擬合退化曲線...")

            # Step 2: 擬合退化模型
            rul = RULModel()
            analysis = await loop.run_in_executor(None, lambda: rul.fit(hi_df))

            if progress_cb:
                await progress_cb(1.0, "RUL 預測完成")

            return SkillOutput(
                status=SkillStatus.SUCCESS,
                data={
                    "model_type": analysis.model_type,
                    "r2_score": analysis.r_squared,
                    "trend": analysis.trend,
                    "degradation_rate": analysis.degradation_rate,
                },
                summary=(
                    f"退化模型: {analysis.model_type}, "
                    f"R²: {analysis.r_squared:.4f}, "
                    f"趨勢: {analysis.trend}"
                ),
                dataframe=df,
            )

        except Exception as e:
            return SkillOutput(status=SkillStatus.ERROR, errors=[str(e)])
