"""SkillComposingAgent DataFrame 管線測試 — 驗證多步驟 DataFrame 傳遞。"""

from __future__ import annotations

import pandas as pd
import pytest

from src.agents.base import TaskContext, TaskStatus
from src.agents.skill_composing_agent import AgentSpec, SkillComposingAgent, TaskRoute
from src.skills.base import BaseSkill, SkillInput, SkillOutput, SkillStatus
from src.skills.registry import SkillRegistry

# ── 測試用技能 ──


class LoadSkill(BaseSkill):
    """載入技能 — 產生 DataFrame。"""

    skill_id = "test_load"
    display_name = "載入技能"

    async def execute(self, inp: SkillInput, progress_cb=None) -> SkillOutput:
        df = pd.DataFrame(
            {
                "wind_speed": [5.0, 10.0, 15.0, 20.0],
                "power": [50.0, 500.0, 1500.0, 2000.0],
            }
        )
        return SkillOutput(
            status=SkillStatus.SUCCESS,
            data={"row_count": len(df), "col_count": len(df.columns)},
            summary="資料載入完成",
            dataframe=df,
        )


class FilterSkill(BaseSkill):
    """過濾技能 — 接收 DataFrame 並過濾。"""

    skill_id = "test_filter"
    display_name = "過濾技能"

    async def execute(self, inp: SkillInput, progress_cb=None) -> SkillOutput:
        df = inp.dataframe
        if df is None:
            return SkillOutput(
                status=SkillStatus.ERROR,
                errors=["未收到 DataFrame 輸入"],
            )

        # 過濾 wind_speed > 8
        filtered = df[df["wind_speed"] > 8].reset_index(drop=True)
        return SkillOutput(
            status=SkillStatus.SUCCESS,
            data={
                "rows_before": len(df),
                "rows_after": len(filtered),
            },
            summary=f"過濾後剩 {len(filtered)} 筆",
            dataframe=filtered,
        )


class StatSkill(BaseSkill):
    """統計技能 — 接收 DataFrame 並計算統計值。"""

    skill_id = "test_stat"
    display_name = "統計技能"

    async def execute(self, inp: SkillInput, progress_cb=None) -> SkillOutput:
        df = inp.dataframe
        if df is None:
            return SkillOutput(
                status=SkillStatus.ERROR,
                errors=["未收到 DataFrame 輸入"],
            )

        mean_power = float(df["power"].mean())
        max_speed = float(df["wind_speed"].max())

        return SkillOutput(
            status=SkillStatus.SUCCESS,
            data={
                "mean_power": mean_power,
                "max_speed": max_speed,
                "count": len(df),
            },
            summary=f"平均功率: {mean_power:.1f}kW",
        )


class NoDfSkill(BaseSkill):
    """不產生 DataFrame 的技能（data-only）。"""

    skill_id = "test_nodf"
    display_name = "無 DF 技能"

    async def execute(self, inp: SkillInput, progress_cb=None) -> SkillOutput:
        return SkillOutput(
            status=SkillStatus.SUCCESS,
            data={"label": "metadata-only"},
            summary="完成",
            # 明確不設 dataframe
        )


class ProgressTrackingSkill(BaseSkill):
    """追蹤進度回呼的技能。"""

    skill_id = "test_progress"
    display_name = "進度追蹤技能"

    progress_calls: list[tuple[float, str]] = []

    async def execute(self, inp: SkillInput, progress_cb=None) -> SkillOutput:
        self.__class__.progress_calls = []  # 重置
        if progress_cb:
            await progress_cb(0.3, "step 1")
            self.__class__.progress_calls.append((0.3, "step 1"))
            await progress_cb(0.6, "step 2")
            self.__class__.progress_calls.append((0.6, "step 2"))
            await progress_cb(1.0, "done")
            self.__class__.progress_calls.append((1.0, "done"))
        return SkillOutput(
            status=SkillStatus.SUCCESS,
            data={"tracked": True},
            summary="進度追蹤完成",
        )


