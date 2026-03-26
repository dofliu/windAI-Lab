"""風機參數自動推斷技能。

從 SCADA 資料中自動推斷風機運轉參數，取代硬編碼值：
- 額定功率 (rated_power)
- 切入風速 (cut_in_speed)
- 切出風速 (cut_out_speed)
- 額定風速 (rated_wind_speed)
- 取樣頻率 (sampling_interval_seconds)
- 轉子直徑 (rotor_diameter，若有轉速資料)

推斷結果會寫入 SkillOutput.data["turbine_profile"]，
後續技能可直接使用這些參數，不再依賴硬編碼。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.skills.base import BaseSkill, SkillInput, SkillOutput, SkillStatus


class TurbineProfilerSkill(BaseSkill):
    """從 SCADA 資料自動推斷風機運轉參數。"""

    skill_id = "turbine_profiler"
    display_name = "風機參數推斷"
    description = "自動從資料推斷額定功率、切入/切出風速、取樣頻率等"
    version = "1.0.0"

    async def execute(
        self,
        inp: SkillInput,
        progress_cb: object | None = None,
    ) -> SkillOutput:
        """執行風機參數推斷。"""
        df = inp.dataframe if inp.dataframe is not None else inp.data
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            return SkillOutput(
                status=SkillStatus.ERROR,
                data={"error": "No DataFrame provided"},
                summary="無資料可分析",
            )

        profile = _infer_turbine_profile(df)

        return SkillOutput(
            status=SkillStatus.SUCCESS,
            data={"turbine_profile": profile},
            dataframe=df,
            summary=(
                f"額定功率 {profile['rated_power_kw']:.0f} kW, "
                f"切入 {profile['cut_in_speed_ms']:.1f} m/s, "
                f"取樣 {profile['sampling_interval_display']}"
            ),
        )


def _infer_turbine_profile(df: pd.DataFrame) -> dict:
    """從 DataFrame 推斷風機運轉參數。

    使用統計方法而非硬編碼值，適用於任何風機型號。
    """
    from src.data_pipeline.cleaning.scada_cleaner import _find_column

    profile: dict = {}

    # ── 1. 尋找關鍵欄位 ──
    ws_col = _find_column(df, ["wind speed", "windspeed", "ws"], "_Mean")
    pw_col = _find_column(df, ["power", "active power"], "_Mean")
    rs_col = _find_column(df, ["rotor speed", "genspeed", "gen_rpm"], "_Mean")

    # 確保數值型態
    ws = pd.to_numeric(df[ws_col], errors="coerce") if ws_col else None
    pw = pd.to_numeric(df[pw_col], errors="coerce") if pw_col else None
    rs = pd.to_numeric(df[rs_col], errors="coerce") if rs_col else None

    # ── 2. 額定功率 (rated_power) ──
    # 方法：取功率的 98th percentile（排除瞬時過載）
    if pw is not None:
        pw_positive = pw[pw > 10]
        if len(pw_positive) > 100:
            rated_power = float(pw_positive.quantile(0.98))
        else:
            rated_power = float(pw.max()) if pw.max() > 0 else 2050.0
    else:
        rated_power = 2050.0  # fallback

    profile["rated_power_kw"] = round(rated_power, 1)

    # ── 3. 切入風速 (cut_in_speed) ──
    # 方法：找功率從 0 → >0 的風速轉折點
    if ws is not None and pw is not None:
        cut_in = _estimate_cut_in_speed(ws, pw, rated_power)
    else:
        cut_in = 3.0

    profile["cut_in_speed_ms"] = round(cut_in, 1)

    # ── 4. 切出風速 (cut_out_speed) ──
    # 方法：取風速的 99.5th percentile（正常運轉範圍上限）
    if ws is not None:
        ws_valid = ws[(ws > 0) & (ws < 100)]
        if len(ws_valid) > 100:
            cut_out = float(ws_valid.quantile(0.995))
            cut_out = max(cut_out, 20.0)  # 至少 20 m/s
            cut_out = min(cut_out, 35.0)  # 最多 35 m/s
        else:
            cut_out = 25.0
    else:
        cut_out = 25.0

    profile["cut_out_speed_ms"] = round(cut_out, 1)

    # ── 5. 額定風速 (rated_wind_speed) ──
    # 方法：找功率達到額定值 90% 時的平均風速
    if ws is not None and pw is not None:
        near_rated = pw > rated_power * 0.9
        if near_rated.sum() > 10:
            rated_wind = float(ws[near_rated].median())
        else:
            rated_wind = 12.5
        rated_wind = max(rated_wind, cut_in + 2)
        rated_wind = min(rated_wind, cut_out - 2)
    else:
        rated_wind = 12.5

    profile["rated_wind_speed_ms"] = round(rated_wind, 1)

    # ── 6. 取樣頻率 ──
    sampling_seconds = _infer_sampling_rate(df)
    profile["sampling_interval_seconds"] = sampling_seconds

    if sampling_seconds < 5:
        profile["sampling_interval_display"] = f"{sampling_seconds}s"
    elif sampling_seconds < 3600:
        profile["sampling_interval_display"] = f"{sampling_seconds // 60}min"
    else:
        profile["sampling_interval_display"] = f"{sampling_seconds // 3600}h"

    # ── 7. 自適應滾動視窗（24 小時）──
    records_per_day = int(86400 / max(sampling_seconds, 1))
    profile["rolling_window_24h"] = records_per_day
    profile["rolling_window_min_periods"] = max(records_per_day // 2, 1)

    # ── 8. 轉子直徑推斷（若有轉速資料）──
    if rs is not None and ws is not None:
        rotor_diameter = _estimate_rotor_diameter(ws, rs, pw, rated_power)
    else:
        rotor_diameter = None

    profile["rotor_diameter_m"] = rotor_diameter

    # ── 9. 運轉率 ──
    if pw is not None:
        operating = pw > rated_power * 0.01
        profile["operating_ratio"] = round(float(operating.mean()), 3)
    else:
        profile["operating_ratio"] = None

    # ── 10. 資料品質指標 ──
    profile["total_records"] = len(df)
    # 統計可轉為數值的欄位數
    num_count = 0
    for col in df.columns:
        if df[col].dtype in (np.float64, np.float32, np.int64, np.int32):
            num_count += 1
        elif pd.to_numeric(df[col], errors="coerce").notna().mean() > 0.5:
            num_count += 1
    profile["numeric_columns"] = num_count
    profile["total_columns"] = len(df.columns)

    return profile


def _estimate_cut_in_speed(
    ws: pd.Series, pw: pd.Series, rated_power: float
) -> float:
    """從功率曲線推斷切入風速。

    方法：將風速分成 0.5 m/s 的 bin，找到平均功率首次超過
    額定功率 1% 的 bin → 該 bin 的中點即為切入風速。
    """
    valid = ws.notna() & pw.notna() & (ws > 0) & (ws < 30)
    if valid.sum() < 100:
        return 3.0

    ws_v = ws[valid]
    pw_v = pw[valid]

    bins = np.arange(0, 30.5, 0.5)
    bin_idx = np.digitize(ws_v, bins) - 1

    threshold = rated_power * 0.02  # 額定功率的 2%

    for i in range(len(bins) - 1):
        mask = bin_idx == i
        if mask.sum() >= 10:
            # 看這個 bin 中「有發電」的比例
            generating_ratio = (pw_v[mask] > threshold).mean()
            # 超過 30% 的時間有發電 = 切入區
            if generating_ratio > 0.3:
                return max(float(bins[i]), 2.0)  # 至少 2 m/s

    return 3.0


def _estimate_rotor_diameter(
    ws: pd.Series, rs: pd.Series, pw: pd.Series, rated_power: float
) -> float | None:
    """從葉尖速度比 (TSR) 反推轉子直徑。

    TSR = (omega × R) / V，典型值 6~8
    → R = TSR × V / omega
    → diameter = 2R
    """
    # 選擇正常運轉區間（功率 20%~80% 額定）
    mask = (
        ws.notna() & rs.notna() & pw.notna()
        & (pw > rated_power * 0.2)
        & (pw < rated_power * 0.8)
        & (rs > 1)  # 轉速 > 1 RPM
        & (ws > 3)
    )

    if mask.sum() < 50:
        return None

    ws_v = ws[mask].values
    rs_v = rs[mask].values

    # omega = RPM × 2π / 60
    omega = rs_v * 2 * np.pi / 60

    # 假設 TSR ≈ 7（大型風機典型值）
    tsr_assumed = 7.0

    # R = TSR × V / omega
    radii = tsr_assumed * ws_v / omega
    radii = radii[(radii > 10) & (radii < 100)]  # 合理範圍

    if len(radii) < 20:
        return None

    diameter = float(np.median(radii) * 2)
    return round(diameter, 1)


def _infer_sampling_rate(df: pd.DataFrame) -> int:
    """從 DatetimeIndex 推斷取樣間隔（秒）。"""
    if not isinstance(df.index, pd.DatetimeIndex):
        return 600  # 預設 10 分鐘

    if len(df) < 3:
        return 600

    diffs = df.index.to_series().diff().dropna()
    if len(diffs) == 0:
        return 600

    median_diff = diffs.median()
    seconds = int(median_diff.total_seconds())

    # 對齊到常見取樣頻率
    common_rates = [1, 2, 5, 10, 30, 60, 300, 600, 900, 3600]
    closest = min(common_rates, key=lambda x: abs(x - seconds))

    return closest
