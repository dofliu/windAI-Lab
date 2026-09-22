"""src.api.agent_registry 的單元測試。

測試代理註冊表的查詢、狀態更新與重設功能，
確保記憶體內狀態管理符合預期行為。
"""

from __future__ import annotations

import pytest

from src.api.agent_registry import (
    get_agent,
    get_all_agents,
    reset_all_agents,
    update_agent_status,
)
from src.api.models import AgentModel, AgentStatus, AgentTier


@pytest.fixture(autouse=True)
def reset_registry() -> None:
    """每個測試前後重設代理註冊表至初始狀態。

    使用 autouse=True 確保測試間彼此隔離，避免狀態污染。
    """
    reset_all_agents()
    yield  # type: ignore[misc]
    reset_all_agents()


class TestGetAllAgents:
    """get_all_agents 函式的測試。"""

    def test_get_all_agents_returns_42_agents(self) -> None:
        """確認回傳正好 42 個代理（6 個層級合計）。"""
        agents = get_all_agents()
        assert len(agents) == 42

    def test_get_all_agents_returns_list_of_agent_model(self) -> None:
        """確認回傳值為 AgentModel 列表。"""
        agents = get_all_agents()
        assert all(isinstance(a, AgentModel) for a in agents)

    def test_get_all_agents_all_start_idle(self) -> None:
        """確認初始狀態所有代理均為 IDLE。"""
        agents = get_all_agents()
        assert all(a.status == AgentStatus.IDLE for a in agents)

    def test_get_all_agents_contains_expected_leadership_ids(self) -> None:
        """確認回傳列表包含所有 Tier 1 Leadership 代理的 ID。"""
        agents = get_all_agents()
        agent_ids = {a.id for a in agents}
        leadership_ids = {"project-director", "project-manager", "tech-lead", "research-lead"}
        assert leadership_ids.issubset(agent_ids)

    def test_get_all_agents_contains_expected_data_ids(self) -> None:
        """確認回傳列表包含所有 Tier 2 Data Engineering 代理的 ID。"""
        agents = get_all_agents()
        agent_ids = {a.id for a in agents}
        data_ids = {
            "scada-processor",
            "quality-checker",
            "etl-engineer",
            "data-validator",
            "stream-processor",
            "storage-manager",
            "metadata-curator",
            "pipeline-monitor",
        }
        assert data_ids.issubset(agent_ids)

    def test_get_all_agents_contains_expected_ai_ml_ids(self) -> None:
        """確認回傳列表包含所有 Tier 3 AI/ML 代理的 ID。"""
        agents = get_all_agents()
        agent_ids = {a.id for a in agents}
        ai_ml_ids = {
            "model-trainer",
            "experiment-tracker",
            "hyperparameter-tuner",
            "predictive-modeler",
            "fault-diagnostician",
            "rag-architect",
            "feature-engineer",
            "model-evaluator",
            "inference-deployer",
            "anomaly-detector",
        }
        assert ai_ml_ids.issubset(agent_ids)

    def test_get_all_agents_contains_leadership_tier(self) -> None:
        """確認至少存在四個 LEADERSHIP 層級的代理。"""
        agents = get_all_agents()
        leadership = [a for a in agents if a.tier == AgentTier.LEADERSHIP]
        assert len(leadership) == 4

    def test_get_all_agents_contains_data_tier(self) -> None:
        """確認存在八個 DATA 層級的代理。"""
        agents = get_all_agents()
        data_agents = [a for a in agents if a.tier == AgentTier.DATA]
        assert len(data_agents) == 8

    def test_get_all_agents_contains_ai_ml_tier(self) -> None:
        """確認存在十個 AI_ML 層級的代理。"""
        agents = get_all_agents()
        ai_agents = [a for a in agents if a.tier == AgentTier.AI_ML]
        assert len(ai_agents) == 10

    def test_get_all_agents_contains_research_tier(self) -> None:
        """確認存在六個 RESEARCH 層級的代理。"""
        agents = get_all_agents()
        research = [a for a in agents if a.tier == AgentTier.RESEARCH]
        assert len(research) == 6

    def test_get_all_agents_all_have_color(self) -> None:
        """確認所有代理均有非空的 color 欄位。"""
        agents = get_all_agents()
        assert all(a.color for a in agents)

    def test_get_all_agents_all_have_display_name(self) -> None:
        """確認所有代理均有非空的 display_name 欄位。"""
        agents = get_all_agents()
        assert all(a.display_name for a in agents)


