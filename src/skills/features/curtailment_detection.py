"""降載偵測技能 — 識別風機被限電或主動降載的時段。

降載 (curtailment) 常見原因：
1. 電網調度限電
2. 噪音管理（夜間降轉速）
3. 陰影閃爍控制
4. 電壓/頻率調節
5. 手動降載（測試或維護）

偵測方法：
- 在額定風速以上，功率明顯低於理論值（但風機仍在運轉）
- 功率被截斷在某個固定值（非額定功率）
- 轉速或槳距角在正常風速下異常
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.skills.base import BaseSkill, ProgressCallback, SkillInput, SkillOutput, SkillStatus
from src.utils.logger import get_logger

logger = get_logger("skill.curtailment_detection")

_WIND_SPEED_COLS = [
    "wind_speed",
    "Wind Speed_Mean",
    "wind_speed_mean",
    "ws_mean",
]
_POWER_COLS = [
    "power",
    "active_power",
    "Active Power_Mean",
    "power_mean",
    "power_output",
]
_PITCH_COLS = [
    "blade_pitch_angle",
    "pitch_angle",
    "Pitch Angle_Mean",
    "pitch",
    "blade_pitch",
]


def _find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    cols_lower = {c.lower().strip(): c for c in df.columns}
    for cand in candidates:
        if cand.lower().strip() in cols_lower:
            return cols_lower[cand.lower().strip()]
    return None


class CurtailmentDetectionSkill(BaseSkill):
    """降載偵測 — 識別被限電或主動降載的時段與損失量。"""

    skill_id = "curtailment_detection"
    display_name = "降載偵測"
    description = "識別風機降載/限電事件，估算發電量損失"
    version = "1.0.0"

    async def execute(
        self,
        inp: SkillInput,
        progress_cb: ProgressCallback = None,
    ) -> SkillOutput:
        """執行降載偵測。"""
        df = inp.dataframe
        if df is None:
            return SkillOutput(
                status=SkillStatus.ERROR,
                errors=["未收到 DataFrame 輸入"],
            )

        rated_power = inp.parameters.get("rated_power") or inp.parameters.get(
            "rated_power_kw", 2050.0
        )
        cut_in = inp.parameters.get("cut_in_speed", 3.0)

        if progress_cb:
            await progress_cb(0.1, "識別欄位...")

        ws_col = _find_col(df, _WIND_SPEED_COLS)
        power_col = _find_col(df, _POWER_COLS)

        if not ws_col or not power_col:
            return SkillOutput(
                status=SkillStatus.ERROR,
                errors=[f"缺少必要欄位：wind_speed={ws_col}, power={power_col}"],
            )

        if progress_cb:
            await progress_cb(0.3, "偵測降載事件...")

        result = self._detect(df, ws_col, power_col, rated_power, cut_in)

        if progress_cb:
            await progress_cb(1.0, f"偵測完成 — {result['curtailment_events']} 個事件")

        return SkillOutput(
            status=SkillStatus.SUCCESS,
            data=result,
            dataframe=df,
            summary=(
                f"降載偵測：{result['curtailment_events']} 個事件, "
                f"影響 {result['curtailment_ratio_pct']:.1f}% 資料, "
                f"估計損失 {result['estimated_energy_loss_kwh']:.0f} kWh"
            ),
        )

    def _detect(
        self,
        df: pd.DataFrame,
        ws_col: str,
        power_col: str,
        rated_power: float,
        cut_in: float,
    ) -> dict[str, Any]:
        """核心降載偵測邏輯。"""
        ws = df[ws_col].copy()
        power = df[power_col].copy()

        # 正常運轉條件：風速 > cut_in 且功率 > 0
        operating = (ws > cut_in) & (power > 0)

        # 計算理論功率（簡化三次方模型 + 額定截斷）
        rated_ws = self._estimate_rated_speed(ws[operating], power[operating], rated_power)
        theoretical = self._theoretical_power(ws, rated_power, cut_in, rated_ws)

        # 降載判定：實際功率 < 理論功率 × 0.85 且風速 > rated_ws × 0.8
        # （排除低風速段的自然偏差）
        high_wind = ws > rated_ws * 0.8
        power_deficit = (power < theoretical * 0.85) & operating & high_wind

        # 額外判定：功率被截斷在某固定值（非額定功率）
        # 檢查功率是否集中在某個非額定的截斷點
        partial_curtail = self._detect_partial_cap(power[operating & high_wind], rated_power)

        # 合併降載標記
        is_curtailed = power_deficit.copy()
        if partial_curtail["detected"]:
            cap_value = partial_curtail["cap_value"]
            is_curtailed = is_curtailed | (
                operating & high_wind & (power > cap_value * 0.95) & (power < cap_value * 1.05)
            )

        curtailed_count = int(is_curtailed.sum())
        total_operating = int(operating.sum())
        curtail_ratio = curtailed_count / max(total_operating, 1) * 100

        # 估算能量損失（kWh）
        # 推斷取樣間隔（秒），預設 600 秒（10 分鐘）
        sampling_hours = self._infer_interval_hours(df)
        power_diff = (theoretical - power).clip(lower=0)
        energy_loss = float(power_diff[is_curtailed].sum() * sampling_hours)

        # 時段分析
        hourly_curtail: dict[str, float] = {}
        if hasattr(df.index, "hour"):
            hourly = pd.DataFrame({"curtailed": is_curtailed}).copy()
            hourly["hour"] = df.index.hour
            hourly_stats = hourly.groupby("hour")["curtailed"].mean() * 100
            hourly_curtail = {str(h): round(v, 1) for h, v in hourly_stats.items() if v > 0}

        return {
            "curtailment_events": curtailed_count,
            "total_operating_records": total_operating,
            "curtailment_ratio_pct": round(curtail_ratio, 2),
            "estimated_energy_loss_kwh": round(energy_loss, 1),
            "rated_power_kw": rated_power,
            "estimated_rated_speed_ms": round(rated_ws, 1),
            "partial_cap": partial_curtail,
            "hourly_curtailment_pct": hourly_curtail,
        }

    @staticmethod
    def _estimate_rated_speed(ws: pd.Series, power: pd.Series, rated_power: float) -> float:
        """估算額定風速：功率首次達到 95% 額定的風速。"""
        threshold = rated_power * 0.95
        above = ws[power >= threshold]
        if above.empty:
            return 12.0  # 預設
        return float(above.quantile(0.1))  # 取低端 10%，避免離群值

    @staticmethod
    def _theoretical_power(
        ws: pd.Series, rated: float, cut_in: float, rated_ws: float
    ) -> pd.Series:
        """簡化理論功率：三次方模型 + 額定截斷。"""
        # P = rated × ((ws - cut_in) / (rated_ws - cut_in))³，截斷於 rated
        ratio = ((ws - cut_in) / max(rated_ws - cut_in, 0.1)).clip(lower=0)
        return (rated * ratio**3).clip(upper=rated)

    @staticmethod
    def _detect_partial_cap(power: pd.Series, rated_power: float) -> dict[str, Any]:
        """偵測功率是否被截斷在某個非額定值。"""
        if power.empty:
            return {"detected": False}

        # 檢查 80% ~ 98% 額定功率區間是否有異常集中
        lower = rated_power * 0.5
        upper = rated_power * 0.98
        band = power[(power > lower) & (power < upper)]

        if len(band) < 20:
            return {"detected": False}

        # 用直方圖找尖峰
        hist, edges = np.histogram(band, bins=50)
        peak_idx = np.argmax(hist)
        peak_count = hist[peak_idx]
        total = len(band)

        # 如果某個 bin 佔比 > 15%，可能是截斷點
        if peak_count / max(total, 1) > 0.15:
            cap_value = float((edges[peak_idx] + edges[peak_idx + 1]) / 2)
            return {
                "detected": True,
                "cap_value": round(cap_value, 1),
                "cap_ratio_of_rated": round(cap_value / rated_power * 100, 1),
                "affected_records": int(peak_count),
            }

        return {"detected": False}

    @staticmethod
    def _infer_interval_hours(df: pd.DataFrame) -> float:
        """推斷 DataFrame 的取樣間隔（小時）。"""
        if isinstance(df.index, pd.DatetimeIndex) and len(df.index) >= 2:
            median_diff = df.index.to_series().diff().median()
            if pd.notna(median_diff):
                return median_diff.total_seconds() / 3600
        return 10 / 60  # 預設 10 分鐘
