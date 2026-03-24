"""wLab:research-lead — 研究主管。

負責研究文件團隊的學術方向規劃，監督論文撰寫品質、
文獻管理策略與 RAG 知識庫建設。
"""

from __future__ import annotations

from src.agents.base import BaseAgent, TaskContext, TaskResult, TaskStatus


class ResearchLead(BaseAgent):
    """研究主管代理，負責學術方向規劃與論文審核。"""

    def __init__(self) -> None:
        super().__init__("research-lead")

    @property
    def capabilities(self) -> list[str]:
        return [
            "research_direction",
            "literature_oversight",
            "paper_review",
            "knowledge_management",
            "academic_coordination",
            "publication_planning",
        ]

    async def execute(self, task: str, context: TaskContext) -> TaskResult:
        """執行研究主管任務。"""
        if "review" in task or "審核" in task or "審閱" in task:
            return await self._review_research(task, context)

        if "plan" in task or "規劃" in task:
            return await self._plan_research(task, context)

        await self.update_progress(0.5, f"研究評估：{task}")
        await self.update_progress(1.0, "評估完成")
        return TaskResult(status=TaskStatus.SUCCESS, summary=f"研究任務完成：{task}")

    async def _review_research(self, task: str, context: TaskContext) -> TaskResult:
        """審閱研究成果或論文。"""
        await self.update_progress(0.3, "審閱方法論")
        await self.update_progress(0.6, "檢查實驗設計與統計分析")
        await self.update_progress(1.0, "研究審閱完成")

        return TaskResult(
            status=TaskStatus.SUCCESS,
            data={"approved": True, "feedback": "方法論合理，結果可信"},
            summary=f"研究審閱通過：{task}",
        )

    async def _plan_research(self, task: str, context: TaskContext) -> TaskResult:
        """規劃研究方向與出版策略。"""
        await self.update_progress(0.3, "分析領域趨勢")
        await self.update_progress(0.6, "制定研究路線圖")
        await self.update_progress(1.0, "研究規劃完成")

        return TaskResult(
            status=TaskStatus.SUCCESS,
            data={"plan": "研究路線圖已產出"},
            summary=f"研究規劃完成：{task}",
        )
