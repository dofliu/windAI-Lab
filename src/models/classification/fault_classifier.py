"""風機故障分類器。

基於 SCADA 特徵的多標籤故障分類模型，使用 Random Forest 識別
不同類型的故障模式：溫度異常、功率曲線偏差、疑似葉片結冰、
偏航偏移等。

每筆 10 分鐘記錄被分類為一或多個故障標籤，並附帶置信度分數。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split

# ── 故障標籤定義 ──────────────────────────────────────────────


class FaultLabel:
    """故障類型常數。"""

    NORMAL = "normal"
    TEMP_ANOMALY = "temperature_anomaly"
    POWER_DEVIATION = "power_curve_deviation"
    BLADE_ICING = "suspected_blade_icing"
    YAW_MISALIGNMENT = "yaw_misalignment"
    OVERHEATING = "overheating"

    ALL_FAULTS: list[str] = [
        TEMP_ANOMALY,
        POWER_DEVIATION,
        BLADE_ICING,
        YAW_MISALIGNMENT,
        OVERHEATING,
    ]

    LABEL_NAMES: dict[str, str] = {
        NORMAL: "正常",
        TEMP_ANOMALY: "溫度異常",
        POWER_DEVIATION: "功率曲線偏差",
        BLADE_ICING: "疑似葉片結冰",
        YAW_MISALIGNMENT: "偏航偏移",
        OVERHEATING: "過熱",
    }


from src.core.constants import TurbineProfile


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
    return None


# ── 結果資料結構 ──────────────────────────────────────────────


@dataclass
class ClassificationResult:
    """分類結果摘要。"""

    total_samples: int = 0
    fault_counts: dict[str, int] = field(default_factory=dict)
    fault_ratios: dict[str, float] = field(default_factory=dict)
    severity_distribution: dict[str, int] = field(default_factory=dict)
    top_faults: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class TrainResult:
    """訓練結果。"""

    f1_macro: float = 0.0
    f1_per_class: dict[str, float] = field(default_factory=dict)
    n_train: int = 0
    n_test: int = 0
    feature_importances: dict[str, float] = field(default_factory=dict)


# ── 故障標籤產生器 ────────────────────────────────────────────


def generate_fault_labels(
    df: pd.DataFrame, profile: TurbineProfile | None = None
) -> pd.DataFrame:
    """根據領域規則從 SCADA 特徵生成故障標籤。

    使用基於物理的規則自動標註故障標籤，作為分類器的訓練目標。

    Parameters
    ----------
    df : pd.DataFrame
        經特徵工程處理後的 SCADA 資料。
    profile : TurbineProfile or None
        風機參數。

    Returns
    -------
    pd.DataFrame
        包含各故障標籤的 0/1 DataFrame，索引與輸入相同。
    """
    p = profile or TurbineProfile()
    labels = pd.DataFrame(index=df.index)

    ws_col = _find_col(df, ["wind speed", "windspeed", "ws"])
    power_col = _find_col(df, ["power", "active power"])

    # ── 溫度異常 ──
    # 齒輪箱油溫 rolling std 過高
    if "gear_oil_temp_rolling_std" in df.columns:
        labels[FaultLabel.TEMP_ANOMALY] = (
            df["gear_oil_temp_rolling_std"] > df["gear_oil_temp_rolling_std"].quantile(0.95)
        ).astype(int)
    elif "gear_oil_temp_delta" in df.columns:
        labels[FaultLabel.TEMP_ANOMALY] = (
            df["gear_oil_temp_delta"].abs() > df["gear_oil_temp_delta"].abs().quantile(0.95)
        ).astype(int)
    else:
        labels[FaultLabel.TEMP_ANOMALY] = 0

    # ── 功率曲線偏差 ──
    if "power_curve_deviation_pct" in df.columns:
        labels[FaultLabel.POWER_DEVIATION] = (df["power_curve_deviation_pct"].abs() > 20).astype(
            int
        )
    else:
        labels[FaultLabel.POWER_DEVIATION] = 0

    # ── 疑似葉片結冰 ──
    # 低溫 + 風速正常但功率偏低
    if ws_col and power_col:
        ws = df[ws_col].astype(float)
        pwr = df[power_col].astype(float)
        ambient_col = _find_col(df, ["ambient temp", "nacelle ambient", "ambient"])

        if ambient_col:
            ambient = df[ambient_col].astype(float)
            # 溫度 < 2°C, 風速在運行範圍, 但功率顯著低於預期
            divisor = p.rated_wind_speed_ms - p.cut_in_speed_ms
            ratio = np.clip(((ws - p.cut_in_speed_ms) / divisor) ** 3, 0, 1) if divisor > 0 else 0
            theoretical = p.rated_power_kw * ratio
            low_power = pwr < theoretical * 0.5
            cold = ambient < 2.0
            wind_ok = (ws >= p.cut_in_speed_ms + 1) & (ws <= 20)
            labels[FaultLabel.BLADE_ICING] = (cold & wind_ok & low_power).astype(int)
        else:
            labels[FaultLabel.BLADE_ICING] = 0
    else:
        labels[FaultLabel.BLADE_ICING] = 0

    # ── 偏航偏移 ──
    # 功率偏差大且溫度正常（排除溫度問題）
    if "power_curve_deviation_pct" in df.columns:
        power_low = df["power_curve_deviation_pct"] < -15
        temp_ok = labels[FaultLabel.TEMP_ANOMALY] == 0
        not_icing = labels[FaultLabel.BLADE_ICING] == 0
        labels[FaultLabel.YAW_MISALIGNMENT] = (power_low & temp_ok & not_icing).astype(int)
    else:
        labels[FaultLabel.YAW_MISALIGNMENT] = 0

    # ── 過熱 ──
    if "gear_oil_temp_delta" in df.columns:
        labels[FaultLabel.OVERHEATING] = (
            df["gear_oil_temp_delta"] > df["gear_oil_temp_delta"].quantile(0.98)
        ).astype(int)
    else:
        labels[FaultLabel.OVERHEATING] = 0

    return labels


# ── 分類器 ────────────────────────────────────────────────────


class FaultClassifier:
    """多標籤風機故障分類器。

    針對每種故障類型訓練獨立的 Random Forest 二元分類器，
    支援同時偵測多種故障模式。
    """

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 8,
        random_state: int = 42,
    ) -> None:
        self._n_estimators = n_estimators
        self._max_depth = max_depth
        self._random_state = random_state
        self._models: dict[str, RandomForestClassifier] = {}
        self._feature_names: list[str] = []
        self._is_fitted = False
        self._train_result: TrainResult | None = None

    @property
    def is_fitted(self) -> bool:
        """模型是否已訓練。"""
        return self._is_fitted

    @property
    def train_result(self) -> TrainResult | None:
        """訓練結果。"""
        return self._train_result

    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """萃取分類器輸入特徵。"""
        feature_cols: list[str] = []
        features = pd.DataFrame(index=df.index)

        # 基礎 SCADA 特徵
        col_map = {
            "wind_speed": ["wind speed", "windspeed", "ws"],
            "power": ["power", "active power"],
            "rotor_speed": ["rotor speed", "rotor rpm"],
            "ambient_temp": ["ambient temp", "nacelle ambient", "ambient"],
            "blade_pitch": ["blade pitch", "pitch angle", "pitch"],
        }
        for feat_name, keywords in col_map.items():
            col = _find_col(df, keywords)
            if col:
                features[feat_name] = df[col].astype(float)
                feature_cols.append(feat_name)

        # 工程特徵
        eng_features = [
            "power_curve_deviation_pct",
            "capacity_factor",
            "normalized_power",
            "gear_oil_temp_delta",
            "gen_bearing_front_delta",
            "gen_bearing_rear_delta",
            "gear_oil_temp_rolling_std",
            "tip_speed_ratio",
        ]
        for feat in eng_features:
            if feat in df.columns:
                features[feat] = df[feat].astype(float)
                feature_cols.append(feat)

        return features[feature_cols]

    def train(
        self,
        df: pd.DataFrame,
        labels: pd.DataFrame | None = None,
        test_size: float = 0.2,
        profile: TurbineProfile | None = None,
    ) -> TrainResult:
        """訓練多標籤故障分類器。

        Parameters
        ----------
        df : pd.DataFrame
            經特徵工程處理後的 SCADA 資料。
        labels : pd.DataFrame or None
            故障標籤。若為 None，會自動使用規則產生。
        test_size : float
            測試集比例。
        profile : TurbineProfile or None
            風機參數。

        Returns
        -------
        TrainResult
            訓練結果。
        """
        if labels is None:
            labels = generate_fault_labels(df, profile=profile)

        features = self._prepare_features(df)

        # 對齊索引並去除 NaN
        common_idx = features.dropna().index.intersection(labels.dropna().index)
        features = features.loc[common_idx]
        labels = labels.loc[common_idx]

        if len(features) < 50:
            raise ValueError(f"有效資料不足：{len(features)} 筆（需要至少 50 筆）")

        self._feature_names = list(features.columns)

        # 分割訓練/測試集
        x_train, x_test, y_train, y_test = train_test_split(
            features.values,
            labels.values,
            test_size=test_size,
            random_state=self._random_state,
        )

        # 對每種故障訓練獨立分類器
        fault_labels = list(labels.columns)
        f1_per_class: dict[str, float] = {}

        for i, fault_name in enumerate(fault_labels):
            y_tr = y_train[:, i]
            y_te = y_test[:, i]

            clf = RandomForestClassifier(
                n_estimators=self._n_estimators,
                max_depth=self._max_depth,
                random_state=self._random_state,
                class_weight="balanced",
            )
            clf.fit(x_train, y_tr)
            self._models[fault_name] = clf

            # 計算 F1（處理全為 0 的情況）
            if y_te.sum() > 0:
                y_pred = clf.predict(x_test)
                f1_per_class[fault_name] = float(f1_score(y_te, y_pred, zero_division=0))
            else:
                f1_per_class[fault_name] = 1.0  # 無正例，無法評估

        self._is_fitted = True

        # 平均特徵重要性
        avg_importances = np.zeros(len(self._feature_names))
        for clf in self._models.values():
            avg_importances += clf.feature_importances_
        avg_importances /= len(self._models)

        f1_values = list(f1_per_class.values())
        result = TrainResult(
            f1_macro=float(np.mean(f1_values)),
            f1_per_class=f1_per_class,
            n_train=len(x_train),
            n_test=len(x_test),
            feature_importances=dict(
                zip(self._feature_names, [float(v) for v in avg_importances], strict=True)
            ),
        )
        self._train_result = result
        return result

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """預測故障標籤。

        Parameters
        ----------
        df : pd.DataFrame
            SCADA 資料。

        Returns
        -------
        pd.DataFrame
            各故障類型的預測結果（0/1）。
        """
        if not self._is_fitted:
            raise RuntimeError("模型尚未訓練，請先呼叫 train()")

        features = self._prepare_features(df)
        for col in self._feature_names:
            if col not in features.columns:
                features[col] = 0.0
        features = features[self._feature_names]

        predictions = pd.DataFrame(index=df.index)
        valid_mask = features.notna().all(axis=1)

        for fault_name, clf in self._models.items():
            pred = pd.Series(0, index=df.index, name=fault_name)
            if valid_mask.any():
                pred[valid_mask] = clf.predict(features[valid_mask].values)
            predictions[fault_name] = pred

        return predictions

    def predict_proba(self, df: pd.DataFrame) -> pd.DataFrame:
        """預測各故障類型的概率。

        Parameters
        ----------
        df : pd.DataFrame
            SCADA 資料。

        Returns
        -------
        pd.DataFrame
            各故障類型的故障概率（0~1）。
        """
        if not self._is_fitted:
            raise RuntimeError("模型尚未訓練，請先呼叫 train()")

        features = self._prepare_features(df)
        for col in self._feature_names:
            if col not in features.columns:
                features[col] = 0.0
        features = features[self._feature_names]

        probas = pd.DataFrame(index=df.index)
        valid_mask = features.notna().all(axis=1)

        for fault_name, clf in self._models.items():
            prob = pd.Series(0.0, index=df.index, name=fault_name)
            if valid_mask.any():
                proba = clf.predict_proba(features[valid_mask].values)
                # predict_proba 回傳 [P(0), P(1)]，取 P(1)
                if proba.shape[1] == 2:
                    prob[valid_mask] = proba[:, 1]
                else:
                    prob[valid_mask] = proba[:, 0]
            probas[fault_name] = prob

        return probas

    def classify(self, df: pd.DataFrame) -> ClassificationResult:
        """執行完整分類並彙整結果。

        Parameters
        ----------
        df : pd.DataFrame
            SCADA 資料。

        Returns
        -------
        ClassificationResult
            分類結果摘要。
        """
        predictions = self.predict(df)
        probas = self.predict_proba(df)

        # 統計各故障數量
        fault_counts = {col: int(predictions[col].sum()) for col in predictions.columns}
        total = len(predictions)
        fault_ratios = {
            col: round(count / total, 4) if total > 0 else 0.0
            for col, count in fault_counts.items()
        }

        # 嚴重度評估：多個故障同時發生 = 更嚴重
        fault_per_row = predictions.sum(axis=1)
        severity_distribution = {
            "normal": int((fault_per_row == 0).sum()),
            "single_fault": int((fault_per_row == 1).sum()),
            "multi_fault": int((fault_per_row >= 2).sum()),
        }

        # 找出最嚴重的故障事件（多重故障 + 高置信度）
        multi_fault_mask = fault_per_row >= 2
        top_faults: list[dict[str, Any]] = []
        if multi_fault_mask.any():
            multi_probas = probas[multi_fault_mask]
            # 按故障數量排序
            sorted_idx = fault_per_row[multi_fault_mask].sort_values(ascending=False).index
            for idx in sorted_idx[:20]:
                active_faults = [
                    col for col in predictions.columns if predictions.loc[idx, col] == 1
                ]
                top_faults.append(
                    {
                        "timestamp": str(idx),
                        "fault_count": int(fault_per_row[idx]),
                        "faults": active_faults,
                        "fault_names": [FaultLabel.LABEL_NAMES.get(f, f) for f in active_faults],
                        "max_probability": round(float(multi_probas.loc[idx].max()), 3),
                    }
                )

        return ClassificationResult(
            total_samples=total,
            fault_counts=fault_counts,
            fault_ratios=fault_ratios,
            severity_distribution=severity_distribution,
            top_faults=top_faults,
        )

    def get_model_summary(self) -> dict[str, Any]:
        """取得模型摘要。"""
        summary: dict[str, Any] = {
            "model_type": "RandomForestClassifier (per-label)",
            "is_fitted": self._is_fitted,
            "fault_types": list(self._models.keys()),
            "features": self._feature_names,
        }
        if self._train_result:
            summary["f1_macro"] = self._train_result.f1_macro
            summary["f1_per_class"] = self._train_result.f1_per_class
            summary["feature_importances"] = self._train_result.feature_importances
        return summary