class TestGetAgent:
    """get_agent 函式的測試。"""

    def test_get_agent_valid_id_returns_agent_model(self) -> None:
        """確認以有效 ID 查詢時回傳 AgentModel 實例。"""
        agent = get_agent("project-director")
        assert agent is not None
        assert isinstance(agent, AgentModel)

    def test_get_agent_valid_id_returns_correct_agent(self) -> None:
        """確認回傳的代理 ID 與查詢 ID 一致。"""
        agent = get_agent("fault-diagnostician")
        assert agent is not None
        assert agent.id == "fault-diagnostician"

    def test_get_agent_invalid_id_returns_none(self) -> None:
        """確認以不存在的 ID 查詢時回傳 None。"""
        agent = get_agent("non-existent-agent")
        assert agent is None

    def test_get_agent_returns_deep_copy(self) -> None:
        """確認回傳的是深拷貝，修改不影響原始狀態。"""
        agent = get_agent("project-director")
        assert agent is not None
        agent.status = AgentStatus.ERROR

        # 再次取得，狀態應仍為 IDLE
        agent_again = get_agent("project-director")
        assert agent_again is not None
        assert agent_again.status == AgentStatus.IDLE

    def test_get_agent_empty_string_returns_none(self) -> None:
        """確認空字串 ID 回傳 None。"""
        agent = get_agent("")
        assert agent is None

    def test_get_agent_returns_correct_tier_for_leadership(self) -> None:
        """確認 project-director 代理的層級為 LEADERSHIP。"""
        agent = get_agent("project-director")
        assert agent is not None
        assert agent.tier == AgentTier.LEADERSHIP

    def test_get_agent_returns_correct_tier_for_data(self) -> None:
        """確認 scada-processor 代理的層級為 DATA。"""
        agent = get_agent("scada-processor")
        assert agent is not None
        assert agent.tier == AgentTier.DATA

    def test_get_agent_returns_correct_tier_for_ai_ml(self) -> None:
        """確認 model-trainer 代理的層級為 AI_ML。"""
        agent = get_agent("model-trainer")
        assert agent is not None
        assert agent.tier == AgentTier.AI_ML

    @pytest.mark.parametrize(
        "agent_id",
        [
            "project-director",
            "project-manager",
            "tech-lead",
            "research-lead",
            "scada-processor",
            "fault-diagnostician",
            "paper-writer",
            "rag-curator",
            "backend-dev",
            "iec-specialist",
        ],
    )
    def test_get_agent_all_valid_ids(self, agent_id: str) -> None:
        """確認多個已知的有效代理 ID 均可成功查詢。

        Args:
            agent_id: 代理唯一識別碼。
        """
        agent = get_agent(agent_id)
        assert agent is not None
        assert agent.id == agent_id