class TurbineProfilerSkill(BaseSkill):
    """模擬 turbine_profiler 技能，產出風機參數。"""

    skill_id = "turbine_profiler"
    display_name = "風機識別"

    async def execute(self, inp: SkillInput, progress_cb=None) -> SkillOutput:
        return SkillOutput(
            status=SkillStatus.SUCCESS,
            data={
                "turbine_profile": {
                    "rated_power_kw": 2050,
                    "cut_in_speed_ms": 3.0,
                    "cut_out_speed_ms": 25.0,
                    "rated_wind_speed_ms": 12.5,
                    "sampling_interval_seconds": 600,
                }
            },
            summary="風機型號識別完成",
        )


class ParamReadingSkill(BaseSkill):
    """讀取 context parameters 的技能（驗證 turbine_profiler 注入）。"""

    skill_id = "test_param_reader"
    display_name = "參數讀取"

    last_params: dict = {}

    async def execute(self, inp: SkillInput, progress_cb=None) -> SkillOutput:
        self.__class__.last_params = dict(inp.parameters)
        return SkillOutput(
            status=SkillStatus.SUCCESS,
            data={"rated_power": inp.parameters.get("rated_power")},
            summary="參數讀取完成",
        )


# ── Fixtures ──


@pytest.fixture()
def skill_registry() -> SkillRegistry:
    reg = SkillRegistry()
    reg.register(LoadSkill())
    reg.register(FilterSkill())
    reg.register(StatSkill())
    reg.register(NoDfSkill())
    reg.register(ProgressTrackingSkill())
    reg.register(TurbineProfilerSkill())
    reg.register(ParamReadingSkill())
    return reg


def _make_agent(
    skill_registry: SkillRegistry,
    agent_id: str = "test-agent",
    routes: list[TaskRoute] | None = None,
    skills: list[str] | None = None,
) -> SkillComposingAgent:
    spec = AgentSpec(
        id=agent_id,
        name=f"wAI:{agent_id}",
        display_name="測試代理",
        tier="ai-ml",
        skills=skills or [],
        task_routing=routes or [],
    )
    return SkillComposingAgent(spec, skill_registry)


# ── DataFrame 管線傳遞測試 ──


class TestDataFramePipeline:
    @pytest.mark.asyncio
    async def test_load_then_filter(self, skill_registry: SkillRegistry) -> None:
        """DataFrame 從載入技能正確傳遞到過濾技能。"""
        agent = _make_agent(
            skill_registry,
            routes=[TaskRoute(match=["process"], pipeline=["test_load", "test_filter"])],
        )
        result = await agent.execute("process data", TaskContext())
        assert result.status == TaskStatus.SUCCESS

        # 過濾結果
        filter_data = result.data["test_filter"]["data"]
        assert filter_data["rows_before"] == 4
        assert filter_data["rows_after"] == 3  # wind_speed > 8: 10, 15, 20

    @pytest.mark.asyncio
    async def test_three_step_pipeline(self, skill_registry: SkillRegistry) -> None:
        """三步驟管線：載入 → 過濾 → 統計。"""
        agent = _make_agent(
            skill_registry,
            routes=[
                TaskRoute(
                    match=["analyze"],
                    pipeline=["test_load", "test_filter", "test_stat"],
                )
            ],
        )
        result = await agent.execute("analyze data", TaskContext())
        assert result.status == TaskStatus.SUCCESS

        # 統計結果應基於過濾後的資料 (3 rows: speed 10,15,20 power 500,1500,2000)
        stat_data = result.data["test_stat"]["data"]
        assert stat_data["count"] == 3
        assert stat_data["max_speed"] == 20.0
        expected_mean = (500.0 + 1500.0 + 2000.0) / 3
        assert stat_data["mean_power"] == pytest.approx(expected_mean, rel=0.01)

    @pytest.mark.asyncio
    async def test_no_df_skill_preserves_previous_df(
        self, skill_registry: SkillRegistry
    ) -> None:
        """不產生 DataFrame 的技能不覆蓋上一步的 DataFrame。"""
        agent = _make_agent(
            skill_registry,
            routes=[
                TaskRoute(
                    match=["mixed"],
                    pipeline=["test_load", "test_nodf", "test_stat"],
                )
            ],
        )
        result = await agent.execute("mixed pipeline", TaskContext())
        assert result.status == TaskStatus.SUCCESS

        # stat 技能應收到 load 技能的 DataFrame（因為 nodf 不覆蓋）
        stat_data = result.data["test_stat"]["data"]
        assert stat_data["count"] == 4  # 未過濾，原始 4 筆

    @pytest.mark.asyncio
    async def test_first_skill_no_df_input(self, skill_registry: SkillRegistry) -> None:
        """第一個技能不接收 DataFrame（dataframe=None）。"""
        agent = _make_agent(
            skill_registry,
            routes=[TaskRoute(match=["load"], pipeline=["test_load"])],
        )
        result = await agent.execute("load data", TaskContext())
        assert result.status == TaskStatus.SUCCESS
        assert result.data["test_load"]["data"]["row_count"] == 4

    @pytest.mark.asyncio
    async def test_filter_without_df_returns_error(
        self, skill_registry: SkillRegistry
    ) -> None:
        """過濾技能未收到 DataFrame 時應回報錯誤。"""
        agent = _make_agent(
            skill_registry,
            routes=[TaskRoute(match=["filter"], pipeline=["test_filter"])],
        )
        result = await agent.execute("filter data", TaskContext())
        assert result.status == TaskStatus.ERROR
        assert any("未收到" in e for e in result.errors)


