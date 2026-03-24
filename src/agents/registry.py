"""WindAI Lab 代理實例註冊表。

負責建立、管理所有 BaseAgent 子類別的實例，
並自動註冊至 MessageBus。支援依 ID、namespace、tier 查詢。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.agents.message_bus import bus
from src.api.models import AgentTier
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.agents.base import BaseAgent

logger = get_logger("agent_registry.instances")

# namespace → AgentTier 映射
_NS_TO_TIER: dict[str, AgentTier] = {
    "wLab": AgentTier.LEADERSHIP,
    "wData": AgentTier.DATA,
    "wAI": AgentTier.AI_ML,
    "wDomain": AgentTier.DOMAIN,
    "wEng": AgentTier.ENGINEERING,
    "wRes": AgentTier.RESEARCH,
}


class AgentInstanceRegistry:
    """代理實例的集中管理器。

    與 ``src.api.agent_registry``（狀態管理）互補：
    - agent_registry：管理 42 個代理的 **狀態資料**（AgentModel）
    - 本模組：管理已實作代理的 **邏輯實例**（BaseAgent subclass）

    未實作邏輯的代理仍在 agent_registry 中存在（可顯示在 UI），
    但不會出現在本模組中。
    """

    def __init__(self) -> None:
        self._instances: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        """註冊代理實例並加入 MessageBus。

        Args:
            agent: BaseAgent 子類別實例。
        """
        self._instances[agent.id] = agent
        bus.register(agent)
        logger.info(f"代理實例已註冊：{agent.id} ({agent.__class__.__name__})")

    def get(self, agent_id: str) -> BaseAgent | None:
        """依 ID 取得代理實例。"""
        return self._instances.get(agent_id)

    def get_by_namespace(self, namespace: str) -> list[BaseAgent]:
        """取得指定 namespace 下所有已註冊的代理。

        Args:
            namespace: 如 "wAI"、"wData" 等。

        Returns:
            該 namespace 下的代理實例列表。
        """
        prefix = f"{namespace}:"
        return [
            a for a in self._instances.values()
            if a.namespace_name.startswith(prefix)
        ]

    def get_by_tier(self, tier: AgentTier) -> list[BaseAgent]:
        """取得指定層級下所有已註冊的代理。"""
        return [
            a for a in self._instances.values()
            if a.model and a.model.tier == tier
        ]

    def get_all(self) -> list[BaseAgent]:
        """取得所有已註冊的代理實例。"""
        return list(self._instances.values())

    @property
    def count(self) -> int:
        """已註冊代理數量。"""
        return len(self._instances)

    def has(self, agent_id: str) -> bool:
        """檢查代理是否已註冊。"""
        return agent_id in self._instances

    def __repr__(self) -> str:
        return f"<AgentInstanceRegistry count={self.count}>"


# 全域單例
agent_instances = AgentInstanceRegistry()


def bootstrap_agents() -> AgentInstanceRegistry:
    """初始化所有已實作的代理實例。

    從各 tier 模組匯入具體代理類別，建立實例並註冊。
    僅初始化有實作的代理，未實作的代理保持為 YAML 定義的空殼。

    Returns:
        已初始化的 AgentInstanceRegistry。
    """
    from src.agents.leadership.director import ProjectDirector
    from src.agents.leadership.project_manager import ProjectManager
    from src.agents.leadership.research_lead import ResearchLead
    from src.agents.leadership.tech_lead import TechLead

    from src.agents.data.scada_processor import ScadaProcessor
    from src.agents.data.quality_checker import QualityChecker

    from src.agents.ai.fault_diagnostician import FaultDiagnostician
    from src.agents.ai.predictive_modeler import PredictiveModeler
    from src.agents.ai.rag_architect import RagArchitect

    from src.agents.domain.power_curve_expert import PowerCurveExpert
    from src.agents.domain.maintenance_planner import MaintenancePlanner

    from src.agents.engineering.backend_dev import BackendDev
    from src.agents.engineering.devops_engineer import DevOpsEngineer
    from src.agents.engineering.test_engineer import TestEngineer

    from src.agents.research.paper_writer import PaperWriter
    from src.agents.research.literature_reviewer import LiteratureReviewer

    agents_to_register: list[BaseAgent] = [
        # Tier 1 — Leadership
        ProjectDirector(),
        ProjectManager(),
        TechLead(),
        ResearchLead(),
        # Tier 2 — Data Engineering
        ScadaProcessor(),
        QualityChecker(),
        # Tier 3 — AI/ML
        FaultDiagnostician(),
        PredictiveModeler(),
        RagArchitect(),
        # Tier 4 — Domain Knowledge
        PowerCurveExpert(),
        MaintenancePlanner(),
        # Tier 5 — Software Engineering
        BackendDev(),
        TestEngineer(),
        DevOpsEngineer(),
        # Tier 6 — Research & Docs
        PaperWriter(),
        LiteratureReviewer(),
    ]

    for agent in agents_to_register:
        agent_instances.register(agent)

    logger.info(f"代理框架初始化完成：{agent_instances.count} 個代理已註冊")
    return agent_instances
