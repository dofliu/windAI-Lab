"""SkillComposingAgent 與 AgentSpec 測試。"""

from __future__ import annotations

import pytest

from src.agents.base import TaskContext, TaskStatus
from src.agents.skill_composing_agent import AgentSpec, SkillComposingAgent, TaskRoute
from src.skills.base import BaseSkill, SkillInput, SkillOutput, SkillStatus
from src.skills.registry import SkillRegistry

# ── 測試用技能 ──


class CleanSkill(BaseSkill):
    skill_id = "test_clean"
    display_name = "清洗技能"

    async def execute(self, inp: SkillInput, progress_cb=None) -> SkillOutput:
        if progress_cb:
            await progress_cb(0.5, "cleaning...")
            await progress_cb(1.0, "done")
        return SkillOutput(
            status=SkillStatus.SUCCESS,
            data={"cleaned": True},
            summary="資料清洗完成",
        )


class AnalyzeSkill(BaseSkill):
    skill_id = "test_analyze"
    display_name = "分析技能"

    async def execute(self, inp: SkillInput, progress_cb=None) -> SkillOutput:
        return SkillOutput(
            status=SkillStatus.SUCCESS,
            data={"analysis": "ok"},
            summary="分析完成",
        )


class FailSkill(BaseSkill):
    skill_id = "test_fail"
    display_name = "失敗技能"

    async def execute(self, inp: SkillInput, progress_cb=None) -> SkillOutput:
        return SkillOutput(
            status=SkillStatus.ERROR,
            errors=["something went wrong"],
            summary="執行失敗",
        )


# ── AgentSpec ──


class TestAgentSpec:
    def test_from_yaml_dict_minimal(self) -> None:
        data = {"id": "test-agent", "name": "wAI:test", "display_name": "測試"}
        spec = AgentSpec.from_yaml_dict(data)
        assert spec.id == "test-agent"
        assert spec.tier == "research"  # default
        assert spec.core is False
        assert spec.skills == []
        assert spec.task_routing == []

    def test_from_yaml_dict_full(self) -> None:
        data = {
            "id": "fault-diag",
            "name": "wAI:fault-diagnostician",
            "display_name": "故障診斷師",
            "tier": "ai-ml",
            "color": "#8b5cf6",
            "icon": "🔧",
            "core": True,
            "description": "風機故障分類",
            "skills": ["clean", "analyze"],
            "task_routing": [
                {"match": ["diagnose", "故障"], "pipeline": ["clean", "analyze"]},
                {"match": ["anomaly"], "pipeline": ["clean"]},
            ],
            "custom_class": "src.agents.ai.fault_diagnostician.FaultDiagnostician",
        }
        spec = AgentSpec.from_yaml_dict(data)
        assert spec.id == "fault-diag"
        assert spec.core is True
        assert spec.tier == "ai-ml"
        assert len(spec.skills) == 2
        assert len(spec.task_routing) == 2
        assert spec.task_routing[0].match == ["diagnose", "故障"]
        assert spec.task_routing[0].pipeline == ["clean", "analyze"]
        assert spec.custom_class == "src.agents.ai.fault_diagnostician.FaultDiagnostician"

    def test_from_yaml_dict_defaults(self) -> None:
        """只給 id 時其餘欄位有合理預設值。"""
        spec = AgentSpec.from_yaml_dict({"id": "minimal"})
        assert spec.name == "minimal"
        assert spec.display_name == "minimal"
        assert spec.color == "#6b7280"
        assert spec.icon == "🤖"


class TestTaskRoute:
    def test_dataclass(self) -> None:
        route = TaskRoute(match=["clean", "清洗"], pipeline=["step_a", "step_b"])
        assert "clean" in route.match
        assert len(route.pipeline) == 2


# ── SkillComposingAgent ──


