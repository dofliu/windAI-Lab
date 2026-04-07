"""WindAI Lab 代理註冊表。

管理所有 Phase 1 代理的元資料與即時狀態，提供查詢與更新介面。
目前採用記憶體內狀態管理，後續可替換為持久化儲存。
"""

from __future__ import annotations

from copy import deepcopy

from src.api.models import AgentModel, AgentStatus, AgentTier

# 全 42 代理定義，依六層階層組織
_AGENT_DEFINITIONS: list[dict] = [
    # -------------------------------------------------------------------------
    # Tier 1 — Leadership (wLab:)  4 agents
    # -------------------------------------------------------------------------
    {
        "id": "project-director",
        "name": "wLab:project-director",
        "display_name": "專案總監",
        "tier": AgentTier.LEADERSHIP,
        "color": "#f59e0b",
        "icon": "👔",
    },
    {
        "id": "project-manager",
        "name": "wLab:project-manager",
        "display_name": "專案經理",
        "tier": AgentTier.LEADERSHIP,
        "color": "#f59e0b",
        "icon": "📋",
    },
    {
        "id": "tech-lead",
        "name": "wLab:tech-lead",
        "display_name": "技術主管",
        "tier": AgentTier.LEADERSHIP,
        "color": "#f59e0b",
        "icon": "⚙️",
    },
    {
        "id": "research-lead",
        "name": "wLab:research-lead",
        "display_name": "研究主管",
        "tier": AgentTier.LEADERSHIP,
        "color": "#f59e0b",
        "icon": "🎯",
    },
    # -------------------------------------------------------------------------
    # Tier 2 — Data Engineering (wData:)  8 agents
    # -------------------------------------------------------------------------
    {
        "id": "scada-processor",
        "name": "wData:scada-processor",
        "display_name": "SCADA 資料處理員",
        "tier": AgentTier.DATA,
        "color": "#10b981",
        "icon": "📡",
    },
    {
        "id": "quality-checker",
        "name": "wData:quality-checker",
        "display_name": "資料品質檢核員",
        "tier": AgentTier.DATA,
        "color": "#10b981",
        "icon": "✅",
    },
    {
        "id": "etl-engineer",
        "name": "wData:etl-engineer",
        "display_name": "ETL 工程師",
        "tier": AgentTier.DATA,
        "color": "#10b981",
        "icon": "🔄",
    },
    {
        "id": "data-validator",
        "name": "wData:data-validator",
        "display_name": "資料驗證員",
        "tier": AgentTier.DATA,
        "color": "#10b981",
        "icon": "🛡️",
    },
    {
        "id": "stream-processor",
        "name": "wData:stream-processor",
        "display_name": "串流資料處理員",
        "tier": AgentTier.DATA,
        "color": "#10b981",
        "icon": "🌊",
    },
    {
        "id": "storage-manager",
        "name": "wData:storage-manager",
        "display_name": "儲存管理員",
        "tier": AgentTier.DATA,
        "color": "#10b981",
        "icon": "🗄️",
    },
    {
        "id": "metadata-curator",
        "name": "wData:metadata-curator",
        "display_name": "元資料策展員",
        "tier": AgentTier.DATA,
        "color": "#10b981",
        "icon": "🏷️",
    },
    {
        "id": "pipeline-monitor",
        "name": "wData:pipeline-monitor",
        "display_name": "資料管線監控員",
        "tier": AgentTier.DATA,
        "color": "#10b981",
        "icon": "📊",
    },
    # -------------------------------------------------------------------------
    # Tier 3 — AI/ML (wAI:)  10 agents
    # -------------------------------------------------------------------------
    {
        "id": "model-trainer",
        "name": "wAI:model-trainer",
        "display_name": "模型訓練師",
        "tier": AgentTier.AI_ML,
        "color": "#8b5cf6",
        "icon": "🏋️",
    },
    {
        "id": "experiment-tracker",
        "name": "wAI:experiment-tracker",
        "display_name": "實驗追蹤員",
        "tier": AgentTier.AI_ML,
        "color": "#8b5cf6",
        "icon": "🧪",
    },
    {
        "id": "hyperparameter-tuner",
        "name": "wAI:hyperparameter-tuner",
        "display_name": "超參數調整師",
        "tier": AgentTier.AI_ML,
        "color": "#8b5cf6",
        "icon": "🎛️",
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
        "id": "fault-diagnostician",
        "name": "wAI:fault-diagnostician",
        "display_name": "故障診斷師",
        "tier": AgentTier.AI_ML,
        "color": "#8b5cf6",
        "icon": "🔧",
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
        "id": "feature-engineer",
        "name": "wAI:feature-engineer",
        "display_name": "特徵工程師",
        "tier": AgentTier.AI_ML,
        "color": "#8b5cf6",
        "icon": "⚗️",
    },
    {
        "id": "model-evaluator",
        "name": "wAI:model-evaluator",
        "display_name": "模型評估員",
        "tier": AgentTier.AI_ML,
        "color": "#8b5cf6",
        "icon": "📈",
    },
    {
        "id": "inference-deployer",
        "name": "wAI:inference-deployer",
        "display_name": "推論部署工程師",
        "tier": AgentTier.AI_ML,
        "color": "#8b5cf6",
        "icon": "🚀",
    },
    {
        "id": "anomaly-detector",
        "name": "wAI:anomaly-detector",
        "display_name": "異常偵測員",
        "tier": AgentTier.AI_ML,
        "color": "#8b5cf6",
        "icon": "🚨",
    },
    # -------------------------------------------------------------------------
    # Tier 4 — Domain Knowledge (wDomain:)  6 agents
    # -------------------------------------------------------------------------
    {
        "id": "iec-specialist",
        "name": "wDomain:iec-specialist",
        "display_name": "IEC 標準專家",
        "tier": AgentTier.DOMAIN,
        "color": "#ec4899",
        "icon": "📜",
    },
    {
        "id": "wake-analyst",
        "name": "wDomain:wake-analyst",
        "display_name": "尾流效應分析師",
        "tier": AgentTier.DOMAIN,
        "color": "#ec4899",
        "icon": "💨",
    },
    {
        "id": "power-curve-expert",
        "name": "wDomain:power-curve-expert",
        "display_name": "功率曲線專家",
        "tier": AgentTier.DOMAIN,
        "color": "#ec4899",
        "icon": "⚡",
    },
    {
        "id": "maintenance-planner",
        "name": "wDomain:maintenance-planner",
        "display_name": "維護計畫員",
        "tier": AgentTier.DOMAIN,
        "color": "#ec4899",
        "icon": "🛠️",
    },
    {
        "id": "wind-resource-analyst",
        "name": "wDomain:wind-resource-analyst",
        "display_name": "風能資源分析師",
        "tier": AgentTier.DOMAIN,
        "color": "#ec4899",
        "icon": "🌬️",
    },
    {
        "id": "regulatory-advisor",
        "name": "wDomain:regulatory-advisor",
        "display_name": "法規顧問",
        "tier": AgentTier.DOMAIN,
        "color": "#ec4899",
        "icon": "⚖️",
    },
    # -------------------------------------------------------------------------
    # Tier 5 — Software Engineering (wEng:)  8 agents
    # -------------------------------------------------------------------------
    {
        "id": "backend-dev",
        "name": "wEng:backend-dev",
        "display_name": "後端開發工程師",
        "tier": AgentTier.ENGINEERING,
        "color": "#f97316",
        "icon": "🖥️",
    },
    {
        "id": "frontend-dev",
        "name": "wEng:frontend-dev",
        "display_name": "前端開發工程師",
        "tier": AgentTier.ENGINEERING,
        "color": "#f97316",
        "icon": "🎨",
    },
    {
        "id": "devops-engineer",
        "name": "wEng:devops-engineer",
        "display_name": "DevOps 工程師",
        "tier": AgentTier.ENGINEERING,
        "color": "#f97316",
        "icon": "♾️",
    },
    {
        "id": "api-designer",
        "name": "wEng:api-designer",
        "display_name": "API 設計師",
        "tier": AgentTier.ENGINEERING,
        "color": "#f97316",
        "icon": "🔌",
    },
    {
        "id": "database-admin",
        "name": "wEng:database-admin",
        "display_name": "資料庫管理員",
        "tier": AgentTier.ENGINEERING,
        "color": "#f97316",
        "icon": "🗃️",
    },
    {
        "id": "test-engineer",
        "name": "wEng:test-engineer",
        "display_name": "測試工程師",
        "tier": AgentTier.ENGINEERING,
        "color": "#f97316",
        "icon": "🧩",
    },
    {
        "id": "security-analyst",
        "name": "wEng:security-analyst",
        "display_name": "資安分析師",
        "tier": AgentTier.ENGINEERING,
        "color": "#f97316",
        "icon": "🔒",
    },
    {
        "id": "infra-manager",
        "name": "wEng:infra-manager",
        "display_name": "基礎設施管理員",
        "tier": AgentTier.ENGINEERING,
        "color": "#f97316",
        "icon": "🏗️",
    },
    # -------------------------------------------------------------------------
    # Tier 6 — Research & Docs (wRes:)  6 agents
    # -------------------------------------------------------------------------
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
        "id": "rag-curator",
        "name": "wRes:rag-curator",
        "display_name": "RAG 知識庫策展員",
        "tier": AgentTier.RESEARCH,
        "color": "#06b6d4",
        "icon": "🗂️",
    },
    {
        "id": "report-generator",
        "name": "wRes:report-generator",
        "display_name": "報告生成員",
        "tier": AgentTier.RESEARCH,
        "color": "#06b6d4",
        "icon": "📄",
    },
    {
        "id": "teaching-assistant",
        "name": "wRes:teaching-assistant",
        "display_name": "教學助理",
        "tier": AgentTier.RESEARCH,
        "color": "#06b6d4",
        "icon": "🎓",
    },
    {
        "id": "data-storyteller",
        "name": "wRes:data-storyteller",
        "display_name": "資料敘事員",
        "tier": AgentTier.RESEARCH,
        "color": "#06b6d4",
        "icon": "📖",
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


# ── 雙軌模式：優先使用 DynamicAgentRegistry，fallback 到舊系統 ──

# 舊系統狀態（作為 fallback）
_agent_state: dict[str, AgentModel] = _build_initial_state()

# 新系統旗標
_use_dynamic: bool = False


def _get_dynamic():
    """延遲取得 dynamic_registry 以避免循環 import。"""
    from src.agents.dynamic_registry import dynamic_registry

    return dynamic_registry


def enable_dynamic_registry() -> None:
    """啟用新架構（由 lifespan 呼叫）。"""
    global _use_dynamic  # noqa: PLW0603
    _use_dynamic = True


def get_all_agents() -> list[AgentModel]:
    """取得所有代理的當前狀態。"""
    if _use_dynamic:
        return _get_dynamic().get_all_agents()
    return list(_agent_state.values())


def get_agent(agent_id: str) -> AgentModel | None:
    """依 ID 取得單一代理的狀態。若代理不存在則回傳 None。"""
    if _use_dynamic:
        agent = _get_dynamic().get_agent(agent_id)
        return deepcopy(agent) if agent else None
    agent = _agent_state.get(agent_id)
    return deepcopy(agent) if agent else None


_state_lock = __import__("threading").Lock()


def update_agent_status(
    agent_id: str,
    *,
    status: AgentStatus | None = None,
    current_task: str | None = None,
    progress: float | None = None,
    collaborating_with: list[str] | None = None,
) -> AgentModel | None:
    """更新指定代理的狀態欄位，回傳更新後的代理模型。

    使用鎖保護狀態字典，避免並行更新時的競態條件。
    """
    with _state_lock:
        if _use_dynamic:
            model = _get_dynamic().update_agent_status(
                agent_id,
                status=status,
                current_task=current_task,
                progress=progress,
                collaborating_with=collaborating_with,
            )
            return deepcopy(model) if model else None

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
    global _agent_state  # noqa: PLW0603
    _agent_state = _build_initial_state()
