"""WindAI Lab FastAPI 主應用程式。

提供 REST API 端點與 WebSocket 即時通訊，作為前端儀表板與後端代理系統之間的橋樑。
支援代理狀態查詢、任務調用、工作日誌取得及即時狀態推播。
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """應用程式生命週期管理：啟動與關閉時的初始化與清理。"""
    from src.agents.registry import agent_instances, bootstrap_agents

    logger.info("WindAI Lab API 啟動中...")
    logger.info(f"已註冊 {len(get_all_agents())} 個代理（狀態）")

    # 初始化代理實例與 MessageBus
    bootstrap_agents()
    logger.info(f"已初始化 {agent_instances.count} 個代理實例（邏輯）")

    yield

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
                if command_name == "diagnose-real":
                    import asyncio as _aio

                    from src.agents.orchestrator.real_workflows import run_real_diagnose

                    tid = parameters.get("turbine_id", "Kelmarsh_1")
                    _aio.create_task(run_real_diagnose(tid))
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

    from src.agents.registry import agent_instances

    agent = get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"代理 '{agent_id}' 不存在")

    task_id = str(uuid.uuid4())

    # 若有真實代理實例，使用 engine 的真實執行路徑
    if agent_instances.has(agent_id):
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
                "name": "diagnose",
                "description": "風機故障診斷（模擬）",
                "parameters": ["turbine_id"],
            },
            {
                "name": "diagnose-real",
                "description": "風機故障診斷（Kelmarsh 真實資料）",
                "parameters": ["turbine_id"],
            },
            {"name": "lit-search", "description": "系統性文獻搜索", "parameters": ["topic"]},
        ]
    }


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
