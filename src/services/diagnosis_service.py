"""風機故障診斷服務。

封裝故障診斷業務邏輯，串接資料清洗、特徵工程與異常分析模組，
提供統一的診斷 API 供 REST 端點與工作流程呼叫。
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
