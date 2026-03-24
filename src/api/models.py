"""WindAI Lab 資料模型定義。

定義所有 API 端點使用的 Pydantic 模型，包含代理狀態、工作日誌與請求回應格式。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    """代理運行狀態列舉。"""

    IDLE = "idle"
    WORKING = "working"
    WAITING = "waiting"
    ERROR = "error"
    OFFLINE = "offline"
    COMPLETED = "completed"


class AgentTier(str, Enum):
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
    collaborating_with: list[str] = Field(default_factory=list, description="正在協作的代理 ID 列表")
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
