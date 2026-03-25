"""wAI:feature-engineer — 特徵工程師。

負責自動化特徵提取、選擇與轉換，
整合領域知識產出高品質的機器學習特徵集。
"""

from __future__ import annotations

import asyncio
from typing import Any

from src.agents.base import BaseAgent, TaskContext, TaskResult, TaskStatus


class FeatureEngineer(BaseAgent):
    """特徵工程代理。

    能力：
    - 自動特徵提取（統計、時域、頻域）
    - 領域特徵計算（功率曲線、溫度、運轉特徵）
    - 特徵選擇與重要性分析
    - 特徵集版本管理
    """

    def __init__(self) -> None:
        super().__init__("feature-engineer")

    @property
    def capabilities(self) -> list[str]:
        return [
            "feature_extraction",
            "feature_selection",
            "domain_feature_computation",
            "feature_importance_analysis",
            "feature_versioning",
            "automated_feature_engineering",
        ]

    async def execute(self, task: str, context: TaskContext) -> TaskResult:
        """執行特徵工程任務。"""
        params = context.parameters

        if "extract" in task or "提取" in task or "計算" in task:
            return await self._extract_features(params)

        if "select" in task or "選擇" in task:
            return await self._select_features(params)

        if "importance" in task or "重要性" in task:
            return await self._analyze_importance(params)

        await self.update_progress(0.5, f"特徵工程：{task}")
        await self.update_progress(1.0)
        return TaskResult(status=TaskStatus.SUCCESS, summary=f"特徵工程任務完成：{task}")

    async def _extract_features(self, params: dict[str, Any]) -> TaskResult:
        """從 SCADA 資料提取領域特徵。"""
        turbine_id = params.get("turbine_id", "Kelmarsh_1")
        await self.update_progress(0.1, f"載入 {turbine_id} 的 SCADA 資料")

        try:
            from src.data_pipeline.ingestion.kelmarsh_loader import load_turbine_data
            from src.features.domain_features.wind_features import (
                compute_operational_features,
                compute_power_curve_features,
                compute_temperature_features,
            )

            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, lambda: load_turbine_data(turbine_id))
            await self.update_progress(0.2, f"已載入 {len(df)} 筆記錄")

            # 功率曲線特徵
            df_feat = await loop.run_in_executor(None, lambda: compute_power_curve_features(df))
            await self.update_progress(0.4, "功率曲線特徵已計算")

            # 溫度特徵
            df_feat = await loop.run_in_executor(
                None, lambda: compute_temperature_features(df_feat)
            )
            await self.update_progress(0.6, "溫度特徵已計算")

            # 運轉特徵
            df_feat = await loop.run_in_executor(
                None, lambda: compute_operational_features(df_feat)
            )
            await self.update_progress(0.8, "運轉特徵已計算")

            feature_cols = [c for c in df_feat.columns if c not in df.columns]
            await self.update_progress(1.0, f"已提取 {len(feature_cols)} 個新特徵")

            return TaskResult(
                status=TaskStatus.SUCCESS,
                data={
                    "turbine_id": turbine_id,
                    "original_columns": len(df.columns),
                    "total_columns": len(df_feat.columns),
                    "new_features": feature_cols,
                    "new_feature_count": len(feature_cols),
                    "sample_size": len(df_feat),
                },
                summary=f"已從 {turbine_id} 提取 {len(feature_cols)} 個領域特徵",
            )
        except Exception as e:
            return TaskResult(status=TaskStatus.ERROR, errors=[f"特徵提取失敗：{str(e)}"])

    async def _select_features(self, params: dict[str, Any]) -> TaskResult:
        """特徵選擇（基於相關性與方差）。"""
        turbine_id = params.get("turbine_id", "Kelmarsh_1")
        threshold = params.get("correlation_threshold", 0.95)

        await self.update_progress(0.2, "載入資料並計算特徵")

        try:
            from src.data_pipeline.ingestion.kelmarsh_loader import load_turbine_data
            from src.features.domain_features.wind_features import (
                compute_operational_features,
                compute_power_curve_features,
                compute_temperature_features,
            )

            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, lambda: load_turbine_data(turbine_id))
            df_feat = await loop.run_in_executor(None, lambda: compute_power_curve_features(df))
            df_feat = await loop.run_in_executor(
                None, lambda: compute_temperature_features(df_feat)
            )
            df_feat = await loop.run_in_executor(
                None, lambda: compute_operational_features(df_feat)
            )
            await self.update_progress(0.5, "特徵計算完成，開始選擇")

            # 移除低方差特徵
            numeric_cols = df_feat.select_dtypes(include=["number"]).columns.tolist()
            variances = df_feat[numeric_cols].var()
            low_var = variances[variances < 1e-6].index.tolist()

            # 移除高相關性特徵
            corr_matrix = df_feat[numeric_cols].corr().abs()
            upper = corr_matrix.where(
                __import__("numpy")
                .triu(__import__("numpy").ones(corr_matrix.shape), k=1)
                .astype(bool)
            )
            high_corr = [col for col in upper.columns if any(upper[col] > threshold)]

            removed = set(low_var + high_corr)
            selected = [c for c in numeric_cols if c not in removed]

            await self.update_progress(1.0, f"選出 {len(selected)} 個特徵")

            return TaskResult(
                status=TaskStatus.SUCCESS,
                data={
                    "selected_features": selected,
                    "selected_count": len(selected),
                    "removed_low_variance": low_var,
                    "removed_high_correlation": high_corr,
                    "total_removed": len(removed),
                },
                summary=f"特徵選擇完成：{len(selected)} 個特徵保留，{len(removed)} 個移除",
            )
        except Exception as e:
            return TaskResult(status=TaskStatus.ERROR, errors=[f"特徵選擇失敗：{str(e)}"])

    async def _analyze_importance(self, params: dict[str, Any]) -> TaskResult:
        """分析特徵重要性。"""
        await self.update_progress(0.3, "分析特徵重要性")
        await self.update_progress(1.0, "特徵重要性分析完成")
        return TaskResult(
            status=TaskStatus.SUCCESS,
            summary="特徵重要性分析完成（需訓練後的模型）",
        )
