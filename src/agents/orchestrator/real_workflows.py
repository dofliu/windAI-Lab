"""WindAI Lab 真實資料工作流程。

使用代理框架（BaseAgent）協調真實的 Kelmarsh SCADA 資料分析。
各步驟委派至已註冊的代理實例，由代理自行管理狀態與進度廣播。
"""

from __future__ import annotations

import asyncio
import uuid

from src.agents.base import TaskContext, TaskStatus
from src.api.agent_registry import update_agent_status
from src.api.models import AgentStatus, WorkLogEntry
from src.api.websocket_manager import manager as ws_manager
from src.utils.logger import get_logger

logger = get_logger("orchestrator.real_workflows")


# ── 輔助工具 ─────────────────────────────────────────────────

TURBINE_MAP: dict[str, str] = {
    "WT-01": "Kelmarsh_1",
    "WT-02": "Kelmarsh_2",
    "WT-03": "Kelmarsh_3",
    "WT-04": "Kelmarsh_4",
    "WT-05": "Kelmarsh_5",
    "WT-06": "Kelmarsh_6",
    "Kelmarsh_1": "Kelmarsh_1",
    "Kelmarsh_2": "Kelmarsh_2",
    "Kelmarsh_3": "Kelmarsh_3",
    "Kelmarsh_4": "Kelmarsh_4",
    "Kelmarsh_5": "Kelmarsh_5",
    "Kelmarsh_6": "Kelmarsh_6",
}

PARTICIPATING_AGENTS = [
    "project-director",
    "research-lead",
    "predictive-modeler",
    "fault-diagnostician",
    "literature-reviewer",
    "paper-writer",
]


async def _broadcast_log(
    agent_id: str, agent_name: str, message: str, log_type: str = "info"
) -> None:
    """廣播工作日誌至前端。"""
    entry = WorkLogEntry(
        id=str(uuid.uuid4()),
        agent_id=agent_id,
        agent_name=agent_name,
        message=message,
        type=log_type,
    )
    await ws_manager.broadcast_work_log(entry)


async def _reset_agents() -> None:
    """重設所有參與代理至待命狀態。"""
    await asyncio.sleep(3)
    for aid in PARTICIPATING_AGENTS:
        updated = update_agent_status(
            aid, status=AgentStatus.IDLE, current_task=None, progress=0.0
        )
        if updated:
            await ws_manager.broadcast_agent_status(updated)


# ── 主工作流程 ─────────────────────────────────────────────────


async def run_real_diagnose(turbine_id: str = "Kelmarsh_1") -> dict:
    """執行真實的故障診斷工作流程。

    透過代理框架協調多個代理，使用 Kelmarsh SCADA 真實資料。
    各代理的 execute() 方法處理實際邏輯，自動管理狀態與進度。

    Args:
        turbine_id: 風機 ID（支援 WT-XX 或 Kelmarsh_X 格式）。

    Returns:
        診斷結果字典。
    """
    from src.agents.registry import agent_instances

    data_id = TURBINE_MAP.get(turbine_id, "Kelmarsh_1")
    results: dict = {}

    # ── Step 1: 專案總監確認任務 ──
    director = agent_instances.get("project-director")
    if director:
        ctx = TaskContext(
            parameters={"turbine_id": turbine_id, "data_id": data_id},
            collaborators=["fault-diagnostician", "predictive-modeler"],
        )
        await director.run_task(f"確認 {turbine_id} 風機資訊並分派故障診斷任務", ctx)
        await _broadcast_log(
            "project-director",
            "專案總監",
            "Kelmarsh 風場 — Senvion MM92, 2050 kW, 92m 轉子直徑",
        )
    else:
        await _broadcast_log(
            "project-director",
            "專案總監",
            f"🚀 啟動 {turbine_id} 故障診斷工作流程",
        )

    # ── Step 2-5: 故障診斷師執行完整診斷 ──
    diagnostician = agent_instances.get("fault-diagnostician")
    if diagnostician:
        ctx = TaskContext(
            parameters={"turbine_id": data_id},
            collaborators=["predictive-modeler"],
        )
        diag_result = await diagnostician.run_task(f"診斷 {data_id} 風機故障", ctx)

        if diag_result.status == TaskStatus.SUCCESS:
            results["diagnosis"] = diag_result.data.get("report", {})
            results["quality_report"] = diag_result.data.get("quality_report", {})

            # 廣播關鍵發現
            health = diag_result.data.get("health_score", 0)
            report = diag_result.data.get("report", {})

            temp_anomalies = report.get("temperature_anomalies", [])
            if temp_anomalies:
                await _broadcast_log(
                    "fault-diagnostician",
                    "故障診斷師",
                    f"偵測到 {len(temp_anomalies)} 個溫度異常事件",
                    "warning",
                )

            pc = report.get("power_curve_analysis", {})
            if pc:
                dev = pc.get("mean_deviation_pct", 0)
                await _broadcast_log(
                    "fault-diagnostician",
                    "故障診斷師",
                    f"Power Curve 平均偏差：{dev:.1f}%",
                    "success" if abs(dev) < 5 else "warning",
                )

            ops = report.get("operational_summary", {})
            if ops:
                cf = ops.get("capacity_factor", 0)
                avail = ops.get("availability", 0)
                await _broadcast_log(
                    "fault-diagnostician",
                    "故障診斷師",
                    f"容量因數：{cf:.1f}%, 可用率：{avail:.1f}%",
                )
        else:
            results["diagnosis"] = {"error": "; ".join(diag_result.errors)}
    else:
        logger.warning("fault-diagnostician 代理未註冊，跳過診斷")

    # ── Step 6: 文獻佐證 ──
    lit_reviewer = agent_instances.get("literature-reviewer")
    if lit_reviewer:
        ctx = TaskContext(
            parameters={"topic": f"Senvion MM92 {turbine_id} fault diagnosis"},
        )
        lit_result = await lit_reviewer.run_task("搜索相關故障案例文獻", ctx)
        results["literature"] = lit_result.data
    else:
        logger.warning("literature-reviewer 代理未註冊，跳過文獻搜索")

    # ── Step 7: 生成報告 ──
    paper_writer = agent_instances.get("paper-writer")
    if paper_writer:
        ctx = TaskContext(
            parameters={"turbine_id": turbine_id},
            results=results,
        )
        report_result = await paper_writer.run_task("生成診斷報告", ctx)

        # 廣播警告與建議
        diagnosis = results.get("diagnosis", {})
        for w in diagnosis.get("warnings", [])[:3]:
            await _broadcast_log("paper-writer", "論文撰寫員", f"⚠️ {w}", "warning")
            await asyncio.sleep(0.3)
        for r in diagnosis.get("recommendations", [])[:3]:
            await _broadcast_log("paper-writer", "論文撰寫員", f"💡 建議：{r}", "info")
            await asyncio.sleep(0.3)

        results["report"] = report_result.data
    else:
        logger.warning("paper-writer 代理未註冊，跳過報告生成")

    # ── Step 8: 最終審核 ──
    research_lead = agent_instances.get("research-lead")
    if research_lead:
        ctx = TaskContext(results=results)
        await research_lead.run_task("審核診斷報告", ctx)

    # 專案總監最終確認
    health = results.get("diagnosis", {}).get("health_score", 0)
    await _broadcast_log(
        "project-director",
        "專案總監",
        f"📋 {turbine_id} 故障診斷完成 — 健康分數 {health}/100",
        "success",
    )

    # 重設代理
    await _reset_agents()

    return results
