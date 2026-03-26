"""故障分類技能 — 包裝 FaultClassifier，執行多標籤故障診斷。"""

from __future__ import annotations

import asyncio

from src.skills.base import BaseSkill, ProgressCallback, SkillInput, SkillOutput, SkillStatus


class FaultClassificationSkill(BaseSkill):
    """使用 ML 模型對風機執行多標籤故障分類與嚴重度評估。"""

    skill_id = "fault_classification"
    display_name = "故障分類"
    description = "使用 RandomForest 多標籤分類器診斷風機故障類型與嚴重度"
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
            await progress_cb(0.2, "訓練故障分類器...")

        loop = asyncio.get_event_loop()

        try:
            from src.models.classification.fault_classifier import FaultClassifier

            classifier = FaultClassifier()

            # FaultClassifier.train() 回傳 TrainResult dataclass
            result = await loop.run_in_executor(None, lambda: classifier.train(df))

            if progress_cb:
                await progress_cb(1.0, "故障分類完成")

            return SkillOutput(
                status=SkillStatus.SUCCESS,
                data={
                    "f1_macro": result.f1_macro,
                    "f1_per_class": result.f1_per_class,
                    "n_train": result.n_train,
                    "n_test": result.n_test,
                    "top_features": dict(
                        sorted(result.feature_importances.items(),
                               key=lambda x: x[1], reverse=True)[:5]
                    ),
                },
                summary=f"F1 Macro: {result.f1_macro:.4f}",
                dataframe=df,
            )

        except Exception as e:
            return SkillOutput(status=SkillStatus.ERROR, errors=[str(e)])
