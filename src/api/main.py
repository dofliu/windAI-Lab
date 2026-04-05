"""WindAI Lab FastAPI 主應用程式。

提供 REST API 端點與 WebSocket 即時通訊，作為前端儀表板與後端代理系統之間的橋樑。
支援代理狀態查詢、任務調用、工作日誌取得及即時狀態推播。
"""

from __future__ import annotations

import math
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.agents.orchestrator.engine import engine as orchestration_engine
from src.agents.orchestrator.workflows import AVAILABLE_WORKFLOWS
from src.api.agent_registry import get_agent, get_all_agents, update_agent_status
from src.api.models import (
    AddWorkOrderNoteRequest,
    AgentModel,
    AgentStatus,
    AlertIngestRequest,
    CreateAlertRequest,
    CreateWorkOrderRequest,
    InvokeRequest,
    InvokeResponse,
    UpdateAlertRequest,
    UpdateWorkOrderRequest,
    WorkLogEntry,
)
from src.api.websocket_manager import manager as ws_manager
from src.utils.logger import get_logger

logger = get_logger("api.main")

# 工作日誌記憶體儲存（後續可替換為資料庫）
_work_logs: list[WorkLogEntry] = []

# 檔案監控服務全域實例
_file_watcher: Any = None


async def _auto_dispatch_workflow(turbine_id: str, event: Any) -> None:
    """檔案偵測後自動派任代理工作流程。

    根據偵測到的欄位自動選擇合適的工作流程：
    - 有 wind_speed + power → 資料清洗 + 功率曲線分析
    - 有 generator_temp / vibration → 故障診斷
    - 其他 → 基本資料載入 + 特徵探索
    """
    from src.agents.orchestrator.engine import engine as orch_engine
    from src.agents.orchestrator.workflows import (
        create_data_clean_workflow,
        create_data_load_workflow,
    )

    detected = event.detected_fields or {}
    has_wind_power = "wind_speed" in detected and "power" in detected

    try:
        if has_wind_power:
            # 有風速+功率 → 執行完整資料清洗流程
            workflow = create_data_clean_workflow(turbine_id)
            logger.info(f"自動派任資料清洗工作流程：{turbine_id}")
        else:
            # 只做基本資料載入+特徵探索
            workflow = create_data_load_workflow(turbine_id)
            logger.info(f"自動派任資料載入工作流程：{turbine_id}")

        await orch_engine.run_workflow_background(workflow)
    except Exception as e:
        logger.error(f"自動派任工作流程失敗：{e}")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """應用程式生命週期管理：啟動與關閉時的初始化與清理。"""
    from src.agents.dynamic_registry import dynamic_registry
    from src.api.agent_registry import enable_dynamic_registry

    logger.info("WindAI Lab API 啟動中...")

    # ═══ 持久化資料庫初始化 ═══
    try:
        from src.core.database import get_database

        db = get_database()
        db.initialize()
        logger.info("資料庫已就緒")
    except Exception as exc:
        logger.warning(f"資料庫初始化失敗（將以記憶體模式運行）：{exc}")

    # ═══ 新架構：YAML + 技能 + 聘用制 ═══
    spec_count = dynamic_registry.load_specs()
    core_count = dynamic_registry.bootstrap_core()
    enable_dynamic_registry()  # 切換主資料來源
    logger.info(
        f"代理系統已啟動：{spec_count} 定義，{core_count} 核心代理，"
        f"{spec_count - core_count} 可聘用"
    )

    # 啟動檔案監控服務
    from src.services.file_watcher import FileWatcherService

    global _file_watcher  # noqa: PLW0603
    _file_watcher = FileWatcherService()
    _file_watcher.set_broadcast(ws_manager.broadcast_file_event)
    _file_watcher.set_workflow_dispatcher(_auto_dispatch_workflow)
    await _file_watcher.start()
    logger.info("FileWatcher 已啟動")

    yield

    # 關閉檔案監控
    if _file_watcher:
        await _file_watcher.stop()
    logger.info("WindAI Lab API 正在關閉...")


