"""WindAI Lab 資料模型定義。

定義所有 API 端點使用的 Pydantic 模型，包含代理狀態、工作日誌與請求回應格式。
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AgentStatus(StrEnum):
    """代理運行狀態列舉。"""

    IDLE = "idle"
    WORKING = "working"
    WAITING = "waiting"
    ERROR = "error"
    OFFLINE = "offline"
    COMPLETED = "completed"


class AgentTier(StrEnum):
    """代理層級列舉。"""

    LEADERSHIP = "leadership"
    DATA = "data"
    AI_ML = "ai-ml"
    DOMAIN = "domain"
    ENGINEERING = "engineering"
    RESEARCH = "research"


class AgentModel(BaseModel):
    """代理資料模型，描述單一代理的完整狀態與元資料。"""

    id: str = Field(..., description="代理唯一識別碼")
    name: str = Field(..., description="代理英文名稱")
    display_name: str = Field(..., description="代理中文顯示名稱")
    tier: AgentTier = Field(..., description="代理所屬層級")
    status: AgentStatus = Field(default=AgentStatus.IDLE, description="當前運行狀態")
    current_task: str | None = Field(default=None, description="當前執行任務描述")
    progress: float = Field(default=0.0, description="任務進度（0.0 至 1.0）")
    collaborating_with: list[str] = Field(
        default_factory=list, description="正在協作的代理 ID 列表"
    )
    color: str = Field(..., description="前端顯示色彩代碼")
    icon: str = Field(..., description="前端顯示圖示名稱")


class WorkLogEntry(BaseModel):
    """工作日誌項目，記錄代理的活動歷程。"""

    id: str = Field(..., description="日誌唯一識別碼")
    timestamp: datetime = Field(default_factory=datetime.now, description="日誌產生時間")
    agent_id: str = Field(..., description="產生此日誌的代理 ID")
    agent_name: str = Field(..., description="產生此日誌的代理名稱")
    message: str = Field(..., description="日誌訊息內容")
    type: str = Field(default="info", description="日誌類型（info / warning / error / success）")


class InvokeRequest(BaseModel):
    """代理調用請求。"""

    command: str = Field(..., description="要執行的指令名稱")
    parameters: dict[str, Any] = Field(default_factory=dict, description="指令參數")


class InvokeResponse(BaseModel):
    """代理調用回應。"""

    task_id: str = Field(..., description="任務追蹤識別碼")
    status: str = Field(..., description="任務狀態")
    message: str = Field(..., description="回應訊息")


# ── Phase 13：告警系統 + 工單管理 ────────────────────────────────


class AlertSeverity(StrEnum):
    """告警嚴重程度。"""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertStatus(StrEnum):
    """告警處理狀態。"""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class AlertSource(StrEnum):
    """告警來源類型。"""

    ANOMALY_DETECTION = "anomaly_detection"
    AGENT_ERROR = "agent_error"
    TASK_FAILURE = "task_failure"
    SCADA_THRESHOLD = "scada_threshold"
    EXTERNAL = "external"
    MANUAL = "manual"


class CreateAlertRequest(BaseModel):
    """手動建立告警的請求。"""

    turbine_id: str | None = Field(default=None, description="風機識別碼")
    severity: AlertSeverity = Field(..., description="嚴重程度")
    title: str = Field(..., description="告警標題")
    description: str = Field(default="", description="告警詳細描述")
    source: AlertSource = Field(default=AlertSource.MANUAL, description="告警來源")
    tags: list[str] = Field(default_factory=list, description="分類標籤")
    metrics: dict[str, Any] = Field(default_factory=dict, description="相關量測值")


class AlertIngestRequest(BaseModel):
    """外部系統推送告警的標準格式。

    提供給外部廠商（如 Vestas CMS、Siemens Gamesa）的統一接口。
    """

    source_system: str = Field(..., description="來源系統識別（如 vestas_cms、sg_scada）")
    source_alert_id: str | None = Field(default=None, description="原始系統告警 ID，用於去重")
    turbine_id: str = Field(..., description="風機識別碼")
    severity: AlertSeverity = Field(..., description="嚴重程度：critical / warning / info")
    title: str = Field(..., description="告警標題")
    description: str = Field(default="", description="告警詳細描述")
    occurred_at: str | None = Field(default=None, description="實際發生時間（ISO 8601 UTC）")
    metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="相關量測值，如 {temperature: 87.3, threshold: 80.0, unit: '°C'}",
    )
    tags: list[str] = Field(
        default_factory=list, description="分類標籤，如 ['gearbox', 'temperature']"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="其他自訂欄位")


class UpdateAlertRequest(BaseModel):
    """更新告警狀態的請求。"""

    status: AlertStatus = Field(..., description="新狀態")
    resolved_by: str | None = Field(default=None, description="處理者（agent_id 或 'user'）")


class WorkOrderPriority(StrEnum):
    """工單優先程度。"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class WorkOrderStatus(StrEnum):
    """工單處理狀態。"""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CreateWorkOrderRequest(BaseModel):
    """建立工單的請求。"""

    title: str = Field(..., description="工單標題")
    description: str = Field(default="", description="工單描述")
    priority: WorkOrderPriority = Field(default=WorkOrderPriority.MEDIUM, description="優先程度")
    turbine_id: str | None = Field(default=None, description="風機識別碼")
    alert_id: str | None = Field(default=None, description="關聯告警 ID")
    assigned_agents: list[str] = Field(default_factory=list, description="指派的代理 ID 列表")
    estimated_duration_hours: float | None = Field(default=None, description="預估工時（小時）")


class UpdateWorkOrderRequest(BaseModel):
    """更新工單的請求。"""

    status: WorkOrderStatus | None = Field(default=None, description="新狀態")
    priority: WorkOrderPriority | None = Field(default=None, description="新優先程度")
    assigned_agents: list[str] | None = Field(default=None, description="更新指派代理")
    title: str | None = Field(default=None, description="更新標題")
    description: str | None = Field(default=None, description="更新描述")


class AddWorkOrderNoteRequest(BaseModel):
    """新增工單備註的請求。"""

    author: str = Field(..., description="備註作者（agent_id 或使用者名稱）")
    text: str = Field(..., description="備註內容")