class TestSkillComposingAgent:
    @pytest.fixture()
    def skill_registry(self) -> SkillRegistry:
        reg = SkillRegistry()
        reg.register(CleanSkill())
        reg.register(AnalyzeSkill())
        reg.register(FailSkill())
        return reg

    @pytest.fixture()
    def spec_with_routes(self) -> AgentSpec:
        return AgentSpec(
            id="test-composer",
            name="wAI:test-composer",
            display_name="測試組合代理",
            tier="ai-ml",
            skills=["test_clean", "test_analyze"],
            task_routing=[
                TaskRoute(match=["clean", "清洗"], pipeline=["test_clean"]),
                TaskRoute(
                    match=["diagnose", "全分析"],
                    pipeline=["test_clean", "test_analyze"],
                ),
                TaskRoute(
                    match=["fail"],
                    pipeline=["test_fail", "test_analyze"],
                ),
            ],
        )

    @pytest.fixture()
    def agent(
        self, spec_with_routes: AgentSpec, skill_registry: SkillRegistry
    ) -> SkillComposingAgent:
        return SkillComposingAgent(spec_with_routes, skill_registry)

    def test_capabilities(self, agent: SkillComposingAgent) -> None:
        assert "test_clean" in agent.capabilities
        assert "test_analyze" in agent.capabilities

    def test_description(self, agent: SkillComposingAgent) -> None:
        assert "測試組合代理" in agent.description or agent.description != ""

    def test_match_route_keyword(self, agent: SkillComposingAgent) -> None:
        route = agent._match_route("請清洗 SCADA 資料")
        assert route is not None
        assert route.pipeline == ["test_clean"]

    def test_match_route_case_insensitive(self, agent: SkillComposingAgent) -> None:
        route = agent._match_route("CLEAN the data")
        assert route is not None
        assert route.pipeline == ["test_clean"]

    def test_match_route_fallback_first(self, agent: SkillComposingAgent) -> None:
        """無匹配時退回第一個路由。"""
        route = agent._match_route("some unrelated task")
        assert route is not None
        assert route.pipeline == ["test_clean"]

    def test_match_route_no_routes(self, skill_registry: SkillRegistry) -> None:
        spec = AgentSpec(id="empty-agent", name="wAI:empty", display_name="空代理", tier="ai-ml")
        agent = SkillComposingAgent(spec, skill_registry)
        assert agent._match_route("anything") is None

    @pytest.mark.asyncio
    async def test_execute_single_skill_pipeline(self, agent: SkillComposingAgent) -> None:
        ctx = TaskContext(parameters={})
        result = await agent.execute("清洗資料", ctx)
        assert result.status == TaskStatus.SUCCESS
        assert "test_clean" in result.data

    @pytest.mark.asyncio
    async def test_execute_multi_skill_pipeline(self, agent: SkillComposingAgent) -> None:
        ctx = TaskContext(parameters={})
        result = await agent.execute("全分析資料集", ctx)
        assert result.status == TaskStatus.SUCCESS
        assert "test_clean" in result.data
        assert "test_analyze" in result.data
        # 摘要應包含各技能的摘要
        assert "→" in result.summary

    @pytest.mark.asyncio
    async def test_execute_pipeline_stops_on_error(self, agent: SkillComposingAgent) -> None:
        ctx = TaskContext(parameters={})
        result = await agent.execute("fail test", ctx)
        assert result.status == TaskStatus.ERROR
        assert len(result.errors) > 0
        # 第二個技能不應執行
        assert "test_analyze" not in result.data

    @pytest.mark.asyncio
    async def test_execute_missing_skill(self, skill_registry: SkillRegistry) -> None:
        spec = AgentSpec(
            id="bad-agent",
            name="wAI:bad",
            display_name="壞代理",
            tier="ai-ml",
            task_routing=[
                TaskRoute(match=["run"], pipeline=["nonexistent_skill"]),
            ],
        )
        agent = SkillComposingAgent(spec, skill_registry)
        ctx = TaskContext(parameters={})
        result = await agent.execute("run something", ctx)
        assert result.status == TaskStatus.ERROR
        assert any("缺少技能" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_execute_no_pipeline(self, skill_registry: SkillRegistry) -> None:
        """沒有路由 → 回傳基本成功訊息。"""
        spec = AgentSpec(
            id="noop-agent",
            name="wAI:noop",
            display_name="空操作",
            tier="ai-ml",
        )
        agent = SkillComposingAgent(spec, skill_registry)
        ctx = TaskContext(parameters={})
        result = await agent.execute("do nothing", ctx)
        assert result.status == TaskStatus.SUCCESS
