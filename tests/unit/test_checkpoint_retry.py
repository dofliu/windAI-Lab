"""總監 Checkpoint 機制與錯誤重試/降級策略測試。"""

from __future__ import annotations

import pytest

from src.agents.orchestrator.engine import (
    CheckpointAction,
    CheckpointConfig,
    DegradationStrategy,
    OrchestrationEngine,
    RetryConfig,
    WorkflowStep,
    _deep_search_metric,
)

# ════════════════════════════════════════════════════════════════
# RetryConfig / DegradationStrategy 資料模型
# ════════════════════════════════════════════════════════════════


class TestRetryConfig:
    def test_defaults(self) -> None:
        cfg = RetryConfig()
        assert cfg.max_retries == 0
        assert cfg.retry_delay == 1.0
        assert cfg.exponential_backoff is True
        assert cfg.degradation == DegradationStrategy.ABORT
        assert cfg.fallback_agent_ids == []

    def test_custom(self) -> None:
        cfg = RetryConfig(
            max_retries=3,
            retry_delay=2.0,
            exponential_backoff=False,
            degradation=DegradationStrategy.SKIP,
            fallback_agent_ids=["backup-agent"],
        )
        assert cfg.max_retries == 3
        assert cfg.retry_delay == 2.0
        assert cfg.exponential_backoff is False
        assert cfg.degradation == DegradationStrategy.SKIP
        assert cfg.fallback_agent_ids == ["backup-agent"]


class TestDegradationStrategy:
    def test_values(self) -> None:
        assert DegradationStrategy.ABORT == "abort"
        assert DegradationStrategy.SKIP == "skip"
        assert DegradationStrategy.FALLBACK == "fallback"


# ════════════════════════════════════════════════════════════════
# CheckpointConfig / CheckpointAction 資料模型
# ════════════════════════════════════════════════════════════════


class TestCheckpointConfig:
    def test_defaults(self) -> None:
        cfg = CheckpointConfig()
        assert cfg.enabled is True
        assert cfg.evaluator_agent_id == "project-director"
        assert cfg.quality_rules == {}
        assert cfg.max_reruns == 1
        assert cfg.param_adjustments == {}
        assert cfg.description == "品質檢查"

    def test_custom(self) -> None:
        cfg = CheckpointConfig(
            evaluator_agent_id="custom-evaluator",
            quality_rules={"r2_score": 0.8, "f1_macro": 0.6},
            max_reruns=3,
            param_adjustments={"n_estimators": "double"},
            description="NBM 品質檢查",
        )
        assert cfg.quality_rules["r2_score"] == 0.8
        assert cfg.max_reruns == 3
        assert cfg.param_adjustments == {"n_estimators": "double"}


class TestCheckpointAction:
    def test_values(self) -> None:
        assert CheckpointAction.PASS == "pass"
        assert CheckpointAction.RETRY == "retry"
        assert CheckpointAction.ABORT == "abort"


# ════════════════════════════════════════════════════════════════
# WorkflowStep 含 retry / checkpoint 欄位
# ════════════════════════════════════════════════════════════════


class TestWorkflowStepExtended:
    def test_step_default_no_retry_no_checkpoint(self) -> None:
        step = WorkflowStep(
            name="basic",
            agent_ids=["a1"],
            description="基本步驟",
        )
        assert step.retry.max_retries == 0
        assert step.checkpoint is None

    def test_step_with_retry(self) -> None:
        step = WorkflowStep(
            name="retryable",
            agent_ids=["a1"],
            description="可重試步驟",
            retry=RetryConfig(max_retries=2, degradation=DegradationStrategy.SKIP),
        )
        assert step.retry.max_retries == 2
        assert step.retry.degradation == DegradationStrategy.SKIP

    def test_step_with_checkpoint(self) -> None:
        step = WorkflowStep(
            name="checked",
            agent_ids=["a1"],
            description="有 checkpoint 的步驟",
            checkpoint=CheckpointConfig(
                quality_rules={"r2_score": 0.7},
                max_reruns=2,
            ),
        )
        assert step.checkpoint is not None
        assert step.checkpoint.quality_rules == {"r2_score": 0.7}
        assert step.checkpoint.max_reruns == 2

    def test_step_with_both(self) -> None:
        step = WorkflowStep(
            name="full",
            agent_ids=["a1", "a2"],
            description="完整設定步驟",
            retry=RetryConfig(max_retries=1),
            checkpoint=CheckpointConfig(
                quality_rules={"f1_macro": 0.5},
                param_adjustments={"n_estimators": "increase_50pct"},
            ),
        )
        assert step.retry.max_retries == 1
        assert step.checkpoint is not None
        assert "f1_macro" in step.checkpoint.quality_rules