class TestUpdateAgentStatus:
    """update_agent_status 函式的測試。"""

    def test_update_status_changes_status_field(self) -> None:
        """確認更新 status 欄位後，查詢結果反映新狀態。"""
        result = update_agent_status("project-director", status=AgentStatus.WORKING)
        assert result is not None
        assert result.status == AgentStatus.WORKING

    def test_update_current_task_changes_task_field(self) -> None:
        """確認更新 current_task 欄位後，查詢結果反映新任務描述。"""
        result = update_agent_status(
            "project-director",
            current_task="執行 SCADA 資料清洗",
        )
        assert result is not None
        assert result.current_task == "執行 SCADA 資料清洗"

    def test_update_progress_changes_progress_field(self) -> None:
        """確認更新 progress 欄位後，查詢結果反映新進度。"""
        result = update_agent_status("project-director", progress=0.75)
        assert result is not None
        assert result.progress == 0.75

    def test_update_collaborating_with_changes_field(self) -> None:
        """確認更新 collaborating_with 欄位後，查詢結果反映新協作列表。"""
        result = update_agent_status(
            "project-director",
            collaborating_with=["fault-diagnostician", "paper-writer"],
        )
        assert result is not None
        assert result.collaborating_with == ["fault-diagnostician", "paper-writer"]

    def test_update_multiple_fields_simultaneously(self) -> None:
        """確認可同時更新多個欄位，且所有欄位均正確反映。"""
        result = update_agent_status(
            "research-lead",
            status=AgentStatus.WAITING,
            current_task="等待資料就緒",
            progress=0.3,
        )
        assert result is not None
        assert result.status == AgentStatus.WAITING
        assert result.current_task == "等待資料就緒"
        assert result.progress == 0.3

    def test_update_non_provided_fields_remain_unchanged(self) -> None:
        """確認未提供的欄位維持原值。"""
        # 先設定 current_task
        update_agent_status("project-director", current_task="初始任務")
        # 再只更新 status，current_task 應保持不變
        result = update_agent_status("project-director", status=AgentStatus.WORKING)
        assert result is not None
        assert result.current_task == "初始任務"

    def test_update_invalid_agent_id_returns_none(self) -> None:
        """確認以不存在的 ID 更新時回傳 None。"""
        result = update_agent_status("non-existent", status=AgentStatus.WORKING)
        assert result is None

    def test_update_returns_deep_copy(self) -> None:
        """確認回傳的是深拷貝，後續修改不影響已存狀態。"""
        result = update_agent_status("project-director", status=AgentStatus.WORKING)
        assert result is not None
        result.status = AgentStatus.ERROR

        # 查詢應仍為 WORKING，而非 ERROR
        agent = get_agent("project-director")
        assert agent is not None
        assert agent.status == AgentStatus.WORKING

    def test_update_persists_to_get_agent(self) -> None:
        """確認更新後透過 get_agent 重新取得的結果一致。"""
        update_agent_status("scada-processor", status=AgentStatus.WORKING, progress=0.5)
        agent = get_agent("scada-processor")
        assert agent is not None
        assert agent.status == AgentStatus.WORKING
        assert agent.progress == 0.5


class TestResetAllAgents:
    """reset_all_agents 函式的測試。"""

    def test_reset_restores_idle_status(self) -> None:
        """確認重設後所有代理恢復 IDLE 狀態。"""
        # 先修改多個代理的狀態
        update_agent_status("project-director", status=AgentStatus.ERROR)
        update_agent_status("paper-writer", status=AgentStatus.WORKING)
        update_agent_status("scada-processor", status=AgentStatus.WAITING)

        reset_all_agents()

        agents = get_all_agents()
        assert all(a.status == AgentStatus.IDLE for a in agents)

    def test_reset_clears_current_task(self) -> None:
        """確認重設後所有代理的 current_task 為 None。"""
        update_agent_status("project-director", current_task="進行中的任務")
        reset_all_agents()

        agent = get_agent("project-director")
        assert agent is not None
        assert agent.current_task is None

    def test_reset_restores_progress_to_zero(self) -> None:
        """確認重設後所有代理的 progress 為 0.0。"""
        update_agent_status("fault-diagnostician", progress=0.9)
        reset_all_agents()

        agent = get_agent("fault-diagnostician")
        assert agent is not None
        assert agent.progress == 0.0

    def test_reset_restores_collaborating_with_to_empty(self) -> None:
        """確認重設後所有代理的 collaborating_with 為空列表。"""
        update_agent_status(
            "research-lead",
            collaborating_with=["paper-writer", "literature-reviewer"],
        )
        reset_all_agents()

        agent = get_agent("research-lead")
        assert agent is not None
        assert agent.collaborating_with == []

    def test_reset_restores_agent_count_to_42(self) -> None:
        """確認重設後代理總數仍為 42。"""
        reset_all_agents()
        agents = get_all_agents()
        assert len(agents) == 42

    def test_reset_all_progress_is_zero(self) -> None:
        """確認重設後所有代理的 progress 均為 0.0。"""
        # 修改多個代理的進度
        for agent_id in ("model-trainer", "paper-writer", "iec-specialist"):
            update_agent_status(agent_id, progress=0.8)

        reset_all_agents()

        agents = get_all_agents()
        assert all(a.progress == 0.0 for a in agents)

    def test_reset_all_current_tasks_are_none(self) -> None:
        """確認重設後所有代理的 current_task 均為 None。"""
        for agent_id in ("model-trainer", "backend-dev", "wake-analyst"):
            update_agent_status(agent_id, current_task="進行中任務")

        reset_all_agents()

        agents = get_all_agents()
        assert all(a.current_task is None for a in agents)
