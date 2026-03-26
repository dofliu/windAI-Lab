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
    AgentModel,
    AgentStatus,
    InvokeRequest,
    InvokeResponse,
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

                # ═══ 新系統：透過 SkillComposingAgent 技能管線執行 ═══
                if command_name in ("diagnose-real", "diagnose-skill"):
                    import asyncio as _aio

                    from src.agents.base import TaskContext
                    from src.agents.dynamic_registry import dynamic_registry

                    tid = parameters.get("turbine_id", "Kelmarsh_1")
                    agent = dynamic_registry.get_instance("fault-diagnostician")
                    if agent:
                        ctx = TaskContext(parameters={"turbine_id": tid})
                        _aio.create_task(agent.run_task(f"diagnose {tid}", ctx))
                        await ws_manager.broadcast(
                            {
                                "type": "work_log_entry",
                                "timestamp": datetime.now().isoformat(),
                                "payload": {
                                    "id": str(uuid.uuid4()),
                                    "agent_id": "system",
                                    "agent_name": "WindAI Lab",
                                    "message": f"已派任故障診斷師分析 {tid}（技能管線）",
                                    "type": "info",
                                },
                            }
                        )

                elif command_name == "train-nbm":
                    import asyncio as _aio

                    from src.agents.base import TaskContext
                    from src.agents.dynamic_registry import dynamic_registry

                    tid = parameters.get("turbine_id", "Kelmarsh_1")
                    agent = dynamic_registry.get_instance("power-curve-expert")
                    if agent:
                        ctx = TaskContext(parameters={"turbine_id": tid})
                        _aio.create_task(agent.run_task(f"NBM {tid}", ctx))

                elif command_name == "predict-rul":
                    import asyncio as _aio

                    from src.agents.base import TaskContext
                    from src.agents.dynamic_registry import dynamic_registry

                    tid = parameters.get("turbine_id", "Kelmarsh_1")
                    agent = dynamic_registry.get_instance("predictive-modeler")
                    if agent:
                        ctx = TaskContext(parameters={"turbine_id": tid})
                        _aio.create_task(agent.run_task(f"predict RUL {tid}", ctx))

                elif command_name in AVAILABLE_WORKFLOWS:
                    workflow_factory = AVAILABLE_WORKFLOWS[command_name]
                    if command_name == "diagnose":
                        workflow = workflow_factory(parameters.get("turbine_id", "WT-07"))
                    elif command_name == "lit-search":
                        workflow = workflow_factory(
                            parameters.get("topic", "wind turbine fault diagnosis")
                        )
                    else:
                        workflow = workflow_factory()
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

    # ── 真實資料診斷（特殊處理） ──
    if command_name == "diagnose-real":
        import asyncio as _aio

        from src.agents.orchestrator.real_workflows import run_real_diagnose

        turbine_id = parameters.get("turbine_id", "Kelmarsh_1")
        task_id = str(uuid.uuid4())
        _aio.create_task(run_real_diagnose(turbine_id))
        return {
            "task_id": task_id,
            "command": command_name,
            "workflow": f"真實資料故障診斷 — {turbine_id}",
            "status": "started",
            "message": f"真實資料工作流程已啟動（Kelmarsh SCADA — {turbine_id}）",
        }

    workflow_factory = AVAILABLE_WORKFLOWS[command_name]

    # 根據指令類型傳入參數
    if command_name == "diagnose":
        turbine_id = parameters.get("turbine_id", "WT-07")
        workflow = workflow_factory(turbine_id)
    elif command_name == "lit-search":
        topic = parameters.get("topic", "wind turbine fault diagnosis")
        workflow = workflow_factory(topic)
    elif command_name in ("data:load", "data:clean", "ai:train", "ai:evaluate"):
        turbine_id = parameters.get("turbine_id", "Kelmarsh_1")
        workflow = workflow_factory(turbine_id)
    else:
        workflow = workflow_factory()

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
async def ml_train(turbine_id: str = "Kelmarsh_1") -> JSONResponse:
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
async def ml_inference(turbine_id: str = "Kelmarsh_1") -> JSONResponse:
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
async def scada_overview(turbine_id: str = "Kelmarsh_1", limit: int = 2000) -> JSONResponse:
    """取得指定風機的 SCADA 資料概覽（用於前端圖表視覺化）。

    智慧載入：先嘗試 Kelmarsh 專用 loader，失敗自動切換通用 smart_load，
    無需針對每種資料來源撰寫專用程式碼。
    """
    import asyncio

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
async def feature_analysis(turbine_id: str = "Kelmarsh_1") -> JSONResponse:
    """對指定風機執行全自動特徵分析。

    自動偵測所有欄位、計算相關性、特徵重要度、異常值、分佈、漂移。
    不需要預先知道欄位名稱 — 資料分析師自動判斷。
    """
    import asyncio

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
        result = rag.ingest_text_file(file_path=file_path, collection_name=collection)
        return JSONResponse(content={"status": "success", **result})
    except FileNotFoundError as e:
        return JSONResponse(status_code=404, content={"status": "error", "detail": str(e)})
    except Exception as e:
        logger.exception("文件嵌入失敗")
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
