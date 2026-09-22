"""AI 輔助派工演算法與負載評估引擎。"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from src.core.database import get_database
from src.services.director_allocation.models import (
    Priority,
    TaskStatus,
    TeamLoadSnapshot,
    TeamNamespace,
)


class TaskInput(BaseModel):
    title: str
    description: str = ""
    github_issue: int | None = None
    labels: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    requested_priority: Priority | None = None


class AllocationSuggestion(BaseModel):
    assignee_agent: str
    priority: Priority
    estimated_hours: float
    rationale: str
    risk_flags: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)


class AllocationEngine:
    """AI 輔助派工決策引擎 (規則式 v0.1)。"""

    def __init__(self) -> None:
        self.db = get_database()

    def get_load_snapshot(self, hackathon_days_remaining: int = 21) -> list[TeamLoadSnapshot]:
        """獲取當前團隊的任務負載快照。"""
        # 1. 查詢 allocations 中所有 WIP (in_progress) 與 Backlog (pending) 的任務
        allocations = self.db.list_allocations()

        wip_counts = dict.fromkeys(TeamNamespace, 0)
        backlog_counts = dict.fromkeys(TeamNamespace, 0)

        for alloc in allocations:
            # 提取 assignee_agent 中的 namespace
            # 格式例如: wEng:backend-dev
            agent = alloc.get("assignee_agent", "")
            if ":" in agent:
                ns_str = agent.split(":")[0]
                if ns_str in wip_counts:
                    status = alloc.get("status")
                    if status == TaskStatus.IN_PROGRESS:
                        wip_counts[ns_str] += 1
                    elif status == TaskStatus.PENDING:
                        backlog_counts[ns_str] += 1

        snapshots = []
        for ns in TeamNamespace:
            wip = wip_counts[ns]
            backlog = backlog_counts[ns]

            # 負載評分規則
            total_load = wip * 1.5 + backlog * 0.5
            if total_load == 0:
                level = "idle"
                sugg = "無待辦任務，可以接案。"
            elif total_load <= 1.5:
                level = "low"
                sugg = "負載偏低，適合分配新工作。"
            elif total_load <= 3.5:
                level = "medium"
                sugg = "工作量適中，可平行推進任務。"
            elif total_load <= 5.5:
                level = "high"
                sugg = "待辦工作較多，建議優先清空 WIP。"
            else:
                level = "critical"
                sugg = "負載已達上限！暫停指派新工作，或安排協作代理。"

            snapshots.append(
                TeamLoadSnapshot(
                    namespace=ns,
                    wip_count=wip,
                    backlog_count=backlog,
                    load_level=level,
                    suggestion=sugg,
                )
            )
        return snapshots

    def suggest(self, task: TaskInput, hackathon_days_remaining: int = 21) -> AllocationSuggestion:
        """根據任務輸入產出派工與優先序建議。"""
        title_lower = task.title.lower()
        desc_lower = task.description.lower()
        comb_text = f"{title_lower} {desc_lower}"

        # 1. 分類決策 (優先使用 labels 進行分類)
        ns = None
        assignee = ""

        labels_lower = [l.lower() for l in task.labels]
        if "paper" in labels_lower or "docs" in labels_lower or "research" in labels_lower:
            ns = TeamNamespace.wRes
            assignee = "wRes:paper-writer"
        elif "backend" in labels_lower or "api" in labels_lower:
            ns = TeamNamespace.wEng
            assignee = "wEng:backend-dev"
        elif "ml" in labels_lower or "model" in labels_lower or "ai" in labels_lower:
            ns = TeamNamespace.wAI
            assignee = "wAI:predictive-modeler"
        elif "data" in labels_lower or "scada" in labels_lower:
            ns = TeamNamespace.wData
            assignee = "wData:scada-processor"

        if ns is None:
            # 基於 regex 決定 Team Namespace 與預設 Assignee
            if re.search(r"backend|api|service|fastapi|route|endpoint|database|sqlite", comb_text):
                ns = TeamNamespace.wEng
                assignee = "wEng:backend-dev"
            elif re.search(
                r"ml|model|training|forecast|diagnosis|lstm|transformer|predictive|nbm", comb_text
            ):
                ns = TeamNamespace.wAI
                assignee = "wAI:predictive-modeler"
            elif re.search(r"data|etl|scada|cleaning|ingestion|loader|watcher", comb_text):
                ns = TeamNamespace.wData
                assignee = "wData:scada-processor"
            elif re.search(r"domain|iec|wake|power-curve|wind|turbine", comb_text):
                ns = TeamNamespace.wDomain
                assignee = "wDomain:power-curve-expert"
            elif re.search(
                r"research|docs|paper|rag|literature|markdown|walkthrough|report", comb_text
            ):
                ns = TeamNamespace.wRes
                assignee = "wRes:paper-writer"
            else:
                ns = TeamNamespace.wLab
                assignee = "wLab:project-manager"

        # 2. 獲取團隊當前負載
        snapshots = self.get_load_snapshot(hackathon_days_remaining)
        target_snap = next((s for s in snapshots if s.namespace == ns), None)

        risk_flags = []
        alternatives = []

        # 如果首選團隊的 WIP 超過 3 個，將其標為高負載並考慮備選
        if target_snap and target_snap.wip_count >= 3:
            risk_flags.append(
                f"首選團隊 {ns.value} 當前 WIP 過多 ({target_snap.wip_count})，有延期風險"
            )
            if ns == TeamNamespace.wEng:
                alternatives.append("wRes:paper-writer (進行 API 設計與文件撰寫)")
            elif ns == TeamNamespace.wAI:
                alternatives.append("wDomain:power-curve-expert (分析特徵變數)")

        # 3. 優先序決策
        if task.requested_priority:
            priority = task.requested_priority
        else:
            # 根據條件自動決定
            if hackathon_days_remaining < 7 and ("critical" in comb_text or "urgent" in comb_text):
                priority = Priority.P1
            elif task.dependencies:
                # 有阻礙鏈的優先級別提高
                priority = Priority.P1
            elif "epic" in comb_text or any("epic" in l.lower() for l in task.labels):
                priority = Priority.P2
            elif "debt" in comb_text or "refactor" in comb_text or "clean" in comb_text:
                priority = Priority.P4
            else:
                priority = Priority.P3

        # 4. 工時估算
        if "design" in comb_text or "文件" in comb_text:
            hours = 2.0
        elif "notifier" in comb_text or "webhook" in comb_text:
            hours = 6.0
        elif "workflow" in comb_text or "pipeline" in comb_text:
            hours = 8.0
        elif "api" in comb_text or "crud" in comb_text:
            hours = 4.0
        else:
            hours = 4.0

        if hours > 10.0:
            risk_flags.append("任務估計時間大於 10 小時，建議拆分為子 PR")

        # 5. 理由 (Rationale)
        rationale = f"基於關鍵字匹配自動指派給 {assignee}。"
        if task.dependencies:
            rationale += (
                f" 任務有前置依賴 {task.dependencies}，因此優先級設定為 {priority.value}。"
            )
        else:
            rationale += f" 設定優先級為 {priority.value} 且預估需要 {hours} 小時。"

        return AllocationSuggestion(
            assignee_agent=assignee,
            priority=priority,
            estimated_hours=hours,
            rationale=rationale,
            risk_flags=risk_flags,
            alternatives=alternatives,
        )
