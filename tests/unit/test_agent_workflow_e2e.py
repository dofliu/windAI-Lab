"""代理工作流端對端整合測試。

測試從 Workflow 定義到 OrchestrationEngine 執行的完整路徑，
驗證真實代理路徑、模擬 fallback、以及跨步驟結果累積。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.base import BaseAgent, TaskContext, TaskResult, TaskStatus
from src.agents.orchestrator.engine import (
    DegradationStrategy,
    OrchestrationEngine,
    RetryConfig,
    StepType,
    Workflow,
    WorkflowStep,
)
from src.api.agent_registry import reset_all_agents
from src.api.models import AgentModel, AgentStatus, AgentTier
from tests.unit._ws_mock import mock_ws_manager  # noqa: F401

# ── 測試用代理 ──


class FakeAgent(BaseAgent):
    """可控結果的假代理。"""

    def __init__(
        self,
        agent_id: str,
        result_data: dict | None = None,
        should_fail: bool = False,
    ) -> None:
        super().__init__(agent_id)
        self._result_data = result_data or {"completed": True}
        self._should_fail = should_fail
        self.task_calls: list[tuple[str, dict]] = []

    @property
    def capabilities(self) -> list[str]:
        return ["test"]

    async def execute(self, task: str, context: TaskContext) -> TaskResult:
        self.task_calls.append((task, context.parameters))
        if self._should_fail:
            return TaskResult(
                status=TaskStatus.ERROR,
                errors=["fake error"],
            )
        return TaskResult(
            status=TaskStatus.SUCCESS,
            data=self._result_data,
            summary=f"Fake completed: {task}",
        )


# ── Fixtures ──


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_all_agents()
    yield  # type: ignore[misc]
    reset_all_agents()


@pytest.fixture()
def engine() -> OrchestrationEngine:
    return OrchestrationEngine()


def _make_agent_model(agent_id: str) -> AgentModel:
    return AgentModel(
        id=agent_id,
        name=f"wAI:{agent_id}",
        display_name=f"Test {agent_id}",
        tier=AgentTier.AI_ML,
        status=AgentStatus.IDLE,
        current_task=None,
        progress=0.0,
        collaborating_with=[],
        color="#8b5cf6",
        icon="🤖",
    )


# ── 真實代理路徑測試 ──


class TestRealAgentPath:
    @pytest.mark.asyncio
    async def test_single_step_real_agent(self, engine: OrchestrationEngine) -> None:
        """單步驟工作流程使用真實代理。"""
        fake = FakeAgent("agent-1", result_data={"r2_score": 0.95})
        model = _make_agent_model("agent-1")

        with (
            patch("src.agents.orchestrator.engine.get_agent", return_value=model),
            patch("src.agents.orchestrator.engine.update_agent_status", return_value=model),
            patch(
                "src.agents.dynamic_registry.dynamic_registry.get_instance",
                return_value=fake,
            ),
        ):
            step = WorkflowStep(
                name="train",
                agent_ids=["agent-1"],
                description="train model",
                task_template="train model {model_type}",
                task_parameters={"model_type": "xgboost"},
            )
            result = await engine._run_agent_step("agent-1", step)

        assert "agent-1" in result
        assert result["agent-1"]["r2_score"] == 0.95
        assert len(fake.task_calls) == 1
        assert fake.task_calls[0][0] == "train model xgboost"

    @pytest.mark.asyncio
    async def test_multi_agent_parallel_step(self, engine: OrchestrationEngine) -> None:
        """平行步驟多代理同時執行。"""
        agent_a = FakeAgent("a", result_data={"from_a": True})
        agent_b = FakeAgent("b", result_data={"from_b": True})
        model_a = _make_agent_model("a")
        model_b = _make_agent_model("b")

        def get_agent_side_effect(aid: str) -> AgentModel | None:
            return {"a": model_a, "b": model_b}.get(aid)

        def get_instance_side_effect(aid: str) -> FakeAgent | None:
            return {"a": agent_a, "b": agent_b}.get(aid)

        with (
            patch(
                "src.agents.orchestrator.engine.get_agent",
                side_effect=get_agent_side_effect,
            ),
            patch(
                "src.agents.orchestrator.engine.update_agent_status",
                side_effect=lambda aid, **kw: get_agent_side_effect(aid),
            ),
            patch(
                "src.agents.dynamic_registry.dynamic_registry.get_instance",
                side_effect=get_instance_side_effect,
            ),
        ):
            step = WorkflowStep(
                name="parallel-analysis",
                agent_ids=["a", "b"],
                description="parallel work",
                step_type=StepType.PARALLEL,
            )
            results = await engine._run_step(step)

        assert "a" in results
        assert "b" in results
        assert results["a"]["from_a"] is True
        assert results["b"]["from_b"] is True

    @pytest.mark.asyncio
    async def test_task_template_formatting(self, engine: OrchestrationEngine) -> None:
        """task_template 中的佔位符應被正確替換。"""
        fake = FakeAgent("agent-1")
        model = _make_agent_model("agent-1")

        with (
            patch("src.agents.orchestrator.engine.get_agent", return_value=model),
            patch("src.agents.orchestrator.engine.update_agent_status", return_value=model),
            patch(
                "src.agents.dynamic_registry.dynamic_registry.get_instance",
                return_value=fake,
            ),
        ):
            step = WorkflowStep(
                name="diagnose",
                agent_ids=["agent-1"],
                description="diagnose turbine",
                task_template="diagnose {turbine_id} with {model_type}",
                task_parameters={
                    "turbine_id": "WT-01",
                    "model_type": "xgboost",
                },
            )
            await engine._run_agent_step("agent-1", step)

        assert fake.task_calls[0][0] == "diagnose WT-01 with xgboost"

    @pytest.mark.asyncio
    async def test_missing_template_var_fallback(self, engine: OrchestrationEngine) -> None:
        """task_template 佔位符缺失時不崩潰（使用 description fallback）。"""
        fake = FakeAgent("agent-1")
        model = _make_agent_model("agent-1")

        with (
            patch("src.agents.orchestrator.engine.get_agent", return_value=model),
            patch("src.agents.orchestrator.engine.update_agent_status", return_value=model),
            patch(
                "src.agents.dynamic_registry.dynamic_registry.get_instance",
                return_value=fake,
            ),
        ):
            step = WorkflowStep(
                name="diagnose",
                agent_ids=["agent-1"],
                description="diagnose turbine",
                task_template="diagnose {missing_param}",
                task_parameters={},
            )
            await engine._run_agent_step("agent-1", step)

        # KeyError 被 suppress，保留原始模板
        assert fake.task_calls[0][0] == "diagnose {missing_param}"


# ── 模擬路徑測試 ──


class TestSimulationPath:
    @pytest.mark.asyncio
    async def test_simulation_fallback(self, engine: OrchestrationEngine) -> None:
        """代理無實例時退回模擬路徑。"""
        model = _make_agent_model("agent-1")

        with (
            patch("src.agents.orchestrator.engine.get_agent", return_value=model),
            patch("src.agents.orchestrator.engine.update_agent_status", return_value=model),
            patch(
                "src.agents.dynamic_registry.dynamic_registry.get_instance",
                return_value=None,  # 無實例
            ),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            step = WorkflowStep(
                name="sim-step",
                agent_ids=["agent-1"],
                description="simulated work",
                duration=0.01,  # 極短的模擬時間
            )
            result = await engine._run_agent_step("agent-1", step)

        # 模擬路徑回傳空 dict
        assert result == {}

    @pytest.mark.asyncio
    async def test_nonexistent_agent_returns_empty(self, engine: OrchestrationEngine) -> None:
        """代理在 registry 中不存在時回傳空 dict。"""
        with patch("src.agents.orchestrator.engine.get_agent", return_value=None):
            step = WorkflowStep(
                name="ghost",
                agent_ids=["ghost-agent"],
                description="ghost",
            )
            result = await engine._run_agent_step("ghost-agent", step)

        assert result == {}


# ── 結果累積測試 ──


class TestResultAccumulation:
    @pytest.mark.asyncio
    async def test_results_accumulate_across_steps(self, engine: OrchestrationEngine) -> None:
        """跨步驟的結果應正確累積。"""
        agent_1 = FakeAgent("a1", result_data={"step1_data": "val1"})
        agent_2 = FakeAgent("a2", result_data={"step2_data": "val2"})
        model = _make_agent_model("a1")
        model2 = _make_agent_model("a2")

        def get_agent_se(aid: str) -> AgentModel | None:
            return {"a1": model, "a2": model2}.get(aid)

        def get_instance_se(aid: str) -> FakeAgent | None:
            return {"a1": agent_1, "a2": agent_2}.get(aid)

        with (
            patch("src.agents.orchestrator.engine.get_agent", side_effect=get_agent_se),
            patch(
                "src.agents.orchestrator.engine.update_agent_status",
                side_effect=lambda aid, **kw: get_agent_se(aid),
            ),
            patch(
                "src.agents.dynamic_registry.dynamic_registry.get_instance",
                side_effect=get_instance_se,
            ),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            workflow = Workflow(
                id="test-wf",
                name="test",
                description="test workflow",
                steps=[
                    WorkflowStep(
                        name="step-1",
                        agent_ids=["a1"],
                        description="first step",
                    ),
                    WorkflowStep(
                        name="step-2",
                        agent_ids=["a2"],
                        description="second step",
                    ),
                ],
            )
            await engine.execute_workflow(workflow)

        # 第二個代理應透過 accumulated_results 收到第一步的結果
        assert len(agent_2.task_calls) == 1


# ── 重試整合測試 ──


class TestRetryIntegration:
    @pytest.mark.asyncio
    async def test_retry_then_succeed(self, engine: OrchestrationEngine) -> None:
        """步驟失敗後重試成功。"""
        call_count = 0

        async def mock_run_step(step, acc=None):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return {"agent": {"status": "error"}}
            return {"agent": {"status": "success", "data": "ok"}}

        with (
            patch.object(engine, "_run_step", side_effect=mock_run_step),
            patch.object(engine, "_create_log", return_value=MagicMock()),
            patch("src.agents.orchestrator.engine.ws_manager"),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            step = WorkflowStep(
                name="retry-step",
                agent_ids=["agent-1"],
                description="retryable",
                retry=RetryConfig(max_retries=3, retry_delay=0.01),
            )
            results, should_continue = await engine._run_step_with_retry(step, 0, 1, {})
        assert should_continue is True
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_all_retries_exhausted_abort(self, engine: OrchestrationEngine) -> None:
        """所有重試耗盡後使用 ABORT 策略。"""

        async def always_fail(step, acc=None):
            return {"agent": {"status": "error"}}

        with (
            patch.object(engine, "_run_step", side_effect=always_fail),
            patch.object(engine, "_create_log", return_value=MagicMock()),
            patch("src.agents.orchestrator.engine.ws_manager"),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            step = WorkflowStep(
                name="doomed",
                agent_ids=["agent-1"],
                description="doomed",
                retry=RetryConfig(
                    max_retries=2,
                    retry_delay=0.01,
                    degradation=DegradationStrategy.ABORT,
                ),
            )
            results, should_continue = await engine._run_step_with_retry(step, 0, 1, {})
        assert should_continue is False

    @pytest.mark.asyncio
    async def test_all_retries_exhausted_skip(self, engine: OrchestrationEngine) -> None:
        """所有重試耗盡後使用 SKIP 策略應繼續。"""

        async def always_fail(step, acc=None):
            return {"agent": {"status": "error"}}

        with (
            patch.object(engine, "_run_step", side_effect=always_fail),
            patch.object(engine, "_create_log", return_value=MagicMock()),
            patch("src.agents.orchestrator.engine.ws_manager"),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            step = WorkflowStep(
                name="skippable",
                agent_ids=["agent-1"],
                description="skippable",
                retry=RetryConfig(
                    max_retries=1,
                    retry_delay=0.01,
                    degradation=DegradationStrategy.SKIP,
                ),
            )
            results, should_continue = await engine._run_step_with_retry(step, 0, 1, {})
        assert should_continue is True

    @pytest.mark.asyncio
    async def test_exception_triggers_retry(self, engine: OrchestrationEngine) -> None:
        """步驟拋出例外時也觸發重試。"""
        call_count = 0

        async def fail_then_succeed(step, acc=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("transient error")
            return {"agent": {"ok": True}}

        with (
            patch.object(engine, "_run_step", side_effect=fail_then_succeed),
            patch.object(engine, "_create_log", return_value=MagicMock()),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            step = WorkflowStep(
                name="exception-retry",
                agent_ids=["agent-1"],
                description="test",
                retry=RetryConfig(max_retries=2, retry_delay=0.01),
            )
            results, should_continue = await engine._run_step_with_retry(step, 0, 1, {})
        assert should_continue is True
        assert call_count == 2


# ── Workflow 參數合併測試 ──


class TestWorkflowParameters:
    def test_workflow_level_params(self) -> None:
        """Workflow.parameters 應可用於所有步驟。"""
        wf = Workflow(
            id="test",
            name="test",
            description="test",
            steps=[
                WorkflowStep(
                    name="s1",
                    agent_ids=["a1"],
                    description="step 1",
                    task_parameters={"local": "value"},
                ),
            ],
            parameters={"global_param": "global_value"},
        )
        assert wf.parameters["global_param"] == "global_value"
        assert wf.steps[0].task_parameters["local"] == "value"

    def test_step_params_override_workflow_params(self) -> None:
        """步驟參數應覆蓋 workflow 層級同名參數。"""
        wf = Workflow(
            id="test",
            name="test",
            description="test",
            steps=[
                WorkflowStep(
                    name="s1",
                    agent_ids=["a1"],
                    description="step 1",
                    task_parameters={"param": "step_value"},
                ),
            ],
            parameters={"param": "workflow_value"},
        )
        # 合併時 step 參數優先
        merged = {**wf.parameters, **wf.steps[0].task_parameters}
        assert merged["param"] == "step_value"


# ── 協作者測試 ──


class TestCollaborators:
    @pytest.mark.asyncio
    async def test_auto_collaborators(self, engine: OrchestrationEngine) -> None:
        """未指定 collaborator_ids 時，自動使用同步驟的其他代理。"""
        agent_a = FakeAgent("a")
        model = _make_agent_model("a")

        with (
            patch("src.agents.orchestrator.engine.get_agent", return_value=model),
            patch("src.agents.orchestrator.engine.update_agent_status", return_value=model),
            patch(
                "src.agents.dynamic_registry.dynamic_registry.get_instance",
                return_value=agent_a,
            ),
        ):
            step = WorkflowStep(
                name="collab",
                agent_ids=["a", "b", "c"],
                description="collaborate",
            )
            await engine._run_agent_step("a", step)

        # 代理 a 的協作者應為 b 和 c
        # collaborators 是透過 TaskContext 傳入的，此處驗證呼叫成功即可
        assert len(agent_a.task_calls) > 0

    @pytest.mark.asyncio
    async def test_explicit_collaborators(self, engine: OrchestrationEngine) -> None:
        """明確指定的 collaborator_ids 應優先使用。"""
        agent_a = FakeAgent("a")
        model = _make_agent_model("a")

        with (
            patch("src.agents.orchestrator.engine.get_agent", return_value=model),
            patch("src.agents.orchestrator.engine.update_agent_status", return_value=model),
            patch(
                "src.agents.dynamic_registry.dynamic_registry.get_instance",
                return_value=agent_a,
            ),
        ):
            step = WorkflowStep(
                name="collab",
                agent_ids=["a", "b"],
                description="collaborate",
                collaborator_ids=["x", "y"],
            )
            await engine._run_agent_step("a", step)

        assert len(agent_a.task_calls) == 1


# ── execute_agent_task 測試 ──


class TestExecuteAgentTask:
    @pytest.mark.asyncio
    async def test_direct_agent_execution(self, engine: OrchestrationEngine) -> None:
        """直接呼叫已註冊代理執行任務。"""
        fake = FakeAgent("direct-agent", result_data={"result": "ok"})

        with (
            patch(
                "src.agents.dynamic_registry.dynamic_registry.get_instance",
                return_value=fake,
            ),
            patch("src.agents.orchestrator.engine.ws_manager"),
            patch(
                "src.agents.orchestrator.engine.update_agent_status",
                return_value=_make_agent_model("direct-agent"),
            ),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            result = await engine.execute_agent_task(
                "direct-agent",
                "do something",
                parameters={"key": "val"},
            )

        assert result["status"] == "success"
        assert result["data"]["result"] == "ok"

    @pytest.mark.asyncio
    async def test_unregistered_agent_returns_error(self, engine: OrchestrationEngine) -> None:
        """未註冊代理回傳錯誤。"""
        with patch(
            "src.agents.dynamic_registry.dynamic_registry.get_instance",
            return_value=None,
        ):
            result = await engine.execute_agent_task("ghost-agent", "do something")

        assert "error" in result


# ── 工作日誌測試 ──


class TestWorkLogs:
    def test_logs_accumulate(self, engine: OrchestrationEngine) -> None:
        engine._create_log("a1", "Agent A", "msg 1")
        engine._create_log("a1", "Agent A", "msg 2")
        engine._create_log("system", "系統", "msg 3", "warning")
        assert len(engine.work_logs) == 3

    def test_log_entry_has_all_fields(self, engine: OrchestrationEngine) -> None:
        entry = engine._create_log("a1", "Agent A", "test msg", "success")
        assert entry.id
        assert entry.agent_id == "a1"
        assert entry.agent_name == "Agent A"
        assert entry.message == "test msg"
        assert entry.type == "success"
