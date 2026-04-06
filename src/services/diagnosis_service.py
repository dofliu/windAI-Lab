"""風機故障診斷服務。

封裝故障診斷業務邏輯，串接資料清洗、特徵工程與異常分析模組，
提供統一的診斷 API 供 REST 端點與工作流程呼叫。

支援兩種模式：
- 基礎模式：統計 + ML 分析（run_full_diagnosis）
- WindGuard 模式：統計 + ML + LLM 深層推理（run_windguard_diagnosis）
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.data_pipeline.cleaning.scada_cleaner import clean_scada_data

if TYPE_CHECKING:
    import pandas as pd

from src.features.domain_features.wind_features import (
    compute_operational_features,
    compute_power_curve_features,
    compute_temperature_features,
)
from src.models.evaluation.anomaly_analysis import generate_diagnosis_report
from src.utils.logger import get_logger

logger = get_logger("services.diagnosis")


def run_full_diagnosis(
    df: pd.DataFrame,
    turbine_id: str,
    rated_power: float = 2050.0,
) -> dict[str, Any]:
    """執行完整的風機故障診斷流程。

    依序執行資料清洗、特徵工程、異常偵測，最終產出診斷報告。

    Args:
        df: 原始 SCADA 資料（時間戳記為索引）。
        turbine_id: 風機 ID。
        rated_power: 額定功率 (kW)，預設 2050。

    Returns:
        包含品質報告與診斷報告的字典。
    """
    logger.info(f"開始對 {turbine_id} 執行完整故障診斷...")

    # 步驟 1：資料清洗
    logger.info("步驟 1/4：資料清洗")
    df_clean, quality_report = clean_scada_data(df, rated_power=rated_power)

    # 步驟 2：功率曲線特徵
    logger.info("步驟 2/4：計算功率曲線特徵")
    df_feat = compute_power_curve_features(df_clean, rated_power=rated_power)

    # 步驟 3：溫度特徵
    logger.info("步驟 3/4：計算溫度特徵")
    df_feat = compute_temperature_features(df_feat)

    # 步驟 4：運行狀態特徵
    logger.info("步驟 4/4：計算運行特徵並生成報告")
    df_feat = compute_operational_features(df_feat)

    # 生成診斷報告
    diagnosis_report = generate_diagnosis_report(df_feat, turbine_id)
    diagnosis_report["quality_report"] = quality_report

    logger.info(f"{turbine_id} 診斷完成 — 健康分數：{diagnosis_report.get('health_score', 'N/A')}")

    return diagnosis_report


def run_windguard_diagnosis(
    df: pd.DataFrame,
    turbine_id: str,
    rated_power: float = 2050.0,
    enable_rag: bool = True,
) -> dict[str, Any]:
    """執行 WindGuard AI 增強診斷（統計 + ML + LLM 推理）。

    在基礎診斷的結果之上，加入 LLM 深層推理，產出：
    - 具體故障類型（非泛用分類）
    - 物理機制說明
    - 嚴重度評估與置信度
    - 具體維護行動建議

    Args:
        df: 原始 SCADA 資料。
        turbine_id: 風機 ID。
        rated_power: 額定功率 (kW)。
        enable_rag: 是否從 RAG 知識庫檢索相關案例輔助推理。

    Returns:
        包含基礎診斷 + LLM 推理結果的完整報告。
    """
    # Step 1: 執行基礎統計/ML 診斷
    base_report = run_full_diagnosis(df, turbine_id, rated_power)

    # Step 2: 嘗試從 RAG 檢索相關案例
    rag_contexts: list[dict[str, Any]] | None = None
    if enable_rag:
        try:
            from src.services.rag_service import RAGService

            rag = RAGService()
            warnings = base_report.get("warnings", [])
            query = f"風機 {turbine_id} 故障 {' '.join(warnings[:3])}"
            results = rag.search(query, n_results=3)
            if results:
                rag_contexts = [
                    {
                        "content": r.content,
                        "source": r.metadata.get("source", ""),
                        "relevance": r.relevance_score,
                    }
                    for r in results
                ]
                logger.info(f"RAG 檢索到 {len(rag_contexts)} 筆相關案例")
        except Exception as e:
            logger.warning(f"RAG 檢索失敗（非致命）：{e}")

    # Step 3: LLM 深層推理
    try:
        from src.services.windguard_diagnosis import WindGuardDiagnosis

        windguard = WindGuardDiagnosis()
        llm_result = windguard.reason_about_diagnosis(base_report, rag_contexts)
        base_report["windguard_llm_diagnosis"] = llm_result

        fault_type = llm_result.get("fault_type_zh", "未判定")
        severity = llm_result.get("severity", "未判定")
        logger.info(
            f"{turbine_id} WindGuard 診斷完成 — " f"故障：{fault_type}, 嚴重度：{severity}"
        )

    except Exception as e:
        logger.error(f"WindGuard LLM 推理失敗：{e}")
        base_report["windguard_llm_diagnosis"] = {
            "error": str(e),
            "note": "LLM 推理失敗，僅回傳統計/ML 分析結果",
        }

    return base_report


def run_fleet_diagnosis(
    turbine_ids: list[str],
    loader: Any = None,
    enable_llm: bool = True,
) -> dict[str, Any]:
    """執行風場級別批次診斷與風險排序。

    Args:
        turbine_ids: 風機 ID 列表。
        loader: 自訂資料載入函式。
        enable_llm: 是否啟用 LLM 風場級別分析。

    Returns:
        包含風險排序與維護建議的風場報告。
    """
    from src.services.fleet_scanner import FleetScanner

    scanner = FleetScanner()

    if enable_llm:
        return scanner.scan_and_reason(turbine_ids, loader=loader)
    else:
        return scanner.scan_fleet(turbine_ids, loader=loader)
