"""ML Pipeline 模組測試。

測試 Normal Behavior Model、故障分類器、RUL 退化模型，
以及 ML Pipeline Service 的端到端流程。
使用合成 SCADA 資料（無需外部檔案）。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

# ── 測試用合成資料產生器 ──────────────────────────────────────


def _make_scada_df(n: int = 5000, seed: int = 42) -> pd.DataFrame:
    """產生合成 SCADA 資料。

    模擬通用風機的 10 分鐘 SCADA 資料（額定功率 2050 kW），
    包含風速、功率、溫度、轉子轉速等欄位。
    """
    rng = np.random.default_rng(seed)

    # 時間索引
    timestamps = pd.date_range("2016-01-01", periods=n, freq="10min")

    # 風速：Weibull 分布
    wind_speed = rng.weibull(2.0, n) * 7 + 1
    wind_speed = np.clip(wind_speed, 0, 30)

    # 理論功率（三次方模型）
    rated_power = 2050
    cut_in = 3.0
    rated_wind = 12.5
    power = np.where(
        wind_speed < cut_in,
        0,
        np.where(
            wind_speed < rated_wind,
            rated_power * ((wind_speed - cut_in) / (rated_wind - cut_in)) ** 3,
            rated_power,
        ),
    )
    # 加入隨機噪音
    power = power + rng.normal(0, 30, n)
    power = np.clip(power, -10, rated_power * 1.1)

    # 環境溫度
    ambient_temp = 10 + 5 * np.sin(np.linspace(0, 4 * np.pi, n)) + rng.normal(0, 2, n)

    # 齒輪箱油溫（與功率正相關）
    gear_oil_temp = 45 + power / rated_power * 20 + rng.normal(0, 2, n)

    # 發電機軸承溫度
    gen_bearing_front = 50 + power / rated_power * 15 + rng.normal(0, 1.5, n)
    gen_bearing_rear = 48 + power / rated_power * 15 + rng.normal(0, 1.5, n)

    # 轉子轉速
    rotor_speed = np.where(wind_speed < cut_in, 0, 8 + wind_speed * 0.5 + rng.normal(0, 0.3, n))

    # 葉片角度
    blade_pitch = np.where(wind_speed < rated_wind, 0, (wind_speed - rated_wind) * 2)
    blade_pitch = blade_pitch + rng.normal(0, 0.5, n)

    df = pd.DataFrame(
        {
            "Wind Speed_Mean": wind_speed,
            "Active Power_Mean": power,
            "Ambient Temperature_Mean": ambient_temp,
            "Gear Oil Temperature_Mean": gear_oil_temp,
            "Generator Bearing Front Temperature_Mean": gen_bearing_front,
            "Generator Bearing Rear Temperature_Mean": gen_bearing_rear,
            "Rotor Speed_Mean": rotor_speed,
            "Blade Pitch Angle_Mean": blade_pitch,
        },
        index=timestamps,
    )
    df.index.name = "Timestamp"
    return df


def _make_featured_df(n: int = 5000, seed: int = 42) -> pd.DataFrame:
    """產生含工程特徵的合成 SCADA 資料。"""
    from src.features.domain_features.wind_features import (
        compute_operational_features,
        compute_power_curve_features,
        compute_temperature_features,
    )

    df = _make_scada_df(n, seed)
    df = compute_power_curve_features(df)
    df = compute_temperature_features(df)
    df = compute_operational_features(df)
    return df


# ══════════════════════════════════════════════════════════════
#  Normal Behavior Model (NBM) 測試
# ══════════════════════════════════════════════════════════════


class TestPowerCurveNBM:
    """Normal Behavior Model 測試。"""

    def test_train_basic(self) -> None:
        """基本訓練功能。"""
        from src.models.nbm.power_curve_nbm import PowerCurveNBM

        df = _make_scada_df()
        nbm = PowerCurveNBM(n_estimators=50)
        result = nbm.train(df)

        assert nbm.is_fitted
        assert result.r2 > 0.8, f"R² 過低：{result.r2}"
        assert result.mae > 0
        assert result.rmse > 0
        assert result.n_train > 0
        assert result.n_test > 0
        assert len(result.feature_importances) > 0

    def test_predict(self) -> None:
        """預測功能。"""
        from src.models.nbm.power_curve_nbm import PowerCurveNBM

        df = _make_scada_df()
        nbm = PowerCurveNBM(n_estimators=50)
        nbm.train(df)

        predictions = nbm.predict(df)
        assert len(predictions) == len(df)
        assert predictions.notna().sum() > 0

    def test_detect_anomalies(self) -> None:
        """異常偵測功能。"""
        from src.models.nbm.power_curve_nbm import PowerCurveNBM

        df = _make_scada_df()
        nbm = PowerCurveNBM(n_estimators=50)
        nbm.train(df)

        result = nbm.detect_anomalies(df)
        assert result.total_points > 0
        assert result.anomaly_count >= 0
        assert 0 <= result.anomaly_ratio <= 1
        assert result.threshold > 0

    def test_not_fitted_raises(self) -> None:
        """未訓練時呼叫 predict 應拋出 RuntimeError。"""
        from src.models.nbm.power_curve_nbm import PowerCurveNBM

        nbm = PowerCurveNBM()
        df = _make_scada_df(100)
        with pytest.raises(RuntimeError, match="尚未訓練"):
            nbm.predict(df)

    def test_insufficient_data_raises(self) -> None:
        """資料不足應拋出 ValueError。"""
        from src.models.nbm.power_curve_nbm import PowerCurveNBM

        df = _make_scada_df(10)
        # 讓大部分資料無效
        df["Wind Speed_Mean"] = 1.0  # 全部低於 cut-in
        nbm = PowerCurveNBM()
        with pytest.raises(ValueError, match="不足"):
            nbm.train(df)

    def test_model_summary(self) -> None:
        """模型摘要。"""
        from src.models.nbm.power_curve_nbm import PowerCurveNBM

        df = _make_scada_df()
        nbm = PowerCurveNBM(n_estimators=50)
        nbm.train(df)

        summary = nbm.get_model_summary()
        assert summary["is_fitted"]
        assert summary["model_type"] == "GradientBoostingRegressor"
        assert "r2" in summary["performance"]

    def test_wind_speed_cubed_feature(self) -> None:
        """風速立方特徵應被包含。"""
        from src.models.nbm.power_curve_nbm import PowerCurveNBM

        df = _make_scada_df()
        nbm = PowerCurveNBM(n_estimators=50)
        nbm.train(df)
        assert "wind_speed_cb" in nbm._feature_names

    def test_anomaly_result_structure(self) -> None:
        """異常結果結構驗證。"""
        from src.models.nbm.power_curve_nbm import PowerCurveNBM

        df = _make_scada_df()
        nbm = PowerCurveNBM(n_estimators=50)
        nbm.train(df)
        result = nbm.detect_anomalies(df, threshold_sigma=1.5)

        if result.anomaly_count > 0:
            anomaly = result.anomalies[0]
            assert "timestamp" in anomaly
            assert "actual_power" in anomaly
            assert "predicted_power" in anomaly
            assert "residual" in anomaly
            assert "deviation_sigma" in anomaly


# ══════════════════════════════════════════════════════════════
#  故障分類器測試
# ══════════════════════════════════════════════════════════════


class TestFaultClassifier:
    """故障分類器測試。"""

    def test_generate_labels(self) -> None:
        """標籤生成功能。"""
        from src.models.classification.fault_classifier import generate_fault_labels

        df = _make_featured_df()
        labels = generate_fault_labels(df)

        assert len(labels) == len(df)
        assert all(
            col in labels.columns
            for col in [
                "temperature_anomaly",
                "power_curve_deviation",
                "suspected_blade_icing",
                "yaw_misalignment",
                "overheating",
            ]
        )
        # 所有值應為 0 或 1
        for col in labels.columns:
            assert set(labels[col].unique()).issubset({0, 1})

    def test_train_basic(self) -> None:
        """基本訓練功能。"""
        from src.models.classification.fault_classifier import FaultClassifier

        df = _make_featured_df()
        clf = FaultClassifier(n_estimators=30)
        result = clf.train(df)

        assert clf.is_fitted
        assert 0 <= result.f1_macro <= 1
        assert result.n_train > 0
        assert result.n_test > 0
        assert len(result.feature_importances) > 0

    def test_predict(self) -> None:
        """預測功能。"""
        from src.models.classification.fault_classifier import FaultClassifier

        df = _make_featured_df()
        clf = FaultClassifier(n_estimators=30)
        clf.train(df)

        predictions = clf.predict(df)
        assert len(predictions) == len(df)
        # 所有預測值應為 0 或 1
        for col in predictions.columns:
            assert set(predictions[col].unique()).issubset({0, 1})

    def test_predict_proba(self) -> None:
        """概率預測功能。"""
        from src.models.classification.fault_classifier import FaultClassifier

        df = _make_featured_df()
        clf = FaultClassifier(n_estimators=30)
        clf.train(df)

        probas = clf.predict_proba(df)
        assert len(probas) == len(df)
        # 概率值應在 0~1 之間
        for col in probas.columns:
            valid = probas[col].dropna()
            assert valid.min() >= 0
            assert valid.max() <= 1

    def test_classify(self) -> None:
        """完整分類結果。"""
        from src.models.classification.fault_classifier import FaultClassifier

        df = _make_featured_df()
        clf = FaultClassifier(n_estimators=30)
        clf.train(df)

        result = clf.classify(df)
        assert result.total_samples == len(df)
        assert "normal" in result.severity_distribution
        assert "single_fault" in result.severity_distribution
        assert "multi_fault" in result.severity_distribution

    def test_not_fitted_raises(self) -> None:
        """未訓練時呼叫 predict 應拋出 RuntimeError。"""
        from src.models.classification.fault_classifier import FaultClassifier

        clf = FaultClassifier()
        df = _make_featured_df(100)
        with pytest.raises(RuntimeError, match="尚未訓練"):
            clf.predict(df)

    def test_fault_label_constants(self) -> None:
        """故障標籤常數驗證。"""
        from src.models.classification.fault_classifier import FaultLabel

        assert len(FaultLabel.ALL_FAULTS) == 5
        assert FaultLabel.NORMAL == "normal"
        assert FaultLabel.TEMP_ANOMALY in FaultLabel.ALL_FAULTS
        assert all(f in FaultLabel.LABEL_NAMES for f in FaultLabel.ALL_FAULTS)

    def test_model_summary(self) -> None:
        """模型摘要。"""
        from src.models.classification.fault_classifier import FaultClassifier

        df = _make_featured_df()
        clf = FaultClassifier(n_estimators=30)
        clf.train(df)

        summary = clf.get_model_summary()
        assert summary["is_fitted"]
        assert len(summary["fault_types"]) == 5
        assert "f1_macro" in summary


# ══════════════════════════════════════════════════════════════
#  RUL 退化模型測試
# ══════════════════════════════════════════════════════════════


class TestRULModel:
    """RUL 退化模型測試。"""

    def _make_hi_df(self, trend: str = "degrading", n_days: int = 60) -> pd.DataFrame:
        """產生合成健康指標資料。"""
        rng = np.random.default_rng(42)
        dates = pd.date_range("2016-01-01", periods=n_days, freq="1D")

        if trend == "degrading":
            hi = 85 - np.linspace(0, 15, n_days) + rng.normal(0, 1, n_days)
        elif trend == "stable":
            hi = 80 + rng.normal(0, 1.5, n_days)
        else:  # improving
            hi = 70 + np.linspace(0, 10, n_days) + rng.normal(0, 1, n_days)

        hi = np.clip(hi, 0, 100)

        return pd.DataFrame(
            {
                "date": dates,
                "health_index": hi,
                "power_score": hi + rng.normal(0, 2, n_days),
                "temp_score": hi + rng.normal(0, 3, n_days),
                "availability_score": np.clip(hi + 10 + rng.normal(0, 2, n_days), 0, 100),
            }
        )

    def test_fit_linear(self) -> None:
        """線性退化模型擬合。"""
        from src.models.degradation.rul_model import RULModel

        hi_df = self._make_hi_df("degrading")
        model = RULModel()
        result = model.fit(hi_df)

        assert model.is_fitted
        assert result.trend == "degrading"
        assert result.degradation_rate > 0
        assert result.r_squared > 0
        assert len(result.health_index_series) == len(hi_df)

    def test_predict_rul_degrading(self) -> None:
        """退化中的 RUL 預測。"""
        from src.models.degradation.rul_model import RULModel

        hi_df = self._make_hi_df("degrading")
        model = RULModel(failure_threshold=50.0)
        model.fit(hi_df)

        rul = model.predict_rul()
        assert rul.rul_days > 0
        assert rul.confidence_interval["lower"] >= 0
        assert rul.confidence_interval["upper"] >= rul.confidence_interval["lower"]
        assert rul.confidence_level == 0.95
        assert rul.current_health_index > 0
        assert rul.trend == "degrading"

    def test_predict_rul_stable(self) -> None:
        """穩定狀態的 RUL 預測（應較長）。"""
        from src.models.degradation.rul_model import RULModel

        hi_df = self._make_hi_df("stable")
        model = RULModel()
        model.fit(hi_df)

        rul = model.predict_rul()
        assert rul.rul_days >= 180  # 穩定狀態 RUL 應較長

    def test_insufficient_data_raises(self) -> None:
        """資料不足應拋出 ValueError。"""
        from src.models.degradation.rul_model import RULModel

        hi_df = self._make_hi_df("degrading", n_days=3)
        model = RULModel()
        with pytest.raises(ValueError, match="不足"):
            model.fit(hi_df)

    def test_not_fitted_raises(self) -> None:
        """未擬合時呼叫 predict_rul 應拋出 RuntimeError。"""
        from src.models.degradation.rul_model import RULModel

        model = RULModel()
        with pytest.raises(RuntimeError, match="尚未擬合"):
            model.predict_rul()

    def test_model_summary(self) -> None:
        """模型摘要。"""
        from src.models.degradation.rul_model import RULModel

        hi_df = self._make_hi_df("degrading")
        model = RULModel()
        model.fit(hi_df)

        summary = model.get_model_summary()
        assert summary["is_fitted"]
        assert summary["model_type"] in ("linear", "exponential")
        assert "parameters" in summary


class TestComputeHealthIndex:
    """健康指標計算測試。"""

    def test_basic(self) -> None:
        """基本健康指標計算。"""
        from src.models.degradation.rul_model import compute_health_index

        df = _make_featured_df()
        hi_df = compute_health_index(df)

        assert len(hi_df) > 0
        assert "date" in hi_df.columns
        assert "health_index" in hi_df.columns
        assert "power_score" in hi_df.columns
        assert "temp_score" in hi_df.columns
        assert "availability_score" in hi_df.columns

        # 健康指標應在 0~100 之間
        assert hi_df["health_index"].min() >= 0
        assert hi_df["health_index"].max() <= 100

    def test_non_datetime_index_raises(self) -> None:
        """非 DatetimeIndex 應拋出 ValueError。"""
        from src.models.degradation.rul_model import compute_health_index

        df = _make_featured_df()
        df = df.reset_index(drop=True)
        with pytest.raises(ValueError, match="DatetimeIndex"):
            compute_health_index(df)


# ══════════════════════════════════════════════════════════════
#  ML Pipeline Service 測試
# ══════════════════════════════════════════════════════════════


class TestMLPipeline:
    """ML Pipeline Service 測試。"""

    def test_train_all(self) -> None:
        """端到端訓練。"""
        from src.services.ml_pipeline_service import MLPipeline

        df = _make_scada_df()
        pipeline = MLPipeline()
        results = pipeline.train_all(df)

        assert pipeline.is_trained
        assert "quality_report" in results
        assert results["nbm"]["status"] == "success"
        assert results["nbm"]["r2"] > 0.5
        assert results["classifier"]["status"] == "success"

    def test_run_inference(self) -> None:
        """端到端推論。"""
        from src.services.ml_pipeline_service import MLPipeline

        df = _make_scada_df()
        pipeline = MLPipeline()
        pipeline.train_all(df)

        results = pipeline.run_inference(df, "test_turbine")
        assert results["turbine_id"] == "test_turbine"
        assert "nbm_anomalies" in results
        assert "fault_classification" in results

    def test_pipeline_summary(self) -> None:
        """Pipeline 摘要。"""
        from src.services.ml_pipeline_service import MLPipeline

        pipeline = MLPipeline()
        summary = pipeline.get_pipeline_summary()
        assert not summary["is_trained"]

        df = _make_scada_df()
        pipeline.train_all(df)
        summary = pipeline.get_pipeline_summary()
        assert summary["is_trained"]
        assert summary["nbm"]["is_fitted"]
        assert summary["classifier"]["is_fitted"]

    def test_inference_without_training(self) -> None:
        """未訓練即推論（模型會被跳過）。"""
        from src.services.ml_pipeline_service import MLPipeline

        df = _make_scada_df(500)
        pipeline = MLPipeline()
        results = pipeline.run_inference(df, "test")
        # 未訓練，不應有 ML 結果
        assert "nbm_anomalies" not in results
        assert "fault_classification" not in results
