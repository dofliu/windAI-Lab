"""ML Pipeline 整合服務。

串接 Normal Behavior Model、故障分類器、RUL 退化模型，
提供統一的訓練與推論 API，供代理與 REST 端點呼叫。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.data_pipeline.cleaning.scada_cleaner import clean_scada_data
from src.features.domain_features.wind_features import (
    compute_operational_features,
    compute_power_curve_features,
    compute_temperature_features,
)
from src.models.classification.fault_classifier import FaultClassifier, generate_fault_labels
from src.models.degradation.rul_model import RULModel, compute_health_index
from src.models.nbm.power_curve_nbm import PowerCurveNBM
from src.utils.logger import get_logger

if TYPE_CHECKING:
    import pandas as pd

logger = get_logger("services.ml_pipeline")


class MLPipeline:
    """ML Pipeline 整合服務。

    管理三個 ML 模型的生命週期（訓練 → 推論），
    並提供端到端的分析流程。
    """

    def __init__(self) -> None:
        self._nbm = PowerCurveNBM()
        self._classifier = FaultClassifier()
        self._rul_model = RULModel()
        self._is_trained = False

    @property
    def is_trained(self) -> bool:
        """Pipeline 是否已訓練。"""
        return self._is_trained

    @property
    def nbm(self) -> PowerCurveNBM:
        """Normal Behavior Model 實例。"""
        return self._nbm

    @property
    def classifier(self) -> FaultClassifier:
        """故障分類器實例。"""
        return self._classifier

    @property
    def rul_model(self) -> RULModel:
        """RUL 模型實例。"""
        return self._rul_model

    def train_all(self, df_raw: pd.DataFrame) -> dict[str, Any]:
        """端到端訓練：清洗 → 特徵工程 → 訓練三個模型。

        Parameters
        ----------
        df_raw : pd.DataFrame
            原始 SCADA 資料。

        Returns
        -------
        dict[str, Any]
            各模型的訓練結果摘要。
        """
        results: dict[str, Any] = {}

        # 步驟 1：資料清洗
        logger.info("ML Pipeline: 步驟 1/5 — 資料清洗")
        df_clean, quality = clean_scada_data(df_raw)
        results["quality_report"] = quality

        # 步驟 2：特徵工程
        logger.info("ML Pipeline: 步驟 2/5 — 特徵工程")
        df_feat = compute_power_curve_features(df_clean)
        df_feat = compute_temperature_features(df_feat)
        df_feat = compute_operational_features(df_feat)

        # 步驟 3：訓練 NBM
        logger.info("ML Pipeline: 步驟 3/5 — 訓練 Normal Behavior Model")
        try:
            nbm_result = self._nbm.train(df_clean)
            results["nbm"] = {
                "status": "success",
                "r2": nbm_result.r2,
                "mae": nbm_result.mae,
                "rmse": nbm_result.rmse,
                "n_train": nbm_result.n_train,
                "feature_importances": nbm_result.feature_importances,
            }
            logger.info(f"NBM 訓練完成：R²={nbm_result.r2:.4f}, MAE={nbm_result.mae:.1f}")
        except Exception as e:
            results["nbm"] = {"status": "error", "error": str(e)}
            logger.warning(f"NBM 訓練失敗：{e}")

        # 步驟 4：訓練故障分類器
        logger.info("ML Pipeline: 步驟 4/5 — 訓練故障分類器")
        try:
            labels = generate_fault_labels(df_feat)
            clf_result = self._classifier.train(df_feat, labels)
            results["classifier"] = {
                "status": "success",
                "f1_macro": clf_result.f1_macro,
                "f1_per_class": clf_result.f1_per_class,
                "n_train": clf_result.n_train,
            }
            logger.info(f"故障分類器訓練完成：F1_macro={clf_result.f1_macro:.4f}")
        except Exception as e:
            results["classifier"] = {"status": "error", "error": str(e)}
            logger.warning(f"故障分類器訓練失敗：{e}")

        # 步驟 5：擬合 RUL 退化模型
        logger.info("ML Pipeline: 步驟 5/5 — 擬合 RUL 退化模型")
        try:
            hi_df = compute_health_index(df_feat)
            if len(hi_df) >= 7:
                deg_result = self._rul_model.fit(hi_df)
                results["rul"] = {
                    "status": "success",
                    "model_type": deg_result.model_type,
                    "trend": deg_result.trend,
                    "degradation_rate": deg_result.degradation_rate,
                    "r_squared": deg_result.r_squared,
                    "days_analyzed": len(hi_df),
                }
                logger.info(
                    f"RUL 模型擬合完成：{deg_result.model_type}, "
                    f"趨勢={deg_result.trend}, R²={deg_result.r_squared:.4f}"
                )
            else:
                results["rul"] = {
                    "status": "skipped",
                    "reason": f"健康指標資料不足（{len(hi_df)} 天）",
                }
        except Exception as e:
            results["rul"] = {"status": "error", "error": str(e)}
            logger.warning(f"RUL 模型擬合失敗：{e}")

        self._is_trained = True
        return results

    def run_inference(self, df_raw: pd.DataFrame, turbine_id: str) -> dict[str, Any]:
        """端到端推論：清洗 → 特徵 → 三個模型推論。

        Parameters
        ----------
        df_raw : pd.DataFrame
            原始 SCADA 資料。
        turbine_id : str
            風機 ID。

        Returns
        -------
        dict[str, Any]
            完整分析結果。
        """
        results: dict[str, Any] = {"turbine_id": turbine_id}

        # 資料準備
        df_clean, quality = clean_scada_data(df_raw)
        df_feat = compute_power_curve_features(df_clean)
        df_feat = compute_temperature_features(df_feat)
        df_feat = compute_operational_features(df_feat)
        results["quality_report"] = quality

        # NBM 推論
        if self._nbm.is_fitted:
            try:
                anomaly_result = self._nbm.detect_anomalies(df_clean)
                results["nbm_anomalies"] = {
                    "total_points": anomaly_result.total_points,
                    "anomaly_count": anomaly_result.anomaly_count,
                    "anomaly_ratio": anomaly_result.anomaly_ratio,
                    "mean_residual": anomaly_result.mean_residual,
                    "threshold": anomaly_result.threshold,
                    "top_anomalies": anomaly_result.anomalies[:10],
                }
                results["nbm_model"] = self._nbm.get_model_summary()
            except Exception as e:
                results["nbm_anomalies"] = {"error": str(e)}

        # 故障分類
        if self._classifier.is_fitted:
            try:
                clf_result = self._classifier.classify(df_feat)
                results["fault_classification"] = {
                    "total_samples": clf_result.total_samples,
                    "fault_counts": clf_result.fault_counts,
                    "fault_ratios": clf_result.fault_ratios,
                    "severity_distribution": clf_result.severity_distribution,
                    "top_faults": clf_result.top_faults[:10],
                }
            except Exception as e:
                results["fault_classification"] = {"error": str(e)}

        # RUL 預測
        if self._rul_model.is_fitted:
            try:
                rul_pred = self._rul_model.predict_rul()
                results["rul_prediction"] = {
                    "rul_days": rul_pred.rul_days,
                    "confidence_interval": rul_pred.confidence_interval,
                    "confidence_level": rul_pred.confidence_level,
                    "degradation_model": rul_pred.degradation_model,
                    "model_r_squared": rul_pred.model_r_squared,
                    "current_health_index": rul_pred.current_health_index,
                    "failure_threshold": rul_pred.failure_threshold,
                    "trend": rul_pred.trend,
                    "daily_degradation_rate": rul_pred.daily_degradation_rate,
                }
            except Exception as e:
                results["rul_prediction"] = {"error": str(e)}

        return results

    def get_pipeline_summary(self) -> dict[str, Any]:
        """取得 Pipeline 摘要。"""
        return {
            "is_trained": self._is_trained,
            "nbm": self._nbm.get_model_summary(),
            "classifier": self._classifier.get_model_summary(),
            "rul": self._rul_model.get_model_summary(),
        }
