"""風場級別批次掃描與風險排序服務。

對整個風場的多台風機進行批次異常偵測，計算各機組的 anomaly rate，
並結合 LLM 推理產出維護優先順序排名。

對應 WindGuard AI Kaggle 專案的「跨風機風險排序」能力。
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from src.utils.logger import get_logger

logger = get_logger("service.fleet_scanner")


# ── 單台風機掃描結果 ──────────────────────────────────────────


def _scan_single_turbine(
    turbine_id: str,
    loader: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """掃描單台風機，回傳異常摘要。

    Args:
        turbine_id: 風機 ID。
        loader: 資料載入函式，接受 turbine_id 回傳 DataFrame。
            若為 None，使用預設的 kelmarsh_loader。

    Returns:
        單台風機的掃描結果。
    """
    try:
        if loader is None:
            from src.data_pipeline.ingestion.kelmarsh_loader import load_turbine_data

            loader = load_turbine_data

        df = loader(turbine_id)

        from src.data_pipeline.cleaning.scada_cleaner import clean_scada_data
        from src.features.domain_features.wind_features import (
            compute_operational_features,
            compute_power_curve_features,
            compute_temperature_features,
        )
        from src.models.evaluation.anomaly_analysis import generate_diagnosis_report

        df_clean, quality = clean_scada_data(df)
        df_feat = compute_power_curve_features(df_clean)
        df_feat = compute_temperature_features(df_feat)
        df_feat = compute_operational_features(df_feat)

        report = generate_diagnosis_report(df_feat, turbine_id)

        total = report.get("total_records", 1)
        temp_anomaly_count = report.get("temperature_anomaly_count", 0)
        pc = report.get("power_curve_analysis", {})

        return {
            "turbine_id": turbine_id,
            "status": "success",
            "total_records": total,
            "anomaly_count": temp_anomaly_count,
            "anomaly_rate_pct": round(temp_anomaly_count / max(total, 1) * 100, 2),
            "health_score": report.get("health_score", 0),
            "power_deviation_pct": pc.get("mean_deviation_pct", 0),
            "efficiency_loss_pct": pc.get("efficiency_loss_pct", 0),
            "availability_pct": report.get("operational_summary", {}).get(
                "availability", 0
            ),
            "warnings_count": len(report.get("warnings", [])),
            "warnings": report.get("warnings", []),
        }

    except Exception as e:
        logger.error(f"風機 {turbine_id} 掃描失敗：{e}")
        return {
            "turbine_id": turbine_id,
            "status": "error",
            "error": str(e),
            "health_score": 0,
            "anomaly_rate_pct": 0,
        }


class FleetScanner:
    """風場級別批次掃描器。

    掃描風場內所有風機，產出風險排序與維護優先順序建議。
    """

    def __init__(self, max_workers: int = 4) -> None:
        self._max_workers = max_workers

    def scan_fleet(
        self,
        turbine_ids: list[str],
        loader: Callable[..., Any] | None = None,
        progress_cb: Callable[[float, str], None] | None = None,
    ) -> dict[str, Any]:
        """批次掃描多台風機。

        Args:
            turbine_ids: 風機 ID 列表。
            loader: 自訂資料載入函式。
            progress_cb: 進度回呼 (pct, msg)。

        Returns:
            包含所有風機掃描結果與風險排序的字典。
        """
        logger.info(f"開始風場掃描：{len(turbine_ids)} 台風機")
        results: list[dict[str, Any]] = []
        completed = 0
        total = len(turbine_ids)

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = {
                executor.submit(_scan_single_turbine, tid, loader): tid
                for tid in turbine_ids
            }

            for future in as_completed(futures):
                tid = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append({
                        "turbine_id": tid,
                        "status": "error",
                        "error": str(e),
                        "health_score": 0,
                        "anomaly_rate_pct": 0,
                    })

                completed += 1
                if progress_cb:
                    pct = completed / total
                    progress_cb(pct, f"已掃描 {completed}/{total} 台風機")

        # 風險排序：依健康分數由低到高（低分 = 高風險）
        successful = [r for r in results if r.get("status") == "success"]
        failed = [r for r in results if r.get("status") != "success"]

        risk_ranking = sorted(
            successful,
            key=lambda x: x.get("health_score", 100),
        )

        # 分類風險等級
        for r in risk_ranking:
            hs = r.get("health_score", 0)
            if hs < 50:
                r["risk_level"] = "Critical"
            elif hs < 70:
                r["risk_level"] = "High"
            elif hs < 85:
                r["risk_level"] = "Medium"
            else:
                r["risk_level"] = "Low"

        # 統計摘要
        health_scores = [r.get("health_score", 0) for r in successful]
        anomaly_rates = [r.get("anomaly_rate_pct", 0) for r in successful]

        fleet_summary = {
            "total_turbines": total,
            "scanned_ok": len(successful),
            "scan_failed": len(failed),
            "avg_health_score": round(
                sum(health_scores) / max(len(health_scores), 1), 1
            ),
            "min_health_score": min(health_scores) if health_scores else 0,
            "max_health_score": max(health_scores) if health_scores else 0,
            "avg_anomaly_rate_pct": round(
                sum(anomaly_rates) / max(len(anomaly_rates), 1), 2
            ),
            "critical_count": sum(
                1 for r in risk_ranking if r.get("risk_level") == "Critical"
            ),
            "high_count": sum(
                1 for r in risk_ranking if r.get("risk_level") == "High"
            ),
        }

        logger.info(
            f"風場掃描完成：{fleet_summary['scanned_ok']}/{total} 台成功, "
            f"平均健康分數 {fleet_summary['avg_health_score']}"
        )

        return {
            "fleet_summary": fleet_summary,
            "risk_ranking": risk_ranking,
            "failed_scans": failed,
        }

    def scan_and_reason(
        self,
        turbine_ids: list[str],
        loader: Callable[..., Any] | None = None,
        progress_cb: Callable[[float, str], None] | None = None,
    ) -> dict[str, Any]:
        """批次掃描 + LLM 推理：掃描所有風機後交由 LLM 做風場級別決策。

        Args:
            turbine_ids: 風機 ID 列表。
            loader: 自訂資料載入函式。
            progress_cb: 進度回呼。

        Returns:
            包含掃描結果與 LLM 分析的完整報告。
        """
        # Step 1: 批次掃描
        scan_results = self.scan_fleet(turbine_ids, loader, progress_cb)

        # Step 2: LLM 分析
        from src.services.windguard_diagnosis import WindGuardDiagnosis

        windguard = WindGuardDiagnosis()
        ranking = scan_results.get("risk_ranking", [])

        if not ranking:
            scan_results["llm_analysis"] = {"note": "無成功掃描的風機，無法進行 LLM 分析"}
            return scan_results

        # 組裝給 LLM 的分析摘要
        summary_table = "| 排名 | 風機 | 健康分數 | 異常率 | 功率偏差 | 效率損失 | 風險等級 |\n"
        summary_table += "|------|------|----------|--------|----------|----------|----------|\n"

        for i, r in enumerate(ranking, 1):
            summary_table += (
                f"| {i} | {r['turbine_id']} | {r.get('health_score', '?')}/100 "
                f"| {r.get('anomaly_rate_pct', '?')}% "
                f"| {r.get('power_deviation_pct', '?')}% "
                f"| {r.get('efficiency_loss_pct', '?')}% "
                f"| {r.get('risk_level', '?')} |\n"
            )

        task = (
            f"以下是風場 {len(ranking)} 台風機的健康狀態掃描結果：\n\n"
            f"{summary_table}\n\n"
            f"請分析整個風場的健康狀態，給出：\n"
            f"1. 需要立即關注的風機及原因\n"
            f"2. 建議的維護排程（考慮天氣窗口與維護船排班）\n"
            f"3. 維護資源分配建議\n"
            f"4. 風場整體風險評估"
        )

        try:
            llm_analysis = windguard.llm.generate(
                prompt=task,
                system_instruction=(
                    "你是離岸風場運維總監，負責管理維護資源與排程。"
                    "請用繁體中文回覆，並以結構化 JSON 格式輸出。"
                ),
                temperature=0.3,
                max_tokens=4096,
            )
            scan_results["llm_analysis"] = windguard._parse_llm_response(llm_analysis)
            scan_results["llm_analysis_raw"] = llm_analysis
        except Exception as e:
            logger.error(f"LLM 風場分析失敗：{e}")
            scan_results["llm_analysis"] = {"error": str(e)}

        return scan_results
