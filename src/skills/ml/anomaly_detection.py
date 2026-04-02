"""統計異常偵測技能 — 包裝 anomaly_analysis 模組為可重用技能。

偵測策略：
1. Z-score 溫度異常偵測（溫度-功率正常行為模型）
2. 功率曲線偏差分析（分箱比較法）
3. 綜合健康分數計算
"""

from __future__ import annotations

import asyncio

from src.skills.base import BaseSkill, ProgressCallback, SkillInput, SkillOutput, SkillStatus


class AnomalyDetectionSkill(BaseSkill):
    """統計異常偵測技能，整合溫度異常、功率曲線偏差與健康分數。"""

    skill_id = "anomaly_detection"
    display_name = "統計異常偵測"
    description = "使用 Z-score / 分箱比較法偵測風機溫度與功率曲線異常，計算健康分數"
    version = "1.0.0"

    async def execute(
        self,
        inp: SkillInput,
        progress_cb: ProgressCallback = None,
    ) -> SkillOutput:
        """執行多維度異常偵測。

        Parameters（透過 inp.parameters）:
            threshold_std: Z-score 門檻（預設 3.0）
            turbine_id: 風機 ID（報告用）

        Returns:
            包含溫度異常、功率曲線偏差、健康分數的完整結果。
        """
        df = inp.dataframe if inp.dataframe is not None else inp.data
        if df is None:
            return SkillOutput(status=SkillStatus.ERROR, errors=["未收到輸入資料"])

        import pandas as pd

        if not isinstance(df, pd.DataFrame) or df.empty:
            return SkillOutput(status=SkillStatus.ERROR, errors=["輸入資料為空或格式不正確"])

        threshold_std = inp.parameters.get("threshold_std", 3.0)
        turbine_id = inp.parameters.get("turbine_id", "未知")

        if progress_cb:
            await progress_cb(0.05, "開始異常偵測分析...")

        loop = asyncio.get_event_loop()

        try:
            from src.core.constants import TurbineProfile
            from src.models.evaluation.anomaly_analysis import (
                compute_health_score,
                detect_power_curve_anomalies,
                detect_temperature_anomalies,
            )

            # 從上游 turbine_profiler 取得風機參數
            profile_data = inp.parameters.get("turbine_profile")
            profile = (
                TurbineProfile(**{k: v for k, v in profile_data.items() if v is not None})
                if profile_data
                else None
            )

            # ── 1. 溫度異常偵測 ──
            if progress_cb:
                await progress_cb(0.15, "偵測溫度異常（Z-score 方法）...")

            temp_result = await loop.run_in_executor(
                None, lambda: detect_temperature_anomalies(df, threshold_std=threshold_std)
            )

            # ── 2. 功率曲線偏差分析 ──
            if progress_cb:
                await progress_cb(0.45, "分析功率曲線偏差...")

            pc_result = await loop.run_in_executor(
                None, lambda: detect_power_curve_anomalies(df, profile=profile)
            )

            # ── 3. 健康分數計算 ──
            if progress_cb:
                await progress_cb(0.75, "計算綜合健康分數...")

            health_result = await loop.run_in_executor(
                None, lambda: compute_health_score(df, profile=profile)
            )

            if progress_cb:
                await progress_cb(1.0, "異常偵測完成")

            # 組裝結果
            anomaly_count = temp_result["anomaly_count"]
            health_score = health_result["health_score"]
            efficiency_loss = pc_result["efficiency_loss_pct"]

            # 摘要文字
            summary_parts = [
                f"風機 {turbine_id} 健康分數: {health_score}/100",
            ]
            if anomaly_count > 0:
                summary_parts.append(f"溫度異常 {anomaly_count} 筆")
            if abs(pc_result["mean_deviation_pct"]) > 5:
                summary_parts.append(f"功率曲線偏差 {pc_result['mean_deviation_pct']:.1f}%")
            if efficiency_loss > 3:
                summary_parts.append(f"效率損失 {efficiency_loss:.1f}%")

            return SkillOutput(
                status=SkillStatus.SUCCESS,
                data={
                    "turbine_id": turbine_id,
                    "health_score": health_score,
                    "health_details": health_result,
                    "temperature_anomaly_count": anomaly_count,
                    "temperature_anomalies": temp_result["anomalies"][:20],
                    "components_checked": temp_result["components_checked"],
                    "power_curve_deviation_pct": pc_result["mean_deviation_pct"],
                    "worst_wind_speed_bin": pc_result["worst_wind_speed_bin"],
                    "efficiency_loss_pct": efficiency_loss,
                    "bin_analysis": pc_result["bin_analysis"][:15],
                },
                summary=" | ".join(summary_parts),
                dataframe=df,
            )

        except Exception as e:
            return SkillOutput(
                status=SkillStatus.ERROR,
                errors=[f"異常偵測失敗：{e}"],
            )
