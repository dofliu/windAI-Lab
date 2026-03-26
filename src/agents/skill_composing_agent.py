"""通用技能組合代理 — 根據 YAML task_routing 自動組合技能執行任務。

大多數代理不再需要獨立的 Python class，
只需在 YAML 中定義技能列表和任務路由即可。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.agents.base import BaseAgent, TaskContext, TaskResult, TaskStatus
from src.skills.base import SkillInput, SkillStatus
from src.skills.registry import SkillRegistry


@dataclass
class TaskRoute:
    """任務路由規則：關鍵字 → 技能管線。"""

    match: list[str]
    pipeline: list[str]


@dataclass
class AgentSpec:
    """從 YAML 載入的代理規格。"""

    id: str
    name: str
    display_name: str
    tier: str
    color: str = "#6b7280"
    icon: str = "🤖"
    core: bool = False
    description: str = ""
    skills: list[str] = field(default_factory=list)
    task_routing: list[TaskRoute] = field(default_factory=list)
    custom_class: str | None = None

    @classmethod
    def from_yaml_dict(cls, data: dict[str, Any]) -> AgentSpec:
        """從 YAML 解析結果建立 AgentSpec。"""
        routes = []
        for route_data in data.get("task_routing", []):
            routes.append(TaskRoute(
                match=route_data.get("match", []),
                pipeline=route_data.get("pipeline", []),
            ))

        return cls(
            id=data["id"],
            name=data.get("name", data["id"]),
            display_name=data.get("display_name", data["id"]),
            tier=data.get("tier", "research"),
            color=data.get("color", "#6b7280"),
            icon=data.get("icon", "🤖"),
            core=data.get("core", False),
            description=data.get("description", ""),
            skills=data.get("skills", []),
            task_routing=routes,
            custom_class=data.get("custom_class"),
        )


class SkillComposingAgent(BaseAgent):
    """根據 YAML 定義的 task_routing 自動組合技能的通用代理。

    工作流程：
    1. 接收任務描述
    2. 用關鍵字匹配找到對應的技能管線
    3. 依序執行管線中的每個技能
    4. 上一個技能的輸出成為下一個的輸入
    5. 彙整所有結果回傳
    """

    def __init__(self, spec: AgentSpec, skill_registry: SkillRegistry) -> None:
        super().__init__(spec.id)
        self._spec = spec
        self._skill_registry = skill_registry
        self._routes = spec.task_routing

    @property
    def capabilities(self) -> list[str]:
        """從技能列表衍生能力。"""
        return list(self._spec.skills)

    @property
    def description(self) -> str:
        return self._spec.description or super().description

    def _match_route(self, task: str) -> TaskRoute | None:
        """根據任務文字匹配最佳路由。"""
        task_lower = task.lower()
        for route in self._routes:
            if any(kw.lower() in task_lower for kw in route.match):
                return route

        # 無匹配時，使用第一個路由（如果有）
        if self._routes:
            return self._routes[0]
        return None

    async def execute(self, task: str, context: TaskContext) -> TaskResult:
        """根據 task_routing 組合技能執行任務。"""
        route = self._match_route(task)

        if route is None or not route.pipeline:
            # 沒有技能管線 → 回傳基本完成訊息
            return TaskResult(
                status=TaskStatus.SUCCESS,
                summary=f"{self._spec.display_name} 已完成任務",
                data={"task": task},
            )

        # 驗證所有技能都存在
        missing = [s for s in route.pipeline if not self._skill_registry.has(s)]
        if missing:
            return TaskResult(
                status=TaskStatus.ERROR,
                errors=[f"缺少技能：{', '.join(missing)}"],
            )

        # 依序執行技能管線
        all_results: dict[str, Any] = {}
        current_df = None
        total_skills = len(route.pipeline)

        for i, skill_id in enumerate(route.pipeline):
            skill = self._skill_registry.get(skill_id)
            if skill is None:
                continue

            # 進度基於管線位置
            base_progress = i / total_skills

            async def _progress_cb(p: float, msg: str) -> None:
                overall = base_progress + p / total_skills
                await self.update_progress(overall, f"[{skill.display_name}] {msg}")

            # 組裝輸入：DataFrame 明確透過 dataframe 欄位傳遞
            inp = SkillInput(
                parameters=context.parameters,
                data=current_df,
                context=all_results,
                dataframe=current_df,
            )

            # 執行技能
            output = await skill.execute(inp, progress_cb=_progress_cb)

            # 收集結果
            all_results[skill_id] = {
                "status": output.status.value,
                "data": output.data,
                "summary": output.summary,
                "errors": output.errors,
            }

            # 傳遞 DataFrame 給下一個技能（只用 dataframe，不 fallback 到 data dict）
            if output.dataframe is not None:
                current_df = output.dataframe

            # ── 關鍵：turbine_profiler 的結果注入到 parameters ──
            # 讓後續所有技能自動使用推斷出的風機參數
            if skill_id == "turbine_profiler" and output.data:
                profile = output.data.get("turbine_profile", {})
                if profile:
                    # 注入到 context.parameters，後續技能可直接讀取
                    context.parameters["turbine_profile"] = profile
                    # 同時設定常用參數的 shortcut
                    context.parameters.setdefault("rated_power", profile.get("rated_power_kw"))
                    context.parameters.setdefault("cut_in_speed", profile.get("cut_in_speed_ms"))
                    context.parameters.setdefault("cut_out_speed", profile.get("cut_out_speed_ms"))
                    context.parameters.setdefault("rated_wind_speed", profile.get("rated_wind_speed_ms"))
                    context.parameters.setdefault("sampling_interval", profile.get("sampling_interval_seconds"))

            # 如果某個技能失敗，提前結束
            if output.status == SkillStatus.ERROR:
                return TaskResult(
                    status=TaskStatus.ERROR,
                    data=all_results,
                    errors=output.errors,
                    summary=f"管線在 {skill.display_name} 步驟失敗",
                )

        await self.update_progress(1.0, "任務完成")

        # 彙整摘要
        summaries = [r["summary"] for r in all_results.values() if r.get("summary")]

        return TaskResult(
            status=TaskStatus.SUCCESS,
            data=all_results,
            summary=" → ".join(summaries) if summaries else "技能管線執行完成",
        )