# ════════════════════════════════════════════════════════════════
# _deep_search_metric 工具函式
# ════════════════════════════════════════════════════════════════


class TestDeepSearchMetric:
    def test_flat_dict(self) -> None:
        data = {"r2_score": 0.85, "mae": 12.3}
        assert _deep_search_metric(data, "r2_score") == 0.85
        assert _deep_search_metric(data, "mae") == 12.3

    def test_nested_dict(self) -> None:
        data = {
            "agent-1": {
                "status": "success",
                "data": {"r2_score": 0.92, "rmse": 5.0},
            }
        }
        assert _deep_search_metric(data, "r2_score") == 0.92
        assert _deep_search_metric(data, "rmse") == 5.0

    def test_deeply_nested(self) -> None:
        data = {"a": {"b": {"c": {"f1_macro": 0.78}}}}
        assert _deep_search_metric(data, "f1_macro") == 0.78

    def test_missing_metric(self) -> None:
        data = {"r2_score": 0.9}
        assert _deep_search_metric(data, "nonexistent") is None

    def test_empty_dict(self) -> None:
        assert _deep_search_metric({}, "any") is None

    def test_non_numeric_value_skipped(self) -> None:
        data = {"r2_score": "not_a_number", "nested": {"r2_score": 0.8}}
        assert _deep_search_metric(data, "r2_score") == 0.8

    def test_list_in_data(self) -> None:
        data = {"results": [{"r2_score": 0.7}, {"r2_score": 0.9}]}
        # 回傳第一個找到的
        assert _deep_search_metric(data, "r2_score") == 0.7

    def test_integer_value(self) -> None:
        data = {"n_estimators": 100}
        assert _deep_search_metric(data, "n_estimators") == 100.0


# ════════════════════════════════════════════════════════════════
# OrchestrationEngine — 品質評估邏輯
# ════════════════════════════════════════════════════════════════


class TestEvaluateQuality:
    def test_no_rules_pass(self) -> None:
        cp = CheckpointConfig(quality_rules={})
        action, violations = OrchestrationEngine._evaluate_quality({}, cp)
        assert action == CheckpointAction.PASS
        assert violations == []

    def test_metrics_above_threshold_pass(self) -> None:
        cp = CheckpointConfig(quality_rules={"r2_score": 0.7, "f1_macro": 0.5})
        results = {
            "agent-1": {"r2_score": 0.85, "f1_macro": 0.72},
        }
        action, violations = OrchestrationEngine._evaluate_quality(results, cp)
        assert action == CheckpointAction.PASS
        assert violations == []

    def test_metric_below_threshold_retry(self) -> None:
        cp = CheckpointConfig(quality_rules={"r2_score": 0.8})
        results = {"agent-1": {"r2_score": 0.65}}
        action, violations = OrchestrationEngine._evaluate_quality(results, cp)
        assert action == CheckpointAction.RETRY
        assert len(violations) == 1
        assert violations[0][0] == "r2_score"
        assert violations[0][1] == 0.65
        assert violations[0][2] == 0.8

    def test_multiple_violations(self) -> None:
        cp = CheckpointConfig(quality_rules={"r2_score": 0.8, "f1_macro": 0.6})
        results = {"a": {"r2_score": 0.5, "f1_macro": 0.3}}
        action, violations = OrchestrationEngine._evaluate_quality(results, cp)
        assert action == CheckpointAction.RETRY
        assert len(violations) == 2

    def test_metric_not_found_pass(self) -> None:
        """若指標不存在於結果中，不視為違規。"""
        cp = CheckpointConfig(quality_rules={"nonexistent": 0.5})
        results = {"a": {"r2_score": 0.9}}
        action, violations = OrchestrationEngine._evaluate_quality(results, cp)
        assert action == CheckpointAction.PASS
        assert violations == []

    def test_nested_metric_detection(self) -> None:
        cp = CheckpointConfig(quality_rules={"r2_score": 0.8})
        results = {
            "power-curve-expert": {
                "status": "success",
                "data": {"model": "nbm", "r2_score": 0.72},
            }
        }
        action, violations = OrchestrationEngine._evaluate_quality(results, cp)
        assert action == CheckpointAction.RETRY
        assert violations[0][1] == 0.72


