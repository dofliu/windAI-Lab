"""WindAI Lab 代理註冊表。

管理所有 Phase 1 代理的元資料與即時狀態，提供查詢與更新介面。
目前採用記憶體內狀態管理，後續可替換為持久化儲存。
"""

from __future__ import annotations

from copy import deepcopy

from src.api.models import AgentModel, AgentStatus, AgentTier

# Phase 1 八大代理定義
_AGENT_DEFINITIONS: list[dict] = [
    {
        "id": "project-director",
        "name": "wLab:project-director",
        "display_name": "專案總監",
        "tier": AgentTier.LEADERSHIP,
        "color": "#f59e0b",
        "icon": "👔",
    },
    {
        "id": "research-lead",
        "name": "wLab:research-lead",
        "display_name": "研究主管",
        "tier": AgentTier.LEADERSHIP,
        "color": "#f59e0b",
        "icon": "🎯",
    },
    {
        "id": "predictive-modeler",
        "name": "wAI:predictive-modeler",
        "display_name": "預測模型師",
        "tier": AgentTier.AI_ML,
        "color": "#8b5cf6",
        "icon": "🤖",
    },
    {
        "id": "rag-architect",
        "name": "wAI:rag-architect",
        "display_name": "RAG 架構師",
        "tier": AgentTier.AI_ML,
        "color": "#8b5cf6",
        "icon": "🔍",
    },
    {
        "id": "fault-diagnostician",
        "name": "wAI:fault-diagnostician",
        "display_name": "故障診斷師",
        "tier": AgentTier.AI_ML,
        "color": "#8b5cf6",
        "icon": "🔧",
    },
    {
        "id": "paper-writer",
        "name": "wRes:paper-writer",
        "display_name": "論文撰寫員",
        "tier": AgentTier.RESEARCH,
        "color": "#06b6d4",
        "icon": "📝",
    },
    {
        "id": "literature-reviewer",
        "name": "wRes:literature-reviewer",
        "display_name": "文獻審閱員",
        "tier": AgentTier.RESEARCH,
        "color": "#06b6d4",
        "icon": "📚",
    },
    {
        "id": "teaching-assistant",
        "name": "wRes:teaching-assistant",
        "display_name": "教學助理",
        "tier": AgentTier.RESEARCH,
        "color": "#06b6d4",
        "icon": "🎓",
    },
]


def _build_initial_state() -> dict[str, AgentModel]:
    """建立初始代理狀態表。"""
    agents: dict[str, AgentModel] = {}
    for defn in _AGENT_DEFINITIONS:
        agents[defn["id"]] = AgentModel(
            id=defn["id"],
            name=defn["name"],
            display_name=defn["display_name"],
            tier=defn["tier"],
            status=AgentStatus.IDLE,
            current_task=None,
            progress=0.0,
            collaborating_with=[],
            color=defn["color"],
            icon=defn["icon"],
        )
    return agents


# 記憶體內狀態儲存
_agent_state: dict[str, AgentModel] = _build_initial_state()


def get_all_agents() -> list[AgentModel]:
    """取得所有代理的當前狀態。"""
    return list(_agent_state.values())


def get_agent(agent_id: str) -> AgentModel | None:
    """依 ID 取得單一代理的狀態。若代理不存在則回傳 None。"""
    agent = _agent_state.get(agent_id)
    return deepcopy(agent) if agent else None


def update_agent_status(
    agent_id: str,
    *,
    status: AgentStatus | None = None,
    current_task: str | None = None,
    progress: float | None = None,
    collaborating_with: list[str] | None = None,
) -> AgentModel | None:
    """更新指定代理的狀態欄位，回傳更新後的代理模型。

    僅更新有提供值的欄位，未提供的欄位維持原值。
    """
    agent = _agent_state.get(agent_id)
    if agent is None:
        return None

    if status is not None:
        agent.status = status
    if current_task is not None:
        agent.current_task = current_task
    if progress is not None:
        agent.progress = progress
    if collaborating_with is not None:
        agent.collaborating_with = collaborating_with

    return deepcopy(agent)


def reset_all_agents() -> None:
    """重設所有代理至初始狀態。"""
    global _agent_state
    _agent_state = _build_initial_state()
