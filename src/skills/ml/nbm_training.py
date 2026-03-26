"""NBM 功率曲線訓練技能 — 包裝 PowerCurveNBM，建立正常行為模型。"""

from __future__ import annotations

import asyncio

from src.skills.base import BaseSkill, ProgressCallback, SkillInput, SkillOutput, SkillStatus


class NbmTrainingSkill(BaseSkill):
    """訓練 Normal Behavior Model (NBM) 用於功率曲線異常偵測。"""

    skill_id = "nbm_training"
    display_name = "NBM 功率曲線訓練"
    description = "以 GBR 回歸訓練風速-功率正常行為模型，計算殘差用於異常偵測"
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
            await progress_cb(0.2, "訓練 NBM 模型...")

        loop = asyncio.get_event_loop()

        try:
            from src.models.nbm.power_curve_nbm import PowerCurveNBM

            nbm = PowerCurveNBM()

            # PowerCurveNBM.train() 回傳 NBMResult dataclass
            result = await loop.run_in_executor(None, lambda: nbm.train(df))

            if progress_cb:
                await progress_cb(1.0, "NBM 訓練完成")

            return SkillOutput(
                status=SkillStatus.SUCCESS,
                data={
                    "r2_score": result.r2,
                    "mae": result.mae,
                    "rmse": result.rmse,
                    "model_type": "PowerCurveNBM (GBR)",
                    "train_samples": result.n_train,
                    "test_samples": result.n_test,
                },
                summary=f"R²: {result.r2:.4f}, MAE: {result.mae:.1f} kW",
                dataframe=df,
            )

        except Exception as e:
            return SkillOutput(status=SkillStatus.ERROR, errors=[str(e)])
