"""偏航對準分析技能 — 偵測 nacelle direction 與 wind direction 的偏差。

偏航偏移 (yaw misalignment) 是常見的效率損失來源：
- 偏差 > 5° 開始影響發電效率
- 偏差 > 10° 可能導致 5-10% 功率損失
- 偏差 > 15° 需立即檢修偏航系統

分析方法：
1. 計算 nacelle_direction - wind_direction 的角度差（考慮 360° 循環）
2. 按風速分箱統計偏差分布
3. 識別系統性偏移（非隨機風向變化）
4. 估算因偏航偏移造成的功率損失
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.skills.base import BaseSkill, ProgressCallback, SkillInput, SkillOutput, SkillStatus
from src.utils.logger import get_logger

logger = get_logger("skill.yaw_misalignment")

# 欄位候選名稱
_NACELLE_DIR_COLS = [
    "nacelle_direction",
    "nacelle_dir",
    "yaw_angle",
    "nacelle direction",
    "yaw",
    "Nacelle Position_Mean",
]
_WIND_DIR_COLS = [
    "wind_direction",
    "wind_dir",
    "wind direction",
    "Wind Direction_Mean",
    "vane_direction",
]
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


def _find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """從候選名稱中找到第一個存在的欄位。"""
    cols_lower = {c.lower().strip(): c for c in df.columns}
    for cand in candidates:
        if cand.lower().strip() in cols_lower:
            return cols_lower[cand.lower().strip()]
    return None


def _circular_diff(a: pd.Series, b: pd.Series) -> pd.Series:
    """計算兩個角度的循環差值（結果在 -180 ~ +180 之間）。"""
    diff = a - b
    return (diff + 180) % 360 - 180


class YawMisalignmentSkill(BaseSkill):
    """偏航對準分析 — 偵測偏航偏移並估算功率損失。"""

    skill_id = "yaw_misalignment"
    display_name = "偏航對準分析"
    description = "分析 nacelle direction vs wind direction 偏差，估算功率損失"
    version = "1.0.0"

    async def execute(
        self,
        inp: SkillInput,
        progress_cb: ProgressCallback = None,
    ) -> SkillOutput:
        """執行偏航對準分析。"""
        df = inp.dataframe
        if df is None:
            return SkillOutput(
                status=SkillStatus.ERROR,
                errors=["未收到 DataFrame 輸入，需先執行資料載入"],
            )

        if progress_cb:
            await progress_cb(0.1, "識別欄位...")

        nacelle_col = _find_col(df, _NACELLE_DIR_COLS)
        wind_dir_col = _find_col(df, _WIND_DIR_COLS)
        wind_speed_col = _find_col(df, _WIND_SPEED_COLS)
        power_col = _find_col(df, _POWER_COLS)

        if not nacelle_col or not wind_dir_col:
            return SkillOutput(
                status=SkillStatus.ERROR,
                errors=[
                    f"缺少必要欄位：nacelle_direction={nacelle_col}, "
                    f"wind_direction={wind_dir_col}"
                ],
            )

        if progress_cb:
            await progress_cb(0.3, "計算偏航偏差...")

        result = self._analyze(df, nacelle_col, wind_dir_col, wind_speed_col, power_col)

        if progress_cb:
            await progress_cb(1.0, f"偏航分析完成 — 平均偏差 {result['mean_offset']:.1f}°")

        mean_offset = result["mean_offset"]
        severity = (
            "Critical"
            if abs(mean_offset) > 15
            else "High" if abs(mean_offset) > 10 else "Medium" if abs(mean_offset) > 5 else "Low"
        )
        result["severity"] = severity

        return SkillOutput(
            status=SkillStatus.SUCCESS,
            data=result,
            dataframe=df,
            summary=(
                f"偏航偏差：平均 {mean_offset:+.1f}°, "
                f"標準差 {result['std_offset']:.1f}°, "
                f"功率損失估算 {result['estimated_power_loss_pct']:.1f}% "
                f"({severity})"
            ),
        )

    def _analyze(
        self,
        df: pd.DataFrame,
        nacelle_col: str,
        wind_dir_col: str,
        wind_speed_col: str | None,
        power_col: str | None,
    ) -> dict[str, Any]:
        """核心偏航分析邏輯。"""
        yaw_error = _circular_diff(df[nacelle_col], df[wind_dir_col])
        valid = yaw_error.dropna()

        mean_offset = float(valid.mean())
        std_offset = float(valid.std())
        median_offset = float(valid.median())

        # 偏差分布
        abs_error = valid.abs()
        pct_gt5 = float((abs_error > 5).mean() * 100)
        pct_gt10 = float((abs_error > 10).mean() * 100)
        pct_gt15 = float((abs_error > 15).mean() * 100)

        # cos³ 功率損失估算：P_loss ≈ 1 - cos³(yaw_error)
        cos_cubed = np.cos(np.radians(valid)) ** 3
        estimated_loss = float((1 - cos_cubed.mean()) * 100)

        result: dict[str, Any] = {
            "mean_offset": mean_offset,
            "std_offset": std_offset,
            "median_offset": median_offset,
            "pct_above_5deg": round(pct_gt5, 1),
            "pct_above_10deg": round(pct_gt10, 1),
            "pct_above_15deg": round(pct_gt15, 1),
            "estimated_power_loss_pct": round(estimated_loss, 2),
            "total_samples": len(valid),
        }

        # 按風速分箱分析（如有風速欄位）
        if wind_speed_col and wind_speed_col in df.columns:
            bins = [0, 4, 8, 12, 16, 25, 50]
            labels = ["0-4", "4-8", "8-12", "12-16", "16-25", "25+"]
            ws_bin = pd.cut(df[wind_speed_col], bins=bins, labels=labels, right=False)
            binned = pd.DataFrame({"yaw_error": yaw_error, "ws_bin": ws_bin}).dropna()
            if not binned.empty:
                bin_stats = (
                    binned.groupby("ws_bin", observed=True)["yaw_error"]
                    .agg(["mean", "std", "count"])
                    .to_dict("index")
                )
                result["wind_speed_bins"] = {
                    k: {
                        "mean": round(v["mean"], 2),
                        "std": round(v["std"], 2),
                        "count": int(v["count"]),
                    }
                    for k, v in bin_stats.items()
                }

        return result
