"""WindAI Lab 代理協調引擎。

負責執行工作流程，依序或平行調度代理，並透過 WebSocket 即時廣播狀態變更。
支援兩種模式：
- 真實模式：代理已註冊實例時，呼叫 BaseAgent.run_task() 執行真實技能管線
- 模擬模式：代理未註冊時，退回至漸進式進度動畫（向下相容）

每個 WorkflowStep 同時攜帶真實執行參數（task_template / task_parameters）
與模擬 fallback 設定（sub_messages / progress_messages / duration），
引擎自動根據代理是否有實例來決定走哪條路徑。
"""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from src.api.agent_registry import get_agent, update_agent_status
from src.api.models import AgentStatus, WorkLogEntry
from src.api.websocket_manager import manager as ws_manager
from src.utils.logger import get_logger

logger = get_logger("orchestrator.engine")


class StepType(StrEnum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    DECISION = "decision"


@dataclass
class WorkflowStep:
    """工作流程步驟定義。

    同時支援真實執行與模擬 fallback：
    - task_template + task_parameters → 真實代理路徑
    - sub_messages + progress_messages + duration → 模擬動畫路徑
    """

    name: str
    agent_ids: list[str]
    description: str
    duration: float = 3.0
    step_type: StepType = StepType.SEQUENTIAL
    sub_messages: list[str] = field(default_factory=list)
    progress_messages: dict[int, str] = field(default_factory=dict)

    # ── 真實執行參數 ──
    task_template: str = ""
    """傳給 agent.run_task() 的任務字串模板，支援 {param} 佔位符。
    例如 "diagnose {turbine_id}" 會觸發 YAML task_routing 關鍵字匹配。
    若為空，退回使用 description。"""

    task_parameters: dict[str, Any] = field(default_factory=dict)
    """注入 TaskContext.parameters 的參數，如 {"turbine_id": "WT-01"}。"""

    collaborator_ids: list[str] = field(default_factory=list)
    """明確指定的協作代理 ID，注入 TaskContext.collaborators。
    若為空，自動使用同步驟的其他代理。"""


@dataclass
class Workflow:
    """工作流程定義。"""

    id: str
    name: str
    description: str
    steps: list[WorkflowStep]

    parameters: dict[str, Any] = field(default_factory=dict)
    """工作流程層級參數，會合併到每個步驟的 task_parameters 中。"""


class OrchestrationEngine:
    """代理協調引擎，執行工作流程並廣播狀態。"""

    def __init__(self) -> None:
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._work_logs: list[WorkLogEntry] = []

    @property
    def work_logs(self) -> list[WorkLogEntry]:
        return self._work_logs

    def _create_log(
        self, agent_id: str, agent_name: str, message: str, log_type: str = "info"
    ) -> WorkLogEntry:
        """建立工作日誌項目。"""
        entry = WorkLogEntry(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            agent_name=agent_name,
            message=message,
            type=log_type,
        )
        self._work_logs.append(entry)
        return entry

    async def _update_and_broadcast(
        self,
        agent_id: str,
        status: AgentStatus,
        task: str | None = None,
        progress: float = 0.0,
        collaborating_with: list[str] | None = None,
    ) -> None:
        """更新代理狀態並廣播。"""
        updated = update_agent_status(
            agent_id,
            status=status,
            current_task=task,
            progress=progress,
            collaborating_with=collaborating_with or [],
        )
        if updated:
            await ws_manager.broadcast_agent_status(updated)

    async def _run_agent_step(
        self,
        agent_id: str,
        step: WorkflowStep,
        accumulated_results: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """執行單一代理的工作步驟。

        優先使用已註冊的真實代理實例（BaseAgent.run_task），
        若代理未實作則退回至模擬進度動畫。

        Returns:
            該代理的執行結果（真實路徑），或空 dict（模擬路徑）。
        """
        from src.agents.base import TaskContext
        from src.agents.dynamic_registry import dynamic_registry

        agent_model = get_agent(agent_id)
        if not agent_model:
            return {}

        display_name = agent_model.display_name
        other_agents = [aid for aid in step.agent_ids if aid != agent_id]
        collaborators = step.collaborator_ids or other_agents

        # ── 真實代理路徑 ──
        real_agent = dynamic_registry.get_instance(agent_id)
        if real_agent is not None:
            # 組裝任務字串：優先使用 task_template，退回 description
            task_str = step.task_template or step.description
            with contextlib.suppress(KeyError, IndexError):
                task_str = task_str.format(**step.task_parameters)

            ctx = TaskContext(
                parameters=step.task_parameters,
                collaborators=collaborators,
                results=accumulated_results or {},
            )

            log = self._create_log(agent_id, display_name, f"開始：{step.description}")
            await ws_manager.broadcast_work_log(log)

            result = await real_agent.run_task(task_str, ctx)

            # 發送子訊息（workflow 層級的補充說明）
            for msg in step.sub_messages:
                log = self._create_log(agent_id, display_name, msg, "success")
                await ws_manager.broadcast_work_log(log)
                await asyncio.sleep(0.3)

            log = self._create_log(
                agent_id,
                display_name,
                f"完成：{step.description}（{result.status.value}）",
                "success" if result.status.value == "success" else "warning",
            )
            await ws_manager.broadcast_work_log(log)
            return {agent_id: result.data} if result.data else {}

        # ── 模擬路徑（向下相容） ──
        await self._update_and_broadcast(
            agent_id, AgentStatus.WORKING, step.description, 0.0, other_agents
        )
        log = self._create_log(agent_id, display_name, f"開始：{step.description}")
        await ws_manager.broadcast_work_log(log)

        total_duration = step.duration
        increments = 10
        increment_time = total_duration / increments

        for i in range(1, increments + 1):
            await asyncio.sleep(increment_time)
            progress = i / increments

            progress_pct = int(progress * 100)
            if progress_pct in step.progress_messages:
                msg = step.progress_messages[progress_pct]
                log = self._create_log(agent_id, display_name, msg)
                await ws_manager.broadcast_work_log(log)

            await self._update_and_broadcast(
                agent_id, AgentStatus.WORKING, step.description, progress, other_agents
            )

        for msg in step.sub_messages:
            log = self._create_log(agent_id, display_name, msg, "success")
            await ws_manager.broadcast_work_log(log)
            await asyncio.sleep(0.3)

        await self._update_and_broadcast(
            agent_id, AgentStatus.COMPLETED, f"已完成：{step.description}", 1.0
        )
        log = self._create_log(agent_id, display_name, f"完成：{step.description}", "success")
        await ws_manager.broadcast_work_log(log)
        return {}

    async def _run_step(
        self, step: WorkflowStep, accumulated_results: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """執行工作流程步驟（可能包含多個平行代理）。

        Returns:
            所有代理在此步驟產出的結果合集。
        """
        step_results: dict[str, Any] = {}
        if step.step_type == StepType.PARALLEL:
            tasks = [
                self._run_agent_step(aid, step, accumulated_results) for aid in step.agent_ids
            ]
            results = await asyncio.gather(*tasks)
            for r in results:
                step_results.update(r)
        else:
            for aid in step.agent_ids:
                r = self._run_agent_step(aid, step, accumulated_results)
                result = await r
                step_results.update(result)
        return step_results

    async def execute_workflow(self, workflow: Workflow) -> str:
        """執行完整工作流程。"""
        task_id = str(uuid.uuid4())
        logger.info(f"開始執行工作流程：{workflow.name} (task_id={task_id})")

        # 廣播工作流程開始
        log = self._create_log(
            "system", "系統", f"🚀 工作流程啟動：{workflow.name} — {workflow.description}", "info"
        )
        await ws_manager.broadcast_work_log(log)

        accumulated_results: dict[str, Any] = {}

        try:
            for i, step in enumerate(workflow.steps):
                # 合併 workflow 層級參數到步驟
                merged_params = {**workflow.parameters, **step.task_parameters}
                step.task_parameters = merged_params

                step_label = f"[{i+1}/{len(workflow.steps)}]"
                log = self._create_log("system", "系統", f"📋 {step_label} {step.name}", "info")
                await ws_manager.broadcast_work_log(log)

                step_results = await self._run_step(step, accumulated_results)
                accumulated_results.update(step_results)

                # 步驟間短暫停頓
                await asyncio.sleep(0.5)

            # 工作流程完成
            log = self._create_log(
                "system", "系統", f"✅ 工作流程完成：{workflow.name}", "success"
            )
            await ws_manager.broadcast_work_log(log)

            # 重設所有參與代理為待命
            all_agent_ids = set()
            for step in workflow.steps:
                all_agent_ids.update(step.agent_ids)

            await asyncio.sleep(2)
            for aid in all_agent_ids:
                await self._update_and_broadcast(aid, AgentStatus.IDLE, None, 0.0)

        except Exception as e:
            logger.error(f"工作流程執行失敗：{e}")
            log = self._create_log("system", "系統", f"❌ 工作流程失敗：{str(e)}", "error")
            await ws_manager.broadcast_work_log(log)

        return task_id

    async def run_workflow_background(self, workflow: Workflow) -> str:
        """在背景執行工作流程，立即回傳 task_id。"""
        task_id = str(uuid.uuid4())

        async def _run():
            await self.execute_workflow(workflow)
            if task_id in self._running_tasks:
                del self._running_tasks[task_id]

        task = asyncio.create_task(_run())
        self._running_tasks[task_id] = task
        return task_id

    # ── 真實代理執行模式 ──────────────────────────────────────

    async def execute_agent_task(
        self,
        agent_id: str,
        task: str,
        parameters: dict | None = None,
        collaborators: list[str] | None = None,
    ) -> dict:
        """直接呼叫已註冊的 BaseAgent 實例執行任務。

        與工作流程不同，此方法直接指定單一代理執行。

        Args:
            agent_id: 代理 ID。
            task: 任務描述。
            parameters: 任務參數。
            collaborators: 協作代理 ID 列表。

        Returns:
            任務結果 dict。
        """
        from src.agents.base import TaskContext
        from src.agents.dynamic_registry import dynamic_registry

        agent = dynamic_registry.get_instance(agent_id)
        if agent is None:
            logger.warning(f"代理 {agent_id} 未註冊實例，無法執行真實任務")
            return {"error": f"Agent {agent_id} not registered"}

        ctx = TaskContext(
            parameters=parameters or {},
            collaborators=collaborators or [],
        )

        log = self._create_log(
            "system",
            "系統",
            f"🚀 指派任務至 {agent.display_name}：{task}",
        )
        await ws_manager.broadcast_work_log(log)

        result = await agent.run_task(task, ctx)

        log = self._create_log(
            "system",
            "系統",
            f"{'✅' if result.status == 'success' else '⚠️'} "
            f"{agent.display_name}：{result.summary}",
            "success" if result.status == "success" else "warning",
        )
        await ws_manager.broadcast_work_log(log)

        # 延遲後重設代理
        await asyncio.sleep(2)
        await self._update_and_broadcast(agent_id, AgentStatus.IDLE, None, 0.0)

        return {
            "agent_id": agent_id,
            "task": task,
            "status": result.status.value,
            "data": result.data,
            "summary": result.summary,
            "errors": result.errors,
        }


# 全域單例
engine = OrchestrationEngine()
