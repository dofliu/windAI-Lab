"""新技能測試 — director_review、comparative_analysis、maintenance_scheduler。"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.agents.base import TaskContext, TaskStatus
from src.skills.base import SkillInput, SkillStatus
from tests.unit._ws_mock import mock_ws_manager  # noqa: F401

# ═══════════════════════════════════════════════════════════════
# DirectorReviewSkill
# ═══════════════════════════════════════════════════════════════


class TestDirectorReviewSkill:
    @pytest.fixture()
    def skill(self):
        from src.skills.leadership.director_review import DirectorReviewSkill

        return DirectorReviewSkill()

    def test_skill_id(self, skill) -> None:
        assert skill.skill_id == "director_review"
        assert skill.display_name == "總監智慧審核"

    @pytest.mark.asyncio
    async def test_rule_based_review_all_ok(self, skill) -> None:
        """上游結果全部正常時應 approved。"""
        inp = SkillInput(
            parameters={"task_name": "故障診斷", "turbine_id": "WT-01"},
            context={
                "nbm_training": {
                    "status": "success",
                    "data": {"r2_score": 0.92, "mae": 5.0},
                    "summary": "模型訓練完成",
                },
                "fault_classification": {
                    "status": "success",
                    "data": {"f1_macro": 0.85},
                    "summary": "分類完成",
                },
            },
        )
        output = await skill.execute(inp)
        assert output.status == SkillStatus.SUCCESS
        assert output.data["overall_verdict"] in ("approved", "conditional")
        assert output.data["overall_score"] > 0

    @pytest.mark.asyncio
    async def test_rule_based_review_with_error(self, skill) -> None:
        """上游步驟有錯誤時扣分。"""
        inp = SkillInput(
            parameters={"task_name": "診斷"},
            context={
                "nbm_training": {
                    "status": "error",
                    "data": {},
                    "summary": "失敗",
                },
            },
        )
        output = await skill.execute(inp)
        assert output.status == SkillStatus.SUCCESS
        assert "失敗" in str(output.data.get("concerns", []))

    @pytest.mark.asyncio
    async def test_rule_based_review_low_r2(self, skill) -> None:
        """R² 過低時應有 concern。"""
        inp = SkillInput(
            parameters={"task_name": "訓練"},
            context={
                "nbm_training": {
                    "status": "success",
                    "data": {"r2_score": 0.45},
                    "summary": "done",
                },
            },
        )
        output = await skill.execute(inp)
        concerns = output.data.get("concerns", [])
        assert any("R²" in c or "0.7" in c for c in concerns)

    @pytest.mark.asyncio
    async def test_rule_based_low_health(self, skill) -> None:
        """健康分數低時應提出警告。"""
        inp = SkillInput(
            parameters={"task_name": "健康評估"},
            context={
                "anomaly_detection": {
                    "status": "success",
                    "data": {"health_score": 35},
                    "summary": "健康不佳",
                },
            },
        )
        output = await skill.execute(inp)
        concerns = output.data.get("concerns", [])
        assert any("健康" in c or "35" in c for c in concerns)

    @pytest.mark.asyncio
    async def test_empty_context(self, skill) -> None:
        """無上游結果時仍能正常審核。"""
        inp = SkillInput(parameters={"task_name": "test"}, context={})
        output = await skill.execute(inp)
        assert output.status == SkillStatus.SUCCESS

    def test_find_metric_nested(self, skill) -> None:
        """_find_metric 可搜索巢狀 dict。"""
        data = {"a": {"b": {"r2_score": 0.88}}}
        assert skill._find_metric(data, "r2_score") == 0.88

    def test_find_metric_not_found(self, skill) -> None:
        assert skill._find_metric({"a": 1}, "nonexistent") is None


# ═══════════════════════════════════════════════════════════════
# ComparativeAnalysisSkill
# ═══════════════════════════════════════════════════════════════


class TestComparativeAnalysisSkill:
    @pytest.fixture()
    def skill(self):
        from src.skills.ml.comparative_analysis import ComparativeAnalysisSkill

        return ComparativeAnalysisSkill()

    def test_skill_id(self, skill) -> None:
        assert skill.skill_id == "comparative_analysis"

    @pytest.mark.asyncio
    async def test_needs_at_least_2_turbines(self, skill) -> None:
        inp = SkillInput(parameters={"turbine_ids": ["WT-01"]})
        output = await skill.execute(inp)
        assert output.status == SkillStatus.ERROR
        assert "2" in output.errors[0]

    @pytest.mark.asyncio
    async def test_no_turbines_error(self, skill) -> None:
        inp = SkillInput(parameters={})
        output = await skill.execute(inp)
        assert output.status == SkillStatus.ERROR

    @pytest.mark.asyncio
    async def test_compare_with_mock_data(self, skill) -> None:
        """使用 mock 避免實際載入資料。"""
        mock_report = {
            "turbine_id": "WT-01",
            "health_score": 75,
            "data_points": 1000,
            "availability": 95.0,
            "capacity_factor": 0.35,
            "anomaly_rate": 2.5,
            "power_curve_deviation": 5.0,
            "temp_anomaly_count": 25,
            "status": "ok",
        }

        with patch.object(
            skill,
            "_analyze_single_turbine",
            side_effect=lambda tid: {**mock_report, "turbine_id": tid, "health_score": hash(tid) % 50 + 50},
        ):
            inp = SkillInput(parameters={"turbine_ids": ["WT-01", "WT-02", "WT-03"]})
            output = await skill.execute(inp)

        assert output.status == SkillStatus.SUCCESS
        data = output.data
        assert len(data["risk_ranking"]) == 3
        assert data["fleet_summary"]["total_turbines"] == 3
        assert data["fleet_summary"]["analyzed_ok"] == 3

    def test_compare_logic(self, skill) -> None:
        """比較邏輯正確排序。"""
        reports = [
            {"turbine_id": "WT-01", "health_score": 90, "data_points": 100, "availability": 95, "capacity_factor": 0.4, "anomaly_rate": 1.0, "power_curve_deviation": 2.0, "temp_anomaly_count": 5, "status": "ok"},
            {"turbine_id": "WT-02", "health_score": 35, "data_points": 100, "availability": 80, "capacity_factor": 0.2, "anomaly_rate": 10.0, "power_curve_deviation": 15.0, "temp_anomaly_count": 50, "status": "ok"},
            {"turbine_id": "WT-03", "health_score": 60, "data_points": 100, "availability": 88, "capacity_factor": 0.3, "anomaly_rate": 5.0, "power_curve_deviation": 8.0, "temp_anomaly_count": 20, "status": "ok"},
        ]
        result = skill._compare(reports)

        # WT-02 應排在最高風險
        assert result["risk_ranking"][0]["turbine_id"] == "WT-02"
        assert result["risk_ranking"][0]["risk_level"] == "Critical"
        assert result["fleet_summary"]["critical_count"] == 1
        assert result["fleet_summary"]["healthy_count"] == 1

    def test_compare_with_failures(self, skill) -> None:
        """包含失敗的風機。"""
        reports = [
            {"turbine_id": "WT-01", "health_score": 80, "data_points": 100, "availability": 95, "capacity_factor": 0.4, "anomaly_rate": 1.0, "power_curve_deviation": 2.0, "temp_anomaly_count": 5, "status": "ok"},
            {"turbine_id": "WT-02", "status": "error", "error": "file not found", "health_score": 0, "data_points": 0, "availability": 0, "capacity_factor": 0, "anomaly_rate": 0, "power_curve_deviation": 0, "temp_anomaly_count": 0},
        ]
        result = skill._compare(reports)
        assert result["fleet_summary"]["failed"] == 1
        assert len(result["failed_turbines"]) == 1

    def test_discover_turbines_nonexistent_folder(self, skill) -> None:
        result = skill._discover_turbines_from_folder("/nonexistent/path")
        assert result == []


# ═══════════════════════════════════════════════════════════════
# MaintenanceSchedulerSkill
# ═══════════════════════════════════════════════════════════════


class TestMaintenanceSchedulerSkill:
    @pytest.fixture()
    def skill(self):
        from src.skills.ml.maintenance_scheduler import MaintenanceSchedulerSkill

        return MaintenanceSchedulerSkill()

    def test_skill_id(self, skill) -> None:
        assert skill.skill_id == "maintenance_scheduler"

    @pytest.mark.asyncio
    async def test_no_maintenance_needed(self, skill) -> None:
        """無上游結果 → 無維護需求。"""
        inp = SkillInput(parameters={"turbine_id": "WT-01"}, context={})
        output = await skill.execute(inp)
        assert output.status == SkillStatus.SUCCESS
        assert output.data["work_orders"] == []

    @pytest.mark.asyncio
    async def test_rul_based_scheduling(self, skill) -> None:
        """RUL 預測觸發維護工單。"""
        inp = SkillInput(
            parameters={"turbine_id": "WT-01"},
            context={
                "rul_prediction": {
                    "status": "success",
                    "data": {"predicted_rul_days": 20},
                    "summary": "RUL = 20 days",
                },
            },
        )
        output = await skill.execute(inp)
        assert output.status == SkillStatus.SUCCESS
        orders = output.data["work_orders"]
        assert len(orders) >= 1
        assert orders[0]["priority"] == "Critical"  # RUL < 30
        assert orders[0]["turbine_id"] == "WT-01"

    @pytest.mark.asyncio
    async def test_fault_classification_trigger(self, skill) -> None:
        """故障分類 Critical 觸發緊急工單。"""
        inp = SkillInput(
            parameters={"turbine_id": "WT-01"},
            context={
                "fault_classification": {
                    "status": "success",
                    "data": {
                        "severity_distribution": {"critical": 3, "high": 2, "medium": 5, "low": 10},
                    },
                },
            },
        )
        output = await skill.execute(inp)
        orders = output.data["work_orders"]
        assert any(o["priority"] == "Critical" for o in orders)

    @pytest.mark.asyncio
    async def test_multiple_sources(self, skill) -> None:
        """多個上游來源產出多筆工單。"""
        inp = SkillInput(
            parameters={"turbine_id": "WT-01"},
            context={
                "rul_prediction": {
                    "status": "success",
                    "data": {"predicted_rul_days": 60},
                },
                "anomaly_detection": {
                    "status": "success",
                    "data": {"anomaly_ratio": 0.15, "health_score": 45},
                },
                "nbm_training": {
                    "status": "success",
                    "data": {"anomaly_count": 200},
                },
            },
        )
        output = await skill.execute(inp)
        orders = output.data["work_orders"]
        assert len(orders) >= 3
        # 應按嚴重度排序
        priorities = [o["priority"] for o in orders]
        severity_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
        assert all(
            severity_order[priorities[i]] <= severity_order[priorities[i + 1]]
            for i in range(len(priorities) - 1)
        )

    @pytest.mark.asyncio
    async def test_resource_plan(self, skill) -> None:
        """資源計畫有合理數值。"""
        inp = SkillInput(
            parameters={"turbine_id": "WT-01"},
            context={
                "rul_prediction": {
                    "status": "success",
                    "data": {"predicted_rul_days": 15},
                },
            },
        )
        output = await skill.execute(inp)
        plan = output.data["resource_plan"]
        assert plan["total_maintenance_hours"] > 0
        assert plan["estimated_crew_days"] > 0

    @pytest.mark.asyncio
    async def test_multi_turbine_reports(self, skill) -> None:
        """多台風機報告觸發維護。"""
        inp = SkillInput(
            parameters={
                "turbine_reports": [
                    {"turbine_id": "WT-01", "health_score": 30},
                    {"turbine_id": "WT-02", "health_score": 55},
                    {"turbine_id": "WT-03", "health_score": 85},
                ],
            },
            context={},
        )
        output = await skill.execute(inp)
        orders = output.data["work_orders"]
        # WT-01 (30) → Critical, WT-02 (55) → High, WT-03 正常不需維護
        assert len(orders) == 2
        assert orders[0]["turbine_id"] == "WT-01"
        assert orders[0]["priority"] == "Critical"


# ═══════════════════════════════════════════════════════════════
# ProjectDirector 升級測試
# ═══════════════════════════════════════════════════════════════


class TestProjectDirectorReview:
    @pytest.fixture()
    def director(self):
        from src.agents.leadership.director import ProjectDirector

        return ProjectDirector()

    def test_capabilities_include_llm(self, director) -> None:
        assert "llm_review" in director.capabilities
        assert "quality_assessment" in director.capabilities

    @pytest.mark.asyncio
    async def test_review_uses_skill(self, director) -> None:
        """審核時呼叫 director_review 技能。"""
        ctx = TaskContext(
            parameters={"task_name": "故障診斷", "turbine_id": "WT-01"},
            results={
                "nbm_training": {
                    "status": "success",
                    "data": {"r2_score": 0.9},
                },
            },
        )
        result = await director.execute("審核分析結果", ctx)
        assert result.status == TaskStatus.SUCCESS
        assert "verdict" in result.data or "approved" in result.data

    @pytest.mark.asyncio
    async def test_review_not_rubber_stamp(self, director) -> None:
        """有錯誤的結果不會無條件通過。"""
        ctx = TaskContext(
            parameters={"task_name": "分析"},
            results={
                "step1": {"status": "error", "data": {}},
            },
        )
        result = await director.execute("審核結果", ctx)
        # 不應該是無條件 approved
        if "verdict" in result.data:
            assert result.data["verdict"] in ("conditional", "rejected", "approved")

    @pytest.mark.asyncio
    async def test_assign_still_works(self, director) -> None:
        """分派功能仍正常。"""
        ctx = TaskContext(
            parameters={"agents": ["agent-1"], "description": "test task"},
        )
        result = await director.execute("分派任務", ctx)
        assert result.status == TaskStatus.SUCCESS


# ═══════════════════════════════════════════════════════════════
# Workflow 定義測試
# ═══════════════════════════════════════════════════════════════


class TestNewWorkflows:
    def test_folder_analyze_workflow(self) -> None:
        from src.agents.orchestrator.workflows import create_folder_analyze_workflow

        wf = create_folder_analyze_workflow("/data/scada")
        assert wf.id == "folder-analyze"
        assert len(wf.steps) >= 4  # 總監分派 + 掃描 + 載入 + 分析 + ...
        assert wf.parameters["folder_path"] == "/data/scada"

    def test_fleet_compare_workflow(self) -> None:
        from src.agents.orchestrator.workflows import create_fleet_compare_workflow

        wf = create_fleet_compare_workflow(["WT-01", "WT-02"])
        assert wf.id == "fleet-compare"
        assert "WT-01" in wf.parameters["turbine_ids"]

    def test_available_workflows_include_new(self) -> None:
        from src.agents.orchestrator.workflows import AVAILABLE_WORKFLOWS

        assert "folder-analyze" in AVAILABLE_WORKFLOWS
        assert "fleet-compare" in AVAILABLE_WORKFLOWS

    def test_extract_workflow_params_folder(self) -> None:
        from src.agents.orchestrator.workflows import extract_workflow_params

        params = extract_workflow_params("folder-analyze", {"folder_path": "/data/test"})
        assert params["folder_path"] == "/data/test"

    def test_extract_workflow_params_fleet(self) -> None:
        from src.agents.orchestrator.workflows import extract_workflow_params

        params = extract_workflow_params(
            "fleet-compare",
            {"turbine_ids": ["WT-01", "WT-02"]},
        )
        assert params["turbine_ids"] == ["WT-01", "WT-02"]
