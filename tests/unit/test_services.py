"""src.services 模組的單元測試。

測試代理管理服務（agent_service）與故障診斷服務（diagnosis_service），
確保業務邏輯層的查詢、篩選、任務指派與診斷流程符合預期。
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.api.agent_registry import reset_all_agents
from src.api.models import AgentModel, AgentStatus, AgentTier
from src.core.constants import TASK_ID_PREFIX
from src.core.exceptions import AgentBusyError, AgentNotFoundError
from src.services.agent_service import (
    assign_task,
    get_agent_or_raise,
    list_agents_by_status,
    list_agents_by_tier,
    reset_all,
)
from src.services.diagnosis_service import run_full_diagnosis

# ── 測試隔離 fixture ──────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_registry_state() -> None:
    """每個測試前後重設代理註冊表，確保狀態隔離。"""
    reset_all_agents()
    yield  # type: ignore[misc]
    reset_all_agents()


# ── get_agent_or_raise 測試 ───────────────────────────────────────────────────


class TestGetAgentOrRaise:
    """agent_service.get_agent_or_raise 的測試。"""

    def test_returns_agent_model_for_valid_id(self) -> None:
        """確認有效 ID 回傳 AgentModel 實例。"""
        agent = get_agent_or_raise("project-director")
        assert isinstance(agent, AgentModel)

    def test_returns_correct_agent_for_id(self) -> None:
        """確認回傳的代理 ID 與查詢值一致。"""
        agent = get_agent_or_raise("project-director")
        assert agent.id == "project-director"

    def test_raises_agent_not_found_for_invalid_id(self) -> None:
        """確認無效 ID 拋出 AgentNotFoundError。"""
        with pytest.raises(AgentNotFoundError):
            get_agent_or_raise("this-does-not-exist")

    def test_agent_not_found_error_contains_agent_id(self) -> None:
        """確認 AgentNotFoundError 中包含查詢的代理 ID。"""
        invalid_id = "ghost-agent"
        with pytest.raises(AgentNotFoundError) as exc_info:
            get_agent_or_raise(invalid_id)
        assert exc_info.value.agent_id == invalid_id

    def test_raises_for_empty_string_id(self) -> None:
        """確認空字串 ID 拋出 AgentNotFoundError。"""
        with pytest.raises(AgentNotFoundError):
            get_agent_or_raise("")

    @pytest.mark.parametrize("agent_id", [
        "project-director",
        "scada-processor",
        "model-trainer",
        "paper-writer",
        "backend-dev",
        "iec-specialist",
    ])
    def test_multiple_valid_agent_ids(self, agent_id: str) -> None:
        """確認多個已知的有效代理 ID 均可成功查詢。

        Args:
            agent_id: 代理唯一識別碼。
        """
        agent = get_agent_or_raise(agent_id)
        assert agent.id == agent_id


# ── list_agents_by_tier 測試 ──────────────────────────────────────────────────


class TestListAgentsByTier:
    """agent_service.list_agents_by_tier 的測試。"""

    def test_leadership_tier_returns_4_agents(self) -> None:
        """確認 LEADERSHIP 層級回傳 4 個代理。"""
        agents = list_agents_by_tier(AgentTier.LEADERSHIP)
        assert len(agents) == 4

    def test_data_tier_returns_8_agents(self) -> None:
        """確認 DATA 層級回傳 8 個代理。"""
        agents = list_agents_by_tier(AgentTier.DATA)
        assert len(agents) == 8

    def test_ai_ml_tier_returns_10_agents(self) -> None:
        """確認 AI_ML 層級回傳 10 個代理。"""
        agents = list_agents_by_tier(AgentTier.AI_ML)
        assert len(agents) == 10

    def test_domain_tier_returns_6_agents(self) -> None:
        """確認 DOMAIN 層級回傳 6 個代理。"""
        agents = list_agents_by_tier(AgentTier.DOMAIN)
        assert len(agents) == 6

    def test_engineering_tier_returns_8_agents(self) -> None:
        """確認 ENGINEERING 層級回傳 8 個代理。"""
        agents = list_agents_by_tier(AgentTier.ENGINEERING)
        assert len(agents) == 8

    def test_research_tier_returns_6_agents(self) -> None:
        """確認 RESEARCH 層級回傳 6 個代理。"""
        agents = list_agents_by_tier(AgentTier.RESEARCH)
        assert len(agents) == 6

    def test_all_returned_agents_have_correct_tier(self) -> None:
        """確認回傳列表中所有代理均屬於指定層級。"""
        for tier in AgentTier:
            agents = list_agents_by_tier(tier)
            assert all(a.tier == tier for a in agents), f"層級 {tier} 的代理中有錯誤歸屬"

    def test_returns_list_of_agent_models(self) -> None:
        """確認回傳值為 AgentModel 列表。"""
        agents = list_agents_by_tier(AgentTier.LEADERSHIP)
        assert isinstance(agents, list)
        assert all(isinstance(a, AgentModel) for a in agents)

    def test_all_tiers_combined_count_equals_42(self) -> None:
        """確認所有層級代理總數為 42。"""
        total = sum(len(list_agents_by_tier(tier)) for tier in AgentTier)
        assert total == 42


# ── assign_task 測試 ──────────────────────────────────────────────────────────


class TestAssignTask:
    """agent_service.assign_task 的測試。"""

    def test_returns_task_id_string(self) -> None:
        """確認 assign_task 回傳字串型別的任務 ID。"""
        task_id = assign_task("project-director", "執行資料清洗")
        assert isinstance(task_id, str)

    def test_task_id_starts_with_wlab_prefix(self) -> None:
        """確認任務 ID 以 WLAB 前綴開頭。"""
        task_id = assign_task("project-director", "執行資料清洗")
        assert task_id.startswith(TASK_ID_PREFIX)

    def test_assign_task_sets_agent_to_working(self) -> None:
        """確認指派任務後代理狀態變為 WORKING。"""
        assign_task("scada-processor", "處理 SCADA 資料")
        agent = get_agent_or_raise("scada-processor")
        assert agent.status == AgentStatus.WORKING

    def test_assign_task_sets_current_task(self) -> None:
        """確認指派任務後代理的 current_task 更新為任務描述。"""
        task_desc = "訓練功率預測模型"
        assign_task("model-trainer", task_desc)
        agent = get_agent_or_raise("model-trainer")
        assert agent.current_task == task_desc

    def test_assign_task_to_nonexistent_agent_raises(self) -> None:
        """確認對不存在的代理指派任務時拋出 AgentNotFoundError。"""
        with pytest.raises(AgentNotFoundError):
            assign_task("ghost-agent", "任何任務")

    def test_assign_task_to_busy_agent_raises(self) -> None:
        """確認對已在執行任務的代理再次指派時拋出 AgentBusyError。"""
        assign_task("paper-writer", "撰寫第一章")
        with pytest.raises(AgentBusyError):
            assign_task("paper-writer", "撰寫第二章")


# ── list_agents_by_status 測試 ───────────────────────────────────────────────


class TestListAgentsByStatus:
    """list_agents_by_status 的測試。"""

    def test_all_agents_idle_at_start(self) -> None:
        """確認初始狀態下，所有 42 個代理均為 IDLE。"""
        idle_agents = list_agents_by_status(AgentStatus.IDLE)
        assert len(idle_agents) == 42

    def test_no_working_agents_at_start(self) -> None:
        """確認初始狀態下，無代理處於 WORKING 狀態。"""
        working_agents = list_agents_by_status(AgentStatus.WORKING)
        assert len(working_agents) == 0

    def test_working_agent_appears_in_working_list(self) -> None:
        """確認指派任務後，代理出現在 WORKING 狀態列表中。"""
        assign_task("iec-specialist", "查詢 IEC 61400 標準")
        working_agents = list_agents_by_status(AgentStatus.WORKING)
        assert len(working_agents) == 1
        assert working_agents[0].id == "iec-specialist"

    def test_working_agent_disappears_from_idle_list(self) -> None:
        """確認指派任務後，代理從 IDLE 列表中移除。"""
        assign_task("iec-specialist", "查詢標準")
        idle_agents = list_agents_by_status(AgentStatus.IDLE)
        assert len(idle_agents) == 41


# ── reset_all 測試 ────────────────────────────────────────────────────────────


class TestResetAll:
    """agent_service.reset_all 的測試。"""

    def test_returns_total_agent_count(self) -> None:
        """確認 reset_all 回傳重設的代理數量（42）。"""
        count = reset_all()
        assert count == 42

    def test_resets_working_agents_to_idle(self) -> None:
        """確認重設後，先前 WORKING 的代理恢復為 IDLE。"""
        assign_task("project-director", "測試任務")
        reset_all()
        idle_agents = list_agents_by_status(AgentStatus.IDLE)
        assert len(idle_agents) == 42

    def test_returns_same_count_regardless_of_state(self) -> None:
        """確認無論代理目前狀態，reset_all 始終回傳 42。"""
        # 將多個代理設為不同狀態
        for agent_id in ("model-trainer", "paper-writer", "backend-dev"):
            assign_task(agent_id, "任務")
        count = reset_all()
        assert count == 42


# ── run_full_diagnosis 測試 ───────────────────────────────────────────────────


class TestRunFullDiagnosis:
    """diagnosis_service.run_full_diagnosis 的測試。"""

    def test_returns_dict(self, sample_scada_df: pd.DataFrame) -> None:
        """確認回傳字典型別的診斷報告。"""
        report = run_full_diagnosis(sample_scada_df, "WT-001")
        assert isinstance(report, dict)

    def test_report_contains_turbine_id(self, sample_scada_df: pd.DataFrame) -> None:
        """確認報告中的 turbine_id 與輸入一致。"""
        report = run_full_diagnosis(sample_scada_df, "WT-TEST")
        assert report["turbine_id"] == "WT-TEST"

    def test_report_contains_health_score(self, sample_scada_df: pd.DataFrame) -> None:
        """確認報告包含 health_score 鍵值。"""
        report = run_full_diagnosis(sample_scada_df, "WT-001")
        assert "health_score" in report

    def test_health_score_in_valid_range(self, sample_scada_df: pd.DataFrame) -> None:
        """確認 health_score 在 0 到 100 之間。"""
        report = run_full_diagnosis(sample_scada_df, "WT-001")
        assert 0.0 <= report["health_score"] <= 100.0

    def test_report_contains_quality_report(self, sample_scada_df: pd.DataFrame) -> None:
        """確認報告包含 quality_report 子字典（來自資料清洗步驟）。"""
        report = run_full_diagnosis(sample_scada_df, "WT-001")
        assert "quality_report" in report
        assert isinstance(report["quality_report"], dict)

    def test_report_contains_warnings_list(self, sample_scada_df: pd.DataFrame) -> None:
        """確認報告包含 warnings 列表。"""
        report = run_full_diagnosis(sample_scada_df, "WT-001")
        assert "warnings" in report
        assert isinstance(report["warnings"], list)

    def test_report_contains_recommendations_list(self, sample_scada_df: pd.DataFrame) -> None:
        """確認報告包含 recommendations 列表。"""
        report = run_full_diagnosis(sample_scada_df, "WT-001")
        assert "recommendations" in report
        assert isinstance(report["recommendations"], list)

    def test_report_contains_power_curve_analysis(self, sample_scada_df: pd.DataFrame) -> None:
        """確認報告包含 power_curve_analysis 子字典。"""
        report = run_full_diagnosis(sample_scada_df, "WT-001")
        assert "power_curve_analysis" in report
        assert isinstance(report["power_curve_analysis"], dict)

    def test_report_contains_operational_summary(self, sample_scada_df: pd.DataFrame) -> None:
        """確認報告包含 operational_summary 子字典。"""
        report = run_full_diagnosis(sample_scada_df, "WT-001")
        assert "operational_summary" in report
        assert isinstance(report["operational_summary"], dict)

    def test_report_contains_analysis_period(self, sample_scada_df: pd.DataFrame) -> None:
        """確認報告包含 analysis_period 子字典，其中有 start 與 end。"""
        report = run_full_diagnosis(sample_scada_df, "WT-001")
        assert "analysis_period" in report
        assert "start" in report["analysis_period"]
        assert "end" in report["analysis_period"]

    def test_report_total_records_matches_input(self, sample_scada_df: pd.DataFrame) -> None:
        """確認報告中的 total_records 與輸入資料列數一致（清洗後）。"""
        report = run_full_diagnosis(sample_scada_df, "WT-001")
        # total_records 反映清洗後的列數（無刪除列，故應等於原始列數）
        assert report["total_records"] == len(sample_scada_df)

    def test_different_turbine_ids_produce_separate_reports(
        self, sample_scada_df: pd.DataFrame
    ) -> None:
        """確認不同風機 ID 的診斷報告彼此獨立。"""
        report_a = run_full_diagnosis(sample_scada_df, "WT-A")
        report_b = run_full_diagnosis(sample_scada_df, "WT-B")
        assert report_a["turbine_id"] == "WT-A"
        assert report_b["turbine_id"] == "WT-B"

    def test_custom_rated_power_is_accepted(self, sample_scada_df: pd.DataFrame) -> None:
        """確認自訂額定功率參數被接受且不拋出例外。"""
        report = run_full_diagnosis(sample_scada_df, "WT-CUSTOM", rated_power=1500.0)
        assert isinstance(report, dict)
        assert "health_score" in report

    def test_quality_report_has_required_keys(self, sample_scada_df: pd.DataFrame) -> None:
        """確認 quality_report 子字典包含所有必要鍵值。"""
        report = run_full_diagnosis(sample_scada_df, "WT-001")
        qr = report["quality_report"]
        for key in ("total_rows", "original_rows", "duplicates_removed", "missing_pct"):
            assert key in qr, f"quality_report 缺少鍵值：{key}"
