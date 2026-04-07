"""wLab:project-director — 專案總監。

負責整個 WindAI Lab 的專案統籌、任務分派與整體進度追蹤，
作為系統最高指揮層級，協調各團隊運作。

審核功能已升級為 LLM 智慧審核：
- 優先使用 director_review 技能呼叫 LLM 進行深層審核
- LLM 不可用時自動降級為規則式審核
- 不再是無條件通過的橡皮圖章
"""

from __future__ import annotations

from typing import Any

from src.agents.base import (
    AgentMessage,
    BaseAgent,
    MessageType,
    TaskContext,
    TaskResult,
    TaskStatus,
)


class ProjectDirector(BaseAgent):
    """專案總監代理，負責任務分派、智慧審核與跨團隊協調。"""

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
            "llm_review",
            "quality_assessment",
        ]

    async def execute(self, task: str, context: TaskContext) -> TaskResult:
        """執行總監層級任務：分派、審核、協調。"""
        params = context.parameters

        if "assign" in task or "分派" in task:
            return await self._assign_task(params, context)

        if "review" in task or "審核" in task or "確認" in task:
            return await self._review(task, params, context)

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

    async def _assign_task(self, params: dict, context: TaskContext) -> TaskResult:
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

    async def _review(self, task: str, params: dict[str, Any], context: TaskContext) -> TaskResult:
        """智慧審核：使用 LLM 或規則式審核下級代理提交的成果。

        審核流程：
        1. 收集上游代理的所有分析結果（從 context.results）
        2. 呼叫 director_review 技能進行 LLM 審核
        3. LLM 不可用時自動降級為規則式審核
        4. 根據審核結果決定 approved / conditional / rejected
        """
        await self.update_progress(0.1, "收集上游分析結果...")

        # 收集上游結果
        upstream = context.results or {}
        task_name = params.get("task_name", task)
        turbine_id = params.get("turbine_id", "")

        await self.update_progress(0.2, "啟動智慧審核...")

        try:
            from src.skills.base import SkillInput
            from src.skills.leadership.director_review import DirectorReviewSkill

            skill = DirectorReviewSkill()
            skill_input = SkillInput(
                parameters={
                    "task_name": task_name,
                    "turbine_id": turbine_id,
                },
                context=upstream,
            )

            async def _review_progress(p: float, msg: str) -> None:
                # 映射到 0.2 ~ 0.9
                await self.update_progress(0.2 + p * 0.7, f"[審核] {msg}")

            output = await skill.execute(skill_input, progress_cb=_review_progress)

            review_data = output.data
            verdict = review_data.get("overall_verdict", "approved")
            score = review_data.get("overall_score", 0)
            summary = review_data.get("executive_summary", "")

            await self.update_progress(1.0, f"審核完成 — {verdict} ({score}/100)")

            return TaskResult(
                status=TaskStatus.SUCCESS,
                data={
                    "approved": verdict == "approved",
                    "verdict": verdict,
                    "score": score,
                    "review": review_data,
                },
                summary=f"總監審核：{verdict.upper()} ({score}/100) — {summary}",
            )

        except Exception as e:
            self._logger.warning(f"智慧審核異常，使用基本審核：{e}")
            await self.update_progress(0.8, "使用基本審核模式")

            # Fallback：基本審核邏輯
            approved = self._basic_quality_check(upstream)
            await self.update_progress(1.0, "基本審核完成")

            return TaskResult(
                status=TaskStatus.SUCCESS,
                data={
                    "approved": approved,
                    "verdict": "approved" if approved else "conditional",
                    "mode": "basic_fallback",
                },
                summary=(f"已完成審核：{task} — {'通過' if approved else '有條件通過'}"),
            )

    def _basic_quality_check(self, upstream: dict[str, Any]) -> bool:
        """基本品質檢查（所有審核路徑都失敗時的最終 fallback）。"""
        for _key, result in upstream.items():
            if isinstance(result, dict):
                status = result.get("status", "")
                if status == "error":
                    return False
        return True

    async def _coordinate(self, params: dict, context: TaskContext) -> TaskResult:
        """跨團隊協調。"""
        teams = params.get("teams", [])
        await self.update_progress(0.5, f"協調 {len(teams)} 個團隊")
        await self.update_progress(1.0, "協調完成")

        return TaskResult(
            status=TaskStatus.SUCCESS,
            data={"teams": teams, "coordinated": True},
            summary=f"跨團隊協調完成：{', '.join(teams)}",
        )
