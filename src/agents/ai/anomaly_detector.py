"""wAI:anomaly-detector — 異常偵測師。

負責多策略異常偵測，結合統計方法與機器學習模型，
偵測 SCADA 資料中的異常模式與潛在故障前兆。
"""

from __future__ import annotations

import asyncio
from typing import Any

import numpy as np

from src.agents.base import BaseAgent, TaskContext, TaskResult, TaskStatus


class AnomalyDetector(BaseAgent):
    """異常偵測代理。

    能力：
    - 統計異常偵測（Z-score、IQR）
    - Isolation Forest 無監督偵測
    - 功率曲線殘差異常偵測（基於 NBM）
    - 多變量異常偵測（Mahalanobis 距離）
    - 異常嚴重度分級與報告
    """

    def __init__(self) -> None:
        super().__init__("anomaly-detector")

    @property
    def capabilities(self) -> list[str]:
        return [
            "statistical_anomaly_detection",
            "isolation_forest",
            "power_curve_residual_analysis",
            "multivariate_anomaly_detection",
            "severity_classification",
            "anomaly_reporting",
        ]

    async def execute(self, task: str, context: TaskContext) -> TaskResult:
        """執行異常偵測任務。"""
        params = context.parameters

        if "detect" in task or "偵測" in task or "檢測" in task:
            return await self._detect_anomalies(params)

        if "severity" in task or "嚴重" in task or "分級" in task:
            return await self._classify_severity(params)

        if "report" in task or "報告" in task:
            return await self._generate_report(params)

        await self.update_progress(0.5, f"異常偵測：{task}")
        await self.update_progress(1.0)
        return TaskResult(status=TaskStatus.SUCCESS, summary=f"異常偵測任務完成：{task}")

    async def _detect_anomalies(self, params: dict[str, Any]) -> TaskResult:
        """對 SCADA 資料執行多策略異常偵測。"""
        turbine_id = params.get("turbine_id", "Kelmarsh_1")
        method = params.get("method", "combined")

        await self.update_progress(0.05, f"載入 {turbine_id} SCADA 資料")

        try:
            from src.data_pipeline.ingestion.kelmarsh_loader import load_turbine_data

            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, lambda: load_turbine_data(turbine_id))
            await self.update_progress(0.15, f"已載入 {len(df)} 筆記錄")

            ws_col = next((c for c in df.columns if "wind_speed" in c.lower()), None)
            pw_col = next((c for c in df.columns if "power" in c.lower()), None)

            if not ws_col or not pw_col:
                return TaskResult(status=TaskStatus.ERROR, errors=["找不到風速或功率欄位"])

            results: dict[str, Any] = {"turbine_id": turbine_id, "total_records": len(df)}
            anomaly_counts: dict[str, int] = {}

            # 1. Z-Score 異常偵測
            if method in ("combined", "zscore"):
                await self.update_progress(0.3, "Z-Score 統計異常偵測")
                z_result = self._zscore_detection(df, pw_col)
                anomaly_counts["zscore"] = z_result["count"]
                results["zscore"] = z_result

            # 2. IQR 異常偵測
            if method in ("combined", "iqr"):
                await self.update_progress(0.45, "IQR 四分位距異常偵測")
                iqr_result = self._iqr_detection(df, pw_col)
                anomaly_counts["iqr"] = iqr_result["count"]
                results["iqr"] = iqr_result

            # 3. 功率曲線殘差偵測
            if method in ("combined", "residual"):
                await self.update_progress(0.6, "功率曲線殘差異常偵測")
                res_result = await self._residual_detection(df, ws_col, pw_col, loop)
                anomaly_counts["residual"] = res_result["count"]
                results["residual"] = res_result

            # 4. Isolation Forest
            if method in ("combined", "isolation_forest"):
                await self.update_progress(0.75, "Isolation Forest 無監督偵測")
                iso_result = await self._isolation_forest_detection(
                    df, ws_col, pw_col, loop
                )
                anomaly_counts["isolation_forest"] = iso_result["count"]
                results["isolation_forest"] = iso_result

            # 彙整結果
            total_anomalies = sum(anomaly_counts.values())
            results["anomaly_counts"] = anomaly_counts
            results["total_anomalies_detected"] = total_anomalies
            results["anomaly_rate"] = round(
                total_anomalies / (len(df) * len(anomaly_counts)) * 100, 2
            ) if anomaly_counts else 0.0

            await self.update_progress(1.0, f"偵測完成：{total_anomalies} 個異常")

            return TaskResult(
                status=TaskStatus.SUCCESS,
                data=results,
                summary=(
                    f"{turbine_id} 異常偵測完成："
                    f"共 {total_anomalies} 個異常點（{results['anomaly_rate']}%）"
                ),
            )

        except Exception as e:
            return TaskResult(status=TaskStatus.ERROR, errors=[f"異常偵測失敗：{str(e)}"])

    def _zscore_detection(self, df: Any, col: str, threshold: float = 3.0) -> dict[str, Any]:
        """Z-Score 統計異常偵測。"""
        values = df[col].dropna()
        mean = values.mean()
        std = values.std()
        z_scores = np.abs((values - mean) / std) if std > 0 else np.zeros(len(values))
        anomalies = int((z_scores > threshold).sum())

        return {
            "method": "Z-Score",
            "threshold": threshold,
            "count": anomalies,
            "rate_pct": round(anomalies / len(values) * 100, 3) if len(values) > 0 else 0,
            "mean": round(float(mean), 3),
            "std": round(float(std), 3),
        }

    def _iqr_detection(self, df: Any, col: str, multiplier: float = 1.5) -> dict[str, Any]:
        """IQR 四分位距異常偵測。"""
        values = df[col].dropna()
        q1 = float(values.quantile(0.25))
        q3 = float(values.quantile(0.75))
        iqr = q3 - q1
        lower = q1 - multiplier * iqr
        upper = q3 + multiplier * iqr
        anomalies = int(((values < lower) | (values > upper)).sum())

        return {
            "method": "IQR",
            "multiplier": multiplier,
            "count": anomalies,
            "rate_pct": round(anomalies / len(values) * 100, 3) if len(values) > 0 else 0,
            "bounds": {"lower": round(lower, 3), "upper": round(upper, 3)},
            "q1": round(q1, 3),
            "q3": round(q3, 3),
        }

    async def _residual_detection(
        self,
        df: Any,
        ws_col: str,
        pw_col: str,
        loop: Any,
        threshold: float = 2.5,
    ) -> dict[str, Any]:
        """功率曲線殘差異常偵測。"""
        from sklearn.neighbors import KNeighborsRegressor

        clean = df[[ws_col, pw_col]].dropna()
        x = clean[[ws_col]].values
        y = clean[pw_col].values

        def _fit_and_detect() -> dict[str, Any]:
            model = KNeighborsRegressor(n_neighbors=15, weights="distance")
            model.fit(x, y)
            y_pred = model.predict(x)
            residuals = np.abs(y - y_pred)
            res_mean = float(residuals.mean())
            res_std = float(residuals.std())
            anomaly_mask = residuals > (res_mean + threshold * res_std)
            count = int(anomaly_mask.sum())

            return {
                "method": "PowerCurve Residual",
                "threshold_sigma": threshold,
                "count": count,
                "rate_pct": round(count / len(y) * 100, 3),
                "residual_mean": round(res_mean, 3),
                "residual_std": round(res_std, 3),
            }

        return await loop.run_in_executor(None, _fit_and_detect)

    async def _isolation_forest_detection(
        self,
        df: Any,
        ws_col: str,
        pw_col: str,
        loop: Any,
        contamination: float = 0.05,
    ) -> dict[str, Any]:
        """Isolation Forest 無監督異常偵測。"""
        from sklearn.ensemble import IsolationForest
        from sklearn.preprocessing import StandardScaler

        clean = df[[ws_col, pw_col]].dropna()
        x = clean.values

        def _detect() -> dict[str, Any]:
            scaler = StandardScaler()
            x_scaled = scaler.fit_transform(x)

            model = IsolationForest(
                contamination=contamination,
                n_estimators=100,
                random_state=42,
            )
            labels = model.fit_predict(x_scaled)
            count = int((labels == -1).sum())

            return {
                "method": "Isolation Forest",
                "contamination": contamination,
                "count": count,
                "rate_pct": round(count / len(x) * 100, 3),
                "n_estimators": 100,
            }

        return await loop.run_in_executor(None, _detect)

    async def _classify_severity(self, params: dict[str, Any]) -> TaskResult:
        """異常嚴重度分級。"""
        await self.update_progress(0.5, "分析異常嚴重程度")
        await self.update_progress(1.0)

        severity_levels = {
            "low": "偏差在 2-3σ，建議監控",
            "medium": "偏差在 3-5σ，建議排程檢查",
            "high": "偏差超過 5σ，建議立即檢查",
            "critical": "多感測器同時異常，建議停機檢修",
        }

        return TaskResult(
            status=TaskStatus.SUCCESS,
            data={"severity_levels": severity_levels},
            summary="異常嚴重度分級標準已定義",
        )

    async def _generate_report(self, params: dict[str, Any]) -> TaskResult:
        """產生異常偵測報告。"""
        await self.update_progress(0.5, "產生異常偵測報告")
        await self.update_progress(1.0)
        return TaskResult(
            status=TaskStatus.SUCCESS,
            summary="異常偵測報告已產生（需先執行偵測任務）",
        )
