"""跨風機比較分析技能 — 同時分析多台風機，產出對比報告。

支援：
1. 健康分數對比
2. 功率曲線效率對比
3. 故障模式分布對比
4. 風險排序與維護優先級
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.skills.base import BaseSkill, ProgressCallback, SkillInput, SkillOutput, SkillStatus
from src.utils.logger import get_logger

logger = get_logger("skill.comparative_analysis")


class ComparativeAnalysisSkill(BaseSkill):
    """跨風機比較分析 — 產出多台風機的對比報告與風險排序。"""

    skill_id = "comparative_analysis"
    display_name = "跨風機比較分析"
    description = "比較多台風機的健康狀態、效率與故障模式，產出風險排序"
    version = "1.0.0"

    async def execute(
        self,
        inp: SkillInput,
        progress_cb: ProgressCallback = None,
    ) -> SkillOutput:
        """執行跨風機比較分析。

        Parameters (inp.parameters):
            turbine_ids: list[str] — 要比較的風機 ID 列表
            folder_path: str — 或指定資料夾，自動辨識各風機
            metrics: list[str] — 比較指標（預設全部）
        """
        turbine_ids = inp.parameters.get("turbine_ids", [])
        folder_path = inp.parameters.get("folder_path", "")

        if progress_cb:
            await progress_cb(0.05, "準備比較分析...")

        # 如果指定了資料夾，嘗試從中辨識風機
        if not turbine_ids and folder_path:
            turbine_ids = self._discover_turbines_from_folder(folder_path)

        if not turbine_ids:
            return SkillOutput(
                status=SkillStatus.ERROR,
                errors=["未指定風機 ID 列表或資料夾路徑"],
            )

        if len(turbine_ids) < 2:
            return SkillOutput(
                status=SkillStatus.ERROR,
                errors=["至少需要 2 台風機才能進行比較分析"],
            )

        # 逐台分析
        turbine_reports: list[dict[str, Any]] = []
        total = len(turbine_ids)

        for i, tid in enumerate(turbine_ids):
            if progress_cb:
                await progress_cb(
                    0.1 + 0.6 * (i / total),
                    f"分析 {tid} ({i+1}/{total})...",
                )
            report = self._analyze_single_turbine(tid)
            turbine_reports.append(report)

        if progress_cb:
            await progress_cb(0.75, "計算比較指標與排序...")

        # 產出比較結果
        comparison = self._compare(turbine_reports)

        if progress_cb:
            await progress_cb(1.0, f"比較分析完成 — {total} 台風機")

        # 風險排序摘要
        risk_ranking = comparison.get("risk_ranking", [])
        top_risk = risk_ranking[0] if risk_ranking else {}
        top_risk_id = top_risk.get("turbine_id", "?")
        top_risk_score = top_risk.get("health_score", "?")

        return SkillOutput(
            status=SkillStatus.SUCCESS,
            data=comparison,
            summary=(
                f"跨風機比較完成：{total} 台 | "
                f"最高風險：{top_risk_id} (健康 {top_risk_score}/100)"
            ),
        )

    def _discover_turbines_from_folder(self, folder_path: str) -> list[str]:
        """從資料夾中辨識不同風機。"""
        from pathlib import Path

        folder = Path(folder_path)
        if not folder.exists():
            return []

        turbine_ids: set[str] = set()
        for f in folder.iterdir():
            if f.suffix in (".csv", ".parquet"):
                # 嘗試從檔名提取風機 ID（常見格式：WT-01_scada.csv）
                name = f.stem.upper()
                for prefix in ("WT-", "WT", "TURBINE-", "T"):
                    if prefix in name:
                        idx = name.index(prefix)
                        # 取 prefix + 後面的數字
                        rest = name[idx:]
                        parts = rest.split("_")[0].split("-")
                        tid = "-".join(parts[:2]) if len(parts) >= 2 else parts[0]
                        turbine_ids.add(tid)
                        break

        return sorted(turbine_ids)

    def _analyze_single_turbine(self, turbine_id: str) -> dict[str, Any]:
        """分析單台風機的關鍵指標。"""
        report: dict[str, Any] = {
            "turbine_id": turbine_id,
            "health_score": 0,
            "data_points": 0,
            "availability": 0.0,
            "capacity_factor": 0.0,
            "anomaly_rate": 0.0,
            "power_curve_deviation": 0.0,
            "temp_anomaly_count": 0,
            "status": "ok",
        }

        try:
            from src.data_pipeline.ingestion.kelmarsh_loader import load_turbine_data
            from src.models.evaluation.anomaly_analysis import generate_diagnosis_report

            df = load_turbine_data(turbine_id)
            diagnosis = generate_diagnosis_report(df, turbine_id)

            report["health_score"] = diagnosis.get("health_score", 0)
            report["data_points"] = diagnosis.get("total_records", 0)
            report["temp_anomaly_count"] = diagnosis.get("temperature_anomaly_count", 0)

            ops = diagnosis.get("operational_summary", {})
            report["availability"] = ops.get("availability", 0)
            report["capacity_factor"] = ops.get("capacity_factor", 0)

            pc = diagnosis.get("power_curve_analysis", {})
            report["power_curve_deviation"] = abs(pc.get("mean_deviation_pct", 0))

            total = max(report["data_points"], 1)
            report["anomaly_rate"] = round(report["temp_anomaly_count"] / total * 100, 2)

        except Exception as e:
            logger.warning(f"分析 {turbine_id} 失敗：{e}")
            report["status"] = "error"
            report["error"] = str(e)

        return report

    def _compare(self, reports: list[dict[str, Any]]) -> dict[str, Any]:
        """產出跨風機比較結果。"""
        valid = [r for r in reports if r["status"] == "ok"]
        failed = [r for r in reports if r["status"] != "ok"]

        if not valid:
            return {
                "risk_ranking": [],
                "summary_table": [],
                "failed_turbines": [r["turbine_id"] for r in failed],
                "fleet_health": 0,
            }

        # 風險排序（健康分數低 → 高風險）
        risk_ranking = sorted(valid, key=lambda r: r["health_score"])

        # 計算風場統計
        health_scores = [r["health_score"] for r in valid]
        avg_health = sum(health_scores) / len(health_scores)

        # 分類
        critical = [r for r in valid if r["health_score"] < 40]
        high_risk = [r for r in valid if 40 <= r["health_score"] < 60]
        medium = [r for r in valid if 60 <= r["health_score"] < 80]
        healthy = [r for r in valid if r["health_score"] >= 80]

        # 效率對比
        cf_values = [r["capacity_factor"] for r in valid if r["capacity_factor"] > 0]
        avg_cf = sum(cf_values) / len(cf_values) if cf_values else 0

        # 功率曲線偏差排序
        deviation_ranking = sorted(
            valid,
            key=lambda r: r["power_curve_deviation"],
            reverse=True,
        )

        return {
            "risk_ranking": [
                {
                    "turbine_id": r["turbine_id"],
                    "health_score": r["health_score"],
                    "anomaly_rate": r["anomaly_rate"],
                    "power_curve_deviation": r["power_curve_deviation"],
                    "risk_level": (
                        "Critical" if r["health_score"] < 40
                        else "High" if r["health_score"] < 60
                        else "Medium" if r["health_score"] < 80
                        else "Low"
                    ),
                }
                for r in risk_ranking
            ],
            "fleet_summary": {
                "total_turbines": len(reports),
                "analyzed_ok": len(valid),
                "failed": len(failed),
                "avg_health_score": round(avg_health, 1),
                "avg_capacity_factor": round(avg_cf, 2),
                "critical_count": len(critical),
                "high_risk_count": len(high_risk),
                "medium_count": len(medium),
                "healthy_count": len(healthy),
            },
            "efficiency_ranking": [
                {
                    "turbine_id": r["turbine_id"],
                    "capacity_factor": r["capacity_factor"],
                    "power_curve_deviation": r["power_curve_deviation"],
                }
                for r in deviation_ranking
            ],
            "failed_turbines": [
                {"turbine_id": r["turbine_id"], "error": r.get("error", "")}
                for r in failed
            ],
        }