app = FastAPI(
    title="WindAI Lab API",
    description="風能人工智慧研究平台 API — 多代理協作系統後端服務",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 中介層設定：允許 Vite 開發伺服器跨域存取
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 資料夾批次載入背景任務 ────────────────────────────────────────


async def _run_folder_load(folder_path: str, ws_mgr: Any) -> None:
    """透過 DataInspectorSkill + BatchLoadSkill 載入整個資料夾。"""
    import traceback
    from pathlib import Path

    try:
        from src.skills.base import SkillInput
        from src.skills.data.batch_load import BatchLoadSkill
        from src.skills.data.data_inspector import DataInspectorSkill

        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            await ws_mgr.broadcast(
                {
                    "type": "work_log_entry",
                    "timestamp": datetime.now().isoformat(),
                    "payload": {
                        "id": str(uuid.uuid4()),
                        "agent_id": "system",
                        "agent_name": "WindAI Lab",
                        "message": f"資料夾不存在或不是目錄：{folder_path}",
                        "type": "error",
                    },
                }
            )
            return

        # Step 1: DataInspector 掃描資料夾
        inspector = DataInspectorSkill()
        inspect_input = SkillInput(parameters={"folder_path": folder_path})
        inspect_result = await inspector.execute(inspect_input)

        await ws_mgr.broadcast(
            {
                "type": "work_log_entry",
                "timestamp": datetime.now().isoformat(),
                "payload": {
                    "id": str(uuid.uuid4()),
                    "agent_id": "scada-processor",
                    "agent_name": "SCADA 資料工程師",
                    "message": f"資料夾掃描完成，策略：{inspect_result.data.get('strategy', 'unknown')}",
                    "type": "info",
                },
            }
        )

        # Step 2: BatchLoad 執行載入
        loader = BatchLoadSkill()
        load_input = SkillInput(
            parameters={
                "folder_path": folder_path,
                "strategy": inspect_result.data.get("strategy", "direct_concat"),
            },
            context={"data": inspect_result.data},
        )
        load_result = await loader.execute(load_input)

        file_count = load_result.data.get("files_loaded", 0)
        total_rows = load_result.data.get("total_rows", 0)
        await ws_mgr.broadcast(
            {
                "type": "work_log_entry",
                "timestamp": datetime.now().isoformat(),
                "payload": {
                    "id": str(uuid.uuid4()),
                    "agent_id": "scada-processor",
                    "agent_name": "SCADA 資料工程師",
                    "message": f"批次載入完成：{file_count} 檔案，共 {total_rows} 筆資料",
                    "type": "success",
                },
            }
        )

        # 推送結果圖表
        if load_result.data.get("column_summary"):
            await ws_mgr.broadcast(
                {
                    "type": "analysis_result",
                    "timestamp": datetime.now().isoformat(),
                    "payload": {
                        "chart_type": "bar",
                        "title": f"資料夾載入結果（{file_count} 檔案）",
                        "data": [
                            {"name": k, "value": v}
                            for k, v in list(load_result.data.get("column_summary", {}).items())[
                                :15
                            ]
                        ],
                        "metadata": {
                            "files_loaded": file_count,
                            "total_rows": total_rows,
                            "strategy": inspect_result.data.get("strategy", "unknown"),
                        },
                    },
                }
            )

    except Exception as e:
        logger.error(f"資料夾載入失敗：{e}\n{traceback.format_exc()}")
        await ws_mgr.broadcast(
            {
                "type": "work_log_entry",
                "timestamp": datetime.now().isoformat(),
                "payload": {
                    "id": str(uuid.uuid4()),
                    "agent_id": "system",
                    "agent_name": "WindAI Lab",
                    "message": f"資料夾載入失敗：{e}",
                    "type": "error",
                },
            }
        )


# ── RAG 知識庫嵌入背景任務 ──────────────────────────────────────


async def _run_rag_ingest(folder_path: str, ws_mgr: Any) -> None:
    """透過 RagDocumentScannerSkill + RagIngestSkill 嵌入整個資料夾。"""
    import traceback

    try:
        from src.skills.base import SkillInput
        from src.skills.rag.rag_document_scanner import RagDocumentScannerSkill
        from src.skills.rag.rag_ingest import RagIngestSkill

        # Step 1: 掃描文件
        scanner = RagDocumentScannerSkill()
        scan_result = await scanner.execute(SkillInput(parameters={"folder_path": folder_path}))

        await ws_mgr.broadcast(
            {
                "type": "work_log_entry",
                "timestamp": datetime.now().isoformat(),
                "payload": {
                    "id": str(uuid.uuid4()),
                    "agent_id": "rag-architect",
                    "agent_name": "RAG 架構師",
                    "message": scan_result.summary,
                    "type": "info",
                },
            }
        )

        if scan_result.status.value == "error":
            return

        # Step 2: 嵌入文件
        async def _progress(pct: float, msg: str) -> None:
            await ws_mgr.broadcast(
                {
                    "type": "work_log_entry",
                    "timestamp": datetime.now().isoformat(),
                    "payload": {
                        "id": str(uuid.uuid4()),
                        "agent_id": "rag-architect",
                        "agent_name": "RAG 架構師",
                        "message": msg,
                        "type": "info",
                    },
                }
            )

        ingester = RagIngestSkill()
        ingest_input = SkillInput(
            parameters={"folder_path": folder_path},
            context={"data": scan_result.data},
        )
        ingest_result = await ingester.execute(ingest_input, progress_cb=_progress)

        # 推送最終結果圖表
        ingested = ingest_result.data.get("ingested", 0)
        errors_count = ingest_result.data.get("errors_count", 0)
        total_in_col = ingest_result.data.get("total_in_collection", 0)

        await ws_mgr.broadcast(
            {
                "type": "work_log_entry",
                "timestamp": datetime.now().isoformat(),
                "payload": {
                    "id": str(uuid.uuid4()),
                    "agent_id": "rag-architect",
                    "agent_name": "RAG 架構師",
                    "message": ingest_result.summary,
                    "type": "success",
                },
            }
        )

        await ws_mgr.broadcast(
            {
                "type": "analysis_result",
                "timestamp": datetime.now().isoformat(),
                "payload": {
                    "chart_type": "bar",
                    "title": f"RAG 知識庫嵌入完成（{ingested} 份文件）",
                    "data": [
                        {"name": "已嵌入", "value": ingested},
                        {"name": "失敗", "value": errors_count},
                        {"name": "知識庫總量", "value": total_in_col},
                    ],
                    "metadata": ingest_result.data,
                },
            }
        )

    except Exception as e:
        logger.error(f"RAG 資料夾嵌入失敗：{e}\n{traceback.format_exc()}")
        await ws_mgr.broadcast(
            {
                "type": "work_log_entry",
                "timestamp": datetime.now().isoformat(),
                "payload": {
                    "id": str(uuid.uuid4()),
                    "agent_id": "rag-architect",
                    "agent_name": "RAG 架構師",
                    "message": f"RAG 嵌入失敗：{e}",
                    "type": "error",
                },
            }
        )


# ── 專案上線背景任務 ────────────────────────────────────────────


async def _run_project_onboard(folder_path: str, ws_mgr: Any) -> None:
    """專案一鍵上線：LLM 分類 → 平行 RAG + 資料載入 → 規格萃取。"""
    import asyncio
    import traceback

    async def _log(agent_id: str, agent_name: str, message: str, log_type: str = "info") -> None:
        await ws_mgr.broadcast(
            {
                "type": "work_log_entry",
                "timestamp": datetime.now().isoformat(),
                "payload": {
                    "id": str(uuid.uuid4()),
                    "agent_id": agent_id,
                    "agent_name": agent_name,
                    "message": message,
                    "type": log_type,
                },
            }
        )

    async def _set_agent_status(
        agent_id: str, status: str, task: str = "", progress: float = 0.0
    ) -> None:
        """廣播 agent 狀態變更，讓前端戰情中心能感知。"""
        from src.api.agent_registry import update_agent_status

        updated = update_agent_status(
            agent_id, status=status, current_task=task, progress=progress
        )
        if updated:
            await ws_mgr.broadcast_agent_status(updated)

    try:
        from src.skills.base import SkillInput

        # ═══ Step 1: LLM 智能檔案分類 ═══
        await _set_agent_status("project-director", "working", "專案檔案分類", 0.1)
        await _log("wLab:director", "專案總監", f"開始分析專案資料夾：{folder_path}")

        from src.skills.data.project_classifier import ProjectClassifierSkill

        classifier = ProjectClassifierSkill()
        classify_result = await classifier.execute(
            SkillInput(parameters={"folder_path": folder_path}),
        )

        await _log("wLab:director", "專案總監", classify_result.summary)

        if classify_result.status.value == "error":
            await _log("wLab:director", "專案總監", f"分類失敗：{classify_result.errors}", "error")
            return

        data_files = classify_result.data.get("data_files", [])
        documents = classify_result.data.get("documents", [])
        other_files = classify_result.data.get("other", [])

        # 廣播分類結果圖表
        await ws_mgr.broadcast(
            {
                "type": "analysis_result",
                "timestamp": datetime.now().isoformat(),
                "payload": {
                    "chart_type": "bar",
                    "title": "專案檔案分類結果",
                    "data": [
                        {"name": "SCADA 資料", "value": len(data_files)},
                        {"name": "技術文件", "value": len(documents)},
                        {"name": "其他", "value": len(other_files)},
                    ],
                    "metadata": {"folder": folder_path},
                },
            }
        )

        # ═══ Step 2: 平行分派 RAG + 資料載入 ═══
        rag_result_holder: dict[str, Any] = {}
        data_result_holder: dict[str, Any] = {}

        async def _ingest_documents() -> None:
            """RAG 嵌入文件。"""
            if not documents:
                await _log("rag-architect", "RAG 架構師", "無技術文件需嵌入")
                return

            await _log("rag-architect", "RAG 架構師", f"開始嵌入 {len(documents)} 份文件...")

            from src.skills.rag.rag_ingest import RagIngestSkill

            ingester = RagIngestSkill()
            doc_files = [
                {"path": d["path"], "name": d["name"], "type": d.get("extension", "")}
                for d in documents
            ]

            async def _rag_progress(pct: float, msg: str) -> None:
                await _log("rag-architect", "RAG 架構師", msg)

            result = await ingester.execute(
                SkillInput(
                    parameters={"folder_path": folder_path},
                    context={"data": {"files": doc_files}},
                ),
                progress_cb=_rag_progress,
            )
            rag_result_holder.update(result.data)
            await _log("rag-architect", "RAG 架構師", result.summary, "success")

        async def _load_data() -> None:
            """載入 SCADA 資料（僅記錄統計，不做完整載入以避免卡死）。"""
            if not data_files:
                await _log("scada-processor", "SCADA 資料工程師", "無 SCADA 資料檔案")
                return

            total = len(data_files)
            await _log("scada-processor", "SCADA 資料工程師", f"發現 {total} 份 SCADA 資料檔案")
            await _set_agent_status("scada-processor", "working", f"分析 {total} 份資料", 0.1)

            # 不逐一載入所有檔案（14000+ 會卡死），只抽樣分析
            from pathlib import Path as _Path

            import pandas as pd

            sample_size = min(5, total)
            sample_files = data_files[:sample_size]
            total_rows = 0
            columns_found: set[str] = set()
            file_sizes: list[int] = []

            for i, f_info in enumerate(sample_files):
                try:
                    fpath = _Path(f_info["path"])
                    ext = f_info.get("extension", fpath.suffix.lower())
                    file_sizes.append(f_info.get("size_bytes", 0))

                    if ext in (".csv", ".tsv"):
                        df = pd.read_csv(fpath, nrows=5, on_bad_lines="skip")
                    elif ext in (".xlsx", ".xls"):
                        df = pd.read_excel(fpath, nrows=5)
                    elif ext == ".parquet":
                        df = pd.read_parquet(fpath)
                    else:
                        continue

                    columns_found.update(df.columns.tolist())
                    # 粗估行數
                    if ext == ".csv":
                        with open(fpath, encoding="utf-8", errors="ignore") as fh:
                            line_count = sum(1 for _ in fh) - 1
                        total_rows += line_count
                    else:
                        total_rows += len(df)
                except Exception:
                    pass

                pct = 0.1 + 0.8 * (i + 1) / sample_size
                await _set_agent_status(
                    "scada-processor", "working", f"抽樣分析 {i + 1}/{sample_size}", pct
                )

            # 推估全量
            if sample_size > 0 and total_rows > 0:
                estimated_total = int(total_rows / sample_size * total)
            else:
                estimated_total = 0

            avg_size = sum(file_sizes) / len(file_sizes) if file_sizes else 0
            total_size_mb = avg_size * total / (1024 * 1024)

            data_result_holder.update(
                {
                    "files_found": total,
                    "sample_analyzed": sample_size,
                    "estimated_rows": estimated_total,
                    "columns": sorted(columns_found),
                    "estimated_size_mb": round(total_size_mb, 1),
                }
            )

            await _set_agent_status("scada-processor", "working", "分析完成", 1.0)
            await _log(
                "scada-processor",
                "SCADA 資料工程師",
                f"分析完成：{total} 檔案, 預估 {estimated_total:,} 筆, "
                f"約 {total_size_mb:.0f} MB, {len(columns_found)} 個欄位",
                "success",
            )

        # 平行執行
        await _set_agent_status("project-director", "working", "平行分派", 0.3)
        await _log("wLab:director", "專案總監", "平行分派：RAG 架構師 + SCADA 資料工程師")
        if documents:
            await _set_agent_status("rag-architect", "working", "RAG 嵌入", 0.0)
        if data_files:
            await _set_agent_status("scada-processor", "working", "資料分析", 0.0)
        results = await asyncio.gather(
            _ingest_documents(),
            _load_data(),
            return_exceptions=True,
        )
        # 檢查並回報任何例外
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                task_name = ["RAG 嵌入", "SCADA 資料載入"][i]
                await _log("wLab:director", "專案總監", f"{task_name} 發生錯誤：{r}", "error")
                logger.error(f"project:onboard {task_name} 錯誤：{r}")

        # ═══ Step 3: 從 RAG 萃取風機規格 ═══
        specs: dict[str, Any] = {}
        if documents:
            await _log("rag-architect", "RAG 架構師", "從知識庫萃取風機規格...")

            # 從資料夾名稱猜測風機型號
            from pathlib import Path as _Path

            from src.skills.rag.turbine_spec_extractor import TurbineSpecExtractorSkill

            turbine_hint = _Path(folder_path).name

            spec_skill = TurbineSpecExtractorSkill()
            spec_result = await spec_skill.execute(
                SkillInput(parameters={"turbine_hint": turbine_hint}),
            )
            specs = spec_result.data.get("turbine_specs", {})
            await _log("rag-architect", "RAG 架構師", spec_result.summary, "success")

        # ═══ Step 4: 統一摘要 ═══
        docs_ingested = rag_result_holder.get("ingested", 0)
        estimated_rows = data_result_holder.get("estimated_rows", 0)
        data_files_count = data_result_holder.get("files_found", 0)
        specs_found = sum(1 for v in specs.values() if v is not None)

        await ws_mgr.broadcast(
            {
                "type": "analysis_result",
                "timestamp": datetime.now().isoformat(),
                "payload": {
                    "chart_type": "bar",
                    "title": f"專案上線完成：{_Path(folder_path).name}",
                    "data": [
                        {"name": "文件已嵌入", "value": docs_ingested},
                        {"name": "SCADA 檔案", "value": data_files_count},
                        {"name": "預估資料筆數", "value": estimated_rows},
                        {"name": "規格已萃取", "value": specs_found},
                    ],
                    "metadata": {
                        "turbine_specs": specs,
                        "classification": classify_result.data,
                        "data_columns": data_result_holder.get("columns", []),
                        "folder": folder_path,
                    },
                },
            }
        )

        summary_parts = []
        if docs_ingested:
            summary_parts.append(f"{docs_ingested} 份文件嵌入")
        if data_files_count:
            summary_parts.append(f"{data_files_count} 份 SCADA 資料（約 {estimated_rows:,} 筆）")
        if specs_found:
            summary_parts.append(f"{specs_found} 項規格萃取")

        await _log(
            "wLab:director",
            "專案總監",
            f"專案上線完成：{', '.join(summary_parts)}",
            "success",
        )

        # 重置所有參與的 agent 狀態
        for aid in ["project-director", "rag-architect", "scada-processor"]:
            await _set_agent_status(aid, "idle", "", 0.0)

    except Exception as e:
        logger.error(f"專案上線失敗：{e}\n{traceback.format_exc()}")
        await _log("wLab:director", "專案總監", f"專案上線失敗：{e}", "error")
        for aid in ["project-director", "rag-architect", "scada-processor"]:
            await _set_agent_status(aid, "idle", "", 0.0)


# ── WebSocket 端點 ──────────────────────────────────────────────


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket 連線端點，用於即時推播代理狀態更新。

    連線建立後會立即傳送所有代理的當前狀態。
    """
    await ws_manager.connect(websocket)
    logger.info(f"WebSocket 客戶端已連線，目前連線數：{ws_manager.active_count}")

    try:
        # 連線時傳送所有代理的當前狀態
        agents = get_all_agents()
        await ws_manager.send_personal(
            websocket,
            {
                "type": "initial_state",
                "timestamp": datetime.now().isoformat(),
                "payload": {
                    "agents": [a.model_dump(mode="json") for a in agents],
                },
            },
        )

        # 持續監聽客戶端訊息
        while True:
            data = await websocket.receive_json()
            logger.debug(f"收到 WebSocket 訊息：{data}")

            # 處理前端發送的指令
            if data.get("type") == "execute_command":
                command_name = data.get("command", "")
                parameters = data.get("parameters", {})

                # ═══ 特殊指令：非 workflow 類（保留獨立處理） ═══
                if command_name == "data:folder":
                    import asyncio as _aio

                    folder_path = parameters.get("folder_path", "")
                    if folder_path:
                        _aio.create_task(_run_folder_load(folder_path, ws_manager))
                        await ws_manager.broadcast(
                            {
                                "type": "work_log_entry",
                                "timestamp": datetime.now().isoformat(),
                                "payload": {
                                    "id": str(uuid.uuid4()),
                                    "agent_id": "system",
                                    "agent_name": "WindAI Lab",
                                    "message": f"開始批次載入資料夾：{folder_path}",
                                    "type": "info",
                                },
                            }
                        )

                elif command_name == "rag:ingest":
                    import asyncio as _aio

                    folder_path = parameters.get("folder_path", "")
                    if folder_path:
                        _aio.create_task(_run_rag_ingest(folder_path, ws_manager))
                        await ws_manager.broadcast(
                            {
                                "type": "work_log_entry",
                                "timestamp": datetime.now().isoformat(),
                                "payload": {
                                    "id": str(uuid.uuid4()),
                                    "agent_id": "rag-architect",
                                    "agent_name": "RAG 架構師",
                                    "message": f"開始嵌入資料夾：{folder_path}",
                                    "type": "info",
                                },
                            }
                        )

                elif command_name == "rag:search":
                    import asyncio as _aio

                    query = parameters.get("query", "")
                    if query:

                        async def _run_rag_ask(q: str) -> None:
                            try:
                                await ws_manager.broadcast(
                                    {
                                        "type": "work_log_entry",
                                        "timestamp": datetime.now().isoformat(),
                                        "payload": {
                                            "id": str(uuid.uuid4()),
                                            "agent_id": "rag-architect",
                                            "agent_name": "RAG 架構師",
                                            "message": f"正在搜尋並整理：{q[:50]}...",
                                            "type": "info",
                                        },
                                    }
                                )
                                rag = _get_rag_service()
                                loop = _aio.get_event_loop()
                                result = await loop.run_in_executor(
                                    None, lambda: rag.ask(query=q, n_results=5)
                                )
                                # 推送 LLM 回答
                                await ws_manager.broadcast(
                                    {
                                        "type": "analysis_result",
                                        "timestamp": datetime.now().isoformat(),
                                        "payload": {
                                            "chart_type": "rag_answer",
                                            "title": f"RAG 問答：{q[:40]}",
                                            "data": [
                                                {
                                                    "name": s.get("source", ""),
                                                    "value": round(s.get("relevance", 0) * 100, 1),
                                                }
                                                for s in result.get("sources", [])
                                            ],
                                            "metadata": {
                                                "query": q,
                                                "answer": result.get("answer", ""),
                                                "sources": result.get("sources", []),
                                            },
                                        },
                                    }
                                )
                            except Exception as e:
                                logger.error(f"RAG 問答失敗：{e}")
                                await ws_manager.broadcast(
                                    {
                                        "type": "work_log_entry",
                                        "timestamp": datetime.now().isoformat(),
                                        "payload": {
                                            "id": str(uuid.uuid4()),
                                            "agent_id": "rag-architect",
                                            "agent_name": "RAG 架構師",
                                            "message": f"RAG 問答失敗：{e}",
                                            "type": "error",
                                        },
                                    }
                                )

                        _aio.create_task(_run_rag_ask(query))

                elif command_name == "project:onboard":
                    import asyncio as _aio

                    folder_path = parameters.get("folder_path", "")
                    if folder_path:
                        _aio.create_task(_run_project_onboard(folder_path, ws_manager))

                # ═══ 統一 Workflow 路由 ═══
                elif command_name in AVAILABLE_WORKFLOWS:
                    from src.agents.orchestrator.workflows import extract_workflow_params

                    workflow_factory = AVAILABLE_WORKFLOWS[command_name]
                    wf_params = extract_workflow_params(command_name, parameters)
                    workflow = workflow_factory(**wf_params)
                    await orchestration_engine.run_workflow_background(workflow)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info(f"WebSocket 客戶端已斷線，剩餘連線數：{ws_manager.active_count}")


# ── REST API 端點 ───────────────────────────────────────────────


@app.get("/api/health", tags=["系統"])
async def health_check() -> dict:
    """健康檢查端點，確認服務運行狀態。"""
    return {
        "status": "healthy",
        "service": "WindAI Lab API",
        "version": "0.1.0",
        "timestamp": datetime.now().isoformat(),
        "active_agents": len(get_all_agents()),
        "ws_connections": ws_manager.active_count,
    }


@app.get("/api/agents", response_model=list[AgentModel], tags=["代理管理"])
async def list_agents() -> list[AgentModel]:
    """列出所有代理及其當前狀態。"""
    return get_all_agents()


@app.get("/api/agents/{agent_id}", response_model=AgentModel, tags=["代理管理"])
async def get_agent_detail(agent_id: str) -> AgentModel:
    """取得指定代理的詳細資訊。"""
    agent = get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"代理 '{agent_id}' 不存在")
    return agent


@app.post(
    "/api/agents/{agent_id}/invoke",
    response_model=InvokeResponse,
    tags=["代理管理"],
)
async def invoke_agent(agent_id: str, request: InvokeRequest) -> InvokeResponse:
    """調用指定代理執行任務。

    若代理已註冊邏輯實例，則透過 OrchestrationEngine 呼叫真實 execute()；
    否則僅更新狀態並廣播（向下相容舊行為）。
    """
    import asyncio as _aio

    from src.agents.dynamic_registry import dynamic_registry

    agent = get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"代理 '{agent_id}' 不存在")

    task_id = str(uuid.uuid4())

    # 若有真實代理實例（新/舊系統皆可），使用 engine 的真實執行路徑
    has_instance = dynamic_registry.get_instance(agent_id) is not None
    if has_instance:
        _aio.create_task(
            orchestration_engine.execute_agent_task(
                agent_id=agent_id,
                task=request.command,
                parameters=request.parameters or {},
            )
        )
        logger.info(f"代理 {agent_id} 已啟動真實任務 {task_id}：{request.command}")
        return InvokeResponse(
            task_id=task_id,
            status="accepted",
            message=f"任務已派發給 {agent.display_name}（真實執行）",
        )

    # 未註冊實例：僅更新狀態（向下相容）
    updated_agent = update_agent_status(
        agent_id,
        status=AgentStatus.WORKING,
        current_task=request.command,
        progress=0.0,
    )

    log_entry = WorkLogEntry(
        id=str(uuid.uuid4()),
        agent_id=agent_id,
        agent_name=agent.display_name,
        message=f"開始執行任務：{request.command}",
        type="info",
    )
    _work_logs.append(log_entry)

    if updated_agent:
        await ws_manager.broadcast_agent_status(updated_agent)
    await ws_manager.broadcast_work_log(log_entry)

    logger.info(f"代理 {agent_id} 已接收任務 {task_id}：{request.command}（僅狀態更新）")

    return InvokeResponse(
        task_id=task_id,
        status="accepted",
        message=f"任務已派發給 {agent.display_name}",
    )


# ── 聘用 / 解聘 API ──────────────────────────────────────────────


@app.post("/api/agents/hire", tags=["代理管理"])
async def hire_agent(agent_id: str) -> dict[str, Any]:
    """聘用代理：從可用清單中啟用一個代理。"""
    from src.agents.dynamic_registry import dynamic_registry

    try:
        model = await dynamic_registry.hire(agent_id)
        return {
            "status": "hired",
            "agent": model.model_dump(mode="json"),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/agents/fire", tags=["代理管理"])
async def fire_agent(agent_id: str) -> dict[str, Any]:
    """解聘代理：將代理設為離線狀態（可重新聘用）。"""
    from src.agents.dynamic_registry import dynamic_registry

    try:
        await dynamic_registry.fire(agent_id)
        return {"status": "fired", "agent_id": agent_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/agents/available", tags=["代理管理"])
async def available_agents() -> dict[str, Any]:
    """列出可聘用但尚未啟用的代理。"""
    from src.agents.dynamic_registry import dynamic_registry

    available = dynamic_registry.get_available()
    return {"total": len(available), "agents": available}


@app.get("/api/skills", tags=["技能管理"])
async def list_skills() -> dict[str, Any]:
    """列出所有已註冊的技能模組。"""
    from src.skills.registry import skill_registry

    return {
        "total": skill_registry.count,
        "skills": skill_registry.to_dict_list(),
    }


@app.post("/api/agents/{agent_id}/skills", tags=["代理管理"])
async def update_agent_skills(agent_id: str, skill_ids: list[str]) -> dict[str, Any]:
    """為代理新增技能。"""
    from src.agents.dynamic_registry import dynamic_registry

    try:
        dynamic_registry.upgrade_skills(agent_id, skill_ids)
        spec = dynamic_registry._specs.get(agent_id)
        return {
            "status": "updated",
            "agent_id": agent_id,
            "skills": spec.skills if spec else [],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/logs", response_model=list[WorkLogEntry], tags=["工作日誌"])
async def get_work_logs(limit: int = 50, agent_id: str | None = None) -> list[WorkLogEntry]:
    """取得工作日誌。"""
    logs = _work_logs + orchestration_engine.work_logs
    logs.sort(key=lambda x: x.timestamp)
    if agent_id:
        logs = [log for log in logs if log.agent_id == agent_id]
    return list(reversed(logs[-limit:]))


# ── 任務歷史 API ──────────────────────────────────────────────


@app.get("/api/tasks/history", tags=["任務歷史"])
async def get_task_history(
    limit: int = 20,
    offset: int = 0,
    status: str | None = None,
) -> dict:
    """查詢任務歷史記錄（含分頁）。"""
    try:
        from src.core.database import get_database

        db = get_database()
        tasks = db.list_tasks(limit=limit, offset=offset, status=status)
        total = db.count_tasks(status=status)
        return {
            "tasks": tasks,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        logger.warning(f"查詢任務歷史失敗：{e}")
        return {"tasks": [], "total": 0, "limit": limit, "offset": offset}


@app.get("/api/tasks/{task_id}", tags=["任務歷史"])
async def get_task_detail(task_id: str) -> dict:
    """取得指定任務的詳細資訊（含工作日誌與分析結果）。"""
    try:
        from src.core.database import get_database

        db = get_database()
        task = db.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail=f"任務 '{task_id}' 不存在")
        task["work_logs"] = db.get_task_logs(task_id)
        task["analysis_results"] = db.get_task_results(task_id)
        return task
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/tasks/stats/summary", tags=["任務歷史"])
async def get_task_stats() -> dict:
    """取得任務統計資訊。"""
    try:
        from src.core.database import get_database

        db = get_database()
        return db.get_stats()
    except Exception as e:
        logger.warning(f"查詢統計失敗：{e}")
        return {
            "tasks_total": 0,
            "tasks_completed": 0,
            "tasks_error": 0,
            "work_logs_total": 0,
            "analysis_results_total": 0,
        }


@app.post("/api/commands/{command_name}", tags=["指令執行"])
async def execute_command(command_name: str, parameters: dict[str, Any] | None = None) -> dict:
    """執行指定的 slash 指令，啟動對應的工作流程。"""
    if parameters is None:
        parameters = {}
    if command_name not in AVAILABLE_WORKFLOWS:
        raise HTTPException(
            status_code=404,
            detail=f"指令 '/{command_name}' 不存在。可用指令：{list(AVAILABLE_WORKFLOWS.keys())}",
        )

    from src.agents.orchestrator.workflows import extract_workflow_params

    workflow_factory = AVAILABLE_WORKFLOWS[command_name]
    wf_params = extract_workflow_params(command_name, parameters)
    workflow = workflow_factory(**wf_params)

    task_id = await orchestration_engine.run_workflow_background(workflow)

    return {
        "task_id": task_id,
        "command": command_name,
        "workflow": workflow.name,
        "status": "started",
        "message": f"工作流程「{workflow.name}」已啟動",
    }


@app.get("/api/commands", tags=["指令執行"])
async def list_commands() -> dict:
    """列出所有可用的 slash 指令。"""
    return {
        "commands": [
            {
                "name": "diagnose-real",
                "description": "🔧 故障診斷（技能管線：載入→清洗→特徵→分類）",
                "parameters": ["turbine_id"],
            },
            {
                "name": "train-nbm",
                "description": "📊 NBM 功率曲線訓練（技能管線）",
                "parameters": ["turbine_id"],
            },
            {
                "name": "predict-rul",
                "description": "📈 RUL 壽命預測（技能管線）",
                "parameters": ["turbine_id"],
            },
            {
                "name": "diagnose",
                "description": "故障診斷（模擬動畫）",
                "parameters": ["turbine_id"],
            },
            {
                "name": "data:load",
                "description": "智慧載入 SCADA 資料",
                "parameters": ["turbine_id"],
            },
            {"name": "data:clean", "description": "自動資料清洗", "parameters": ["turbine_id"]},
            {"name": "lit-search", "description": "系統性文獻搜索", "parameters": ["topic"]},
        ]
    }


# ── ML Pipeline API ────────────────────────────────────────────

# 全域 ML Pipeline 實例
_ml_pipeline: Any = None


def _get_ml_pipeline() -> Any:
    """取得或建立 ML Pipeline 單例。"""
    global _ml_pipeline  # noqa: PLW0603
    if _ml_pipeline is None:
        from src.services.ml_pipeline_service import MLPipeline

        _ml_pipeline = MLPipeline()
    return _ml_pipeline


@app.post("/api/ml/train", tags=["ML Pipeline"])
async def ml_train(turbine_id: str = "WT-01") -> JSONResponse:
    """訓練 ML Pipeline（NBM + 故障分類器 + RUL 模型）。

    使用指定風機的 SCADA 資料端到端訓練三個模型。
    """
    import asyncio

    pipeline = _get_ml_pipeline()

    async def _train() -> dict[str, Any]:
        from src.data_pipeline.ingestion.kelmarsh_loader import load_turbine_data

        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(None, lambda: load_turbine_data(turbine_id))
        result = await loop.run_in_executor(None, lambda: pipeline.train_all(df))
        return result

    try:
        result = await _train()
        return JSONResponse(
            content={
                "status": "success",
                "turbine_id": turbine_id,
                "models": result,
            }
        )
    except FileNotFoundError as e:
        return JSONResponse(status_code=404, content={"status": "error", "detail": str(e)})
    except Exception as e:
        logger.exception("ML 訓練失敗")
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})


@app.post("/api/ml/inference", tags=["ML Pipeline"])
async def ml_inference(turbine_id: str = "WT-01") -> JSONResponse:
    """使用已訓練的 ML Pipeline 進行推論。

    需先呼叫 /api/ml/train 完成訓練。
    """
    import asyncio

    pipeline = _get_ml_pipeline()
    if not pipeline.is_trained:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "detail": "Pipeline 尚未訓練，請先呼叫 /api/ml/train"},
        )

    try:
        from src.data_pipeline.ingestion.kelmarsh_loader import load_turbine_data

        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(None, lambda: load_turbine_data(turbine_id))
        result = await loop.run_in_executor(None, lambda: pipeline.run_inference(df, turbine_id))
        return JSONResponse(content={"status": "success", **result})
    except FileNotFoundError as e:
        return JSONResponse(status_code=404, content={"status": "error", "detail": str(e)})
    except Exception as e:
        logger.exception("ML 推論失敗")
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})


@app.get("/api/ml/summary", tags=["ML Pipeline"])
async def ml_summary() -> dict[str, Any]:
    """取得 ML Pipeline 模型摘要。"""
    pipeline = _get_ml_pipeline()
    return pipeline.get_pipeline_summary()


# ── SCADA 資料視覺化 API ──────────────────────────────────────────


def _safe_float(value: Any, decimals: int = 2) -> float | None:
    """將數值安全轉為 JSON 相容的 float，NaN/Inf 回傳 None。"""
    try:
        v = float(value)
        if math.isfinite(v):
            return round(v, decimals)
        return None
    except (TypeError, ValueError):
        return None


@app.get("/api/scada/{turbine_id}/overview", tags=["SCADA 資料"])
async def scada_overview(turbine_id: str = "WT-01", limit: int = 2000) -> JSONResponse:
    """取得指定風機的 SCADA 資料概覽（用於前端圖表視覺化）。

    智慧載入：先嘗試 Kelmarsh 專用 loader，失敗自動切換通用 smart_load，
    無需針對每種資料來源撰寫專用程式碼。
    """
    import asyncio

    # 去除使用者可能輸入的副檔名
    for ext in (".csv", ".parquet", ".xlsx", ".zip"):
        if turbine_id.lower().endswith(ext):
            turbine_id = turbine_id[: -len(ext)]
            break

    try:
        from src.data_pipeline.ingestion.kelmarsh_loader import load_turbine_data
        from src.data_pipeline.ingestion.smart_loader import smart_load

        loop = asyncio.get_event_loop()

        # 智慧載入策略：Kelmarsh → smart_load fallback
        try:
            df = await loop.run_in_executor(None, lambda: load_turbine_data(turbine_id))
        except (FileNotFoundError, ValueError):
            # 在所有資料目錄中搜尋匹配的檔案
            from pathlib import Path as _Path

            data_root = _Path(__file__).resolve().parents[2] / "data"
            df = None
            for sub in ["raw", "external", "processed"]:
                d = data_root / sub
                if not d.exists():
                    continue
                for f in sorted(d.iterdir()):
                    if f.is_file() and turbine_id.lower() in f.stem.lower():
                        df = await loop.run_in_executor(
                            None, lambda fp=f: smart_load(fp, turbine_id=turbine_id)
                        )
                        break
                    if f.suffix.lower() == ".zip":
                        try:
                            df = await loop.run_in_executor(
                                None, lambda fp=f: smart_load(fp, turbine_id=turbine_id)
                            )
                            break
                        except (ValueError, KeyError):
                            continue
                if df is not None:
                    break
            if df is None:
                raise FileNotFoundError(f"找不到風機 '{turbine_id}' 的資料") from None

        # 取樣以控制前端資料量
        df_sample = df.sample(n=limit, random_state=42).sort_index() if len(df) > limit else df

        # 風速-功率散佈圖資料
        scatter_data: list[dict[str, Any]] = []
        ws_col = next((c for c in df_sample.columns if "wind_speed" in c.lower()), None)
        pw_col = next((c for c in df_sample.columns if "power" in c.lower()), None)

        if ws_col and pw_col:
            for _, row in df_sample[[ws_col, pw_col]].dropna().iterrows():
                ws = _safe_float(row[ws_col], 2)
                pw = _safe_float(row[pw_col], 2)
                if ws is not None and pw is not None:
                    scatter_data.append({"windSpeed": ws, "power": pw})

        # 時序趨勢（每日平均）
        ts_col = next(
            (c for c in df.columns if "timestamp" in c.lower() or "time" in c.lower()), None
        )
        trend_data: list[dict[str, Any]] = []
        if ts_col and ws_col and pw_col:
            import pandas as pd

            df_ts = df.copy()
            df_ts[ts_col] = pd.to_datetime(df_ts[ts_col], errors="coerce")
            daily = df_ts.set_index(ts_col)[[ws_col, pw_col]].resample("D").mean().dropna()
            for idx, row in daily.tail(90).iterrows():
                ws = _safe_float(row[ws_col], 2)
                pw = _safe_float(row[pw_col], 2)
                if ws is not None and pw is not None:
                    trend_data.append(
                        {"date": idx.strftime("%Y-%m-%d"), "windSpeed": ws, "power": pw}
                    )

        # 基本統計（NaN 安全）
        stats: dict[str, Any] = {}
        numeric = df.select_dtypes(include=["number"])
        for col in numeric.columns[:10]:
            col_stats = {
                "mean": _safe_float(numeric[col].mean(), 3),
                "std": _safe_float(numeric[col].std(), 3),
                "min": _safe_float(numeric[col].min(), 3),
                "max": _safe_float(numeric[col].max(), 3),
            }
            # 跳過全為 None 的欄位
            if any(v is not None for v in col_stats.values()):
                stats[col] = col_stats

        return JSONResponse(
            content={
                "status": "success",
                "turbine_id": turbine_id,
                "total_records": len(df),
                "scatter": scatter_data[:limit],
                "trend": trend_data,
                "statistics": stats,
            }
        )
    except FileNotFoundError as e:
        return JSONResponse(status_code=404, content={"status": "error", "detail": str(e)})
    except Exception as e:
        logger.exception("SCADA 概覽查詢失敗")
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})


@app.get("/api/scada/turbines", tags=["SCADA 資料"])
async def list_turbines() -> dict[str, Any]:
    """列出可用的風機清單（自動掃描所有資料來源）。"""
    from pathlib import Path

    turbines: list[str] = []
    seen: set[str] = set()
    data_root = Path(__file__).resolve().parents[2] / "data"

    # 掃描 raw/ 目錄的 CSV/Parquet
    for sub in ["raw", "external", "processed"]:
        d = data_root / sub
        if not d.exists():
            continue
        for f in sorted(d.iterdir()):
            if (
                f.is_file()
                and f.suffix.lower() in (".csv", ".parquet", ".xlsx")
                and f.stem not in seen
            ):
                turbines.append(f.stem)
                seen.add(f.stem)

    # 嘗試 Kelmarsh ZIP 自動發現
    try:
        for tid in [f"Kelmarsh_{i}" for i in range(1, 7)]:
            if tid not in seen:
                turbines.append(tid)
                seen.add(tid)
    except Exception:
        if not turbines:
            turbines = [f"Kelmarsh_{i}" for i in range(1, 7)]

    return {"turbines": turbines}


@app.get("/api/scada/discover", tags=["SCADA 資料"])
async def discover_sources() -> dict[str, Any]:
    """智慧掃描所有資料目錄，自動發現並分析可用的資料來源。

    回傳每個檔案的欄位偵測結果，包含：
    - 自動識別的標準欄位（風速、功率等）
    - 資料筆數
    - 是否可用於分析
    """
    import asyncio

    try:
        from src.data_pipeline.ingestion.smart_loader import discover_data_sources

        loop = asyncio.get_event_loop()
        sources = await loop.run_in_executor(None, discover_data_sources)
        return {
            "status": "success",
            "total_sources": len(sources),
            "usable_sources": sum(1 for s in sources if s.get("usable")),
            "sources": sources,
        }
    except Exception as e:
        logger.exception("資料來源掃描失敗")
        return {"status": "error", "detail": str(e), "sources": []}


# ── 檔案監控 API ─────────────────────────────────────────────────


@app.post("/api/file-watcher/start", tags=["檔案監控"])
async def start_file_watcher(
    scan_interval: int = 30,
    auto_analyze: bool = True,
) -> dict[str, Any]:
    """啟動檔案監控服務。"""
    global _file_watcher  # noqa: PLW0603
    if _file_watcher is None:
        from src.services.file_watcher import FileWatcherService

        _file_watcher = FileWatcherService(scan_interval=scan_interval, auto_analyze=auto_analyze)
        _file_watcher.set_broadcast(ws_manager.broadcast_file_event)

    if not _file_watcher.is_running:
        _file_watcher.scan_interval = scan_interval
        _file_watcher.auto_analyze = auto_analyze
        await _file_watcher.start()

    return {"status": "started", **_file_watcher.status}


@app.post("/api/file-watcher/stop", tags=["檔案監控"])
async def stop_file_watcher() -> dict[str, Any]:
    """停止檔案監控服務。"""
    if _file_watcher and _file_watcher.is_running:
        await _file_watcher.stop()
        return {"status": "stopped"}
    return {"status": "not_running"}


@app.get("/api/file-watcher/status", tags=["檔案監控"])
async def file_watcher_status() -> dict[str, Any]:
    """取得檔案監控服務狀態。"""
    if _file_watcher:
        return _file_watcher.status
    return {"running": False, "scan_interval": 0, "known_files": 0, "processed_count": 0}


@app.post("/api/file-watcher/scan", tags=["檔案監控"])
async def force_scan_files(path: str | None = None) -> dict[str, Any]:
    """強制掃描並處理檔案。可指定路徑或掃描所有未處理檔案。"""
    if _file_watcher:
        results = await _file_watcher.force_scan(path)
        return {"status": "completed", "processed": len(results), "results": results}
    return {"status": "error", "detail": "FileWatcher 未啟動"}


@app.get("/api/file-watcher/history", tags=["檔案監控"])
async def file_watcher_history() -> dict[str, Any]:
    """取得已自動處理的檔案歷史記錄。"""
    if _file_watcher:
        events = _file_watcher.history
        return {
            "total": len(events),
            "events": [
                {
                    "filename": e.filename,
                    "path": e.path,
                    "turbine_id": e.turbine_id,
                    "event_type": e.event_type,
                    "total_records": e.total_records,
                    "detected_fields": e.detected_fields,
                    "analysis_summary": e.analysis_summary,
                    "error_message": e.error_message,
                }
                for e in events[-20:]  # 最近 20 筆
            ],
        }
    return {"total": 0, "events": []}


# ── 特徵分析 API ─────────────────────────────────────────────────


@app.get("/api/scada/{turbine_id}/features", tags=["特徵分析"])
async def feature_analysis(turbine_id: str = "WT-01") -> JSONResponse:
    """對指定風機執行全自動特徵分析。

    自動偵測所有欄位、計算相關性、特徵重要度、異常值、分佈、漂移。
    不需要預先知道欄位名稱 — 資料分析師自動判斷。
    """
    import asyncio

    # 去除使用者可能輸入的副檔名
    for ext in (".csv", ".parquet", ".xlsx", ".zip"):
        if turbine_id.lower().endswith(ext):
            turbine_id = turbine_id[: -len(ext)]
            break

    try:
        from src.data_pipeline.ingestion.kelmarsh_loader import load_turbine_data
        from src.data_pipeline.ingestion.smart_loader import smart_load
        from src.features.auto_feature_analysis import analyze_features

        loop = asyncio.get_event_loop()

        # 智慧載入
        try:
            df = await loop.run_in_executor(None, lambda: load_turbine_data(turbine_id))
        except (FileNotFoundError, ValueError):
            from pathlib import Path as _Path

            data_root = _Path(__file__).resolve().parents[2] / "data"
            df = None
            for sub in ["raw", "external", "processed"]:
                d = data_root / sub
                if not d.exists():
                    continue
                for f in sorted(d.iterdir()):
                    if f.is_file() and turbine_id.lower() in f.stem.lower():
                        df = await loop.run_in_executor(
                            None, lambda fp=f: smart_load(fp, turbine_id=turbine_id)
                        )
                        break
                if df is not None:
                    break
            if df is None:
                raise FileNotFoundError(f"找不到風機 '{turbine_id}' 的資料") from None

        # 執行自動特徵分析
        report = await loop.run_in_executor(None, lambda: analyze_features(df))

        return JSONResponse(
            content={
                "status": "success",
                "turbine_id": turbine_id,
                **report,
            }
        )

    except FileNotFoundError as e:
        return JSONResponse(status_code=404, content={"status": "error", "detail": str(e)})
    except Exception as e:
        logger.exception("特徵分析失敗")
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})


# ── RAG 知識庫 API ────────────────────────────────────────────────


_rag_service: Any = None


def _get_rag_service() -> Any:
    """取得或建立 RAG Service 單例。"""
    global _rag_service  # noqa: PLW0603
    if _rag_service is None:
        from src.services.rag_service import RAGService

        _rag_service = RAGService()
    return _rag_service


@app.post("/api/knowledge-base/search", tags=["知識庫"])
async def kb_search(
    query: str = "",
    n_results: int = 5,
    collection: str | None = None,
) -> JSONResponse:
    """語意搜尋知識庫。"""
    if not query:
        return JSONResponse(
            status_code=400, content={"status": "error", "detail": "query 不可為空"}
        )

    try:
        rag = _get_rag_service()
        results = rag.search(query=query, n_results=n_results, collection_name=collection)
        return JSONResponse(
            content={
                "status": "success",
                "query": query,
                "results": [
                    {
                        "doc_id": r.doc_id,
                        "content": r.content[:500],
                        "relevance": round(r.relevance_score, 3),
                        "metadata": r.metadata,
                    }
                    for r in results
                ],
                "total": len(results),
            }
        )
    except Exception as e:
        logger.exception("知識庫搜尋失敗")
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})


@app.post("/api/knowledge-base/ask", tags=["知識庫"])
async def kb_ask(
    query: str = "",
    n_results: int = 5,
    collection: str | None = None,
) -> JSONResponse:
    """RAG 問答 — 檢索相關文件並透過 LLM 生成回答。"""
    if not query:
        return JSONResponse(
            status_code=400, content={"status": "error", "detail": "query 不可為空"}
        )

    try:
        import asyncio

        rag = _get_rag_service()
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: rag.ask(query=query, n_results=n_results, collection_name=collection)
        )
        return JSONResponse(content={"status": "success", **result})
    except Exception as e:
        logger.exception("RAG 問答失敗")
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})


@app.post("/api/knowledge-base/ingest", tags=["知識庫"])
async def kb_ingest(
    file_path: str = "",
    collection: str | None = None,
) -> JSONResponse:
    """匯入文件至知識庫。"""
    if not file_path:
        return JSONResponse(
            status_code=400, content={"status": "error", "detail": "file_path 不可為空"}
        )

    try:
        rag = _get_rag_service()
        result = rag.ingest_file(file_path=file_path, collection_name=collection)
        return JSONResponse(content={"status": "success", **result})
    except FileNotFoundError as e:
        return JSONResponse(status_code=404, content={"status": "error", "detail": str(e)})
    except Exception as e:
        logger.exception("文件嵌入失敗")
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})


@app.post("/api/knowledge-base/ingest-folder", tags=["知識庫"])
async def kb_ingest_folder(
    folder_path: str = "",
    collection: str | None = None,
) -> JSONResponse:
    """匯入文件至知識庫（支援單一檔案路徑或資料夾路徑）。"""
    if not folder_path:
        return JSONResponse(status_code=400, content={"status": "error", "detail": "路徑不可為空"})

    try:
        import asyncio
        from pathlib import Path as _Path

        rag = _get_rag_service()
        target = _Path(folder_path)

        if target.is_file():
            # 單一檔案模式
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: rag.ingest_file(str(target), collection_name=collection)
            )
            result["total"] = 1
            result["ingested"] = 1
            result["skipped"] = 0
            result["errors"] = []
            stats = rag.get_collection_stats(collection)
            result["total_in_collection"] = stats.get("count", 0)
            result["chunks_added"] = result.get("added", 0)
        elif target.is_dir():
            # 資料夾模式
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: rag.ingest_folder(folder_path, collection_name=collection)
            )
        else:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "detail": f"路徑不存在：{folder_path}"},
            )

        return JSONResponse(content={"status": "success", **result})
    except FileNotFoundError as e:
        return JSONResponse(status_code=404, content={"status": "error", "detail": str(e)})
    except ValueError as e:
        return JSONResponse(status_code=400, content={"status": "error", "detail": str(e)})
    except Exception as e:
        logger.exception("嵌入失敗")
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})


@app.get("/api/knowledge-base/stats", tags=["知識庫"])
async def kb_stats() -> dict[str, Any]:
    """取得知識庫統計資訊。"""
    try:
        rag = _get_rag_service()
        collections = rag.list_collections()
        return {
            "status": "success",
            "collections": collections,
            "total_collections": len(collections),
            "total_documents": sum(c["count"] for c in collections),
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.get("/api/knowledge-base/sources", tags=["知識庫"])
async def kb_list_sources(
    collection: str | None = None,
) -> dict[str, Any]:
    """列出知識庫中所有來源檔案。"""
    try:
        rag = _get_rag_service()
        sources = rag.list_sources(collection_name=collection)
        return {"status": "success", "sources": sources, "total": len(sources)}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.delete("/api/knowledge-base/source", tags=["知識庫"])
async def kb_delete_source(
    source: str = "",
    collection: str | None = None,
) -> JSONResponse:
    """刪除指定來源的所有文件 chunks。"""
    if not source:
        return JSONResponse(
            status_code=400, content={"status": "error", "detail": "source 不可為空"}
        )
    try:
        rag = _get_rag_service()
        result = rag.delete_by_source(source=source, collection_name=collection)
        return JSONResponse(content={"status": "success", **result})
    except Exception as e:
        logger.exception("刪除來源失敗")
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})


# ── Phase 13：告警系統 API ──────────────────────────────────────


def _get_db():
    """取得資料庫單例（lazy import 避免循環依賴）。"""
    from src.core.database import get_database
    return get_database()


@app.get("/api/alerts", tags=["告警系統"])
async def list_alerts(
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
    severity: str | None = None,
    turbine_id: str | None = None,
) -> dict[str, Any]:
    """查詢告警列表，支援依狀態、嚴重程度、風機篩選。"""
    db = _get_db()
    alerts = db.list_alerts(limit=limit, offset=offset, status=status, severity=severity, turbine_id=turbine_id)
    return {"status": "success", "alerts": alerts, "total": len(alerts)}


@app.get("/api/alerts/stats", tags=["告警系統"])
async def alert_stats() -> dict[str, Any]:
    """取得告警統計數據。"""
    db = _get_db()
    return {"status": "success", **db.count_alerts()}


@app.get("/api/alerts/{alert_id}", tags=["告警系統"])
async def get_alert(alert_id: str) -> dict[str, Any]:
    """取得單一告警詳細資訊。"""
    db = _get_db()
    alert = db.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")
    return {"status": "success", "alert": alert}


@app.post("/api/alerts", tags=["告警系統"])
async def create_alert(req: CreateAlertRequest) -> JSONResponse:
    """手動建立告警。"""
    db = _get_db()
    alert_id = db.create_alert(
        source=req.source,
        severity=req.severity,
        title=req.title,
        description=req.description,
        turbine_id=req.turbine_id,
        tags=req.tags,
        metrics=req.metrics,
    )
    alert = db.get_alert(alert_id)
    if alert:
        await ws_manager.broadcast_alert(alert, is_new=True)
    return JSONResponse(
        status_code=201,
        content={"status": "success", "alert_id": alert_id},
    )


@app.post("/api/alerts/ingest", tags=["告警系統"])
async def ingest_alert(req: AlertIngestRequest) -> JSONResponse:
    """外部系統推送告警的標準接口。

    提供統一的 JSON 格式讓外部廠商（Vestas CMS、Siemens Gamesa SCADA 等）推送告警。
    支援 source_alert_id 自動去重：相同 source_system + source_alert_id 不會重複建立。
    """
    db = _get_db()
    alert_id = db.create_alert(
        source="external",
        severity=req.severity,
        title=req.title,
        description=req.description,
        turbine_id=req.turbine_id,
        source_system=req.source_system,
        source_alert_id=req.source_alert_id,
        tags=req.tags,
        metrics=req.metrics,
        metadata=req.metadata,
        occurred_at=req.occurred_at,
    )
    alert = db.get_alert(alert_id)
    if alert:
        await ws_manager.broadcast_alert(alert, is_new=True)
    return JSONResponse(
        status_code=201,
        content={"status": "success", "alert_id": alert_id},
    )


@app.patch("/api/alerts/{alert_id}", tags=["告警系統"])
async def update_alert(alert_id: str, req: UpdateAlertRequest) -> dict[str, Any]:
    """更新告警狀態（確認、解決、駁回）。"""
    db = _get_db()
    ok = db.update_alert_status(alert_id, status=req.status, resolved_by=req.resolved_by)
    if not ok:
        raise HTTPException(status_code=404, detail="告警不存在")
    alert = db.get_alert(alert_id)
    if alert:
        await ws_manager.broadcast_alert(alert, is_new=False)
    return {"status": "success", "alert": alert}


@app.post("/api/alerts/{alert_id}/create-work-order", tags=["告警系統"])
async def create_work_order_from_alert(alert_id: str) -> JSONResponse:
    """從告警自動建立工單（預填告警資訊）。"""
    db = _get_db()
    alert = db.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")
    if alert.get("work_order_id"):
        raise HTTPException(status_code=409, detail="此告警已有關聯工單")
    # 嚴重程度對應工單優先程度
    priority_map = {"critical": "critical", "warning": "high", "info": "medium"}
    order_id = db.create_work_order(
        title=f"[{alert['severity'].upper()}] {alert['title']}",
        description=alert.get("description", ""),
        priority=priority_map.get(alert["severity"], "medium"),
        turbine_id=alert.get("turbine_id"),
        alert_id=alert_id,
    )
    order = db.get_work_order(order_id)
    if order:
        await ws_manager.broadcast_work_order_update(order)
    updated_alert = db.get_alert(alert_id)
    if updated_alert:
        await ws_manager.broadcast_alert(updated_alert, is_new=False)
    return JSONResponse(
        status_code=201,
        content={"status": "success", "work_order_id": order_id, "alert_id": alert_id},
    )


# ── Phase 13：工單管理 API ──────────────────────────────────────


@app.get("/api/work-orders", tags=["工單管理"])
async def list_work_orders(
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
    priority: str | None = None,
    turbine_id: str | None = None,
) -> dict[str, Any]:
    """查詢工單列表。"""
    db = _get_db()
    orders = db.list_work_orders(limit=limit, offset=offset, status=status, priority=priority, turbine_id=turbine_id)
    return {"status": "success", "work_orders": orders, "total": len(orders)}


@app.get("/api/work-orders/stats", tags=["工單管理"])
async def work_order_stats() -> dict[str, Any]:
    """取得工單統計數據。"""
    db = _get_db()
    return {"status": "success", **db.count_work_orders()}


@app.get("/api/work-orders/{order_id}", tags=["工單管理"])
async def get_work_order(order_id: str) -> dict[str, Any]:
    """取得單一工單詳細資訊。"""
    db = _get_db()
    order = db.get_work_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="工單不存在")
    return {"status": "success", "work_order": order}


@app.post("/api/work-orders", tags=["工單管理"])
async def create_work_order(req: CreateWorkOrderRequest) -> JSONResponse:
    """建立新工單。"""
    db = _get_db()
    order_id = db.create_work_order(
        title=req.title,
        description=req.description,
        priority=req.priority,
        turbine_id=req.turbine_id,
        alert_id=req.alert_id,
        assigned_agents=req.assigned_agents,
        estimated_duration_hours=req.estimated_duration_hours,
    )
    order = db.get_work_order(order_id)
    if order:
        await ws_manager.broadcast_work_order_update(order)
    return JSONResponse(
        status_code=201,
        content={"status": "success", "work_order_id": order_id},
    )


@app.patch("/api/work-orders/{order_id}", tags=["工單管理"])
async def update_work_order(order_id: str, req: UpdateWorkOrderRequest) -> dict[str, Any]:
    """更新工單狀態、優先程度或指派代理。"""
    db = _get_db()
    fields = {k: v for k, v in req.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="未提供任何更新欄位")
    ok = db.update_work_order(order_id, **fields)
    if not ok:
        raise HTTPException(status_code=404, detail="工單不存在")
    order = db.get_work_order(order_id)
    if order:
        await ws_manager.broadcast_work_order_update(order)
    return {"status": "success", "work_order": order}


@app.post("/api/work-orders/{order_id}/notes", tags=["工單管理"])
async def add_work_order_note(order_id: str, req: AddWorkOrderNoteRequest) -> dict[str, Any]:
    """新增工單備註。"""
    db = _get_db()
    ok = db.add_work_order_note(order_id, author=req.author, text=req.text)
    if not ok:
        raise HTTPException(status_code=404, detail="工單不存在")
    order = db.get_work_order(order_id)
    if order:
        await ws_manager.broadcast_work_order_update(order)
    return {"status": "success", "work_order": order}


# ── 應用程式啟動入口 ────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
