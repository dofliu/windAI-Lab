"""IEC 61400-12 功率曲線分箱分析技能。

依據 IEC 61400-12-1 標準，將風速分箱（0.5 m/s 間隔），
計算各箱的平均功率、標準差、資料點數，產出標準化功率曲線。

功能：
1. 標準 0.5 m/s 風速分箱
2. 各箱統計：平均功率、標準差、資料點數
3. AEP 估算（搭配 Rayleigh 分布）
4. 保證功率曲線 vs 實測功率曲線對比（如有保證值）
5. 功率曲線品質指標
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.skills.base import BaseSkill, ProgressCallback, SkillInput, SkillOutput, SkillStatus
from src.utils.logger import get_logger

logger = get_logger("skill.power_curve_binning")

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
    cols_lower = {c.lower().strip(): c for c in df.columns}
    for cand in candidates:
        if cand.lower().strip() in cols_lower:
            return cols_lower[cand.lower().strip()]
    return None


class PowerCurveBinningSkill(BaseSkill):
    """IEC 61400-12 功率曲線分箱分析。"""

    skill_id = "power_curve_binning"
    display_name = "IEC 功率曲線分箱"
    description = "依 IEC 61400-12 標準分箱分析功率曲線，估算 AEP"
    version = "1.0.0"

    async def execute(
        self,
        inp: SkillInput,
        progress_cb: ProgressCallback = None,
    ) -> SkillOutput:
        """執行 IEC 功率曲線分箱。"""
        df = inp.dataframe
        if df is None:
            return SkillOutput(
                status=SkillStatus.ERROR,
                errors=["未收到 DataFrame 輸入"],
            )

        rated_power = inp.parameters.get("rated_power") or inp.parameters.get(
            "rated_power_kw", 2050.0
        )
        bin_width = inp.parameters.get("bin_width", 0.5)
        mean_wind_speed = inp.parameters.get("mean_wind_speed", 7.0)

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
            await progress_cb(0.3, "執行 IEC 分箱...")

        result = self._bin_analysis(df, ws_col, power_col, rated_power, bin_width, mean_wind_speed)

        if progress_cb:
            await progress_cb(1.0, f"分箱完成 — {result['valid_bins']} 個有效箱")

        return SkillOutput(
            status=SkillStatus.SUCCESS,
            data=result,
            dataframe=df,
            summary=(
                f"IEC 分箱：{result['valid_bins']} 個有效箱, "
                f"AEP 估算 {result['estimated_aep_mwh']:.0f} MWh, "
                f"容量因數 {result['capacity_factor_pct']:.1f}%"
            ),
        )

    def _bin_analysis(
        self,
        df: pd.DataFrame,
        ws_col: str,
        power_col: str,
        rated_power: float,
        bin_width: float,
        mean_ws: float,
    ) -> dict[str, Any]:
        """核心 IEC 分箱邏輯。"""
        ws = df[ws_col].dropna()
        power = df[power_col].dropna()
        common_idx = ws.index.intersection(power.index)
        ws = ws.loc[common_idx]
        power = power.loc[common_idx]

        # 建立分箱
        max_ws = min(float(ws.max()), 30.0)
        bin_edges = np.arange(0, max_ws + bin_width, bin_width)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

        ws_binned = pd.cut(
            ws, bins=bin_edges, labels=bin_centers[: len(bin_edges) - 1], right=False
        )

        # 各箱統計
        bin_stats_df = pd.DataFrame({"power": power, "bin": ws_binned}).dropna()
        grouped = bin_stats_df.groupby("bin", observed=True)["power"]

        bin_table: list[dict[str, Any]] = []
        for center, group in grouped:
            if len(group) < 3:  # IEC 要求每箱至少 3 筆
                continue
            bin_table.append(
                {
                    "wind_speed": float(center),
                    "mean_power_kw": round(float(group.mean()), 1),
                    "std_power_kw": round(float(group.std()), 1),
                    "count": int(len(group)),
                    "min_power_kw": round(float(group.min()), 1),
                    "max_power_kw": round(float(group.max()), 1),
                }
            )

        valid_bins = len(bin_table)

        # AEP 估算（Rayleigh 分布）
        aep_mwh = self._estimate_aep_rayleigh(bin_table, bin_width, mean_ws)

        # 容量因數
        theoretical_max = rated_power * 8760 / 1000  # MWh
        cf = aep_mwh / max(theoretical_max, 1) * 100

        # 品質指標
        total_data = int(len(common_idx))
        completeness = total_data / max(len(df), 1) * 100

        return {
            "bin_table": bin_table,
            "valid_bins": valid_bins,
            "bin_width_ms": bin_width,
            "total_data_points": total_data,
            "data_completeness_pct": round(completeness, 1),
            "estimated_aep_mwh": round(aep_mwh, 1),
            "capacity_factor_pct": round(cf, 1),
            "rated_power_kw": rated_power,
            "mean_wind_speed_ms": mean_ws,
        }

    @staticmethod
    def _estimate_aep_rayleigh(
        bin_table: list[dict[str, Any]],
        bin_width: float,
        mean_ws: float,
    ) -> float:
        """使用 Rayleigh 分布估算年發電量。"""
        if not bin_table:
            return 0.0

        # Rayleigh PDF: f(v) = (π/2) × (v/v_mean²) × exp(-π/4 × (v/v_mean)²)
        hours_per_year = 8760
        total_energy = 0.0

        for b in bin_table:
            v = b["wind_speed"]
            p = b["mean_power_kw"]
            if v <= 0:
                continue

            # Rayleigh 機率密度
            x = v / max(mean_ws, 0.1)
            f_v = (np.pi / 2) * x * np.exp(-np.pi / 4 * x**2) / max(mean_ws, 0.1)

            # 此箱對 AEP 的貢獻
            total_energy += p * f_v * bin_width * hours_per_year

        return total_energy / 1000  # kWh → MWh
