"""src.api.models 的單元測試。

測試所有 Pydantic 資料模型的建立、驗證行為與預設值，
包含 AgentModel、AgentStatus、AgentTier、WorkLogEntry、
InvokeRequest 與 InvokeResponse。
"""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.api.models import (
    AgentModel,
    AgentStatus,
    AgentTier,
    InvokeRequest,
    InvokeResponse,
    WorkLogEntry,
)


class TestAgentStatus:
    """AgentStatus 列舉的測試。"""

    def test_agent_status_idle_value(self) -> None:
        """確認 IDLE 狀態的字串值為 'idle'。"""
        assert AgentStatus.IDLE == "idle"

    def test_agent_status_working_value(self) -> None:
        """確認 WORKING 狀態的字串值為 'working'。"""
        assert AgentStatus.WORKING == "working"

    def test_agent_status_waiting_value(self) -> None:
        """確認 WAITING 狀態的字串值為 'waiting'。"""
        assert AgentStatus.WAITING == "waiting"

    def test_agent_status_error_value(self) -> None:
        """確認 ERROR 狀態的字串值為 'error'。"""
        assert AgentStatus.ERROR == "error"

    def test_agent_status_offline_value(self) -> None:
        """確認 OFFLINE 狀態的字串值為 'offline'。"""
        assert AgentStatus.OFFLINE == "offline"

    def test_agent_status_completed_value(self) -> None:
        """確認 COMPLETED 狀態的字串值為 'completed'。"""
        assert AgentStatus.COMPLETED == "completed"

    def test_agent_status_all_members(self) -> None:
        """確認列舉包含全部六個成員。"""
        members = set(AgentStatus)
        assert len(members) == 6

    def test_agent_status_is_str_subclass(self) -> None:
        """確認 AgentStatus 可作為字串使用。"""
        assert isinstance(AgentStatus.IDLE, str)

    def test_agent_status_members_contain_all_expected(self) -> None:
        """確認所有預期的狀態值均存在於列舉中。"""
        expected_values = {"idle", "working", "waiting", "error", "offline", "completed"}
        actual_values = {s.value for s in AgentStatus}
        assert actual_values == expected_values


class TestAgentTier:
    """AgentTier 列舉的測試。"""

    def test_agent_tier_leadership_value(self) -> None:
        """確認 LEADERSHIP 層級的字串值為 'leadership'。"""
        assert AgentTier.LEADERSHIP == "leadership"

    def test_agent_tier_data_value(self) -> None:
        """確認 DATA 層級的字串值為 'data'。"""
        assert AgentTier.DATA == "data"

    def test_agent_tier_ai_ml_value(self) -> None:
        """確認 AI_ML 層級的字串值為 'ai-ml'。"""
        assert AgentTier.AI_ML == "ai-ml"

    def test_agent_tier_domain_value(self) -> None:
        """確認 DOMAIN 層級的字串值為 'domain'。"""
        assert AgentTier.DOMAIN == "domain"

    def test_agent_tier_engineering_value(self) -> None:
        """確認 ENGINEERING 層級的字串值為 'engineering'。"""
        assert AgentTier.ENGINEERING == "engineering"

    def test_agent_tier_research_value(self) -> None:
        """確認 RESEARCH 層級的字串值為 'research'。"""
        assert AgentTier.RESEARCH == "research"

    def test_agent_tier_all_members(self) -> None:
        """確認列舉包含全部六個成員。"""
        assert len(set(AgentTier)) == 6

    def test_agent_tier_is_str_subclass(self) -> None:
        """確認 AgentTier 可作為字串使用。"""
        assert isinstance(AgentTier.LEADERSHIP, str)

    def test_agent_tier_members_contain_all_expected(self) -> None:
        """確認所有預期的層級值均存在於列舉中。"""
        expected_values = {"leadership", "data", "ai-ml", "domain", "engineering", "research"}
        actual_values = {t.value for t in AgentTier}
        assert actual_values == expected_values


