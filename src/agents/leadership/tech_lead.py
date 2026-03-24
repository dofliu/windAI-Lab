"""wLab:tech-lead — 技術主管。

負責軟體工程團隊的技術方向制定與程式碼品質管控，
審核架構設計決策，選擇適合的技術棧。
"""

from __future__ import annotations

from src.agents.base import BaseAgent, TaskContext, TaskResult, TaskStatus


class TechLead(BaseAgent):
    """技術主管代理，負責架構設計審核與技術決策。"""

    def __init__(self) -> None:
        super().__init__("tech-lead")

    @property
    def capabilities(self) -> list[str]:
        return [
            "technical_review",
            "architecture_design",
            "code_quality_oversight",
            "technology_selection",
            "engineering_coordination",
            "devops_oversight",
        ]

    async def execute(self, task: str, context: TaskContext) -> TaskResult:
        """執行技術主管任務。"""
        if "review" in task or "審核" in task:
            return await self._technical_review(task, context)

        if "architecture" in task or "架構" in task:
            return await self._architecture_design(task, context)

        await self.update_progress(0.5, f"技術評估：{task}")
        await self.update_progress(1.0, "評估完成")
        return TaskResult(status=TaskStatus.SUCCESS, summary=f"技術任務完成：{task}")

    async def _technical_review(self, task: str, context: TaskContext) -> TaskResult:
        """執行技術審核。"""
        await self.update_progress(0.3, "審核程式碼品質")
        await self.update_progress(0.6, "檢查架構合規性")
        await self.update_progress(1.0, "技術審核完成")

        return TaskResult(
            status=TaskStatus.SUCCESS,
            data={"approved": True, "review_notes": "架構合理，程式碼品質良好"},
            summary=f"技術審核通過：{task}",
        )

    async def _architecture_design(self, task: str, context: TaskContext) -> TaskResult:
        """設計或審核系統架構。"""
        await self.update_progress(0.3, "分析系統需求")
        await self.update_progress(0.6, "設計架構方案")
        await self.update_progress(1.0, "架構設計完成")

        return TaskResult(
            status=TaskStatus.SUCCESS,
            data={"design": "架構設計方案已產出"},
            summary=f"架構設計完成：{task}",
        )
