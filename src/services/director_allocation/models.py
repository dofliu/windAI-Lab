"""派工系統 Pydantic 資料模型定義。"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class Priority(str, Enum):
    P0 = "P0"  # 例行（每日掃描、日報）
    P1 = "P1"  # Hackathon 關鍵路徑
    P2 = "P2"  # Epic 推進
    P3 = "P3"  # 平行推進
    P4 = "P4"  # 使用者需求 / 技術債
    P5 = "P5"  # 待排程


class TeamNamespace(str, Enum):
    wLab = "wLab"
    wData = "wData"
    wAI = "wAI"
    wDomain = "wDomain"
    wEng = "wEng"
    wRes = "wRes"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Allocation(BaseModel):
    """單一派工紀錄。對應 Markdown 派工單中的一個任務欄位。"""

    task_id: str = Field(..., description="WLAB-YYYYMMDD-NN")
    github_issue: int | None = None
    title: str
    assignee_agent: str = Field(..., description="namespace:role")
    collaborators: list[str] = Field(default_factory=list)
    priority: Priority
    estimated_hours: float
    dependencies: list[str] = Field(default_factory=list)
    deadline: date
    acceptance_criteria: list[str]
    rationale: str = Field(..., description="派工理由")
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TeamLoadSnapshot(BaseModel):
    namespace: TeamNamespace
    wip_count: int
    backlog_count: int
    load_level: str  # idle, low, medium, high, critical
    suggestion: str


class AiAdvice(BaseModel):
    bottlenecks: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    resource_suggestions: list[str] = Field(default_factory=list)
    schedule_suggestions: list[str] = Field(default_factory=list)
    lessons_learned: list[str] = Field(default_factory=list)


class DailyAllocationSheet(BaseModel):
    """一日派工單 — 對應 YYYY-MM-DD-allocation.md。"""

    date: date
    hackathon_days_remaining: int
    decision_summary: str
    load_snapshot: list[TeamLoadSnapshot]
    allocations: list[Allocation]
    ai_advice: AiAdvice
    signed_off: bool = False
    markdown_path: str = ""


class WorkRecord(BaseModel):
    """工作紀錄 — 對應 WLAB-*.md 檔案。"""

    task_id: str
    summary: str
    execution_steps: list[str]
    deliverables: list[str]
    title: str = "未知任務"
    github_issue: int | None = None
    assignee: str = ""
    status: str = "pending"
    commits: list[str] = Field(default_factory=list)
    prs: list[int] = Field(default_factory=list)
    test_results: dict[str, str] = Field(default_factory=dict)
    learnings: list[str] = Field(default_factory=list)
    follow_up_actions: list[str] = Field(default_factory=list)
    markdown_path: str = ""
    closed_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