class TestAgentModel:
    """AgentModel Pydantic 模型的測試。"""

    def _make_agent(self, **overrides: object) -> AgentModel:
        """建立最小有效的 AgentModel 實例。

        Args:
            **overrides: 要覆蓋預設欄位值的關鍵字引數。

        Returns:
            AgentModel 實例。
        """
        defaults: dict[str, object] = {
            "id": "test-agent",
            "name": "wLab:test-agent",
            "display_name": "測試代理",
            "tier": AgentTier.LEADERSHIP,
            "color": "#ffffff",
            "icon": "T",
        }
        defaults.update(overrides)
        return AgentModel(**defaults)  # type: ignore[arg-type]

    def test_agent_model_required_fields(self) -> None:
        """確認必要欄位設定後可建立模型，且欄位值正確。"""
        agent = self._make_agent()
        assert agent.id == "test-agent"
        assert agent.name == "wLab:test-agent"
        assert agent.display_name == "測試代理"
        assert agent.tier == AgentTier.LEADERSHIP
        assert agent.color == "#ffffff"
        assert agent.icon == "T"

    def test_agent_model_default_status_is_idle(self) -> None:
        """確認 status 預設值為 IDLE。"""
        agent = self._make_agent()
        assert agent.status == AgentStatus.IDLE

    def test_agent_model_default_current_task_is_none(self) -> None:
        """確認 current_task 預設值為 None。"""
        agent = self._make_agent()
        assert agent.current_task is None

    def test_agent_model_default_progress_is_zero(self) -> None:
        """確認 progress 預設值為 0.0。"""
        agent = self._make_agent()
        assert agent.progress == 0.0

    def test_agent_model_default_collaborating_with_is_empty_list(self) -> None:
        """確認 collaborating_with 預設值為空列表。"""
        agent = self._make_agent()
        assert agent.collaborating_with == []

    def test_agent_model_accepts_working_status(self) -> None:
        """確認可設定 WORKING 狀態。"""
        agent = self._make_agent(status=AgentStatus.WORKING)
        assert agent.status == AgentStatus.WORKING

    def test_agent_model_accepts_all_tiers(self) -> None:
        """確認所有 AgentTier 值均可設定於 tier 欄位。"""
        for tier in AgentTier:
            agent = self._make_agent(tier=tier)
            assert agent.tier == tier

    def test_agent_model_accepts_collaborating_with_list(self) -> None:
        """確認可設定協作代理列表。"""
        agent = self._make_agent(collaborating_with=["agent-a", "agent-b"])
        assert agent.collaborating_with == ["agent-a", "agent-b"]

    def test_agent_model_missing_required_field_raises(self) -> None:
        """確認缺少必要欄位時拋出驗證例外。"""
        with pytest.raises(ValidationError):
            AgentModel(  # type: ignore[call-arg]
                name="wLab:test-agent",
                display_name="測試代理",
                tier=AgentTier.LEADERSHIP,
                color="#ffffff",
                icon="T",
                # 缺少 id
            )

    def test_agent_model_missing_color_raises(self) -> None:
        """確認缺少 color 欄位時拋出驗證例外。"""
        with pytest.raises(ValidationError):
            AgentModel(  # type: ignore[call-arg]
                id="test-agent",
                name="wLab:test-agent",
                display_name="測試代理",
                tier=AgentTier.LEADERSHIP,
                icon="T",
                # 缺少 color
            )

    def test_agent_model_default_list_instances_are_independent(self) -> None:
        """確認兩個不同實例的 collaborating_with 不共用同一個列表物件。"""
        agent_a = self._make_agent(id="agent-a")
        agent_b = self._make_agent(id="agent-b")
        agent_a.collaborating_with.append("agent-c")
        assert "agent-c" not in agent_b.collaborating_with

    def test_agent_model_progress_can_be_set_to_one(self) -> None:
        """確認 progress 可設定為 1.0（任務完成）。"""
        agent = self._make_agent(progress=1.0)
        assert agent.progress == 1.0

    def test_agent_model_current_task_can_be_set(self) -> None:
        """確認 current_task 可設定為字串值。"""
        agent = self._make_agent(current_task="執行風機診斷")
        assert agent.current_task == "執行風機診斷"


class TestWorkLogEntry:
    """WorkLogEntry Pydantic 模型的測試。"""

    def test_work_log_entry_creation_with_required_fields(self) -> None:
        """確認必要欄位設定後可建立工作日誌，欄位值正確。"""
        entry = WorkLogEntry(
            id="log-001",
            agent_id="project-director",
            agent_name="wLab:project-director",
            message="任務開始執行",
        )
        assert entry.id == "log-001"
        assert entry.agent_id == "project-director"
        assert entry.agent_name == "wLab:project-director"
        assert entry.message == "任務開始執行"

    def test_work_log_entry_default_type_is_info(self) -> None:
        """確認 type 預設值為 'info'。"""
        entry = WorkLogEntry(
            id="log-002",
            agent_id="agent-x",
            agent_name="wLab:agent-x",
            message="測試訊息",
        )
        assert entry.type == "info"

    def test_work_log_entry_timestamp_is_auto_generated(self) -> None:
        """確認未提供 timestamp 時自動產生，且為 datetime 型別。"""
        before = datetime.now()
        entry = WorkLogEntry(
            id="log-003",
            agent_id="agent-x",
            agent_name="wLab:agent-x",
            message="時間戳記測試",
        )
        after = datetime.now()
        assert isinstance(entry.timestamp, datetime)
        assert before <= entry.timestamp <= after

    def test_work_log_entry_accepts_custom_type(self) -> None:
        """確認可設定自訂日誌類型。"""
        entry = WorkLogEntry(
            id="log-004",
            agent_id="agent-x",
            agent_name="wLab:agent-x",
            message="錯誤訊息",
            type="error",
        )
        assert entry.type == "error"

    def test_work_log_entry_accepts_explicit_timestamp(self) -> None:
        """確認可設定明確的時間戳記。"""
        explicit_ts = datetime(2024, 1, 15, 10, 30, 0)
        entry = WorkLogEntry(
            id="log-005",
            agent_id="agent-x",
            agent_name="wLab:agent-x",
            message="指定時間",
            timestamp=explicit_ts,
        )
        assert entry.timestamp == explicit_ts

    def test_work_log_entry_accepts_warning_type(self) -> None:
        """確認 type 欄位可設定為 'warning'。"""
        entry = WorkLogEntry(
            id="log-006",
            agent_id="agent-x",
            agent_name="wLab:agent-x",
            message="警告訊息",
            type="warning",
        )
        assert entry.type == "warning"

    def test_work_log_entry_accepts_success_type(self) -> None:
        """確認 type 欄位可設定為 'success'。"""
        entry = WorkLogEntry(
            id="log-007",
            agent_id="agent-x",
            agent_name="wLab:agent-x",
            message="成功訊息",
            type="success",
        )
        assert entry.type == "success"

    def test_work_log_entry_missing_id_raises(self) -> None:
        """確認缺少 id 欄位時拋出驗證例外。"""
        with pytest.raises(ValidationError):
            WorkLogEntry(  # type: ignore[call-arg]
                agent_id="agent-x",
                agent_name="wLab:agent-x",
                message="訊息",
            )


