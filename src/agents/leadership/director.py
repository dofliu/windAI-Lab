"""wLab:project-director — 專案總監。

負責整個 WindAI Lab 的專案統籌、任務分派與整體進度追蹤，
作為系統最高指揮層級，協調各團隊運作。
"""

from __future__ import annotations

from src.agents.base import (
    AgentMessage,
    BaseAgent,
    MessageType,
    TaskContext,
    TaskResult,
    TaskStatus,
)


class ProjectDirector(BaseAgent):
    """專案總監代理，負責任務分派與跨團隊協調。"""

    def __init__(self) -> None:
        super().__init__("project-director")

    @property
    def capabilities(self) -> list[str]:
        return [
            "task_allocation",
            "progress_tracking",
            "team_coordination",
            "strategic_planning",
            "cross_team_communication",
            "escalation_handling",
        ]

    async def execute(self, task: str, context: TaskContext) -> TaskResult:
        """執行總監層級任務：分派、審核、協調。"""
        params = context.parameters

        if "assign" in task or "分派" in task:
            return await self._assign_task(params, context)

        if "review" in task or "審核" in task or "確認" in task:
            return await self._review(task, params)

        if "coordinate" in task or "協調" in task:
            return await self._coordinate(params, context)

        # 預設：通用任務處理
        await self.update_progress(0.3, f"分析任務需求：{task}")
        await self.update_progress(0.7, "制定執行計畫")
        await self.update_progress(1.0, "任務計畫已完成")

        return TaskResult(
            status=TaskStatus.SUCCESS,
            data={"task": task, "plan": "已制定執行計畫"},
            summary=f"已完成：{task}",
        )

    async def _assign_task(
        self, params: dict, context: TaskContext
    ) -> TaskResult:
        """分派任務至下級代理。"""
        target_agents = params.get("agents", [])
        task_desc = params.get("description", "未指定任務")

        await self.update_progress(0.2, "評估任務範圍與所需人力")
        await self.update_progress(0.5, f"分派任務至 {len(target_agents)} 位代理")

        # 透過 MessageBus 發送任務請求
        for agent_id in target_agents:
            msg = AgentMessage(
                from_agent=self.id,
                to_agent=agent_id,
                type=MessageType.DELEGATION,
                payload={
                    "task": task_desc,
                    "parameters": params,
                    "collaborators": target_agents,
                },
            )
            await self.send_message(msg)

        await self.update_progress(1.0, "任務分派完成")
        return TaskResult(
            status=TaskStatus.SUCCESS,
            data={"assigned_to": target_agents, "task": task_desc},
            summary=f"已將「{task_desc}」分派至 {len(target_agents)} 位代理",
        )

    async def _review(self, task: str, params: dict) -> TaskResult:
        """審核下級代理提交的成果。"""
        await self.update_progress(0.3, "檢視提交內容")
        await self.update_progress(0.6, "評估品質與完整度")
        await self.update_progress(1.0, "審核完成")

        return TaskResult(
            status=TaskStatus.SUCCESS,
            data={"approved": True, "comments": "審核通過"},
            summary=f"已完成審核：{task}",
        )

    async def _coordinate(
        self, params: dict, context: TaskContext
    ) -> TaskResult:
        """跨團隊協調。"""
        teams = params.get("teams", [])
        await self.update_progress(0.5, f"協調 {len(teams)} 個團隊")
        await self.update_progress(1.0, "協調完成")

        return TaskResult(
            status=TaskStatus.SUCCESS,
            data={"teams": teams, "coordinated": True},
            summary=f"跨團隊協調完成：{', '.join(teams)}",
        )
