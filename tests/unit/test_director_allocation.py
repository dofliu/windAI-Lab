"""單元測試 — 總監派工系統與雙向同步。"""

from __future__ import annotations

from datetime import date, datetime
import pytest

from src.services.director_allocation.models import (
    Priority,
    TeamNamespace,
    TaskStatus,
    Allocation,
    DailyAllocationSheet,
    AiAdvice,
    WorkRecord,
    TeamLoadSnapshot,
)
from src.services.director_allocation.allocator import AllocationEngine, TaskInput
from src.services.director_allocation.converter import AllocationMarkdownConverter


def test_allocation_engine_suggest():
    engine = AllocationEngine()
    
    # 測試後端/API任務
    task1 = TaskInput(
        title="開發通知與告警 API 路由",
        description="在 src/api 下新增派工與通知的 REST 端點",
        github_issue=42,
    )
    sugg1 = engine.suggest(task1)
    assert sugg1.assignee_agent == "wEng:backend-dev"
    assert sugg1.priority == Priority.P3
    
    # 測試 RAG/論文任務
    task2 = TaskInput(
        title="寫論文的 Results 章節",
        description="撰寫風場故障診斷 LSTM 模型的實驗數據分析報告與圖表",
        labels=["paper"],
    )
    sugg2 = engine.suggest(task2)
    assert sugg2.assignee_agent == "wRes:paper-writer"


def test_markdown_sheet_roundtrip():
    # 建立一個測試用 DailyAllocationSheet
    sheet = DailyAllocationSheet(
        date=date(2026, 4, 20),
        hackathon_days_remaining=21,
        decision_summary="今日決定推進 Epic E 與派工系統階段二。",
        load_snapshot=[
            TeamLoadSnapshot(
                namespace=TeamNamespace.wEng,
                wip_count=1,
                backlog_count=2,
                load_level="low",
                suggestion="適合承接新工作",
            ),
            TeamLoadSnapshot(
                namespace=TeamNamespace.wRes,
                wip_count=0,
                backlog_count=0,
                load_level="idle",
                suggestion="無待辦任務",
            ),
        ],
        allocations=[
            Allocation(
                task_id="WLAB-20260420-01",
                github_issue=42,
                title="實作通知渠道",
                assignee_agent="wEng:backend-dev",
                priority=Priority.P2,
                estimated_hours=6.0,
                dependencies=["WLAB-20260419-01"],
                deadline=date(2026, 4, 25),
                acceptance_criteria=["單元測試通過", "Email 順利送出"],
                rationale="完成告警引擎外部通知能力",
                status=TaskStatus.PENDING,
            )
        ],
        ai_advice=AiAdvice(
            bottlenecks=["wEng 待辦工作稍多"],
            risks=["LINE Notify API 限速問題"],
            resource_suggestions=["可安排 wRes 代理支援設計"],
            schedule_suggestions=["建議本週內完成 Epic E"],
            lessons_learned=["設計先行確實減少了程式碼返工"],
        ),
    )
    
    # 1. 渲染成 Markdown 字串
    md_content = AllocationMarkdownConverter.render_sheet(sheet)
    
    # 2. 將 Markdown 字串解析回 DailyAllocationSheet 物件
    parsed = AllocationMarkdownConverter.parse_sheet(md_content)
    
    # 3. 斷言兩者欄位值完全相等，驗證無損 roundtrip 序列化
    assert parsed.date == sheet.date
    assert parsed.hackathon_days_remaining == sheet.hackathon_days_remaining
    assert parsed.decision_summary == sheet.decision_summary
    assert len(parsed.allocations) == len(sheet.allocations)
    assert parsed.allocations[0].task_id == sheet.allocations[0].task_id
    assert parsed.allocations[0].github_issue == sheet.allocations[0].github_issue
    assert parsed.allocations[0].title == sheet.allocations[0].title
    assert parsed.allocations[0].priority == sheet.allocations[0].priority
    assert parsed.allocations[0].estimated_hours == sheet.allocations[0].estimated_hours
    assert parsed.allocations[0].dependencies == sheet.allocations[0].dependencies
    assert parsed.allocations[0].deadline == sheet.allocations[0].deadline
    assert parsed.allocations[0].acceptance_criteria == sheet.allocations[0].acceptance_criteria
    assert parsed.allocations[0].status == sheet.allocations[0].status
    assert parsed.ai_advice.bottlenecks == sheet.ai_advice.bottlenecks
    assert parsed.ai_advice.risks == sheet.ai_advice.risks
    assert parsed.ai_advice.lessons_learned == sheet.ai_advice.lessons_learned


def test_markdown_record_roundtrip():
    # 建立一個測試用 WorkRecord
    record = WorkRecord(
        task_id="WLAB-20260420-01",
        summary="完成了通知渠道模組的實作並整合至告警規則引擎。",
        execution_steps=[
            "建立 BaseNotifier 抽象基底類別",
            "實作 Email, Webhook, LINE 渠道",
            "在 alert_engine.py 中加上 notify_manager.dispatch() 呼叫",
        ],
        deliverables=[
            "src/services/notifiers/base.py",
            "src/services/notifiers/email.py",
            "src/services/notifiers/webhook.py",
            "src/services/notifiers/line.py",
            "src/services/notification_manager.py",
        ],
        commits=["abc1234", "def5678"],
        prs=[12],
        test_results={
            "單元測試": "PASS | 測試覆蓋率 90%",
            "手動驗證": "PASS | LINE Notify 順利收到推送",
        },
        learnings=["使用 asyncio.to_thread 防止同步郵件寄送阻塞事件循環"],
        follow_up_actions=["下個階段安排 Webhook HMAC 驗證"],
        created_at=datetime(2026, 4, 20, 10, 0),
        closed_at=datetime(2026, 4, 20, 18, 0),
    )
    
    # 1. 渲染
    md_content = AllocationMarkdownConverter.render_record(
        record, title="實作通知渠道", github_issue=42, assignee_agent="wEng:backend-dev"
    )
    
    # 2. 解析
    parsed = AllocationMarkdownConverter.parse_record(md_content)
    
    # 3. 斷言
    assert parsed.task_id == record.task_id
    assert parsed.summary == record.summary
    assert parsed.execution_steps == record.execution_steps
    assert parsed.deliverables == record.deliverables
    assert parsed.commits == record.commits
    assert parsed.prs == record.prs
    assert parsed.learnings == record.learnings
    assert parsed.follow_up_actions == record.follow_up_actions
    assert parsed.test_results["單元測試"] == record.test_results["單元測試"]
    assert parsed.test_results["手動驗證"] == record.test_results["手動驗證"]
