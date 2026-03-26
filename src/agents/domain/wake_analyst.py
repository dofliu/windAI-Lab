"""wDomain:wake-analyst — 尾流效應分析師。

負責風機尾流效應模擬與分析，使用 Jensen (Park) 模型
計算風機間的交互影響，優化風場佈局與運轉策略。
"""

from __future__ import annotations

import asyncio
import math
from typing import Any

import numpy as np

from src.agents.base import BaseAgent, TaskContext, TaskResult, TaskStatus


class WakeAnalyst(BaseAgent):
    """尾流效應分析代理。

    能力：
    - Jensen (Park) 尾流模型模擬
    - 風場佈局尾流損失計算
    - 風向與風速條件分析
    - 尾流疊加效應評估
    - 風場效率最佳化建議
    """

    def __init__(self) -> None:
        super().__init__("wake-analyst")

    @property
    def capabilities(self) -> list[str]:
        return [
            "jensen_wake_model",
            "wake_loss_calculation",
            "wind_direction_analysis",
            "wake_superposition",
            "farm_efficiency_optimization",
            "layout_analysis",
        ]

    async def execute(self, task: str, context: TaskContext) -> TaskResult:
        """執行尾流分析任務。"""
        params = context.parameters

        if "simulate" in task or "模擬" in task or "計算" in task:
            return await self._simulate_wake(params)

        if "layout" in task or "佈局" in task:
            return await self._analyze_layout(params)

        if "efficiency" in task or "效率" in task:
            return await self._calculate_farm_efficiency(params)

        await self.update_progress(0.5, f"尾流分析：{task}")
        await self.update_progress(1.0)
        return TaskResult(status=TaskStatus.SUCCESS, summary=f"尾流分析任務完成：{task}")

    async def _simulate_wake(self, params: dict[str, Any]) -> TaskResult:
        """執行 Jensen (Park) 尾流模型模擬。"""
        # 模擬參數
        wind_speed = params.get("wind_speed", 10.0)  # m/s
        wind_direction = params.get("wind_direction", 270.0)  # 度
        ct = params.get("thrust_coefficient", 0.8)  # 推力係數
        rotor_diameter = params.get("rotor_diameter", 126.0)  # m
        _hub_height = params.get("hub_height", 90.0)  # m
        wake_decay = params.get("wake_decay_constant", 0.04)  # Jensen k 值

        # 示範用預設佈局（3 台風機排成一行，間距 500m）
        turbine_positions = params.get(
            "turbine_positions",
            [
                {"id": "WT-01", "x": 0, "y": 0},
                {"id": "WT-02", "x": 500, "y": 0},
                {"id": "WT-03", "x": 1000, "y": 0},
            ],
        )

        await self.update_progress(
            0.1, f"初始化 Jensen 模型（風速={wind_speed} m/s, 風向={wind_direction}°）"
        )

        loop = asyncio.get_event_loop()

        def _compute() -> dict[str, Any]:
            n = len(turbine_positions)
            rotor_r = rotor_diameter / 2.0

            # 將風向轉為弧度（氣象慣例：0=北，順時針）
            wd_rad = math.radians(270 - wind_direction)

            # 計算每台風機的有效風速
            effective_speeds: dict[str, float] = {}
            wake_deficits: dict[str, list[dict[str, Any]]] = {}

            for i, t_down in enumerate(turbine_positions):
                total_deficit_sq = 0.0
                deficit_sources: list[dict[str, Any]] = []

                for j, t_up in enumerate(turbine_positions):
                    if i == j:
                        continue

                    # 計算沿風向的距離
                    dx = t_down["x"] - t_up["x"]
                    dy = t_down["y"] - t_up["y"]
                    streamwise = dx * math.cos(wd_rad) + dy * math.sin(wd_rad)

                    if streamwise <= 0:
                        continue  # 上游風機

                    # 橫向距離
                    crosswind = abs(-dx * math.sin(wd_rad) + dy * math.cos(wd_rad))

                    # Jensen 尾流半徑
                    wake_radius = rotor_r + wake_decay * streamwise

                    if crosswind > wake_radius:
                        continue  # 不在尾流區

                    # Jensen 速度虧損
                    deficit = (1 - math.sqrt(1 - ct)) * (rotor_r / wake_radius) ** 2

                    # 部分遮蔽修正
                    overlap = max(0, min(1, (wake_radius - crosswind) / rotor_diameter))
                    deficit *= overlap

                    total_deficit_sq += deficit**2
                    deficit_sources.append(
                        {
                            "upstream": t_up["id"],
                            "distance_m": round(streamwise, 1),
                            "deficit_pct": round(deficit * 100, 2),
                        }
                    )

                # 尾流疊加（RSS 方法）
                combined_deficit = math.sqrt(total_deficit_sq)
                eff_speed = wind_speed * (1 - combined_deficit)

                effective_speeds[t_down["id"]] = round(eff_speed, 3)
                wake_deficits[t_down["id"]] = deficit_sources

            # 計算功率損失（P ∝ v³）
            power_ratios: dict[str, float] = {}
            total_loss = 0.0
            for tid, eff_v in effective_speeds.items():
                ratio = (eff_v / wind_speed) ** 3
                power_ratios[tid] = round(ratio * 100, 2)
                total_loss += 1 - ratio

            avg_efficiency = round((1 - total_loss / n) * 100, 2)

            return {
                "model": "Jensen (Park)",
                "parameters": {
                    "wind_speed_ms": wind_speed,
                    "wind_direction_deg": wind_direction,
                    "thrust_coefficient": ct,
                    "rotor_diameter_m": rotor_diameter,
                    "wake_decay_constant": wake_decay,
                },
                "turbine_count": n,
                "effective_wind_speeds": effective_speeds,
                "power_ratios_pct": power_ratios,
                "wake_interactions": wake_deficits,
                "farm_efficiency_pct": avg_efficiency,
                "total_wake_loss_pct": round(100 - avg_efficiency, 2),
            }

        result_data = await loop.run_in_executor(None, _compute)
        await self.update_progress(
            1.0, f"尾流模擬完成：風場效率 {result_data['farm_efficiency_pct']}%"
        )

        return TaskResult(
            status=TaskStatus.SUCCESS,
            data=result_data,
            summary=(
                f"Jensen 尾流模擬完成：風場效率 {result_data['farm_efficiency_pct']}%，"
                f"尾流損失 {result_data['total_wake_loss_pct']}%"
            ),
        )

    async def _analyze_layout(self, params: dict[str, Any]) -> TaskResult:
        """分析風場佈局的尾流影響。"""
        await self.update_progress(0.1, "分析風場佈局")

        # 模擬多個風向的尾流效應
        directions = list(range(0, 360, 30))  # 每 30 度
        efficiency_by_direction: dict[str, float] = {}

        for i, wd in enumerate(directions):
            params_copy = {**params, "wind_direction": wd, "wind_speed": 10.0}
            result = await self._simulate_wake(params_copy)
            if result.status == TaskStatus.SUCCESS:
                efficiency_by_direction[f"{wd}°"] = result.data["farm_efficiency_pct"]

            progress = 0.1 + 0.8 * (i + 1) / len(directions)
            await self.update_progress(progress, f"風向 {wd}° 模擬完成")

        avg_eff = (
            round(np.mean(list(efficiency_by_direction.values())), 2)
            if efficiency_by_direction
            else 0.0
        )

        worst_dir = min(efficiency_by_direction, key=efficiency_by_direction.get) if efficiency_by_direction else "N/A"  # type: ignore[arg-type]
        best_dir = max(efficiency_by_direction, key=efficiency_by_direction.get) if efficiency_by_direction else "N/A"  # type: ignore[arg-type]

        await self.update_progress(1.0, f"佈局分析完成：平均效率 {avg_eff}%")

        return TaskResult(
            status=TaskStatus.SUCCESS,
            data={
                "efficiency_by_direction": efficiency_by_direction,
                "average_efficiency_pct": avg_eff,
                "worst_direction": worst_dir,
                "best_direction": best_dir,
            },
            summary=(
                f"風場佈局分析完成：平均效率 {avg_eff}%，"
                f"最差風向 {worst_dir}，最佳風向 {best_dir}"
            ),
        )

    async def _calculate_farm_efficiency(self, params: dict[str, Any]) -> TaskResult:
        """計算風場整體效率。"""
        await self.update_progress(0.2, "計算風場效率")
        result = await self._simulate_wake(params)
        if result.status != TaskStatus.SUCCESS:
            return result

        await self.update_progress(1.0)
        return TaskResult(
            status=TaskStatus.SUCCESS,
            data={
                "farm_efficiency_pct": result.data.get("farm_efficiency_pct", 0),
                "wake_loss_pct": result.data.get("total_wake_loss_pct", 0),
                "turbine_details": result.data.get("power_ratios_pct", {}),
            },
            summary=f"風場效率：{result.data.get('farm_efficiency_pct', 0)}%",
        )
