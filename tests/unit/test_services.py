"""服務層測試。"""

from __future__ import annotations

import pandas as pd
import pytest

from src.api.models import AgentStatus, AgentTier
from src.core.exceptions import AgentNotFoundError
from src.services.agent_service import (
    get_agent_or_raise,
    list_agents_by_status,
    list_agents_by_tier,
    reset_all,
)
from src.services.diagnosis_service import run_full_diagnosis


class TestAgentService:
    """代理管理服務測試群組。"""

    def test_get_existing_agent(self) -> None:
        """應成功取得存在的代理。"""
        agent = get_agent_or_raise("project-director")
        assert agent.id == "project-director"

    def test_get_nonexistent_agent_raises(self) -> None:
        """不存在的代理應拋出 AgentNotFoundError。"""
        with pytest.raises(AgentNotFoundError):
            get_agent_or_raise("nonexistent-agent")

    def test_list_by_tier(self) -> None:
        """依層級篩選應回傳正確數量的代理。"""
        leadership = list_agents_by_tier(AgentTier.LEADERSHIP)
        assert len(leadership) == 4

    def test_list_by_status_idle(self) -> None:
        """初始狀態下所有代理都應為 idle。"""
        reset_all()
        idle_agents = list_agents_by_status(AgentStatus.IDLE)
        assert len(idle_agents) == 42

    def test_reset_all(self) -> None:
        """重設後應回傳代理數量。"""
        count = reset_all()
        assert count == 42


class TestDiagnosisService:
    """故障診斷服務測試群組。"""

    def test_run_full_diagnosis(self, sample_scada_df: pd.DataFrame) -> None:
        """應成功回傳診斷報告。"""
        report = run_full_diagnosis(sample_scada_df, "TEST-01")
        assert isinstance(report, dict)
        assert report["turbine_id"] == "TEST-01"
        assert "health_score" in report
        assert "quality_report" in report

    def test_diagnosis_report_has_warnings(self, sample_scada_df: pd.DataFrame) -> None:
        """診斷報告應包含警告列表。"""
        report = run_full_diagnosis(sample_scada_df, "TEST-02")
        assert "warnings" in report
        assert isinstance(report["warnings"], list)

    def test_diagnosis_report_has_recommendations(self, sample_scada_df: pd.DataFrame) -> None:
        """診斷報告應包含建議列表。"""
        report = run_full_diagnosis(sample_scada_df, "TEST-03")
        assert "recommendations" in report
        assert isinstance(report["recommendations"], list)
