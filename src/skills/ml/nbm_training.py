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
                await progress_cb(0.7, "生成功率曲線視覺化資料...")

            # 生成功率曲線散佈圖資料點（實際 vs NBM 預測）
            power_curve_points = await loop.run_in_executor(
                None, lambda: self._generate_power_curve_data(nbm, df)
            )

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
                    "power_curve_points": power_curve_points,
                },
                summary=f"R²: {result.r2:.4f}, MAE: {result.mae:.1f} kW",
                dataframe=df,
            )

        except Exception as e:
            return SkillOutput(status=SkillStatus.ERROR, errors=[str(e)])

    @staticmethod
    def _generate_power_curve_data(nbm: object, df: object) -> list[dict[str, float]]:
        """生成功率曲線散佈圖資料（風速 vs 實際功率 vs 預測功率）。"""
        import numpy as np
        import pandas as pd

        from src.models.nbm.power_curve_nbm import PowerCurveNBM

        assert isinstance(nbm, PowerCurveNBM)
        assert isinstance(df, pd.DataFrame)

        if not nbm.is_fitted:
            return []

        try:
            from src.models.nbm.power_curve_nbm import _find_col

            ws_col = _find_col(df, ["wind speed", "windspeed", "ws"])
            power_col = _find_col(df, ["power", "active power"])
            if not ws_col or not power_col:
                return []

            ws = df[ws_col].astype(float)
            pwr = df[power_col].astype(float)

            # 準備預測
            features, _ = nbm._prepare_features(df)
            valid_mask = features.notna().all(axis=1)
            predicted = pd.Series(np.nan, index=df.index)
            if valid_mask.any():
                predicted[valid_mask] = nbm._model.predict(
                    features[valid_mask][nbm._feature_names].values
                )

            # 取樣最多 500 點（避免前端負擔過重）
            sample_idx = df.index
            if len(sample_idx) > 500:
                rng = np.random.default_rng(42)
                sample_idx = rng.choice(sample_idx, 500, replace=False)

            points: list[dict[str, float]] = []
            for idx in sample_idx:
                w = ws.get(idx, np.nan)
                p = pwr.get(idx, np.nan)
                pred = predicted.get(idx, np.nan)
                if pd.notna(w) and pd.notna(p):
                    pt: dict[str, float] = {
                        "wind_speed": round(float(w), 2),
                        "actual_power": round(float(p), 1),
                    }
                    if pd.notna(pred):
                        pt["predicted_power"] = round(float(pred), 1)
                    points.append(pt)

            return sorted(points, key=lambda x: x["wind_speed"])
        except Exception:
            return []