# ── turbine_profiler 注入測試 ──


class TestTurbineProfilerInjection:
    @pytest.mark.asyncio
    async def test_profiler_injects_params(self, skill_registry: SkillRegistry) -> None:
        """turbine_profiler 的結果應注入到 context.parameters。"""
        agent = _make_agent(
            skill_registry,
            routes=[
                TaskRoute(
                    match=["profile"],
                    pipeline=["turbine_profiler", "test_param_reader"],
                )
            ],
        )
        result = await agent.execute("profile turbine", TaskContext())
        assert result.status == TaskStatus.SUCCESS

        # param_reader 應收到注入的參數
        reader_data = result.data["test_param_reader"]["data"]
        assert reader_data["rated_power"] == 2050

    @pytest.mark.asyncio
    async def test_profiler_doesnt_override_existing_params(
        self, skill_registry: SkillRegistry
    ) -> None:
        """如果 parameters 已有 rated_power，turbine_profiler 不應覆蓋。"""
        agent = _make_agent(
            skill_registry,
            routes=[
                TaskRoute(
                    match=["profile"],
                    pipeline=["turbine_profiler", "test_param_reader"],
                )
            ],
        )
        ctx = TaskContext(parameters={"rated_power": 3000})
        result = await agent.execute("profile turbine", ctx)
        assert result.status == TaskStatus.SUCCESS

        # 原始值應保留
        reader_data = result.data["test_param_reader"]["data"]
        assert reader_data["rated_power"] == 3000


# ── 進度回呼測試 ──


class TestProgressCallback:
    @pytest.mark.asyncio
    async def test_progress_callback_called(self, skill_registry: SkillRegistry) -> None:
        """進度回呼函式被正確呼叫。"""
        agent = _make_agent(
            skill_registry,
            routes=[TaskRoute(match=["track"], pipeline=["test_progress"])],
        )
        result = await agent.execute("track progress", TaskContext())
        assert result.status == TaskStatus.SUCCESS
        assert len(ProgressTrackingSkill.progress_calls) == 3

    @pytest.mark.asyncio
    async def test_multi_skill_progress_proportional(
        self, skill_registry: SkillRegistry
    ) -> None:
        """多技能管線中，各技能進度在整體中按比例分配。"""
        agent = _make_agent(
            skill_registry,
            routes=[
                TaskRoute(
                    match=["multi"],
                    pipeline=["test_load", "test_progress"],
                )
            ],
        )
        result = await agent.execute("multi step", TaskContext())
        assert result.status == TaskStatus.SUCCESS


# ── 錯誤傳播測試 ──


class FailAtStepSkill(BaseSkill):
    """在特定位置失敗的技能。"""

    skill_id = "test_fail_mid"
    display_name = "中途失敗"

    async def execute(self, inp: SkillInput, progress_cb=None) -> SkillOutput:
        return SkillOutput(
            status=SkillStatus.ERROR,
            errors=["pipeline break"],
            summary="失敗了",
        )


