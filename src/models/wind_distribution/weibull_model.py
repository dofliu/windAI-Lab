"""Weibull 風速分佈擬合模型。

使用 Weibull 分佈（兩參數）擬合風速資料，用於：
- 風資源評估（年平均能量密度）
- 風場選址分析（風速頻率分佈）
- 可用率估算（風速 >= cut-in 的比例）
- 理論年發電量估算（AEP）

支援兩種擬合方法：
- MLE（最大概似估計）：scipy.stats.weibull_min.fit
- 風能標準方法：矩量法估計

References:
    IEC 61400-12-1:2022 — Power performance measurements
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy import stats

from src.core.constants import TurbineProfile


@dataclass
class WeibullFitResult:
    """Weibull 擬合結果。

    Attributes:
        shape_k: 形狀參數 k（值越大，風速分佈越集中）。
        scale_c: 尺度參數 c (m/s)（近似平均風速）。
        mean_wind_speed: 資料平均風速 (m/s)。
        std_wind_speed: 資料風速標準差 (m/s)。
        median_wind_speed: 中位數風速 (m/s)。
        ks_statistic: Kolmogorov-Smirnov 檢驗統計量。
        ks_p_value: K-S 檢驗 p 值。
        energy_density_w_m2: 平均風能密度 (W/m²)。
        fit_method: 擬合方法（"mle" / "moments"）。
        sample_count: 樣本數。
    """

    shape_k: float = 2.0
    scale_c: float = 8.0
    mean_wind_speed: float = 0.0
    std_wind_speed: float = 0.0
    median_wind_speed: float = 0.0
    ks_statistic: float = 0.0
    ks_p_value: float = 0.0
    energy_density_w_m2: float = 0.0
    fit_method: str = "mle"
    sample_count: int = 0


@dataclass
class AEPEstimate:
    """年發電量估算結果。

    Attributes:
        aep_mwh: 年發電量 (MWh)。
        capacity_factor: 容量因數（0~1）。
        availability_pct: 可用風速比例（%）。
        full_load_hours: 滿載等效小時數 (h)。
        weibull_params: 使用的 Weibull 參數。
    """

    aep_mwh: float = 0.0
    capacity_factor: float = 0.0
    availability_pct: float = 0.0
    full_load_hours: float = 0.0
    weibull_params: dict[str, float] = field(default_factory=dict)


class WeibullDistributionModel:
    """Weibull 風速分佈擬合與分析。"""

    def __init__(self, air_density: float = 1.225) -> None:
        self._air_density = air_density
        self._fit_result: WeibullFitResult | None = None

    @property
    def fit_result(self) -> WeibullFitResult | None:
        return self._fit_result

    def fit(
        self,
        wind_speeds: np.ndarray,
        method: str = "mle",
    ) -> WeibullFitResult:
        """擬合 Weibull 分佈。

        Parameters
        ----------
        wind_speeds : np.ndarray
            風速資料 (m/s)，正值。
        method : str
            擬合方法，"mle"（最大概似）或 "moments"（矩量法）。

        Returns
        -------
        WeibullFitResult
            擬合結果。
        """
        ws = np.asarray(wind_speeds, dtype=float)
        ws = ws[np.isfinite(ws) & (ws > 0)]

        if len(ws) < 10:
            return WeibullFitResult(sample_count=len(ws))

        if method == "moments":
            k, c = self._fit_moments(ws)
        else:
            k, c = self._fit_mle(ws)

        # Kolmogorov-Smirnov 適合度檢驗
        ks_stat, ks_p = stats.kstest(ws, "weibull_min", args=(k, 0, c))

        # 風能密度：E = 0.5 * ρ * Σ(v³) / n ≈ 0.5 * ρ * c³ * Γ(1 + 3/k)
        from scipy.special import gamma

        energy_density = 0.5 * self._air_density * (c**3) * gamma(1 + 3 / k)

        self._fit_result = WeibullFitResult(
            shape_k=round(k, 4),
            scale_c=round(c, 4),
            mean_wind_speed=round(float(np.mean(ws)), 2),
            std_wind_speed=round(float(np.std(ws)), 2),
            median_wind_speed=round(float(np.median(ws)), 2),
            ks_statistic=round(float(ks_stat), 4),
            ks_p_value=round(float(ks_p), 4),
            energy_density_w_m2=round(energy_density, 1),
            fit_method=method,
            sample_count=len(ws),
        )

        return self._fit_result

    @staticmethod
    def _fit_mle(ws: np.ndarray) -> tuple[float, float]:
        """MLE 擬合。"""
        shape, _loc, scale = stats.weibull_min.fit(ws, floc=0)
        return float(shape), float(scale)

    @staticmethod
    def _fit_moments(ws: np.ndarray) -> tuple[float, float]:
        """矩量法擬合。使用 mean / std 的比值估計 k，再反推 c。"""
        mean = float(np.mean(ws))
        std = float(np.std(ws))
        if std < 1e-6:
            return 2.0, mean

        # 經驗公式：k ≈ (std / mean) ^ -1.086
        cv = std / mean
        k = (cv) ** (-1.086)
        k = max(0.5, min(10.0, k))  # 限制合理範圍

        from scipy.special import gamma

        c = mean / gamma(1 + 1 / k)

        return k, c

    def predict_frequency(self, wind_speed: float) -> float:
        """計算指定風速的機率密度。"""
        if self._fit_result is None:
            return 0.0
        k = self._fit_result.shape_k
        c = self._fit_result.scale_c
        return float(stats.weibull_min.pdf(wind_speed, k, loc=0, scale=c))

    def predict_exceedance(self, wind_speed: float) -> float:
        """計算風速超過指定值的機率。"""
        if self._fit_result is None:
            return 0.0
        k = self._fit_result.shape_k
        c = self._fit_result.scale_c
        return float(1 - stats.weibull_min.cdf(wind_speed, k, loc=0, scale=c))

    def estimate_aep(
        self,
        profile: TurbineProfile | None = None,
        hours_per_year: float = 8760.0,
    ) -> AEPEstimate:
        """估算年發電量 (AEP)。

        使用 Weibull 分佈與風機功率曲線（三次方理論模型）積分計算。

        Parameters
        ----------
        profile : TurbineProfile | None
            風機參數，預設使用通用值。
        hours_per_year : float
            年運行小時數。

        Returns
        -------
        AEPEstimate
            年發電量估算結果。
        """
        if self._fit_result is None:
            return AEPEstimate()

        p = profile or TurbineProfile()
        k = self._fit_result.shape_k
        c = self._fit_result.scale_c

        # 數值積分：P(v) * f(v) * dv
        ws_range = np.arange(0, p.cut_out_speed_ms + 1, 0.5)
        total_power = 0.0
        total_prob = 0.0

        for v in ws_range:
            prob = float(stats.weibull_min.pdf(v, k, loc=0, scale=c))
            power = _theoretical_power(v, p)
            total_power += power * prob * 0.5  # dv = 0.5
            total_prob += prob * 0.5

        # 可用風速比例（cut_in ≤ v ≤ cut_out）
        avail = float(
            stats.weibull_min.cdf(p.cut_out_speed_ms, k, loc=0, scale=c)
            - stats.weibull_min.cdf(p.cut_in_speed_ms, k, loc=0, scale=c)
        )

        aep_kwh = total_power * hours_per_year
        aep_mwh = aep_kwh / 1000
        capacity_factor = total_power / p.rated_power_kw if p.rated_power_kw > 0 else 0.0
        full_load_hours = capacity_factor * hours_per_year

        return AEPEstimate(
            aep_mwh=round(aep_mwh, 1),
            capacity_factor=round(capacity_factor, 4),
            availability_pct=round(avail * 100, 1),
            full_load_hours=round(full_load_hours, 1),
            weibull_params={"shape_k": k, "scale_c": c},
        )

    def generate_frequency_table(self, bin_width: float = 1.0) -> list[dict[str, Any]]:
        """產出風速頻率表（供前端圖表使用）。"""
        if self._fit_result is None:
            return []

        k = self._fit_result.shape_k
        c = self._fit_result.scale_c
        bins = np.arange(0, 30 + bin_width, bin_width)

        table: list[dict[str, Any]] = []
        for v in bins:
            prob = float(stats.weibull_min.pdf(v, k, loc=0, scale=c))
            table.append({
                "wind_speed": round(float(v), 1),
                "probability": round(prob, 6),
                "frequency_pct": round(prob * bin_width * 100, 2),
            })

        return table


def _theoretical_power(wind_speed: float, profile: TurbineProfile) -> float:
    """三次方理論功率計算。"""
    if wind_speed < profile.cut_in_speed_ms or wind_speed > profile.cut_out_speed_ms:
        return 0.0
    if wind_speed >= profile.rated_wind_speed_ms:
        return profile.rated_power_kw
    divisor = profile.rated_wind_speed_ms - profile.cut_in_speed_ms
    if divisor <= 0:
        return 0.0
    return profile.rated_power_kw * ((wind_speed - profile.cut_in_speed_ms) / divisor) ** 3
