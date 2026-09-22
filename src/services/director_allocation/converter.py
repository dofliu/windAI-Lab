"""Markdown 與資料庫物件雙向同步轉換器。"""

from __future__ import annotations

import logging
import re
from datetime import date
from pathlib import Path

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

logger = logging.getLogger("windailab.director_allocation.converter")


class AllocationMarkdownConverter:
    """Markdown ↔ DB Pydantic Model 雙向序列化與解析器。"""

    @staticmethod
    def parse_sheet(path_or_content: Path | str) -> DailyAllocationSheet:
        """解析 YYYY-MM-DD-allocation.md 派工單檔案。"""
        if isinstance(path_or_content, Path):
            with path_or_content.open("r", encoding="utf-8") as f:
                content = f.read()
            markdown_path = str(path_or_content)
        else:
            content = path_or_content
            markdown_path = ""

        # 1. 解析日期
        date_match = re.search(r"# 總監派工單 — (\d{4}-\d{2}-\d{2})", content)
        if date_match:
            sheet_date = date.fromisoformat(date_match.group(1))
        else:
            sheet_date = date.today()

        # 2. 解析剩餘天數
        days_match = re.search(r"\* Hackathon 剩餘天數：(\d+)", content)
        days_rem = int(days_match.group(1)) if days_match else 21

        # 3. 解析決策摘要 (## 1. 到 ## 2. 之間)
        summary = ""
        summary_section = re.search(r"## 1. 本日決策摘要\n(.*?)(?=\n## 2.)", content, re.DOTALL)
        if summary_section:
            summary = summary_section.group(1).strip()

        # 4. 解析任務分配表格
        allocations = []
        # 按列找到 ## 3. 今日任務分配 下方的表格
        alloc_section = re.search(r"## 3. 今日任務分配\n(.*?)(?=\n## 4.|\Z)", content, re.DOTALL)
        if alloc_section:
            table_lines = alloc_section.group(1).strip().split("\n")
            for line in table_lines:
                if not line.strip().startswith("|") or "任務 ID" in line or "---" in line:
                    continue
                # 分割欄位
                parts = [p.strip() for p in line.split("|")[1:-1]]
                if len(parts) >= 11:
                    task_id = parts[0]
                    # GitHub issue 格式可能是 #12 或 空
                    issue_str = parts[1].replace("#", "")
                    issue = int(issue_str) if issue_str.isdigit() else None
                    title = parts[2]
                    assignee = parts[3]

                    # 處理優先序
                    try:
                        pri = Priority(parts[4])
                    except ValueError:
                        pri = Priority.P3

                    # 估計工時
                    try:
                        hours = float(parts[5])
                    except ValueError:
                        hours = 4.0

                    # 依賴
                    deps = [d.strip() for d in parts[6].split(",") if d.strip()]

                    # 截止日期
                    try:
                        dl = date.fromisoformat(parts[7])
                    except Exception:
                        dl = date.today()

                    # 驗收標準，通常是多個標準，在 markdown 中可能用 comma 或是 <br> 隔開
                    criteria = [
                        c.strip() for c in parts[8].replace("<br>", "\n").split("\n") if c.strip()
                    ]
                    if not criteria:
                        criteria = [c.strip() for c in parts[8].split(",") if c.strip()]

                    rationale = parts[9]

                    try:
                        status = TaskStatus(parts[10].lower())
                    except ValueError:
                        status = TaskStatus.PENDING

                    allocations.append(
                        Allocation(
                            task_id=task_id,
                            github_issue=issue,
                            title=title,
                            assignee_agent=assignee,
                            priority=pri,
                            estimated_hours=hours,
                            dependencies=deps,
                            deadline=dl,
                            acceptance_criteria=criteria,
                            rationale=rationale,
                            status=status,
                        )
                    )

        # 5. 解析團隊負載
        load_snapshot = []
        load_section = re.search(
            r"## 2. 團隊負載與 Hackathon 倒數\n(.*?)(?=\n## 3.)", content, re.DOTALL
        )
        if load_section:
            table_lines = load_section.group(1).strip().split("\n")
            for line in table_lines:
                if not line.strip().startswith("|") or "Namespace" in line or "---" in line:
                    continue
                parts = [p.strip() for p in line.split("|")[1:-1]]
                if len(parts) >= 5:
                    try:
                        ns = TeamNamespace(parts[0])
                        wip = int(parts[1])
                        back = int(parts[2])
                        level = parts[3]
                        sugg = parts[4]
                        load_snapshot.append(
                            TeamLoadSnapshot(
                                namespace=ns,
                                wip_count=wip,
                                backlog_count=back,
                                load_level=level,
                                suggestion=sugg,
                            )
                        )
                    except Exception:
                        pass

        # 6. 解析 AI 建議
        bottlenecks = []
        risks = []
        res_sugg = []
        sch_sugg = []
        lessons = []

        ai_section = re.search(r"## 4. AI 輔助派工建議與回饋\n(.*?)(?=\Z)", content, re.DOTALL)
        if ai_section:
            ai_text = ai_section.group(1)

            # 簡單正則提取列表項
            def extract_bullets(title_pattern: str) -> list[str]:
                m = re.search(f"{title_pattern}\n(.*?)(?=\n\\*|\\Z)", ai_text, re.DOTALL)
                if not m:
                    return []
                return [
                    item.strip()[2:]
                    for item in m.group(1).strip().split("\n")
                    if item.strip().startswith("-")
                ]

            bottlenecks = extract_bullets(r"\* 潛在瓶頸：")
            risks = extract_bullets(r"\* 風險警示：")
            res_sugg = extract_bullets(r"\* 資源調配建議：")
            sch_sugg = extract_bullets(r"\* 進度排程與時間規劃建議：")
            lessons = extract_bullets(r"\* 近期經驗與檢討：")

        return DailyAllocationSheet(
            date=sheet_date,
            hackathon_days_remaining=days_rem,
            decision_summary=summary,
            load_snapshot=load_snapshot,
            allocations=allocations,
            ai_advice=AiAdvice(
                bottlenecks=bottlenecks,
                risks=risks,
                resource_suggestions=res_sugg,
                schedule_suggestions=sch_sugg,
                lessons_learned=lessons,
            ),
            markdown_path=markdown_path,
        )

    @staticmethod
    def render_sheet(sheet: DailyAllocationSheet) -> str:
        """渲染成 YYYY-MM-DD-allocation.md 派工單 Markdown 內容。"""
        lines = [
            f"# 總監派工單 — {sheet.date}",
            "",
            "## 1. 本日決策摘要",
            sheet.decision_summary,
            "",
            "## 2. 團隊負載與 Hackathon 倒數",
            f"* Hackathon 剩餘天數：{sheet.hackathon_days_remaining} 天",
            "* 負載快照：",
            "  | Namespace | WIP 數 | Backlog 數 | 負載等級 | 派工建議 |",
            "  | --- | --- | --- | --- | --- |",
        ]

        for snap in sheet.load_snapshot:
            lines.append(
                f"  | {snap.namespace.value} | {snap.wip_count} | {snap.backlog_count} | {snap.load_level} | {snap.suggestion} |"
            )

        lines.extend(
            [
                "",
                "## 3. 今日任務分配",
                "| 任務 ID | GitHub | 任務標題 | 指派代理 | 優先級 | 估計工時 | 前置依賴 | 截止日期 | 驗收標準 | 派工理由 | 狀態 |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )

        for alloc in sheet.allocations:
            issue_str = f"#{alloc.github_issue}" if alloc.github_issue else ""
            deps_str = ", ".join(alloc.dependencies) if alloc.dependencies else ""
            criteria_str = "<br>".join(alloc.acceptance_criteria)
            lines.append(
                f"| {alloc.task_id} | {issue_str} | {alloc.title} | {alloc.assignee_agent} | {alloc.priority.value} | "
                f"{alloc.estimated_hours} | {deps_str} | {alloc.deadline} | {criteria_str} | {alloc.rationale} | {alloc.status.value} |"
            )

        lines.extend(
            [
                "",
                "## 4. AI 輔助派工建議與回饋",
            ]
        )

        def render_bullets(title: str, bullets: list[str]) -> None:
            lines.append(f"* {title}")
            if bullets:
                for b in bullets:
                    lines.append(f"  - {b}")
            else:
                lines.append("  - 暫無。")

        render_bullets("潛在瓶頸：", sheet.ai_advice.bottlenecks)
        render_bullets("風險警示：", sheet.ai_advice.risks)
        render_bullets("資源調配建議：", sheet.ai_advice.resource_suggestions)
        render_bullets("進度排程與時間規劃建議：", sheet.ai_advice.schedule_suggestions)
        render_bullets("近期經驗與檢討：", sheet.ai_advice.lessons_learned)

        return "\n".join(lines) + "\n"

    @staticmethod
    def parse_record(path_or_content: Path | str) -> WorkRecord:
        """解析 WLAB-*.md 工作紀錄檔案。"""
        if isinstance(path_or_content, Path):
            with path_or_content.open("r", encoding="utf-8") as f:
                content = f.read()
            markdown_path = str(path_or_content)
        else:
            content = path_or_content
            markdown_path = ""

        # 1. 解析任務 ID
        id_match = re.search(r"# 工作紀錄 — (WLAB-\d{8}-\w+)", content)
        task_id = id_match.group(1) if id_match else "WLAB-unknown"

        # 2. 解析基本欄位（Metadata）
        # > **任務名稱**：...
        # > **GitHub Issue**：...
        # > **指派代理**：...
        # > **建立日期**：...
        # > **狀態**：...
        title = "未知任務"
        github_issue: int | None = None
        assignee = ""
        status = "pending"

        meta_matches = re.findall(r"> \*\*([^*]+)\*\*：(.*)", content)
        for name, value in meta_matches:
            name = name.strip()
            val = value.strip()
            if "任務名稱" in name:
                title = val
            elif "GitHub Issue" in name:
                # 解析其中的 issue number, 例如 [#42](...)
                issue_nums = re.findall(r"#(\d+)", val)
                if issue_nums:
                    github_issue = int(issue_nums[0])
            elif "指派代理" in name:
                assignee = val
            elif "狀態" in name:
                status = val

        # 3. 解析任務概述 (## 1. 任務概述 到 ## 2. 執行歷程 之間)
        summary = ""
        summary_section = re.search(r"## 1. 任務概述\n(.*?)(?=\n## 2.)", content, re.DOTALL)
        if summary_section:
            summary = summary_section.group(1).strip()

        # 4. 解析執行歷程 (## 2. 執行歷程)
        steps = []
        steps_section = re.search(r"## 2. 執行歷程\n(.*?)(?=\n## 3.)", content, re.DOTALL)
        if steps_section:
            steps = [
                line.strip()[2:]
                for line in steps_section.group(1).strip().split("\n")
                if line.strip().startswith("*") or line.strip().startswith("-")
            ]

        # 5. 解析變更紀錄 (## 3. 變更記錄)
        commits = []
        prs = []
        change_section = re.search(r"## 3. 變更記錄\n(.*?)(?=\n## 4.)", content, re.DOTALL)
        if change_section:
            change_text = change_section.group(1)
            commits = re.findall(r"- `([a-f0-9]+)`", change_text)
            prs_str = re.findall(r"- #(\d+)", change_text)
            prs = [int(p) for p in prs_str]

        # 6. 解析測試與驗證 (## 4. 測試與驗證)
        test_results = {}
        test_section = re.search(r"## 4. 測試與驗證\n(.*?)(?=\n## 5.)", content, re.DOTALL)
        if test_section:
            # 找表格或清單
            table_match = re.search(r"\|(.*?)(?=\n\n|\n##|\Z)", test_section.group(1), re.DOTALL)
            if table_match:
                table_lines = table_match.group(1).strip().split("\n")
                for line in table_lines:
                    if not line.strip().startswith("|") or "測試類型" in line or "---" in line:
                        continue
                    parts = [p.strip() for p in line.split("|")[1:-1]]
                    if len(parts) >= 3:
                        test_results[parts[0]] = f"{parts[1]} | {parts[2]}"

        # 7. 解析成果與交付物 (## 5. 成果與交付物)
        deliverables = []
        deliv_section = re.search(r"## 5. 成果與交付物\n(.*?)(?=\n## 6.)", content, re.DOTALL)
        if deliv_section:
            deliverables = [
                line.strip()[2:]
                for line in deliv_section.group(1).strip().split("\n")
                if line.strip().startswith("*") or line.strip().startswith("-")
            ]

        # 8. 解析學習與後續建議 (## 6. 學習與後續建議)
        learnings = []
        follow_up = []
        learn_section = re.search(r"## 6. 學習與後續建議\n(.*?)(?=\Z)", content, re.DOTALL)
        if learn_section:
            learn_text = learn_section.group(1)

            l_match = re.search(r"\* 學到什麼：?\n(.*?)(?=\* 後續行動|\Z)", learn_text, re.DOTALL)
            if l_match:
                learnings = [
                    line.strip()[2:]
                    for line in l_match.group(1).strip().split("\n")
                    if line.strip().startswith("-") or line.strip().startswith("*")
                ]

            f_match = re.search(r"\* 後續行動：?\n(.*?)(?=\Z)", learn_text, re.DOTALL)
            if f_match:
                follow_up = [
                    line.strip()[2:]
                    for line in f_match.group(1).strip().split("\n")
                    if line.strip().startswith("-") or line.strip().startswith("*")
                ]

        return WorkRecord(
            task_id=task_id,
            summary=summary,
            execution_steps=steps,
            deliverables=deliverables,
            title=title,
            github_issue=github_issue,
            assignee=assignee,
            status=status,
            commits=commits,
            prs=prs,
            test_results=test_results,
            learnings=learnings,
            follow_up_actions=follow_up,
            markdown_path=markdown_path,
        )

    @staticmethod
    def render_record(
        record: WorkRecord,
        title: str | None = None,
        github_issue: int | None = None,
        assignee_agent: str | None = None,
    ) -> str:
        """渲染成 WLAB-*.md 工作紀錄 Markdown 內容。

        `title` / `github_issue` / `assignee_agent` 未顯式提供時，回退採用
        `record` 自身同名欄位（例如來自 `parse_record()` 的往返解析結果）。
        """
        title = title if title is not None else record.title
        github_issue = github_issue if github_issue is not None else record.github_issue
        assignee_agent = assignee_agent if assignee_agent is not None else record.assignee
        issue_str = (
            f"[#{github_issue}](https://github.com/dofliu/windai-lab/issues/{github_issue})"
            if github_issue
            else "無"
        )
        status_str = "in_progress" if not record.closed_at else "completed"

        lines = [
            f"# 工作紀錄 — {record.task_id}",
            "",
            f"> **任務名稱**：{title}",
            f"> **GitHub Issue**：{issue_str}",
            f"> **指派代理**：{assignee_agent}",
            f"> **建立日期**：{record.created_at.strftime('%Y-%m-%d')}",
            f"> **狀態**：{status_str}",
            "",
            "---",
            "",
            "## 1. 任務概述",
            record.summary,
            "",
            "## 2. 執行歷程",
        ]

        if record.execution_steps:
            for step in record.execution_steps:
                lines.append(f"* {step}")
        else:
            lines.append("* 執行中。")

        lines.extend(["", "## 3. 變更記錄", "* Commits:"])

        if record.commits:
            for c in record.commits:
                lines.append(f"  - `{c}`")
        else:
            lines.append("  - 暫無。")

        lines.append("* PRs:")
        if record.prs:
            for p in record.prs:
                lines.append(f"  - #{p}")
        else:
            lines.append("  - 暫無。")

        lines.extend(["", "## 4. 測試與驗證", "| 測試類型 | 狀態 | 結果 |", "| --- | --- | --- |"])

        if record.test_results:
            for k, v in record.test_results.items():
                lines.append(f"| {k} | {v} |")
        else:
            lines.append("| 單元測試 | PENDING | 待驗證 |")

        lines.extend(
            [
                "",
                "## 5. 成果與交付物",
            ]
        )

        if record.deliverables:
            for d in record.deliverables:
                lines.append(f"* {d}")
        else:
            lines.append("* 暫無。")

        lines.extend(["", "## 6. 學習與後續建議", "* 學到什麼："])

        if record.learnings:
            for l in record.learnings:
                lines.append(f"  - {l}")
        else:
            lines.append("  - 暫無。")

        lines.append("* 後續行動：")
        if record.follow_up_actions:
            for f in record.follow_up_actions:
                lines.append(f"  - {f}")
        else:
            lines.append("  - 暫無。")

        return "\n".join(lines) + "\n"