# ════════════════════════════════════════════════════════════════
# OrchestrationEngine — 參數調整邏輯
# ════════════════════════════════════════════════════════════════


class TestApplyParamAdjustments:
    def test_increase_50pct(self) -> None:
        params = {"n_estimators": 100, "max_depth": 5}
        result = OrchestrationEngine._apply_param_adjustments(
            params, {"n_estimators": "increase_50pct"}
        )
        assert result["n_estimators"] == 150
        assert result["max_depth"] == 5  # 未調整

    def test_double(self) -> None:
        params = {"n_estimators": 100}
        result = OrchestrationEngine._apply_param_adjustments(
            params, {"n_estimators": "double"}
        )
        assert result["n_estimators"] == 200

    def test_halve(self) -> None:
        params = {"learning_rate": 0.1}
        result = OrchestrationEngine._apply_param_adjustments(
            params, {"learning_rate": "halve"}
        )
        assert result["learning_rate"] == pytest.approx(0.05)

    def test_increase_100pct(self) -> None:
        params = {"batch_size": 32}
        result = OrchestrationEngine._apply_param_adjustments(
            params, {"batch_size": "increase_100pct"}
        )
        assert result["batch_size"] == 64

    def test_decrease_50pct(self) -> None:
        params = {"threshold": 1.0}
        result = OrchestrationEngine._apply_param_adjustments(
            params, {"threshold": "decrease_50pct"}
        )
        assert result["threshold"] == pytest.approx(0.5)

    def test_int_stays_int(self) -> None:
        params = {"n_estimators": 100}
        result = OrchestrationEngine._apply_param_adjustments(
            params, {"n_estimators": "increase_50pct"}
        )
        assert isinstance(result["n_estimators"], int)

    def test_float_stays_float(self) -> None:
        params = {"learning_rate": 0.1}
        result = OrchestrationEngine._apply_param_adjustments(
            params, {"learning_rate": "double"}
        )
        assert isinstance(result["learning_rate"], float)

    def test_nonexistent_param_ignored(self) -> None:
        params = {"a": 1}
        result = OrchestrationEngine._apply_param_adjustments(
            params, {"nonexistent": "double"}
        )
        assert result == {"a": 1}

    def test_non_numeric_param_ignored(self) -> None:
        params = {"name": "test_model", "n_estimators": 100}
        result = OrchestrationEngine._apply_param_adjustments(
            params, {"name": "double", "n_estimators": "double"}
        )
        assert result["name"] == "test_model"
        assert result["n_estimators"] == 200

    def test_does_not_mutate_original(self) -> None:
        params = {"n_estimators": 100}
        result = OrchestrationEngine._apply_param_adjustments(
            params, {"n_estimators": "double"}
        )
        assert params["n_estimators"] == 100
        assert result["n_estimators"] == 200


# ════════════════════════════════════════════════════════════════
# OrchestrationEngine — 重試延遲計算
# ════════════════════════════════════════════════════════════════


class TestCalcRetryDelay:
    def test_exponential_backoff(self) -> None:
        cfg = RetryConfig(retry_delay=1.0, exponential_backoff=True)
        assert OrchestrationEngine._calc_retry_delay(cfg, 0) == 1.0
        assert OrchestrationEngine._calc_retry_delay(cfg, 1) == 2.0
        assert OrchestrationEngine._calc_retry_delay(cfg, 2) == 4.0
        assert OrchestrationEngine._calc_retry_delay(cfg, 3) == 8.0

    def test_fixed_delay(self) -> None:
        cfg = RetryConfig(retry_delay=3.0, exponential_backoff=False)
        assert OrchestrationEngine._calc_retry_delay(cfg, 0) == 3.0
        assert OrchestrationEngine._calc_retry_delay(cfg, 1) == 3.0
        assert OrchestrationEngine._calc_retry_delay(cfg, 5) == 3.0


