"""RUL 退化模型 — 剩餘使用壽命預測。

基於健康指標 (Health Index) 的退化曲線擬合，
使用指數退化模型與線性退化模型估算風機元件的剩餘使用壽命。

支援的退化模型：
- 線性退化：HI(t) = a * t + b
- 指數退化：HI(t) = a * exp(b * t) + c
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy.stats import norm

# ── 退化函數定義 ──────────────────────────────────────────────


def _linear_degradation(t: np.ndarray, a: float, b: float) -> np.ndarray:
    """線性退化模型：HI(t) = a * t + b。"""
    return a * t + b


def _exponential_degradation(t: np.ndarray, a: float, b: float, c: float) -> np.ndarray:
    """指數退化模型：HI(t) = a * exp(b * t) + c。"""
    return a * np.exp(b * t) + c


# ── 結果資料結構 ──────────────────────────────────────────────


@dataclass
class RULPrediction:
    """RUL 預測結果。"""

    rul_days: float = 0.0
    confidence_interval: dict[str, float] = field(default_factory=dict)
    confidence_level: float = 0.95
    degradation_model: str = "linear"
    model_r_squared: float = 0.0
    current_health_index: float = 100.0
    failure_threshold: float = 50.0
    trend: str = "stable"
    daily_degradation_rate: float = 0.0


@dataclass
class DegradationAnalysis:
    """退化分析結果。"""

    health_index_series: list[dict[str, Any]] = field(default_factory=list)
    trend: str = "stable"
    degradation_rate: float = 0.0
    model_type: str = "linear"
    model_params: dict[str, float] = field(default_factory=dict)
    r_squared: float = 0.0


# ── 健康指標計算 ──────────────────────────────────────────────


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


def compute_health_index(
    df: pd.DataFrame,
    window: str = "1D",
) -> pd.DataFrame:
    """從 SCADA 特徵計算每日健康指標 (0~100)。

    健康指標綜合考量：
    - 功率曲線符合度（權重 40%）
    - 溫度穩定度（權重 35%）
    - 可用率（權重 25%）

    Parameters
    ----------
    df : pd.DataFrame
        經特徵工程處理後的 SCADA 資料（DatetimeIndex）。
    window : str
        聚合窗口，預設 '1D'（每日）。

    Returns
    -------
    pd.DataFrame
        每日健康指標，包含 date, health_index, power_score,
        temp_score, availability_score 欄位。
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("資料索引必須為 DatetimeIndex")

    daily_records: list[dict[str, Any]] = []

    # 按日聚合
    for date, day_df in df.resample(window):
        if len(day_df) < 6:  # 至少 1 小時資料
            continue

        record: dict[str, Any] = {"date": date}

        # 功率曲線分數
        if "power_curve_deviation_pct" in day_df.columns:
            valid = day_df["power_curve_deviation_pct"].dropna()
            if len(valid) > 0:
                abs_dev = valid.abs().mean()
                record["power_score"] = float(max(0, min(100, 100 - abs_dev * 2)))
            else:
                record["power_score"] = 50.0
        else:
            record["power_score"] = 50.0

        # 溫度穩定度分數
        temp_score = 100.0
        if "gear_oil_temp_rolling_std" in day_df.columns:
            valid = day_df["gear_oil_temp_rolling_std"].dropna()
            if len(valid) > 0:
                mean_std = valid.mean()
                temp_score = float(max(0, min(100, 100 - (mean_std - 2) * 12.5)))
        record["temp_score"] = temp_score

        # 可用率分數
        power_col = _find_col(day_df, ["power", "active power"])
        if "operating_state" in day_df.columns:
            total = len(day_df)
            operating = day_df["operating_state"].isin(["partial", "full"]).sum()
            avail = float(operating / total * 100) if total > 0 else 50.0
        elif power_col:
            pwr = day_df[power_col].astype(float)
            total = len(pwr.dropna())
            avail = float((pwr > 0).sum() / total * 100) if total > 0 else 50.0
        else:
            avail = 50.0
        record["availability_score"] = min(100.0, avail * 1.1)

        # 綜合健康指標
        hi = (
            record["power_score"] * 0.40
            + record["temp_score"] * 0.35
            + record["availability_score"] * 0.25
        )
        record["health_index"] = round(max(0, min(100, hi)), 2)

        daily_records.append(record)

    if not daily_records:
        return pd.DataFrame(
            columns=["date", "health_index", "power_score", "temp_score", "availability_score"]
        )

    result = pd.DataFrame(daily_records)
    result["date"] = pd.to_datetime(result["date"])
    return result