class TestErrorPropagation:
    @pytest.fixture(autouse=True)
    def _register_fail(self, skill_registry: SkillRegistry) -> None:
        skill_registry.register(FailAtStepSkill())

    @pytest.mark.asyncio
    async def test_error_stops_pipeline(self, skill_registry: SkillRegistry) -> None:
        """管線中某步驟失敗後，後續步驟不執行。"""
        agent = _make_agent(
            skill_registry,
            routes=[
                TaskRoute(
                    match=["fail"],
                    pipeline=["test_load", "test_fail_mid", "test_stat"],
                )
            ],
        )
        result = await agent.execute("fail mid", TaskContext())
        assert result.status == TaskStatus.ERROR
        assert "test_load" in result.data
        assert "test_fail_mid" in result.data
        assert "test_stat" not in result.data  # 不應執行

    @pytest.mark.asyncio
    async def test_missing_skill_returns_error(self, skill_registry: SkillRegistry) -> None:
        """管線中有不存在的技能應回報錯誤。"""
        agent = _make_agent(
            skill_registry,
            routes=[
                TaskRoute(match=["bad"], pipeline=["nonexistent_skill"]),
            ],
        )
        result = await agent.execute("bad pipeline", TaskContext())
        assert result.status == TaskStatus.ERROR
        assert any("缺少技能" in e for e in result.errors)


# ── 路由匹配測試 ──


class TestRouteMatching:
    def test_exact_keyword(self, skill_registry: SkillRegistry) -> None:
        agent = _make_agent(
            skill_registry,
            routes=[
                TaskRoute(match=["clean"], pipeline=["test_load"]),
                TaskRoute(match=["analyze"], pipeline=["test_stat"]),
            ],
        )
        route = agent._match_route("clean SCADA data")
        assert route is not None
        assert route.pipeline == ["test_load"]

    def test_case_insensitive(self, skill_registry: SkillRegistry) -> None:
        agent = _make_agent(
            skill_registry,
            routes=[TaskRoute(match=["CLEAN"], pipeline=["test_load"])],
        )
        route = agent._match_route("clean data")
        assert route is not None

    def test_chinese_keyword(self, skill_registry: SkillRegistry) -> None:
        agent = _make_agent(
            skill_registry,
            routes=[TaskRoute(match=["診斷", "故障"], pipeline=["test_load"])],
        )
        route = agent._match_route("進行風機故障診斷")
        assert route is not None

    def test_fallback_to_first_route(self, skill_registry: SkillRegistry) -> None:
        agent = _make_agent(
            skill_registry,
            routes=[
                TaskRoute(match=["specific"], pipeline=["test_load"]),
                TaskRoute(match=["other"], pipeline=["test_filter"]),
            ],
        )
        route = agent._match_route("unmatched task")
        assert route is not None
        assert route.pipeline == ["test_load"]

    def test_no_routes_returns_none(self, skill_registry: SkillRegistry) -> None:
        agent = _make_agent(skill_registry, routes=[])
        assert agent._match_route("anything") is None


# ── 空管線與無路由測試 ──


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_pipeline(self, skill_registry: SkillRegistry) -> None:
        """路由存在但管線為空 → 回傳基本成功。"""
        agent = _make_agent(
            skill_registry,
            routes=[TaskRoute(match=["empty"], pipeline=[])],
        )
        result = await agent.execute("empty pipeline", TaskContext())
        assert result.status == TaskStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_no_routing_returns_success(self, skill_registry: SkillRegistry) -> None:
        """無路由定義 → 回傳基本成功訊息。"""
        agent = _make_agent(skill_registry, routes=[])
        result = await agent.execute("do nothing", TaskContext())
        assert result.status == TaskStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_summary_joins_skill_summaries(
        self, skill_registry: SkillRegistry
    ) -> None:
        """最終摘要應包含各技能摘要，以 → 連接。"""
        agent = _make_agent(
            skill_registry,
            routes=[
                TaskRoute(match=["full"], pipeline=["test_load", "test_filter"]),
            ],
        )
        result = await agent.execute("full pipeline", TaskContext())
        assert "→" in result.summary
        assert "載入" in result.summary
        assert "過濾" in result.summary
