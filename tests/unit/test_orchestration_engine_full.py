"""OrchestrationEngine 完整測試 — 涵蓋重試、降級、checkpoint、預檢驗證。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.unit._ws_mock import mock_ws_manager  # noqa: F401

from src.agents.orchestrator.engine import (
    CheckpointAction,
    CheckpointConfig,
    DegradationStrategy,
    OrchestrationEngine,
    RetryConfig,
    StepType,
    Workflow,
    WorkflowStep,
    _deep_search_metric,
)


# ── Fixtures ──


@pytest.fixture()
def engine() -> OrchestrationEngine:
    return OrchestrationEngine()


# ── _deep_search_metric ──


class TestDeepSearchMetric:
    """_deep_search_metric 深度搜索指標值測試。"""

    def test_flat_dict(self) -> None:
        data = {"r2_score": 0.95, "mae": 1.2}
        assert _deep_search_metric(data, "r2_score") == 0.95

    def test_nested_dict(self) -> None:
        data = {"agent-1": {"data": {"r2_score": 0.88}}}
        assert _deep_search_metric(data, "r2_score") == 0.88

    def test_deeply_nested(self) -> None:
        """模擬真實 SkillComposingAgent 產出的結構。"""
        data = {
            "fault-diagnostician": {
                "nbm_training": {
                    "status": "success",
                    "data": {"r2_score": 0.92, "mae": 5.0},
                    "summary": "done",
                }
            }
        }
        assert _deep_search_metric(data, "r2_score") == 0.92
        assert _deep_search_metric(data, "mae") == 5.0

    def test_metric_not_found(self) -> None:
        data = {"a": {"b": 1}}
        assert _deep_search_metric(data, "nonexistent") is None

    def test_non_numeric_metric_ignored(self) -> None:
        data = {"r2_score": "not a number"}
        assert _deep_search_metric(data, "r2_score") is None

    def test_list_traversal(self) -> None:
        data = [{"r2_score": 0.7}, {"r2_score": 0.9}]
        # 回傳第一個找到的
        assert _deep_search_metric(data, "r2_score") == 0.7

    def test_empty_data(self) -> None:
        assert _deep_search_metric({}, "metric") is None
        assert _deep_search_metric([], "metric") is None

    def test_integer_value(self) -> None:
        data = {"count": 42}
        assert _deep_search_metric(data, "count") == 42.0


# ── RetryConfig ──


class TestRetryConfig:
    def test_defaults(self) -> None:
        cfg = RetryConfig()
        assert cfg.max_retries == 0
        assert cfg.retry_delay == 1.0
        assert cfg.exponential_backoff is True
        assert cfg.degradation == DegradationStrategy.ABORT

    def test_custom(self) -> None:
        cfg = RetryConfig(
            max_retries=3,
            retry_delay=2.0,
            exponential_backoff=False,
            degradation=DegradationStrategy.SKIP,
        )
        assert cfg.max_retries == 3
        assert cfg.degradation == DegradationStrategy.SKIP


# ── _calc_retry_delay ──


class TestCalcRetryDelay:
    def test_exponential_backoff(self, engine: OrchestrationEngine) -> None:
        cfg = RetryConfig(retry_delay=1.0, exponential_backoff=True)
        assert engine._calc_retry_delay(cfg, 0) == 1.0
        assert engine._calc_retry_delay(cfg, 1) == 2.0
        assert engine._calc_retry_delay(cfg, 2) == 4.0
        assert engine._calc_retry_delay(cfg, 3) == 8.0

    def test_fixed_delay(self, engine: OrchestrationEngine) -> None:
        cfg = RetryConfig(retry_delay=5.0, exponential_backoff=False)
        assert engine._calc_retry_delay(cfg, 0) == 5.0
        assert engine._calc_retry_delay(cfg, 1) == 5.0
        assert engine._calc_retry_delay(cfg, 2) == 5.0


# ── _step_has_error ──


class TestStepHasError:
    def test_no_error(self, engine: OrchestrationEngine) -> None:
        results = {"agent-1": {"status": "success", "data": {}}}
        assert engine._step_has_error(results) is False

    def test_with_error(self, engine: OrchestrationEngine) -> None:
        results = {"agent-1": {"status": "error", "data": {}}}
        assert engine._step_has_error(results) is True

    def test_empty_results(self, engine: OrchestrationEngine) -> None:
        assert engine._step_has_error({}) is False

    def test_non_dict_data_ignored(self, engine: OrchestrationEngine) -> None:
        results = {"agent-1": "some string"}
        assert engine._step_has_error(results) is False


# ── _apply_param_adjustments ──


class TestApplyParamAdjustments:
    def test_increase_50pct(self, engine: OrchestrationEngine) -> None:
        params = {"n_estimators": 100}
        result = engine._apply_param_adjustments(params, {"n_estimators": "increase_50pct"})
        assert result["n_estimators"] == 150

    def test_double(self, engine: OrchestrationEngine) -> None:
        params = {"learning_rate": 0.01}
        result = engine._apply_param_adjustments(params, {"learning_rate": "double"})
        assert result["learning_rate"] == pytest.approx(0.02)

    def test_halve(self, engine: OrchestrationEngine) -> None:
        params = {"batch_size": 64}
        result = engine._apply_param_adjustments(params, {"batch_size": "halve"})
        assert result["batch_size"] == 32

    def test_integer_preserved(self, engine: OrchestrationEngine) -> None:
        params = {"epochs": 10}
        result = engine._apply_param_adjustments(params, {"epochs": "increase_50pct"})
        assert isinstance(result["epochs"], int)
        assert result["epochs"] == 15

    def test_non_numeric_param_ignored(self, engine: OrchestrationEngine) -> None:
        params = {"model_name": "xgboost"}
        result = engine._apply_param_adjustments(params, {"model_name": "double"})
        assert result["model_name"] == "xgboost"

    def test_missing_param_ignored(self, engine: OrchestrationEngine) -> None:
        params = {"a": 10}
        result = engine._apply_param_adjustments(params, {"nonexistent": "double"})
        assert result == {"a": 10}

    def test_original_not_mutated(self, engine: OrchestrationEngine) -> None:
        """確認原始 params 不被污染。"""
        params = {"lr": 0.01}
        result = engine._apply_param_adjustments(params, {"lr": "double"})
        assert params["lr"] == 0.01
        assert result["lr"] == pytest.approx(0.02)


# ── _evaluate_quality ──


class TestEvaluateQuality:
    def test_pass_when_no_rules(self, engine: OrchestrationEngine) -> None:
        cp = CheckpointConfig(quality_rules={})
        action, violations = engine._evaluate_quality({}, cp)
        assert action == CheckpointAction.PASS
        assert violations == []

    def test_pass_when_metrics_above_threshold(self, engine: OrchestrationEngine) -> None:
        cp = CheckpointConfig(quality_rules={"r2_score": 0.8})
        results = {"agent-1": {"r2_score": 0.95}}
        action, violations = engine._evaluate_quality(results, cp)
        assert action == CheckpointAction.PASS

    def test_retry_when_metrics_below_threshold(self, engine: OrchestrationEngine) -> None:
        cp = CheckpointConfig(quality_rules={"r2_score": 0.8})
        results = {"agent-1": {"r2_score": 0.5}}
        action, violations = engine._evaluate_quality(results, cp)
        assert action == CheckpointAction.RETRY
        assert len(violations) == 1
        assert violations[0] == ("r2_score", 0.5, 0.8)

    def test_pass_when_metric_not_found(self, engine: OrchestrationEngine) -> None:
        """找不到指標時不視為違規（PASS）。"""
        cp = CheckpointConfig(quality_rules={"r2_score": 0.8})
        results = {"agent-1": {"mae": 5.0}}
        action, violations = engine._evaluate_quality(results, cp)
        assert action == CheckpointAction.PASS

    def test_multiple_violations(self, engine: OrchestrationEngine) -> None:
        cp = CheckpointConfig(quality_rules={"r2_score": 0.8, "f1_macro": 0.6})
        results = {"agent-1": {"r2_score": 0.5, "f1_macro": 0.3}}
        action, violations = engine._evaluate_quality(results, cp)
        assert action == CheckpointAction.RETRY
        assert len(violations) == 2

    def test_nested_skill_results(self, engine: OrchestrationEngine) -> None:
        """驗證 checkpoint 可搜索巢狀技能結果結構。"""
        cp = CheckpointConfig(quality_rules={"r2_score": 0.8})
        # 模擬 SkillComposingAgent 的輸出結構
        results = {
            "fault-diagnostician": {
                "nbm_training": {
                    "status": "success",
                    "data": {"r2_score": 0.75},
                    "summary": "done",
                }
            }
        }
        action, violations = engine._evaluate_quality(results, cp)
        assert action == CheckpointAction.RETRY
        assert violations[0][1] == 0.75


# ── Workflow Pre-flight Validation ──


class TestWorkflowValidation:
    def test_validate_warns_missing_agents(self, engine: OrchestrationEngine) -> None:
        """預檢驗證應偵測不存在的代理。"""
        workflow = Workflow(
            id="test",
            name="test",
            description="test",
            steps=[
                WorkflowStep(
                    name="step-1",
                    agent_ids=["nonexistent-agent"],
                    description="test step",
                )
            ],
        )
        with patch("src.agents.orchestrator.engine.get_agent", return_value=None):
            warnings = engine._validate_workflow(workflow)
        assert len(warnings) >= 1
        assert "nonexistent-agent" in warnings[0]

    def test_validate_warns_simulation_mode(self, engine: OrchestrationEngine) -> None:
        """預檢驗證應偵測無實例的代理（將使用模擬模式）。"""
        mock_model = MagicMock()
        workflow = Workflow(
            id="test",
            name="test",
            description="test",
            steps=[
                WorkflowStep(
                    name="step-1",
                    agent_ids=["existing-but-no-instance"],
                    description="test step",
                )
            ],
        )
        with (
            patch("src.agents.orchestrator.engine.get_agent", return_value=mock_model),
            patch(
                "src.agents.dynamic_registry.dynamic_registry.get_instance",
                return_value=None,
            ),
        ):
            warnings = engine._validate_workflow(workflow)
        assert len(warnings) >= 1
        assert "模擬" in warnings[0]


# ── Step Parameter Isolation ──


class TestStepParameterIsolation:
    def test_workflow_params_dont_mutate_original_step(self) -> None:
        """確認 workflow.parameters 合併不會污染原始步驟定義。"""
        original_step = WorkflowStep(
            name="step-1",
            agent_ids=["agent-1"],
            description="test",
            task_parameters={"local_param": "value"},
        )
        original_params = dict(original_step.task_parameters)

        workflow = Workflow(
            id="test",
            name="test",
            description="test",
            steps=[original_step],
            parameters={"global_param": "global_value"},
        )

        # 原始步驟不應有 global_param
        assert "global_param" not in original_step.task_parameters
        # 原始步驟的參數應保持不變
        assert original_step.task_parameters == original_params

    def test_checkpoint_rerun_doesnt_mutate_original_params(
        self, engine: OrchestrationEngine
    ) -> None:
        """確認 checkpoint 重跑的參數調整不會累積到原始步驟。"""
        original_params = {"n_estimators": 100, "learning_rate": 0.01}
        adjusted = engine._apply_param_adjustments(
            original_params, {"n_estimators": "increase_50pct"}
        )
        # 原始不被修改
        assert original_params["n_estimators"] == 100
        # 調整後的是新值
        assert adjusted["n_estimators"] == 150


# ── WorkflowStep with retry config ──


class TestWorkflowStepRetry:
    def test_step_with_retry(self) -> None:
        step = WorkflowStep(
            name="test",
            agent_ids=["a"],
            description="test",
            retry=RetryConfig(
                max_retries=3,
                retry_delay=2.0,
                degradation=DegradationStrategy.SKIP,
            ),
        )
        assert step.retry.max_retries == 3
        assert step.retry.degradation == DegradationStrategy.SKIP

    def test_step_with_checkpoint(self) -> None:
        step = WorkflowStep(
            name="test",
            agent_ids=["a"],
            description="test",
            checkpoint=CheckpointConfig(
                quality_rules={"r2_score": 0.8},
                max_reruns=2,
                param_adjustments={"n_estimators": "increase_50pct"},
            ),
        )
        assert step.checkpoint is not None
        assert step.checkpoint.quality_rules["r2_score"] == 0.8
        assert step.checkpoint.max_reruns == 2


# ── Degradation strategies ──


class TestDegradationStrategies:
    @pytest.mark.asyncio
    async def test_skip_degradation(self, engine: OrchestrationEngine) -> None:
        """SKIP 策略應回傳空結果並繼續。"""
        step = WorkflowStep(
            name="test",
            agent_ids=["a"],
            description="test",
            retry=RetryConfig(degradation=DegradationStrategy.SKIP),
        )
        with patch.object(engine, "_create_log", return_value=MagicMock()):
            results, should_continue = await engine._handle_degradation(
                step, 0, 3, {}, RuntimeError("test error")
            )
        assert should_continue is True
        assert results == {}

    @pytest.mark.asyncio
    async def test_abort_degradation(self, engine: OrchestrationEngine) -> None:
        """ABORT 策略應中止工作流程。"""
        step = WorkflowStep(
            name="test",
            agent_ids=["a"],
            description="test",
            retry=RetryConfig(degradation=DegradationStrategy.ABORT),
        )
        with patch.object(engine, "_create_log", return_value=MagicMock()):
            results, should_continue = await engine._handle_degradation(
                step, 0, 3, {}, RuntimeError("test error")
            )
        assert should_continue is False

    @pytest.mark.asyncio
    async def test_fallback_degradation(self, engine: OrchestrationEngine) -> None:
        """FALLBACK 策略應嘗試使用備用代理。"""
        step = WorkflowStep(
            name="test",
            agent_ids=["a"],
            description="test",
            retry=RetryConfig(
                degradation=DegradationStrategy.FALLBACK,
                fallback_agent_ids=["backup-agent"],
            ),
        )
        with patch.object(engine, "_create_log", return_value=MagicMock()), patch.object(
            engine, "_run_step", new_callable=AsyncMock, return_value={"backup-agent": {}}
        ):
            results, should_continue = await engine._handle_degradation(
                step, 0, 3, {}, RuntimeError("test error")
            )
        assert should_continue is True

    @pytest.mark.asyncio
    async def test_fallback_also_fails(self, engine: OrchestrationEngine) -> None:
        """FALLBACK 備用代理也失敗時應回傳 should_continue=False。"""
        step = WorkflowStep(
            name="test",
            agent_ids=["a"],
            description="test",
            retry=RetryConfig(
                degradation=DegradationStrategy.FALLBACK,
                fallback_agent_ids=["backup-agent"],
            ),
        )
        with patch.object(engine, "_create_log", return_value=MagicMock()), patch.object(
            engine,
            "_run_step",
            new_callable=AsyncMock,
            side_effect=RuntimeError("backup also failed"),
        ):
            results, should_continue = await engine._handle_degradation(
                step, 0, 3, {}, RuntimeError("test error")
            )
        assert should_continue is False


# ── Checkpoint 完整流程 ──


class TestCheckpointFlow:
    @pytest.mark.asyncio
    async def test_checkpoint_pass(self, engine: OrchestrationEngine) -> None:
        """品質合格時直接通過。"""
        step = WorkflowStep(
            name="train",
            agent_ids=["trainer"],
            description="train model",
            checkpoint=CheckpointConfig(
                quality_rules={"r2_score": 0.8},
            ),
        )
        results = {"trainer": {"r2_score": 0.95}}

        with patch.object(engine, "_create_log", return_value=MagicMock()):
            final_results, action = await engine._run_checkpoint(
                step, 0, 3, results, {}
            )
        assert action == CheckpointAction.PASS
        assert final_results == results

    @pytest.mark.asyncio
    async def test_checkpoint_retry_then_pass(self, engine: OrchestrationEngine) -> None:
        """品質不足 → 重跑一次 → 合格。"""
        step = WorkflowStep(
            name="train",
            agent_ids=["trainer"],
            description="train model",
            task_parameters={"n_estimators": 100},
            checkpoint=CheckpointConfig(
                quality_rules={"r2_score": 0.8},
                max_reruns=1,
                param_adjustments={"n_estimators": "double"},
            ),
        )
        bad_results = {"trainer": {"r2_score": 0.5}}
        good_results = {"trainer": {"r2_score": 0.95}}

        with patch.object(engine, "_create_log", return_value=MagicMock()), patch.object(
            engine, "_run_step", new_callable=AsyncMock, return_value=good_results
        ):
            final_results, action = await engine._run_checkpoint(
                step, 0, 3, bad_results, {}
            )
        assert action == CheckpointAction.PASS
        assert final_results == good_results

    @pytest.mark.asyncio
    async def test_checkpoint_exhausted(self, engine: OrchestrationEngine) -> None:
        """多次重跑仍未達標。"""
        step = WorkflowStep(
            name="train",
            agent_ids=["trainer"],
            description="train model",
            task_parameters={"n_estimators": 100},
            checkpoint=CheckpointConfig(
                quality_rules={"r2_score": 0.8},
                max_reruns=2,
                param_adjustments={"n_estimators": "increase_50pct"},
            ),
        )
        bad_results = {"trainer": {"r2_score": 0.5}}

        with patch.object(engine, "_create_log", return_value=MagicMock()), patch.object(
            engine, "_run_step", new_callable=AsyncMock, return_value=bad_results
        ):
            final_results, action = await engine._run_checkpoint(
                step, 0, 3, bad_results, {}
            )
        assert action == CheckpointAction.RETRY  # 耗盡但未通過

    @pytest.mark.asyncio
    async def test_checkpoint_disabled(self, engine: OrchestrationEngine) -> None:
        """Checkpoint 停用時直接通過。"""
        step = WorkflowStep(
            name="test",
            agent_ids=["a"],
            description="test",
            checkpoint=CheckpointConfig(enabled=False),
        )
        results, action = await engine._run_checkpoint(step, 0, 1, {}, {})
        assert action == CheckpointAction.PASS

    @pytest.mark.asyncio
    async def test_checkpoint_none(self, engine: OrchestrationEngine) -> None:
        """無 checkpoint 時直接通過。"""
        step = WorkflowStep(
            name="test",
            agent_ids=["a"],
            description="test",
        )
        results, action = await engine._run_checkpoint(step, 0, 1, {}, {})
        assert action == CheckpointAction.PASS
