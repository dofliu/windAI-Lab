"""風機領域特徵工程模組。

根據風機運行領域知識，從 SCADA 資料中萃取功率曲線特徵、
溫度差異特徵、以及運行狀態特徵，供下游異常偵測與健康評估使用。

適用風機：Senvion MM92 (2050 kW, 92m 轉子直徑)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Senvion MM92 預設參數
_DEFAULT_RATED_POWER = 2050  # 額定功率 (kW)
_DEFAULT_ROTOR_DIAMETER = 92  # 轉子直徑 (m)
_DEFAULT_CUT_IN = 3.0  # 切入風速 (m/s)
_DEFAULT_RATED_WIND = 12.5  # 額定風速 (m/s)
_DEFAULT_CUT_OUT = 25.0  # 切出風速 (m/s)


def _find_col(df: pd.DataFrame, keywords: list[str], suffix: str = "_Mean") -> str | None:
    """根據關鍵字在欄位中搜尋匹配的欄位名稱。

    Parameters
    ----------
    df : pd.DataFrame
        資料表。
    keywords : list[str]
        搜尋關鍵字。
    suffix : str
        優先匹配的後綴。

    Returns
    -------
    str or None
        匹配的欄位名稱。
    """
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


def _theoretical_power(
    wind_speed: pd.Series, rated_power: float = _DEFAULT_RATED_POWER
) -> pd.Series:
    """計算理論功率曲線（簡化三次方模型）。

    使用切入風速至額定風速間的三次方關係估算理論功率。

    Parameters
    ----------
    wind_speed : pd.Series
        風速序列 (m/s)。
    rated_power : float
        額定功率 (kW)。

    Returns
    -------
    pd.Series
        理論功率序列 (kW)。
    """
    ws = wind_speed.copy()
    power = pd.Series(0.0, index=ws.index)

    # 切入 ~ 額定風速：三次方關係
    partial_mask = (ws >= _DEFAULT_CUT_IN) & (ws < _DEFAULT_RATED_WIND)
    power[partial_mask] = (
        rated_power
        * ((ws[partial_mask] - _DEFAULT_CUT_IN) / (_DEFAULT_RATED_WIND - _DEFAULT_CUT_IN)) ** 3
    )

    # 額定風速 ~ 切出風速：額定功率
    full_mask = (ws >= _DEFAULT_RATED_WIND) & (ws <= _DEFAULT_CUT_OUT)
    power[full_mask] = rated_power

    # 超過切出風速：關機
    power[ws > _DEFAULT_CUT_OUT] = 0.0

    return power


def compute_power_curve_features(
    df: pd.DataFrame,
    rated_power: float = _DEFAULT_RATED_POWER,
) -> pd.DataFrame:
    """計算功率曲線相關特徵。

    新增欄位：
    - theoretical_power：理論功率 (kW)
    - power_curve_deviation：實際功率與理論功率的偏差 (kW)
    - power_curve_deviation_pct：偏差百分比 (%)
    - capacity_factor：容量因數（實際功率 / 額定功率）
    - normalized_power：正規化功率（0~1）

    Parameters
    ----------
    df : pd.DataFrame
        含風速與功率欄位的 SCADA 資料。
    rated_power : float
        額定功率 (kW)，預設 2050。

    Returns
    -------
    pd.DataFrame
        新增功率曲線特徵後的資料表。
    """
    df = df.copy()

    ws_col = _find_col(df, ["wind speed", "windspeed", "ws"])
    power_col = _find_col(df, ["power", "active power"])

    if ws_col and power_col:
        ws = df[ws_col].astype(float)
        pwr = df[power_col].astype(float)

        # 理論功率
        df["theoretical_power"] = _theoretical_power(ws, rated_power)

        # 功率曲線偏差
        df["power_curve_deviation"] = pwr - df["theoretical_power"]
        with np.errstate(divide="ignore", invalid="ignore"):
            df["power_curve_deviation_pct"] = np.where(
                df["theoretical_power"] > 10,
                (df["power_curve_deviation"] / df["theoretical_power"]) * 100,
                0.0,
            )

        # 容量因數
        df["capacity_factor"] = pwr / rated_power

        # 正規化功率
        df["normalized_power"] = np.clip(pwr / rated_power, 0, 1.2)

    return df


def compute_temperature_features(df: pd.DataFrame) -> pd.DataFrame:
    """計算溫度差異與滾動統計特徵。

    新增欄位（視可用欄位而定）：
    - gear_oil_temp_delta：齒輪箱油溫 - 環境溫度
    - gen_bearing_front_delta：發電機前軸承溫度 - 環境溫度
    - gen_bearing_rear_delta：發電機後軸承溫度 - 環境溫度
    - gear_oil_temp_rolling_mean：齒輪箱油溫 24 小時滾動平均
    - gear_oil_temp_rolling_std：齒輪箱油溫 24 小時滾動標準差

    Parameters
    ----------
    df : pd.DataFrame
        含溫度相關欄位的 SCADA 資料。

    Returns
    -------
    pd.DataFrame
        新增溫度特徵後的資料表。
    """
    df = df.copy()

    ambient_col = _find_col(df, ["ambient temp", "nacelle ambient", "ambient"])
    gear_oil_col = _find_col(df, ["gear oil temp", "gearoil temp", "gear oil"])
    gear_oil_inlet_col = _find_col(df, ["gear oil inlet", "gearoil inlet"])
    gen_front_col = _find_col(df, ["generator bearing front", "gen bearing front"])
    gen_rear_col = _find_col(df, ["generator bearing rear", "gen bearing rear"])
    front_bearing_col = _find_col(df, ["front bearing temp"])
    rear_bearing_col = _find_col(df, ["rear bearing temp"])

    ambient = df[ambient_col].astype(float) if ambient_col else None

    # 溫度差異
    if gear_oil_col and ambient is not None:
        df["gear_oil_temp_delta"] = df[gear_oil_col].astype(float) - ambient

    if gear_oil_inlet_col and gear_oil_col:
        df["gear_oil_temp_diff_inlet"] = df[gear_oil_col].astype(float) - df[
            gear_oil_inlet_col
        ].astype(float)

    if gen_front_col and ambient is not None:
        df["gen_bearing_front_delta"] = df[gen_front_col].astype(float) - ambient

    if gen_rear_col and ambient is not None:
        df["gen_bearing_rear_delta"] = df[gen_rear_col].astype(float) - ambient

    if front_bearing_col and ambient is not None:
        df["front_bearing_delta"] = df[front_bearing_col].astype(float) - ambient

    if rear_bearing_col and ambient is not None:
        df["rear_bearing_delta"] = df[rear_bearing_col].astype(float) - ambient

    # 滾動統計（144 筆 = 24 小時 @ 10 分鐘間隔）
    rolling_window = 144

    if gear_oil_col:
        gear_series = df[gear_oil_col].astype(float)
        df["gear_oil_temp_rolling_mean"] = gear_series.rolling(
            window=rolling_window, min_periods=72
        ).mean()
        df["gear_oil_temp_rolling_std"] = gear_series.rolling(
            window=rolling_window, min_periods=72
        ).std()

    if gen_front_col:
        gen_f = df[gen_front_col].astype(float)
        df["gen_front_rolling_mean"] = gen_f.rolling(window=rolling_window, min_periods=72).mean()

    return df


def compute_operational_features(df: pd.DataFrame) -> pd.DataFrame:
    """計算運行狀態與機械特徵。

    新增欄位：
    - operating_state：運行狀態分類（idle/partial/full/shutdown）
    - tip_speed_ratio：葉尖速度比估算值

    Parameters
    ----------
    df : pd.DataFrame
        含風速、功率、轉子轉速等欄位的 SCADA 資料。

    Returns
    -------
    pd.DataFrame
        新增運行特徵後的資料表。
    """
    df = df.copy()

    ws_col = _find_col(df, ["wind speed", "windspeed", "ws"])
    power_col = _find_col(df, ["power", "active power"])
    rotor_col = _find_col(df, ["rotor speed", "rotor rpm"])

    # ── 運行狀態分類 ──
    if ws_col and power_col:
        ws = df[ws_col].astype(float)
        pwr = df[power_col].astype(float)

        conditions = [
            (ws < _DEFAULT_CUT_IN) | (pwr <= 0),  # idle
            (ws >= _DEFAULT_CUT_IN) & (pwr > 0) & (pwr < _DEFAULT_RATED_POWER * 0.95),  # partial
            pwr >= _DEFAULT_RATED_POWER * 0.95,  # full
            ws > _DEFAULT_CUT_OUT,  # shutdown
        ]
        choices = ["idle", "partial", "full", "shutdown"]
        df["operating_state"] = np.select(conditions, choices, default="unknown")

    # ── 葉尖速度比 ──
    if ws_col and rotor_col:
        ws = df[ws_col].astype(float)
        rotor_rpm = df[rotor_col].astype(float)
        radius = _DEFAULT_ROTOR_DIAMETER / 2.0

        # TSR = (omega * R) / V = (RPM * 2 * pi / 60) * R / V
        omega = rotor_rpm * 2 * np.pi / 60
        with np.errstate(divide="ignore", invalid="ignore"):
            tsr = np.where(ws > 1.0, (omega * radius) / ws, np.nan)
        df["tip_speed_ratio"] = tsr

    return df
