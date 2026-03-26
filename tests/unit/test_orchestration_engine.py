"""OrchestrationEngine 測試。"""

from __future__ import annotations

import pytest

from src.agents.orchestrator.engine import (
    OrchestrationEngine,
    StepType,
    Workflow,
    WorkflowStep,
)


class TestWorkflowDataModels:
    def test_step_type_values(self) -> None:
        assert StepType.SEQUENTIAL == "sequential"
        assert StepType.PARALLEL == "parallel"
        assert StepType.DECISION == "decision"

    def test_workflow_step_defaults(self) -> None:
        step = WorkflowStep(
            name="test_step",
            agent_ids=["agent-1"],
            description="測試步驟",
        )
        assert step.duration == 3.0
        assert step.step_type == StepType.SEQUENTIAL
        assert step.sub_messages == []
        assert step.progress_messages == {}

    def test_workflow_step_full(self) -> None:
        step = WorkflowStep(
            name="analysis",
            agent_ids=["agent-a", "agent-b"],
            description="平行分析",
            duration=5.0,
            step_type=StepType.PARALLEL,
            sub_messages=["步驟一完成", "步驟二完成"],
            progress_messages={50: "進度 50%", 100: "完成"},
        )
        assert len(step.agent_ids) == 2
        assert step.step_type == StepType.PARALLEL
        assert step.progress_messages[50] == "進度 50%"

    def test_workflow_creation(self) -> None:
        wf = Workflow(
            id="wf-001",
            name="SCADA 清洗流程",
            description="自動清洗 SCADA 資料",
            steps=[
                WorkflowStep(
                    name="載入",
                    agent_ids=["data-loader"],
                    description="載入原始資料",
                ),
                WorkflowStep(
                    name="清洗",
                    agent_ids=["data-cleaner"],
                    description="清洗異常值",
                ),
            ],
        )
        assert wf.id == "wf-001"
        assert len(wf.steps) == 2


class TestOrchestrationEngine:
    @pytest.fixture()
    def engine(self) -> OrchestrationEngine:
        return OrchestrationEngine()

    def test_initial_state(self, engine: OrchestrationEngine) -> None:
        assert engine.work_logs == []
        assert len(engine._running_tasks) == 0

    def test_create_log(self, engine: OrchestrationEngine) -> None:
        entry = engine._create_log("agent-1", "測試代理", "開始工作", "info")
        assert entry.agent_id == "agent-1"
        assert entry.agent_name == "測試代理"
        assert entry.message == "開始工作"
        assert entry.type == "info"
        assert entry.id  # 應有 UUID
        assert len(engine.work_logs) == 1

    def test_create_log_types(self, engine: OrchestrationEngine) -> None:
        engine._create_log("a1", "Agent A", "msg 1", "info")
        engine._create_log("a1", "Agent A", "msg 2", "success")
        engine._create_log("a1", "Agent A", "msg 3", "warning")
        engine._create_log("a1", "Agent A", "msg 4", "error")
        assert len(engine.work_logs) == 4
        types = [log.type for log in engine.work_logs]
        assert types == ["info", "success", "warning", "error"]

    def test_work_logs_accumulate(self, engine: OrchestrationEngine) -> None:
        for i in range(5):
            engine._create_log("a", "Agent", f"msg {i}")
        assert len(engine.work_logs) == 5
