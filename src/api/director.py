"""派工系統 REST API 控制器。"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from src.core.database import get_database
from src.services.director_allocation.allocator import (
    AllocationEngine,
    AllocationSuggestion,
    TaskInput,
)
from src.services.director_allocation.converter import AllocationMarkdownConverter
from src.services.director_allocation.models import (
    AiAdvice,
    Allocation,
    DailyAllocationSheet,
    Priority,
    TaskStatus,
    TeamLoadSnapshot,
    TeamNamespace,
    WorkRecord,
)

logger = logging.getLogger("windailab.api.director")

router = APIRouter(prefix="/api/director", tags=["總監派工系統"])

# 專案根目錄
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


@router.get("/allocations", response_model=list[dict[str, Any]])
async def list_allocations(
    sheet_date: str | None = Query(None, description="篩選派工單日期 (YYYY-MM-DD)"),
    assignee: str | None = Query(None, description="篩選指派代理 (namespace:role)"),
    status: str | None = Query(None, description="篩選狀態"),
):
    """列出符合條件的派工紀錄。"""
    db = get_database()
    return db.list_allocations(sheet_date=sheet_date, assignee=assignee, status=status)


@router.post("/allocations", status_code=201)
async def create_allocation(alloc: Allocation):
    """建立一筆派工，寫入資料庫並同步更新/生成 YYYY-MM-DD-allocation.md。"""
    db = get_database()

    # 1. 寫入資料庫
    db.create_allocation(
        task_id=alloc.task_id,
        sheet_date=alloc.sheet_date.isoformat(),
        github_issue=alloc.github_issue,
        title=alloc.title,
        assignee_agent=alloc.assignee_agent,
        collaborators=alloc.collaborators,
        priority=alloc.priority.value,
        estimated_hours=alloc.estimated_hours,
        dependencies=alloc.dependencies,
        deadline=alloc.deadline.isoformat(),
        acceptance_criteria=alloc.acceptance_criteria,
        rationale=alloc.rationale,
        status=alloc.status.value,
    )

    # 2. 同步更新 Markdown 派工單
    sheet_date_str = alloc.sheet_date.isoformat()
    await _sync_sheet_to_markdown(db, sheet_date_str)

    return {"status": "success", "task_id": alloc.task_id}


@router.get("/allocations/{task_id}", response_model=dict[str, Any])
async def get_allocation(task_id: str):
    """取得單一派工紀錄。"""
    db = get_database()
    alloc = db.get_allocation(task_id)
    if not alloc:
        raise HTTPException(status_code=404, detail=f"找不到派工紀錄：{task_id}")
    return alloc


@router.patch("/allocations/{task_id}")
async def update_allocation_status(task_id: str, status: TaskStatus):
    """更新派工狀態，並同步更新對置派工單的 Markdown 狀態。"""
    db = get_database()
    alloc = db.get_allocation(task_id)
    if not alloc:
        raise HTTPException(status_code=404, detail=f"找不到派工紀錄：{task_id}")

    success = db.update_allocation_status(task_id, status.value)
    if not success:
        raise HTTPException(status_code=500, detail="更新派工狀態失敗")

    # 同步更新 markdown
    sheet_date_str = alloc.get("sheet_date")
    if sheet_date_str:
        await _sync_sheet_to_markdown(db, sheet_date_str)

    return {"status": "success", "task_id": task_id, "new_status": status.value}


@router.post("/suggest", response_model=AllocationSuggestion)
async def suggest_allocation(task: TaskInput):
    """依據任務資訊產出 AI 輔助派工建議與時程預估。"""
    engine = AllocationEngine()
    return engine.suggest(task)


@router.get("/load-snapshot", response_model=list[TeamLoadSnapshot])
async def get_load_snapshot():
    """獲取各團隊 namespace 的當前 WIP 與負載狀態。"""
    engine = AllocationEngine()
    return engine.get_load_snapshot()


@router.get("/sheets/{sheet_date}", response_model=dict[str, Any])
async def get_daily_sheet(sheet_date: str):
    """取得一日完整派工單。若資料庫不存在，嘗試從 Markdown 檔案解析匯入。"""
    db = get_database()
    sheet = db.get_daily_sheet(sheet_date)

    if not sheet:
        # 嘗試從實體檔案載入
        try:
            dt = date.fromisoformat(sheet_date)
            folder = _PROJECT_ROOT / "docs" / "work-logs" / dt.strftime("%Y-%m")
            filepath = folder / f"{sheet_date}-allocation.md"
            if filepath.exists():
                parsed = AllocationMarkdownConverter.parse_sheet(filepath)
                # 寫入資料庫
                db.create_daily_sheet(
                    sheet_date=sheet_date,
                    hackathon_days_remaining=parsed.hackathon_days_remaining,
                    decision_summary=parsed.decision_summary,
                    ai_advice=parsed.ai_advice.dict(),
                    load_snapshot=[snap.dict() for snap in parsed.load_snapshot],
                    signed_off=parsed.signed_off,
                    markdown_path=str(filepath),
                )
                for alloc in parsed.allocations:
                    db.create_allocation(
                        task_id=alloc.task_id,
                        sheet_date=sheet_date,
                        github_issue=alloc.github_issue,
                        title=alloc.title,
                        assignee_agent=alloc.assignee_agent,
                        collaborators=alloc.collaborators,
                        priority=alloc.priority.value,
                        estimated_hours=alloc.estimated_hours,
                        dependencies=alloc.dependencies,
                        deadline=alloc.deadline.isoformat(),
                        acceptance_criteria=alloc.acceptance_criteria,
                        rationale=alloc.rationale,
                        status=alloc.status.value,
                    )
                sheet = db.get_daily_sheet(sheet_date)
        except Exception as e:
            logger.warning(f"從 Markdown 載入派工單失敗：{e}")

    if not sheet:
        raise HTTPException(status_code=404, detail=f"找不到該日期的派工單：{sheet_date}")

    # 合併 allocations 列表
    allocations = db.list_allocations(sheet_date=sheet_date)
    sheet["allocations"] = allocations
    return sheet


@router.post("/sheets/{sheet_date}/signoff")
async def signoff_daily_sheet(sheet_date: str):
    """簽核一日派工單。"""
    db = get_database()
    sheet = db.get_daily_sheet(sheet_date)
    if not sheet:
        raise HTTPException(status_code=404, detail=f"找不到該日期的派工單：{sheet_date}")

    db.create_daily_sheet(
        sheet_date=sheet_date,
        hackathon_days_remaining=sheet["hackathon_days_remaining"],
        decision_summary=sheet["decision_summary"],
        ai_advice=sheet["ai_advice"],
        load_snapshot=sheet["load_snapshot"],
        signed_off=True,
        markdown_path=sheet.get("markdown_path", ""),
    )

    # 同步更新 markdown
    await _sync_sheet_to_markdown(db, sheet_date)
    return {"status": "success", "sheet_date": sheet_date, "signed_off": True}


@router.get("/work-records/{task_id}", response_model=dict[str, Any])
async def get_work_record(task_id: str):
    """取得單一工作紀錄。"""
    db = get_database()
    record = db.get_work_record(task_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"找不到工作紀錄：{task_id}")
    return record


@router.post("/work-records")
async def create_or_update_work_record(record: WorkRecord):
    """建立或更新工作紀錄，寫入資料庫並同步更新 Markdown。"""
    db = get_database()

    # 1. 寫入資料庫
    db.create_work_record(
        task_id=record.task_id,
        summary=record.summary,
        execution_steps=record.execution_steps,
        deliverables=record.deliverables,
        markdown_path=record.markdown_path,
        commits=record.commits,
        prs=record.prs,
        test_results=record.test_results,
        learnings=record.learnings,
        follow_up_actions=record.follow_up_actions,
        closed_at=record.closed_at.isoformat() if record.closed_at else None,
    )

    # 2. 取得對置派工資訊，組裝渲染 Markdown
    alloc = db.get_allocation(record.task_id) or {}
    title = alloc.get("title", "未知任務")
    issue = alloc.get("github_issue")
    assignee = alloc.get("assignee_agent", "")

    # 確定 Markdown 路徑
    # 根據 task_id 的日期決定，WLAB-YYYYMMDD-NN
    markdown_path = record.markdown_path
    if not markdown_path:
        try:
            date_str = record.task_id.split("-")[1]
            dt = datetime.strptime(date_str, "%Y%m%d")
            folder = _PROJECT_ROOT / "docs" / "work-logs" / dt.strftime("%Y-%m")
            folder.mkdir(parents=True, exist_ok=True)
            slug = title.lower().replace(" ", "-")
            # 移除非法字元
            slug = re.sub(r"[^\w\-]", "", slug)
            markdown_path = str(folder / f"{record.task_id}-{slug}.md")
        except Exception:
            markdown_path = str(
                _PROJECT_ROOT / "docs" / "work-logs" / f"{record.task_id}-record.md"
            )

    # 更新實體檔案
    md_content = AllocationMarkdownConverter.render_record(
        record, title=title, github_issue=issue, assignee_agent=assignee
    )

    path = Path(markdown_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(md_content)

    # 把路徑存回資料庫
    db.create_work_record(
        task_id=record.task_id,
        summary=record.summary,
        execution_steps=record.execution_steps,
        deliverables=record.deliverables,
        markdown_path=markdown_path,
        commits=record.commits,
        prs=record.prs,
        test_results=record.test_results,
        learnings=record.learnings,
        follow_up_actions=record.follow_up_actions,
        closed_at=record.closed_at.isoformat() if record.closed_at else None,
    )

    return {"status": "success", "task_id": record.task_id, "markdown_path": markdown_path}


@router.post("/import-markdown")
async def import_markdown_logs():
    """自動掃描 docs/work-logs/ 目錄，將所有歷史派工單與工作紀錄解析並匯入 SQLite 資料庫中。"""
    db = get_database()
    work_logs_dir = _PROJECT_ROOT / "docs" / "work-logs"

    if not work_logs_dir.exists():
        return {"status": "warning", "detail": f"目錄不存在：{work_logs_dir}"}

    sheets_imported = 0
    records_imported = 0

    # 遍歷所有的子目錄 (按月份 YYYY-MM)
    for month_dir in work_logs_dir.iterdir():
        if not month_dir.is_dir() or not re.match(r"^\d{4}-\d{2}$", month_dir.name):
            continue

        for filepath in month_dir.iterdir():
            if not filepath.is_file() or not filepath.name.endswith(".md"):
                continue

            try:
                # 1. 判斷是否是一日派工單 YYYY-MM-DD-allocation.md
                if filepath.name.endswith("-allocation.md"):
                    parsed = AllocationMarkdownConverter.parse_sheet(filepath)
                    # 寫入 daily_sheets
                    db.create_daily_sheet(
                        sheet_date=parsed.date.isoformat(),
                        hackathon_days_remaining=parsed.hackathon_days_remaining,
                        decision_summary=parsed.decision_summary,
                        ai_advice=parsed.ai_advice.dict(),
                        load_snapshot=[snap.dict() for snap in parsed.load_snapshot],
                        signed_off=parsed.signed_off,
                        markdown_path=str(filepath),
                    )
                    # 寫入 allocations
                    for alloc in parsed.allocations:
                        db.create_allocation(
                            task_id=alloc.task_id,
                            sheet_date=parsed.date.isoformat(),
                            github_issue=alloc.github_issue,
                            title=alloc.title,
                            assignee_agent=alloc.assignee_agent,
                            collaborators=alloc.collaborators,
                            priority=alloc.priority.value,
                            estimated_hours=alloc.estimated_hours,
                            dependencies=alloc.dependencies,
                            deadline=alloc.deadline.isoformat(),
                            acceptance_criteria=alloc.acceptance_criteria,
                            rationale=alloc.rationale,
                            status=alloc.status.value,
                        )
                    sheets_imported += 1

                # 2. 判斷是否是工作紀錄 WLAB-*.md
                elif filepath.name.startswith("WLAB-"):
                    parsed = AllocationMarkdownConverter.parse_record(filepath)
                    # 寫入 work_records
                    db.create_work_record(
                        task_id=parsed.task_id,
                        summary=parsed.summary,
                        execution_steps=parsed.execution_steps,
                        deliverables=parsed.deliverables,
                        markdown_path=str(filepath),
                        commits=parsed.commits,
                        prs=parsed.prs,
                        test_results=parsed.test_results,
                        learnings=parsed.learnings,
                        follow_up_actions=parsed.follow_up_actions,
                        closed_at=parsed.closed_at.isoformat() if parsed.closed_at else None,
                    )
                    records_imported += 1
            except Exception as e:
                logger.error(f"匯入 Markdown 檔案失敗：{filepath.name} — {e}")

    return {
        "status": "success",
        "sheets_imported": sheets_imported,
        "records_imported": records_imported,
    }


async def _sync_sheet_to_markdown(db: Any, sheet_date_str: str) -> None:
    """將資料庫中的某日派工單重新渲染並寫回 Markdown 實體檔案中。"""
    try:
        sheet = db.get_daily_sheet(sheet_date_str)
        if not sheet:
            return

        allocations = db.list_allocations(sheet_date=sheet_date_str)

        # 組裝 allocations Pydantic 列表
        alloc_models = []
        for a in allocations:
            alloc_models.append(
                Allocation(
                    task_id=a["task_id"],
                    github_issue=a.get("github_issue"),
                    title=a["title"],
                    assignee_agent=a["assignee_agent"],
                    priority=Priority(a["priority"]),
                    estimated_hours=a["estimated_hours"],
                    dependencies=a["dependencies"],
                    deadline=date.fromisoformat(a["deadline"]),
                    acceptance_criteria=a["acceptance_criteria"],
                    rationale=a["rationale"],
                    status=TaskStatus(a["status"]),
                )
            )

        # 組裝 load_snapshot Pydantic 列表
        load_models = []
        for l in sheet["load_snapshot"]:
            load_models.append(
                TeamLoadSnapshot(
                    namespace=TeamNamespace(l["namespace"]),
                    wip_count=l["wip_count"],
                    backlog_count=l["backlog_count"],
                    load_level=l["load_level"],
                    suggestion=l["suggestion"],
                )
            )

        advice = sheet["ai_advice"]
        sheet_model = DailyAllocationSheet(
            date=date.fromisoformat(sheet_date_str),
            hackathon_days_remaining=sheet["hackathon_days_remaining"],
            decision_summary=sheet["decision_summary"],
            load_snapshot=load_models,
            allocations=alloc_models,
            ai_advice=AiAdvice(
                bottlenecks=advice.get("bottlenecks", []),
                risks=advice.get("risks", []),
                resource_suggestions=advice.get("resource_suggestions", []),
                schedule_suggestions=advice.get("schedule_suggestions", []),
                lessons_learned=advice.get("lessons_learned", []),
            ),
            signed_off=sheet["signed_off"],
            markdown_path=sheet.get("markdown_path", ""),
        )

        markdown_path = sheet_model.markdown_path
        if not markdown_path:
            dt = date.fromisoformat(sheet_date_str)
            folder = _PROJECT_ROOT / "docs" / "work-logs" / dt.strftime("%Y-%m")
            folder.mkdir(parents=True, exist_ok=True)
            markdown_path = str(folder / f"{sheet_date_str}-allocation.md")

        md_content = AllocationMarkdownConverter.render_sheet(sheet_model)

        path = Path(markdown_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            f.write(md_content)

        # 如果路徑是新的，更新回資料庫
        if not sheet.get("markdown_path"):
            db.create_daily_sheet(
                sheet_date=sheet_date_str,
                hackathon_days_remaining=sheet["hackathon_days_remaining"],
                decision_summary=sheet["decision_summary"],
                ai_advice=sheet["ai_advice"],
                load_snapshot=sheet["load_snapshot"],
                signed_off=sheet["signed_off"],
                markdown_path=markdown_path,
            )
    except Exception as e:
        logger.error(f"同步更新派工單 Markdown 失敗：{sheet_date_str} — {e}")
