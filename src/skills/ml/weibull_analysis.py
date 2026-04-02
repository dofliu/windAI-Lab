"""Weibull 風速分佈分析技能 — 包裝 WeibullDistributionModel。"""

from __future__ import annotations

import asyncio
from typing import Any

from src.skills.base import BaseSkill, ProgressCallback, SkillInput, SkillOutput, SkillStatus


class WeibullAnalysisSkill(BaseSkill):
    """Weibull 風速分佈擬合與年發電量估算。"""

    skill_id = "weibull_analysis"
    display_name = "Weibull 風速分佈"
    description = "使用 Weibull 分佈擬合風速資料，評估風資源與估算年發電量 (AEP)"
    version = "1.0.0"

    async def execute(
        self,
        inp: SkillInput,
        progress_cb: ProgressCallback = None,
    ) -> SkillOutput:
        """執行 Weibull 擬合與 AEP 估算。

        Parameters（透過 inp.parameters）:
            turbine_id: 風機 ID
            fit_method: 擬合方法（"mle" / "moments"），預設 "mle"
        """
        df = inp.dataframe if inp.dataframe is not None else inp.data
        if df is None:
            return SkillOutput(status=SkillStatus.ERROR, errors=["未收到輸入資料"])

        import pandas as pd

        if not isinstance(df, pd.DataFrame) or df.empty:
            return SkillOutput(status=SkillStatus.ERROR, errors=["輸入資料為空"])

        turbine_id = inp.parameters.get("turbine_id", "未知")
        fit_method = inp.parameters.get("fit_method", "mle")

        if progress_cb:
            await progress_cb(0.1, "尋找風速欄位...")

        loop = asyncio.get_event_loop()

        try:
            from src.core.constants import TurbineProfile
            from src.models.wind_distribution.weibull_model import WeibullDistributionModel

            # 找風速欄位
            ws_col = _find_wind_speed_col(df)
            if ws_col is None:
                return SkillOutput(
                    status=SkillStatus.ERROR,
                    errors=["未找到風速欄位（需包含 'wind speed' 或 'ws' 關鍵字）"],
                )

            wind_speeds = df[ws_col].dropna().values

            if progress_cb:
                await progress_cb(0.3, f"擬合 Weibull 分佈（{fit_method}）...")

            model = WeibullDistributionModel()
            fit_result = await loop.run_in_executor(
                None, lambda: model.fit(wind_speeds, method=fit_method)
            )

            if progress_cb:
                await progress_cb(0.6, "估算年發電量...")

            # 從上游取 TurbineProfile
            profile_data = inp.parameters.get("turbine_profile")
            profile = (
                TurbineProfile(**{k: v for k, v in profile_data.items() if v is not None})
                if profile_data
                else None
            )

            aep = await loop.run_in_executor(None, lambda: model.estimate_aep(profile=profile))

            if progress_cb:
                await progress_cb(0.85, "產出頻率表...")

            freq_table = model.generate_frequency_table()

            if progress_cb:
                await progress_cb(1.0, "Weibull 分析完成")

            return SkillOutput(
                status=SkillStatus.SUCCESS,
                data={
                    "turbine_id": turbine_id,
                    "shape_k": fit_result.shape_k,
                    "scale_c": fit_result.scale_c,
                    "mean_wind_speed": fit_result.mean_wind_speed,
                    "std_wind_speed": fit_result.std_wind_speed,
                    "median_wind_speed": fit_result.median_wind_speed,
                    "ks_statistic": fit_result.ks_statistic,
                    "ks_p_value": fit_result.ks_p_value,
                    "energy_density_w_m2": fit_result.energy_density_w_m2,
                    "fit_method": fit_result.fit_method,
                    "sample_count": fit_result.sample_count,
                    "aep_mwh": aep.aep_mwh,
                    "capacity_factor": aep.capacity_factor,
                    "availability_pct": aep.availability_pct,
                    "full_load_hours": aep.full_load_hours,
                    "frequency_table": freq_table[:30],
                },
                summary=(
                    f"Weibull k={fit_result.shape_k}, c={fit_result.scale_c} m/s | "
                    f"AEP={aep.aep_mwh} MWh | CF={aep.capacity_factor:.1%}"
                ),
                dataframe=df,
            )

        except Exception as e:
            return SkillOutput(
                status=SkillStatus.ERROR,
                errors=[f"Weibull 分析失敗：{e}"],
            )


def _find_wind_speed_col(df: Any) -> str | None:
    """搜尋風速欄位。"""
    keywords = ["wind speed", "windspeed", "ws"]
    for kw in keywords:
        for col in df.columns:
            if kw.lower() in col.lower():
                return col
    return None