class TestInvokeRequest:
    """InvokeRequest Pydantic 模型的測試。"""

    def test_invoke_request_with_command_only(self) -> None:
        """確認只提供 command 時可建立請求物件，且 parameters 預設為空字典。"""
        req = InvokeRequest(command="run_diagnosis")
        assert req.command == "run_diagnosis"
        assert req.parameters == {}

    def test_invoke_request_with_parameters(self) -> None:
        """確認可附帶參數建立請求物件，且參數值正確。"""
        req = InvokeRequest(
            command="ai:train",
            parameters={"epochs": 100, "learning_rate": 0.001},
        )
        assert req.command == "ai:train"
        assert req.parameters["epochs"] == 100
        assert req.parameters["learning_rate"] == 0.001

    def test_invoke_request_missing_command_raises(self) -> None:
        """確認缺少 command 時拋出驗證例外。"""
        with pytest.raises(ValidationError):
            InvokeRequest()  # type: ignore[call-arg]

    def test_invoke_request_parameters_default_is_empty_dict(self) -> None:
        """確認兩個不同實例的 parameters 不共用同一個字典物件。"""
        req_a = InvokeRequest(command="cmd-a")
        req_b = InvokeRequest(command="cmd-b")
        req_a.parameters["key"] = "value"
        assert "key" not in req_b.parameters

    def test_invoke_request_command_with_slash_notation(self) -> None:
        """確認 command 欄位可接受含斜線的指令格式（如 /data:load）。"""
        req = InvokeRequest(command="/data:load")
        assert req.command == "/data:load"

    def test_invoke_request_parameters_accept_nested_dict(self) -> None:
        """確認 parameters 可接受巢狀字典結構。"""
        req = InvokeRequest(
            command="ai:evaluate",
            parameters={"model": {"name": "xgboost", "version": "1.0"}, "threshold": 0.5},
        )
        assert req.parameters["model"]["name"] == "xgboost"
        assert req.parameters["threshold"] == 0.5


class TestInvokeResponse:
    """InvokeResponse Pydantic 模型的測試。"""

    def test_invoke_response_creation(self) -> None:
        """確認必要欄位設定後可建立回應物件，欄位值正確。"""
        resp = InvokeResponse(
            task_id="WLAB-20240115-001",
            status="accepted",
            message="任務已接受，正在排程中",
        )
        assert resp.task_id == "WLAB-20240115-001"
        assert resp.status == "accepted"
        assert resp.message == "任務已接受，正在排程中"

    def test_invoke_response_missing_fields_raises(self) -> None:
        """確認缺少必要欄位時拋出驗證例外。"""
        with pytest.raises(ValidationError):
            InvokeResponse(task_id="WLAB-001")  # type: ignore[call-arg]

    def test_invoke_response_status_is_plain_string(self) -> None:
        """確認 status 欄位接受任意字串值，不受 enum 限制。"""
        for status_str in ("accepted", "running", "completed", "failed"):
            resp = InvokeResponse(
                task_id="WLAB-001",
                status=status_str,
                message="測試",
            )
            assert resp.status == status_str

    def test_invoke_response_missing_status_raises(self) -> None:
        """確認缺少 status 欄位時拋出驗證例外。"""
        with pytest.raises(ValidationError):
            InvokeResponse(  # type: ignore[call-arg]
                task_id="WLAB-001",
                message="訊息",
            )

    def test_invoke_response_task_id_format(self) -> None:
        """確認 task_id 欄位接受標準 WLAB 格式的任務識別碼。"""
        resp = InvokeResponse(
            task_id="WLAB-20260324-scada-processor",
            status="queued",
            message="已排入佇列",
        )
        assert resp.task_id.startswith("WLAB-")
