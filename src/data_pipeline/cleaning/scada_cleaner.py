"""SCADA 資料清洗模組。

針對風機 SCADA 資料執行基本品質檢查與清洗，包括：
重複時間戳記移除、缺失值處理（小間隙插值、大間隙標記）、
明顯異常值過濾（負功率、超額定功率等），並產出資料品質報告。
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# 風機運行參數預設值
_DEFAULT_CUT_IN = 3.0       # 切入風速 (m/s)
_DEFAULT_RATED_POWER = 2050  # 額定功率 (kW)
_DEFAULT_CUT_OUT = 25.0      # 切出風速 (m/s)
_MAX_GAP_INTERPOLATE = 3     # 最大插值間隙（筆數，即 30 分鐘）


def _find_column(df: pd.DataFrame, keywords: list[str], suffix: str = "_Mean") -> str | None:
    """根據關鍵字尋找欄位名稱。

    在 DataFrame 欄位中搜尋包含指定關鍵字的欄位，
    優先尋找帶有指定後綴（如 _Mean）的欄位。

    Parameters
    ----------
    df : pd.DataFrame
        輸入資料表。
    keywords : list[str]
        搜尋關鍵字列表。
    suffix : str
        優先尋找的後綴。

    Returns
    -------
    str or None
        找到的欄位名稱，找不到時回傳 None。
    """
    cols = df.columns.tolist()

    # 先找帶 suffix 的
    for kw in keywords:
        for col in cols:
            if kw.lower() in col.lower() and suffix.lower() in col.lower():
                return col

    # 再找不帶 suffix 的（排除含 Standard deviation, Minimum, Maximum 的欄位）
    exclude = ["standard deviation", "minimum", "maximum", "min ", "max ", "std"]
    for kw in keywords:
        for col in cols:
            col_lower = col.lower()
            if kw.lower() in col_lower and not any(ex in col_lower for ex in exclude):
                return col

    # 最後不排除任何條件
    for kw in keywords:
        for col in cols:
            if kw.lower() in col.lower():
                return col

    return None


def clean_scada_data(
    df: pd.DataFrame,
    rated_power: float = _DEFAULT_RATED_POWER,
    cut_in_speed: float = _DEFAULT_CUT_IN,
    cut_out_speed: float = _DEFAULT_CUT_OUT,
) -> tuple[pd.DataFrame, dict]:
    """清洗 SCADA 資料並產出品質報告。

    執行下列清洗步驟：
    1. 移除重複時間戳記
    2. 處理缺失值（小間隙線性插值，大間隙保留 NaN）
    3. 移除明顯異常值（負功率 + 風速高於切入、功率超過額定值 110%）

    Parameters
    ----------
    df : pd.DataFrame
        原始 SCADA 資料（時間戳記為索引）。
    rated_power : float
        額定功率 (kW)，預設 2050。
    cut_in_speed : float
        切入風速 (m/s)，預設 3.0。
    cut_out_speed : float
        切出風速 (m/s)，預設 25.0。

    Returns
    -------
    tuple[pd.DataFrame, dict]
        (清洗後的資料表, 品質報告字典)。
        品質報告包含：total_rows, missing_pct, outliers_removed, time_range。
    """
    original_rows = len(df)
    df_clean = df.copy()

    # ── 步驟 1：移除重複時間戳記 ──
    duplicates_before = df_clean.index.duplicated().sum()
    df_clean = df_clean[~df_clean.index.duplicated(keep="first")]

    # ── 步驟 2：處理缺失值 ──
    missing_before = df_clean.isna().sum().sum()
    total_cells = df_clean.shape[0] * df_clean.shape[1]
    missing_pct = (missing_before / total_cells * 100) if total_cells > 0 else 0.0

    # 對數值欄位執行小間隙線性插值
    numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        # 標記連續缺失的組
        is_null = df_clean[col].isna()
        groups = is_null.ne(is_null.shift()).cumsum()
        gap_sizes = is_null.groupby(groups).transform("sum")

        # 只插值小間隙
        small_gap_mask = is_null & (gap_sizes <= _MAX_GAP_INTERPOLATE)
        if small_gap_mask.any():
            df_clean[col] = df_clean[col].interpolate(method="linear", limit=_MAX_GAP_INTERPOLATE)

    # ── 步驟 3：移除明顯異常值 ──
    outliers_removed = 0

    # 尋找風速與功率欄位
    ws_col = _find_column(df_clean, ["wind speed", "windspeed", "ws"], "_Mean")
    power_col = _find_column(df_clean, ["power", "active power"], "_Mean")

    if ws_col and power_col:
        ws = df_clean[ws_col]
        pwr = df_clean[power_col]

        # 異常 1：風速高於切入但功率為負值
        mask_neg_power = (ws > cut_in_speed + 1) & (pwr < -10)

        # 異常 2：功率超過額定值 110%
        mask_over_rated = pwr > rated_power * 1.1

        # 異常 3：風速超過合理範圍（>50 m/s 或 <0）
        mask_bad_ws = (ws < 0) | (ws > 50)

        combined_mask = mask_neg_power | mask_over_rated | mask_bad_ws
        outliers_removed = int(combined_mask.sum())

        # 將異常值設為 NaN 而非直接刪除列（保留時間連續性）
        df_clean.loc[combined_mask, power_col] = np.nan
        if ws_col:
            df_clean.loc[mask_bad_ws, ws_col] = np.nan

    # ── 計算時間範圍 ──
    if isinstance(df_clean.index, pd.DatetimeIndex) and len(df_clean) > 0:
        valid_idx = df_clean.index.dropna()
        time_start = str(valid_idx.min()) if len(valid_idx) > 0 else "N/A"
        time_end = str(valid_idx.max()) if len(valid_idx) > 0 else "N/A"
    else:
        time_start = "N/A"
        time_end = "N/A"

    quality_report = {
        "total_rows": len(df_clean),
        "original_rows": original_rows,
        "duplicates_removed": int(duplicates_before),
        "missing_pct": round(missing_pct, 2),
        "outliers_removed": outliers_removed,
        "time_range": {"start": time_start, "end": time_end},
    }

    return df_clean, quality_report