# ── RUL 模型 ──────────────────────────────────────────────────


class RULModel:
    """剩餘使用壽命預測模型。

    基於健康指標時序的退化曲線擬合，外推至故障閾值以估算 RUL。
    """

    def __init__(self, failure_threshold: float = 50.0) -> None:
        self._failure_threshold = failure_threshold
        self._model_type: str = "linear"
        self._params: dict[str, float] = {}
        self._r_squared: float = 0.0
        self._residual_std: float = 0.0
        self._is_fitted = False
        self._hi_series: pd.DataFrame | None = None

    @property
    def is_fitted(self) -> bool:
        """模型是否已擬合。"""
        return self._is_fitted

    def fit(self, hi_df: pd.DataFrame) -> DegradationAnalysis:
        """擬合退化曲線。

        嘗試指數退化模型，若擬合失敗則退回線性模型。

        Parameters
        ----------
        hi_df : pd.DataFrame
            由 compute_health_index() 產出的每日健康指標資料，
            需包含 date 與 health_index 欄位。

        Returns
        -------
        DegradationAnalysis
            退化分析結果。

        Raises
        ------
        ValueError
            資料不足時拋出。
        """
        if len(hi_df) < 7:
            raise ValueError(f"健康指標資料不足：{len(hi_df)} 天（需要至少 7 天）")

        self._hi_series = hi_df.copy()

        # 將日期轉為天數
        dates = pd.to_datetime(hi_df["date"])
        t_days = (dates - dates.iloc[0]).dt.total_seconds() / 86400.0
        t = t_days.values.astype(float)
        hi = hi_df["health_index"].values.astype(float)

        # 嘗試指數退化模型
        try:
            popt, pcov = curve_fit(
                _exponential_degradation,
                t,
                hi,
                p0=[-0.01, 0.01, hi[0]],
                maxfev=5000,
            )
            hi_pred = _exponential_degradation(t, *popt)
            ss_res = np.sum((hi - hi_pred) ** 2)
            ss_tot = np.sum((hi - np.mean(hi)) ** 2)
            r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

            if r2 > 0.3 and popt[1] > 0:
                # 指數增長不合理（健康指標應下降），改用線性
                raise ValueError("指數增長不合理")

            if r2 > 0.3:
                self._model_type = "exponential"
                self._params = {"a": float(popt[0]), "b": float(popt[1]), "c": float(popt[2])}
                self._r_squared = float(r2)
                self._residual_std = float(np.std(hi - hi_pred))
                self._is_fitted = True
            else:
                raise ValueError("指數模型 R² 過低")

        except (RuntimeError, ValueError, TypeError):
            # 退回線性模型
            popt, pcov = curve_fit(_linear_degradation, t, hi)
            hi_pred = _linear_degradation(t, *popt)
            ss_res = np.sum((hi - hi_pred) ** 2)
            ss_tot = np.sum((hi - np.mean(hi)) ** 2)
            r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

            self._model_type = "linear"
            self._params = {"a": float(popt[0]), "b": float(popt[1])}
            self._r_squared = float(r2)
            self._residual_std = float(np.std(hi - hi_pred))
            self._is_fitted = True

        # 判斷趨勢
        slope = self._params.get("a", 0)
        if slope < -0.1:
            trend = "degrading"
        elif slope > 0.1:
            trend = "improving"
        else:
            trend = "stable"

        hi_records = [
            {
                "date": str(dates.iloc[i].date()),
                "day": int(t[i]),
                "health_index": round(float(hi[i]), 2),
                "predicted_hi": round(float(hi_pred[i]), 2),
            }
            for i in range(len(t))
        ]

        return DegradationAnalysis(
            health_index_series=hi_records,
            trend=trend,
            degradation_rate=round(abs(float(slope)), 4),
            model_type=self._model_type,
            model_params={k: round(v, 6) for k, v in self._params.items()},
            r_squared=round(self._r_squared, 4),
        )

    def predict_rul(self, confidence_level: float = 0.95) -> RULPrediction:
        """預測剩餘使用壽命。

        從最後一天的健康指標外推退化曲線，找出達到故障閾值的天數。

        Parameters
        ----------
        confidence_level : float
            信賴水準，預設 0.95。

        Returns
        -------
        RULPrediction
            RUL 預測結果，包含點估計與信賴區間。

        Raises
        ------
        RuntimeError
            模型尚未擬合時拋出。
        """
        if not self._is_fitted or self._hi_series is None:
            raise RuntimeError("模型尚未擬合，請先呼叫 fit()")

        dates = pd.to_datetime(self._hi_series["date"])
        t_days = (dates - dates.iloc[0]).dt.total_seconds() / 86400.0
        t_last = float(t_days.iloc[-1])
        current_hi = float(self._hi_series["health_index"].iloc[-1])

        # 判斷趨勢
        slope = self._params.get("a", 0)

        # 如果健康指標沒有下降趨勢，回傳較長的 RUL
        if slope >= 0:
            return RULPrediction(
                rul_days=365.0,
                confidence_interval={"lower": 180.0, "upper": 730.0},
                confidence_level=confidence_level,
                degradation_model=self._model_type,
                model_r_squared=self._r_squared,
                current_health_index=round(current_hi, 2),
                failure_threshold=self._failure_threshold,
                trend="stable" if abs(slope) < 0.1 else "improving",
                daily_degradation_rate=0.0,
            )

        # 外推至故障閾值
        max_extrapolate = 730  # 最多外推 2 年
        rul_point = None

        if self._model_type == "linear":
            # HI(t) = a * t + b, 解 a * t + b = threshold
            a, b = self._params["a"], self._params["b"]
            if a < 0:
                t_fail = (self._failure_threshold - b) / a
                rul_point = t_fail - t_last
        else:
            # 指數模型：數值搜尋
            for future_day in range(1, max_extrapolate + 1):
                t_future = t_last + future_day
                hi_future = _exponential_degradation(
                    np.array([t_future]),
                    self._params["a"],
                    self._params["b"],
                    self._params["c"],
                )[0]
                if hi_future <= self._failure_threshold:
                    rul_point = float(future_day)
                    break

        if rul_point is None or rul_point < 0:
            rul_point = float(max_extrapolate)

        rul_days = max(0, min(rul_point, float(max_extrapolate)))

        # 信賴區間（基於殘差不確定性）
        z = norm.ppf((1 + confidence_level) / 2)
        uncertainty_days = (
            z * self._residual_std / abs(slope) if abs(slope) > 0.001 else rul_days * 0.3
        )

        ci_lower = max(0, rul_days - uncertainty_days)
        ci_upper = rul_days + uncertainty_days

        daily_rate = abs(slope)

        return RULPrediction(
            rul_days=round(rul_days, 1),
            confidence_interval={
                "lower": round(ci_lower, 1),
                "upper": round(ci_upper, 1),
            },
            confidence_level=confidence_level,
            degradation_model=self._model_type,
            model_r_squared=round(self._r_squared, 4),
            current_health_index=round(current_hi, 2),
            failure_threshold=self._failure_threshold,
            trend="degrading" if slope < -0.1 else "stable",
            daily_degradation_rate=round(daily_rate, 4),
        )

    def get_model_summary(self) -> dict[str, Any]:
        """取得模型摘要。"""
        return {
            "model_type": self._model_type,
            "is_fitted": self._is_fitted,
            "failure_threshold": self._failure_threshold,
            "parameters": self._params,
            "r_squared": self._r_squared,
            "residual_std": round(self._residual_std, 4),
        }
