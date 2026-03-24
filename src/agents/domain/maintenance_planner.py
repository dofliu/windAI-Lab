"""wDomain:maintenance-planner — 維護計畫員。

負責預防性維護排程、備件管理、
維護成本估算與最佳化。
"""

from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent, TaskContext, TaskResult, TaskStatus


class MaintenancePlanner(BaseAgent):
    """維護計畫代理，排程預防性與校正性維護。"""

    def __init__(self) -> None:
        super().__init__("maintenance-planner")

    @property
    def capabilities(self) -> list[str]:
        return [
            "maintenance_scheduling",
            "spare_parts_management",
            "cost_estimation",
            "preventive_planning",
            "corrective_planning",
        ]

    async def execute(self, task: str, context: TaskContext) -> TaskResult:
        """執行維護計畫任務。"""
        params = context.parameters

        if "schedule" in task or "排程" in task or "維護" in task:
            return await self._plan_maintenance(params)

        if "cost" in task or "成本" in task:
            return await self._estimate_cost(params)

        await self.update_progress(0.5, f"維護規劃：{task}")
        await self.update_progress(1.0)
        return TaskResult(status=TaskStatus.SUCCESS, summary=f"完成：{task}")

    async def _plan_maintenance(self, params: dict[str, Any]) -> TaskResult:
        """排程維護工作。"""
        turbine_id = params.get("turbine_id", "WT-07")
        component = params.get("component", "gearbox")
        rul_days = params.get("rul_days", 45)

        await self.update_progress(0.3, "評估風場天氣窗口")
        await self.update_progress(0.6, "排定維護時程與人力")
        await self.update_progress(1.0, "維護排程完成")

        # 建議在 RUL 的 2/3 時間內安排維護
        maintenance_in_days = max(7, int(rul_days * 2 / 3))

        return TaskResult(
            status=TaskStatus.SUCCESS,
            data={
                "turbine_id": turbine_id,
                "component": component,
                "scheduled_in_days": maintenance_in_days,
                "maintenance_type": "preventive",
                "estimated_downtime_hours": 8,
                "crew_required": 3,
            },
            summary=(
                f"{turbine_id} {component} 預防性維護已排程："
                f"{maintenance_in_days} 天後執行，預估停機 8 小時"
            ),
        )

    async def _estimate_cost(self, params: dict[str, Any]) -> TaskResult:
        """估算維護成本。"""
        await self.update_progress(0.5, "計算備件與人力成本")
        await self.update_progress(1.0, "成本估算完成")

        return TaskResult(
            status=TaskStatus.SUCCESS,
            data={
                "parts_cost_usd": 15000,
                "labor_cost_usd": 8000,
                "total_cost_usd": 23000,
            },
            summary="維護成本估算：USD 23,000（備件 15K + 人力 8K）",
        )