# ════════════════════════════════════════════════════════════════
# OrchestrationEngine — _step_has_error
# ════════════════════════════════════════════════════════════════


class TestStepHasError:
    def test_no_error(self) -> None:
        results = {"a": {"status": "success", "data": {}}}
        assert OrchestrationEngine._step_has_error(results) is False

    def test_with_error(self) -> None:
        results = {"a": {"status": "error", "errors": ["something failed"]}}
        assert OrchestrationEngine._step_has_error(results) is True

    def test_mixed(self) -> None:
        results = {
            "a": {"status": "success"},
            "b": {"status": "error"},
        }
        assert OrchestrationEngine._step_has_error(results) is True

    def test_non_dict_data(self) -> None:
        results = {"a": [1, 2, 3]}
        assert OrchestrationEngine._step_has_error(results) is False

    def test_empty_results(self) -> None:
        assert OrchestrationEngine._step_has_error({}) is False


# ════════════════════════════════════════════════════════════════
# Workflow 定義整合
# ════════════════════════════════════════════════════════════════


class TestWorkflowWithCheckpointRetry:
    def test_diagnose_workflow_has_checkpoint(self) -> None:
        from src.agents.orchestrator.workflows import create_diagnose_workflow

        wf = create_diagnose_workflow("WT-01")
        ai_step = wf.steps[1]  # AI 故障分析
        assert ai_step.name == "AI 故障分析"
        assert ai_step.retry.max_retries == 2
        assert ai_step.retry.degradation == DegradationStrategy.SKIP
        assert ai_step.checkpoint is not None
        assert "f1_macro" in ai_step.checkpoint.quality_rules
        assert ai_step.checkpoint.max_reruns == 1

    def test_diagnose_nbm_step_has_checkpoint(self) -> None:
        from src.agents.orchestrator.workflows import create_diagnose_workflow

        wf = create_diagnose_workflow("WT-01")
        nbm_step = wf.steps[2]  # 功率曲線 + RUL
        assert nbm_step.checkpoint is not None
        assert "r2_score" in nbm_step.checkpoint.quality_rules

    def test_ai_train_has_checkpoint(self) -> None:
        from src.agents.orchestrator.workflows import create_ai_train_workflow

        wf = create_ai_train_workflow("WT-01")
        train_step = wf.steps[2]  # 模型訓練（平行）
        assert train_step.retry.max_retries == 2
        assert train_step.checkpoint is not None
        assert train_step.checkpoint.max_reruns == 2

    def test_train_nbm_has_checkpoint(self) -> None:
        from src.agents.orchestrator.workflows import create_train_nbm_workflow

        wf = create_train_nbm_workflow("WT-01")
        nbm_step = wf.steps[1]  # NBM 功率曲線訓練
        assert nbm_step.retry.max_retries == 2
        assert nbm_step.checkpoint is not None
        assert "r2_score" in nbm_step.checkpoint.quality_rules

    def test_monthly_review_has_checkpoint(self) -> None:
        from src.agents.orchestrator.workflows import create_monthly_review_workflow

        wf = create_monthly_review_workflow("WT-01")
        analysis_step = wf.steps[3]  # 故障分析 + 健康評分
        assert analysis_step.retry.max_retries == 1
        assert analysis_step.checkpoint is not None

    def test_lit_search_no_checkpoint(self) -> None:
        from src.agents.orchestrator.workflows import create_lit_search_workflow

        wf = create_lit_search_workflow("test topic")
        # 文獻搜索不需要品質檢查
        for step in wf.steps:
            assert step.checkpoint is None

    def test_step_without_retry_has_zero_retries(self) -> None:
        from src.agents.orchestrator.workflows import create_data_load_workflow

        wf = create_data_load_workflow("WT-01")
        for step in wf.steps:
            assert step.retry.max_retries == 0
