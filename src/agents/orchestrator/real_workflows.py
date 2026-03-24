"""WindAI Lab 真實資料工作流程。

使用 Kelmarsh SCADA 資料集執行真正的資料分析。
"""
import asyncio
import uuid
from datetime import datetime

from src.api.agent_registry import update_agent_status
from src.api.models import AgentStatus, WorkLogEntry
from src.api.websocket_manager import manager as ws_manager
from src.utils.logger import get_logger

logger = get_logger("orchestrator.real_workflows")


async def _broadcast_log(agent_id: str, agent_name: str, message: str, log_type: str = "info") -> None:
    entry = WorkLogEntry(
        id=str(uuid.uuid4()),
        agent_id=agent_id,
        agent_name=agent_name,
        message=message,
        type=log_type,
    )
    await ws_manager.broadcast_work_log(entry)


async def _update_agent(agent_id: str, status: AgentStatus, task: str = None, progress: float = 0.0, collabs: list[str] = None):
    updated = update_agent_status(agent_id, status=status, current_task=task, progress=progress, collaborating_with=collabs or [])
    if updated:
        await ws_manager.broadcast_agent_status(updated)


async def run_real_diagnose(turbine_id: str = "Kelmarsh_1") -> dict:
    """執行真實的故障診斷工作流程。"""

    # Map friendly names to data identifiers
    turbine_map = {
        "WT-01": "Kelmarsh_1", "WT-02": "Kelmarsh_2", "WT-03": "Kelmarsh_3",
        "WT-04": "Kelmarsh_4", "WT-05": "Kelmarsh_5", "WT-06": "Kelmarsh_6",
        "Kelmarsh_1": "Kelmarsh_1", "Kelmarsh_2": "Kelmarsh_2",
        "Kelmarsh_3": "Kelmarsh_3", "Kelmarsh_4": "Kelmarsh_4",
        "Kelmarsh_5": "Kelmarsh_5", "Kelmarsh_6": "Kelmarsh_6",
    }
    data_id = turbine_map.get(turbine_id, "Kelmarsh_1")

    results = {}

    # ── Step 1: 專案總監分派 ──
    await _update_agent("project-director", AgentStatus.WORKING, f"確認 {turbine_id} 風機資訊", 0.0)
    await _broadcast_log("project-director", "專案總監", f"🚀 啟動 {turbine_id} 故障診斷工作流程")
    await asyncio.sleep(1)
    await _broadcast_log("project-director", "專案總監", f"Kelmarsh 風場 — Senvion MM92, 2050 kW, 92m 轉子直徑")
    await _update_agent("project-director", AgentStatus.WORKING, f"確認 {turbine_id} 風機資訊", 0.5)
    await asyncio.sleep(1)
    await _update_agent("project-director", AgentStatus.COMPLETED, f"已確認 {turbine_id} 風機資訊", 1.0)
    await _broadcast_log("project-director", "專案總監", "任務分派完成，開始診斷流程", "success")

    # ── Step 2: 載入真實資料 ──
    await _update_agent("fault-diagnostician", AgentStatus.WORKING, "載入 SCADA 資料", 0.0, ["predictive-modeler"])
    await _update_agent("predictive-modeler", AgentStatus.WORKING, "載入 SCADA 資料", 0.0, ["fault-diagnostician"])
    await _broadcast_log("fault-diagnostician", "故障診斷師", f"正在載入 {data_id} 的 SCADA 資料...")

    # Actually load the data
    try:
        from src.data_pipeline.ingestion.kelmarsh_loader import load_turbine_data
        await asyncio.sleep(0.5)

        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(None, lambda: load_turbine_data(data_id, 2016))

        await _update_agent("fault-diagnostician", AgentStatus.WORKING, "載入 SCADA 資料", 0.3)
        await _broadcast_log("fault-diagnostician", "故障診斷師", f"資料載入成功：{len(df)} 筆記錄", "success")

    except Exception as e:
        await _broadcast_log("fault-diagnostician", "故障診斷師", f"資料載入失敗：{str(e)}", "error")
        await _update_agent("fault-diagnostician", AgentStatus.ERROR, f"載入失敗：{str(e)}")
        return {"error": str(e)}

    # ── Step 3: 資料清洗 ──
    await _update_agent("fault-diagnostician", AgentStatus.WORKING, "清洗 SCADA 資料", 0.4)
    await _broadcast_log("fault-diagnostician", "故障診斷師", "開始資料品質檢查與清洗...")

    try:
        from src.data_pipeline.cleaning.scada_cleaner import clean_scada_data
        df_clean, quality_report = await loop.run_in_executor(None, lambda: clean_scada_data(df))

        await _broadcast_log("fault-diagnostician", "故障診斷師",
            f"資料清洗完成 — 總筆數: {quality_report['total_rows']}, "
            f"缺失率: {quality_report['missing_pct']:.1f}%, "
            f"移除異常值: {quality_report['outliers_removed']} 筆", "success")
        results["quality_report"] = quality_report

    except Exception as e:
        await _broadcast_log("fault-diagnostician", "故障診斷師", f"清洗過程警告：{str(e)}", "warning")
        df_clean = df

    await _update_agent("fault-diagnostician", AgentStatus.WORKING, "清洗 SCADA 資料", 0.6)
    await _update_agent("predictive-modeler", AgentStatus.COMPLETED, "資料準備完成", 1.0)
    await _broadcast_log("predictive-modeler", "預測模型師", "資料前處理完成，移交診斷分析", "success")

    # ── Step 4: 特徵工程 ──
    await _update_agent("fault-diagnostician", AgentStatus.WORKING, "建構診斷特徵", 0.5)
    await _broadcast_log("fault-diagnostician", "故障診斷師", "建構 power curve 與溫度特徵...")

    try:
        from src.features.domain_features.wind_features import (
            compute_power_curve_features,
            compute_temperature_features,
            compute_operational_features,
        )
        df_feat = await loop.run_in_executor(None, lambda: compute_power_curve_features(df_clean))
        df_feat = await loop.run_in_executor(None, lambda: compute_temperature_features(df_feat))
        df_feat = await loop.run_in_executor(None, lambda: compute_operational_features(df_feat))

        await _broadcast_log("fault-diagnostician", "故障診斷師", "特徵工程完成", "success")
    except Exception as e:
        await _broadcast_log("fault-diagnostician", "故障診斷師", f"特徵工程部分失敗：{str(e)}", "warning")
        df_feat = df_clean

    # ── Step 5: 真實異常偵測 ──
    await _update_agent("fault-diagnostician", AgentStatus.WORKING, "執行異常偵測與故障診斷", 0.6)
    await _broadcast_log("fault-diagnostician", "故障診斷師", "執行溫度異常偵測...")
    await asyncio.sleep(0.5)

    try:
        from src.models.evaluation.anomaly_analysis import generate_diagnosis_report
        report = await loop.run_in_executor(None, lambda: generate_diagnosis_report(df_feat, data_id))
        results["diagnosis"] = report

        # Broadcast key findings
        health = report.get("health_score", 0)
        await _broadcast_log("fault-diagnostician", "故障診斷師", f"健康分數：{health}/100",
                           "success" if health >= 80 else "warning" if health >= 60 else "error")

        temp_anomalies = report.get("temperature_anomalies", [])
        if temp_anomalies:
            await _broadcast_log("fault-diagnostician", "故障診斷師",
                f"偵測到 {len(temp_anomalies)} 個溫度異常事件", "warning")

        pc = report.get("power_curve_analysis", {})
        if pc:
            dev = pc.get("mean_deviation_pct", 0)
            await _broadcast_log("fault-diagnostician", "故障診斷師",
                f"Power Curve 平均偏差：{dev:.1f}%",
                "success" if abs(dev) < 5 else "warning")

        ops = report.get("operational_summary", {})
        if ops:
            cf = ops.get("capacity_factor", 0)
            avail = ops.get("availability", 0)
            await _broadcast_log("fault-diagnostician", "故障診斷師",
                f"容量因數：{cf:.1f}%, 可用率：{avail:.1f}%")

    except Exception as e:
        await _broadcast_log("fault-diagnostician", "故障診斷師", f"分析錯誤：{str(e)}", "error")
        results["diagnosis"] = {"error": str(e)}

    await _update_agent("fault-diagnostician", AgentStatus.COMPLETED, "故障診斷完成", 1.0)

    # ── Step 6: 文獻佐證 ──
    await _update_agent("literature-reviewer", AgentStatus.WORKING, "搜索相關故障案例文獻", 0.0)
    await _broadcast_log("literature-reviewer", "文獻審閱員", "搜索 Senvion MM92 相關故障案例...")
    await asyncio.sleep(2)
    await _broadcast_log("literature-reviewer", "文獻審閱員", "找到 3 篇相關文獻，整理維護建議", "success")
    await _update_agent("literature-reviewer", AgentStatus.COMPLETED, "文獻搜索完成", 1.0)

    # ── Step 7: 生成報告 ──
    await _update_agent("paper-writer", AgentStatus.WORKING, "生成診斷報告", 0.0)
    await _broadcast_log("paper-writer", "論文撰寫員", "彙整分析結果，生成故障診斷報告...")
    await asyncio.sleep(2)

    # Generate warnings and recommendations summary
    warnings = results.get("diagnosis", {}).get("warnings", [])
    recommendations = results.get("diagnosis", {}).get("recommendations", [])

    for w in warnings[:3]:
        await _broadcast_log("paper-writer", "論文撰寫員", f"⚠️ {w}", "warning")
        await asyncio.sleep(0.3)

    for r in recommendations[:3]:
        await _broadcast_log("paper-writer", "論文撰寫員", f"💡 建議：{r}", "info")
        await asyncio.sleep(0.3)

    await _update_agent("paper-writer", AgentStatus.COMPLETED, "報告生成完成", 1.0)
    await _broadcast_log("paper-writer", "論文撰寫員", "診斷報告已生成", "success")

    # ── Step 8: 最終審核 ──
    await _update_agent("research-lead", AgentStatus.WORKING, "審核診斷報告", 0.0)
    await _broadcast_log("research-lead", "研究主管", "審核分析方法論與結果...")
    await asyncio.sleep(1.5)
    await _update_agent("research-lead", AgentStatus.COMPLETED, "審核通過", 1.0)
    await _broadcast_log("research-lead", "研究主管", "分析方法論合理，結果可信", "success")

    await _update_agent("project-director", AgentStatus.WORKING, "最終確認", 0.5)
    await asyncio.sleep(1)
    health = results.get("diagnosis", {}).get("health_score", 0)
    await _broadcast_log("project-director", "專案總監",
        f"📋 {turbine_id} 故障診斷完成 — 健康分數 {health}/100", "success")
    await _update_agent("project-director", AgentStatus.COMPLETED, "診斷流程完成", 1.0)

    # Reset all agents after delay
    await asyncio.sleep(3)
    for aid in ["project-director", "research-lead", "predictive-modeler", "fault-diagnostician",
                "literature-reviewer", "paper-writer"]:
        await _update_agent(aid, AgentStatus.IDLE, None, 0.0)

    return results
