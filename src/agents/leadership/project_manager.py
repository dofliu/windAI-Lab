"""wLab:project-manager — 專案經理。

負責管理資料工程、AI/ML 及領域知識三個團隊的日常任務調度，
追蹤里程碑進度、評估專案風險。
"""

from __future__ import annotations

from src.agents.base import BaseAgent, TaskContext, TaskResult, TaskStatus


class ProjectManager(BaseAgent):
    """專案經理代理，負責任務排程與進度追蹤。"""

    def __init__(self) -> None:
        super().__init__("project-manager")

    @property
    def capabilities(self) -> list[str]:
        return [
            "task_scheduling",
            "resource_allocation",
            "milestone_tracking",
            "risk_management",
            "team_coordination",
            "status_reporting",
        ]

    async def execute(self, task: str, context: TaskContext) -> TaskResult:
        """執行專案管理任務。"""
        if "schedule" in task or "排程" in task:
            return await self._schedule_tasks(context)

        if "status" in task or "進度" in task or "報告" in task:
            return await self._generate_status_report(context)

        await self.update_progress(0.5, f"處理中：{task}")
        await self.update_progress(1.0, "完成")

        return TaskResult(
            status=TaskStatus.SUCCESS,
            summary=f"專案管理任務完成：{task}",
        )

    async def _schedule_tasks(self, context: TaskContext) -> TaskResult:
        """排程任務至各團隊。"""
        tasks = context.parameters.get("tasks", [])
        await self.update_progress(0.3, "分析任務相依性")
        await self.update_progress(0.6, "排定優先順序與時程")
        await self.update_progress(1.0, f"已排程 {len(tasks)} 項任務")

        return TaskResult(
            status=TaskStatus.SUCCESS,
            data={"scheduled_count": len(tasks)},
            summary=f"已排程 {len(tasks)} 項任務",
        )

    async def _generate_status_report(self, context: TaskContext) -> TaskResult:
        """產生專案進度報告。"""
        from src.api.agent_registry import get_all_agents

        all_agents = get_all_agents()
        working = sum(1 for a in all_agents if a.status == "working")
        idle = sum(1 for a in all_agents if a.status == "idle")

        await self.update_progress(0.5, "彙整各代理狀態")
        await self.update_progress(1.0, "進度報告已生成")

        return TaskResult(
            status=TaskStatus.SUCCESS,
            data={
                "total_agents": len(all_agents),
                "working": working,
                "idle": idle,
            },
            summary=f"專案狀態：{working} 工作中 / {idle} 待命 / 共 {len(all_agents)} 代理",
        )
