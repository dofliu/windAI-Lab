"""領域特徵萃取技能 — 包裝 wind_features，計算風力發電專用特徵。"""

from __future__ import annotations

import asyncio

from src.skills.base import BaseSkill, ProgressCallback, SkillInput, SkillOutput, SkillStatus


class DomainFeatureExtractionSkill(BaseSkill):
    """從清洗後的 SCADA 資料萃取風力發電領域特徵。"""

    skill_id = "domain_feature_extraction"
    display_name = "領域特徵萃取"
    description = "計算功率曲線偏差、風速比、溫度差等風力發電專用特徵"
    version = "1.0.0"

    async def execute(
        self,
        inp: SkillInput,
        progress_cb: ProgressCallback = None,
    ) -> SkillOutput:
        df = inp.dataframe if hasattr(inp, "dataframe") and inp.dataframe is not None else inp.data
        if df is None:
            return SkillOutput(status=SkillStatus.ERROR, errors=["未收到輸入資料"])

        # 從 turbine_profiler 推斷的參數
        rated_power = inp.parameters.get("rated_power", 2050.0)
        extra_params = {}
        for key in ("cut_in_speed", "cut_out_speed", "rated_wind_speed"):
            if key in inp.parameters:
                extra_params[key] = inp.parameters[key]

        if progress_cb:
            await progress_cb(0.2, f"計算領域特徵（額定 {rated_power:.0f} kW）...")

        loop = asyncio.get_event_loop()

        try:
            from src.features.domain_features.wind_features import (
                compute_power_curve_features,
            )

            df_feat = await loop.run_in_executor(
                None,
                lambda: compute_power_curve_features(df, rated_power=rated_power, **extra_params),
            )

            new_cols = [c for c in df_feat.columns if c not in df.columns]

            if progress_cb:
                await progress_cb(1.0, f"萃取 {len(new_cols)} 個新特徵")

            return SkillOutput(
                status=SkillStatus.SUCCESS,
                data={
                    "new_features": new_cols,
                    "total_features": len(df_feat.columns),
                },
                summary=f"萃取 {len(new_cols)} 個領域特徵",
                dataframe=df_feat,
            )

        except Exception as e:
            return SkillOutput(status=SkillStatus.ERROR, errors=[str(e)])
