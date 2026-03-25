"""Normal Behavior Model (NBM) — 功率曲線 ML 模型。

使用 Gradient Boosting Regressor 學習風機正常運行時的功率曲線，
比對實際功率與模型預測功率，偏差即為異常指標。

模型輸入特徵：風速、環境溫度、轉子轉速、葉片角度等
模型輸出：預測功率 (kW)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

# Senvion MM92 參數
_DEFAULT_RATED_POWER = 2050
_DEFAULT_CUT_IN = 3.0


def _find_col(df: pd.DataFrame, keywords: list[str], suffix: str = "_Mean") -> str | None:
    """根據關鍵字搜尋欄位名稱。"""
    for kw in keywords:
        for col in df.columns:
            if kw.lower() in col.lower() and suffix.lower() in col.lower():
                return col
    exclude = ["standard deviation", "minimum", "maximum", "min ", "max ", "std"]
    for kw in keywords:
        for col in df.columns:
            col_lower = col.lower()
            if kw.lower() in col_lower and not any(ex in col_lower for ex in exclude):
                return col
    for kw in keywords:
        for col in df.columns:
            if kw.lower() in col.lower():
                return col
    return None


@dataclass
class NBMResult:
    """NBM 訓練與預測結果。"""

    r2: float = 0.0
    mae: float = 0.0
    rmse: float = 0.0
    feature_importances: dict[str, float] = field(default_factory=dict)
    n_train: int = 0
    n_test: int = 0


@dataclass
class AnomalyResult:
    """NBM 異常偵測結果。"""

    total_points: int = 0
    anomaly_count: int = 0
    anomaly_ratio: float = 0.0
    mean_residual: float = 0.0
    std_residual: float = 0.0
    threshold: float = 0.0
    anomalies: list[dict[str, Any]] = field(default_factory=list)


class PowerCurveNBM:
    """基於 Gradient Boosting 的功率曲線 Normal Behavior Model。

    訓練時使用正常運行資料學習「風速 → 功率」的非線性映射，
    推論時比對實際功率與預測功率的殘差，殘差超過閾值即為異常。
    """

    def __init__(
        self,
        n_estimators: int = 200,
        max_depth: int = 5,
        learning_rate: float = 0.1,
        random_state: int = 42,
    ) -> None:
        self._model = GradientBoostingRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            random_state=random_state,
            subsample=0.8,
            min_samples_leaf=10,
        )
        self._is_fitted = False
        self._feature_names: list[str] = []
        self._residual_std: float = 0.0
        self._residual_mean: float = 0.0
        self._train_result: NBMResult | None = None

    @property
    def is_fitted(self) -> bool:
        """模型是否已訓練。"""
        return self._is_fitted

    @property
    def train_result(self) -> NBMResult | None:
        """訓練結果摘要。"""
        return self._train_result

    def _prepare_features(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
        """從 SCADA 資料中萃取 NBM 輸入特徵。

        Parameters
        ----------
        df : pd.DataFrame
            SCADA 資料。

        Returns
        -------
        tuple[pd.DataFrame, list[str]]
            (特徵矩陣, 特徵名稱列表)。
        """
        feature_cols: list[str] = []
        features = pd.DataFrame(index=df.index)

        # 必要特徵：風速
        ws_col = _find_col(df, ["wind speed", "windspeed", "ws"])
        if ws_col:
            features["wind_speed"] = df[ws_col].astype(float)
            feature_cols.append("wind_speed")

        # 選用特徵：環境溫度
        ambient_col = _find_col(df, ["ambient temp", "nacelle ambient", "ambient"])
        if ambient_col:
            features["ambient_temp"] = df[ambient_col].astype(float)
            feature_cols.append("ambient_temp")

        # 選用特徵：轉子轉速
        rotor_col = _find_col(df, ["rotor speed", "rotor rpm"])
        if rotor_col:
            features["rotor_speed"] = df[rotor_col].astype(float)
            feature_cols.append("rotor_speed")

        # 選用特徵：葉片角度
        pitch_col = _find_col(df, ["blade pitch", "pitch angle", "pitch"])
        if pitch_col:
            features["blade_pitch"] = df[pitch_col].astype(float)
            feature_cols.append("blade_pitch")

        # 衍生特徵：風速平方、風速立方
        if "wind_speed" in features.columns:
            features["wind_speed_sq"] = features["wind_speed"] ** 2
            features["wind_speed_cb"] = features["wind_speed"] ** 3
            feature_cols.extend(["wind_speed_sq", "wind_speed_cb"])

        return features[feature_cols], feature_cols

    def _filter_normal_operation(self, df: pd.DataFrame, power_col: str) -> pd.DataFrame:
        """過濾正常運行資料（排除停機、異常功率）。

        Parameters
        ----------
        df : pd.DataFrame
            原始 SCADA 資料。
        power_col : str
            功率欄位名稱。

        Returns
        -------
        pd.DataFrame
            僅包含正常運行期間的資料。
        """
        ws_col = _find_col(df, ["wind speed", "windspeed", "ws"])
        if not ws_col:
            return df

        mask = (
            (df[ws_col].astype(float) >= _DEFAULT_CUT_IN)
            & (df[ws_col].astype(float) <= 25.0)
            & (df[power_col].astype(float) > 0)
            & (df[power_col].astype(float) <= _DEFAULT_RATED_POWER * 1.05)
        )
        return df[mask]

    def train(self, df: pd.DataFrame, test_size: float = 0.2) -> NBMResult:
        """訓練 Normal Behavior Model。

        使用正常運行資料訓練 GBR 模型，並在測試集上評估性能。

        Parameters
        ----------
        df : pd.DataFrame
            經清洗的 SCADA 資料。
        test_size : float
            測試集比例，預設 0.2。

        Returns
        -------
        NBMResult
            訓練結果，包含 R², MAE, RMSE 等指標。

        Raises
        ------
        ValueError
            資料不足或找不到必要欄位時拋出。
        """
        power_col = _find_col(df, ["power", "active power"])
        if not power_col:
            raise ValueError("找不到功率欄位，無法訓練 NBM")

        # 過濾正常運行資料
        df_normal = self._filter_normal_operation(df, power_col)
        if len(df_normal) < 100:
            raise ValueError(f"正常運行資料不足：{len(df_normal)} 筆（需要至少 100 筆）")

        # 準備特徵
        features, feature_names = self._prepare_features(df_normal)
        target = df_normal[power_col].astype(float)

        # 對齊索引並去除 NaN
        combined = pd.concat([features, target.rename("_target")], axis=1).dropna()
        if len(combined) < 100:
            raise ValueError(f"有效資料不足：{len(combined)} 筆（需要至少 100 筆）")

        x = combined[feature_names].values
        y = combined["_target"].values

        # 分割訓練/測試集
        x_train, x_test, y_train, y_test = train_test_split(
            x, y, test_size=test_size, random_state=42
        )

        # 訓練模型
        self._model.fit(x_train, y_train)
        self._feature_names = feature_names
        self._is_fitted = True

        # 評估
        y_pred = self._model.predict(x_test)
        residuals = y_test - y_pred
        self._residual_mean = float(np.mean(residuals))
        self._residual_std = float(np.std(residuals))

        # 特徵重要性
        importances = dict(
            zip(feature_names, [float(v) for v in self._model.feature_importances_], strict=True)
        )

        result = NBMResult(
            r2=float(r2_score(y_test, y_pred)),
            mae=float(mean_absolute_error(y_test, y_pred)),
            rmse=float(np.sqrt(mean_squared_error(y_test, y_pred))),
            feature_importances=importances,
            n_train=len(x_train),
            n_test=len(x_test),
        )
        self._train_result = result
        return result

    def predict(self, df: pd.DataFrame) -> pd.Series:
        """預測功率。

        Parameters
        ----------
        df : pd.DataFrame
            SCADA 資料。

        Returns
        -------
        pd.Series
            預測功率序列 (kW)。

        Raises
        ------
        RuntimeError
            模型尚未訓練時拋出。
        """
        if not self._is_fitted:
            raise RuntimeError("模型尚未訓練，請先呼叫 train()")

        features, _ = self._prepare_features(df)
        # 確保特徵順序一致
        for col in self._feature_names:
            if col not in features.columns:
                features[col] = 0.0
        features = features[self._feature_names]

        # 處理 NaN：填充後預測
        mask_valid = features.notna().all(axis=1)
        predictions = pd.Series(np.nan, index=df.index, name="nbm_predicted_power")

        if mask_valid.any():
            valid_features = features[mask_valid].values
            predictions[mask_valid] = self._model.predict(valid_features)

        return predictions

    def detect_anomalies(
        self,
        df: pd.DataFrame,
        threshold_sigma: float = 2.5,
        max_anomalies: int = 100,
    ) -> AnomalyResult:
        """使用 NBM 殘差偵測功率曲線異常。

        計算實際功率與 NBM 預測功率的殘差，
        殘差超過 threshold_sigma 倍標準差的時間點標記為異常。

        Parameters
        ----------
        df : pd.DataFrame
            SCADA 資料。
        threshold_sigma : float
            異常判定門檻，以訓練集殘差標準差的倍數計。
        max_anomalies : int
            最多回報的異常數量。

        Returns
        -------
        AnomalyResult
            異常偵測結果。
        """
        if not self._is_fitted:
            raise RuntimeError("模型尚未訓練，請先呼叫 train()")

        power_col = _find_col(df, ["power", "active power"])
        if not power_col:
            return AnomalyResult()

        predicted = self.predict(df)
        actual = df[power_col].astype(float)

        # 計算殘差（只在有預測值且正常運行的時間點）
        residuals = actual - predicted
        valid_mask = residuals.notna() & (actual > 0)
        valid_residuals = residuals[valid_mask]

        if len(valid_residuals) == 0:
            return AnomalyResult()

        threshold = self._residual_std * threshold_sigma
        anomaly_mask = valid_residuals.abs() > threshold
        anomaly_indices = valid_residuals[anomaly_mask]

        # 取偏差最大的
        anomaly_indices = anomaly_indices.reindex(
            anomaly_indices.abs().sort_values(ascending=False).index
        )[:max_anomalies]

        anomalies: list[dict[str, Any]] = []
        for idx in anomaly_indices.index:
            anomalies.append(
                {
                    "timestamp": str(idx),
                    "actual_power": round(float(actual.get(idx, 0)), 1),
                    "predicted_power": round(float(predicted.get(idx, 0)), 1),
                    "residual": round(float(residuals.get(idx, 0)), 1),
                    "deviation_sigma": round(
                        float(abs(residuals.get(idx, 0)) / self._residual_std), 2
                    ),
                }
            )

        return AnomalyResult(
            total_points=int(valid_mask.sum()),
            anomaly_count=int(anomaly_mask.sum()),
            anomaly_ratio=round(float(anomaly_mask.sum() / len(valid_residuals)), 4),
            mean_residual=round(float(valid_residuals.mean()), 2),
            std_residual=round(float(valid_residuals.std()), 2),
            threshold=round(threshold, 2),
            anomalies=anomalies,
        )

    def get_model_summary(self) -> dict[str, Any]:
        """取得模型摘要資訊。

        Returns
        -------
        dict[str, Any]
            模型參數與訓練結果摘要。
        """
        summary: dict[str, Any] = {
            "model_type": "GradientBoostingRegressor",
            "is_fitted": self._is_fitted,
            "features": self._feature_names,
        }
        if self._train_result:
            summary["performance"] = {
                "r2": self._train_result.r2,
                "mae": self._train_result.mae,
                "rmse": self._train_result.rmse,
            }
            summary["feature_importances"] = self._train_result.feature_importances
            summary["n_train"] = self._train_result.n_train
            summary["n_test"] = self._train_result.n_test
        return summary
