"""WindAI Lab 代理協調引擎。

負責執行工作流程，依序或平行調度代理，並透過 WebSocket 即時廣播狀態變更。
支援兩種模式：
- 真實模式：代理已註冊實例時，呼叫 BaseAgent.run_task() 執行真實技能管線
- 模擬模式：代理未註冊時，退回至漸進式進度動畫（向下相容）

每個 WorkflowStep 同時攜帶真實執行參數（task_template / task_parameters）
與模擬 fallback 設定（sub_messages / progress_messages / duration），
引擎自動根據代理是否有實例來決定走哪條路徑。

進階功能：
- 總監 Checkpoint 機制：步驟完成後由總監代理評估品質，決定是否需要調參重跑
- 錯誤重試/降級策略：skill 執行失敗時自動重試，持續失敗則降級或跳過
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


# ── 重試與降級設定 ───────────────────────────────────────────


class DegradationStrategy(StrEnum):
    """步驟失敗時的降級策略。"""

    ABORT = "abort"
    """中止整個工作流程（預設行為）。"""

    SKIP = "skip"
    """跳過失敗步驟，繼續下一步。"""

    FALLBACK = "fallback"
    """使用 fallback_agent_ids 或簡化參數重新執行。"""


@dataclass
class RetryConfig:
    """步驟錯誤重試設定。

    Attributes:
        max_retries: 最大重試次數（不含首次執行），0 表示不重試。
        retry_delay: 重試間隔秒數，支援指數退避。
        exponential_backoff: 是否啟用指數退避（delay × 2^attempt）。
        degradation: 所有重試耗盡後的降級策略。
        fallback_agent_ids: 降級策略為 FALLBACK 時，使用的替代代理 ID。
    """

    max_retries: int = 0
    retry_delay: float = 1.0
    exponential_backoff: bool = True
    degradation: DegradationStrategy = DegradationStrategy.ABORT
    fallback_agent_ids: list[str] = field(default_factory=list)


# ── 總監 Checkpoint 設定 ─────────────────────────────────────


class CheckpointAction(StrEnum):
    """Checkpoint 評估結果對應的動作。"""

    PASS = "pass"
    """品質合格，繼續下一步。"""

    RETRY = "retry"
    """品質不足，用調整後的參數重跑此步驟。"""

    ABORT = "abort"
    """品質嚴重不足，中止工作流程。"""


@dataclass
class CheckpointConfig:
    """總監品質檢查點設定。

    在步驟完成後，由總監代理（或自動規則）評估該步驟的產出品質。
    若品質未達門檻，可自動調參重跑或中止。

    Attributes:
        enabled: 是否啟用此 checkpoint。
        evaluator_agent_id: 執行品質評估的代理 ID（預設 project-director）。
        quality_rules: 品質規則，鍵為指標名稱，值為最低門檻。
            例如 {"r2_score": 0.8, "f1_macro": 0.6}。
        max_reruns: 最多重跑次數。
        param_adjustments: 重跑時的參數調整，鍵為參數名稱，值為調整規則。
            例如 {"n_estimators": "increase_50pct"}。
        description: checkpoint 描述（顯示在前端）。
    """

    enabled: bool = True
    evaluator_agent_id: str = "project-director"
    quality_rules: dict[str, float] = field(default_factory=dict)
    max_reruns: int = 1
    param_adjustments: dict[str, str] = field(default_factory=dict)
    description: str = "品質檢查"


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

    # ── 重試與降級 ──
    retry: RetryConfig = field(default_factory=RetryConfig)
    """步驟錯誤重試設定。預設不重試。"""

    # ── 總監 Checkpoint ──
    checkpoint: CheckpointConfig | None = None
    """步驟完成後的品質檢查點設定。None 表示不檢查。"""


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

    # ── 重試機制 ─────────────────────────────────────────────

    async def _run_step_with_retry(
        self,
        step: WorkflowStep,
        step_index: int,
        total_steps: int,
        accumulated_results: dict[str, Any],
    ) -> tuple[dict[str, Any], bool]:
        """執行步驟，含重試與降級邏輯。

        Returns:
            (step_results, should_continue) — 步驟結果與是否繼續工作流程。
        """
        retry_cfg = step.retry
        last_error: Exception | None = None

        for attempt in range(1 + retry_cfg.max_retries):
            try:
                step_results = await self._run_step(step, accumulated_results)

                # 檢查步驟結果是否包含錯誤
                has_error = self._step_has_error(step_results)
                if not has_error:
                    return step_results, True

                # 步驟內部回報了錯誤，視同失敗
                if attempt < retry_cfg.max_retries:
                    delay = self._calc_retry_delay(retry_cfg, attempt)
                    await self._broadcast_retry(step, attempt + 1, retry_cfg.max_retries, delay)
                    await asyncio.sleep(delay)
                    continue

                # 所有重試耗盡
                last_error = None
                break

            except Exception as e:
                last_error = e
                logger.warning(
                    f"步驟 [{step_index+1}/{total_steps}] {step.name} "
                    f"第 {attempt+1} 次執行失敗：{e}"
                )

                if attempt < retry_cfg.max_retries:
                    delay = self._calc_retry_delay(retry_cfg, attempt)
                    await self._broadcast_retry(step, attempt + 1, retry_cfg.max_retries, delay)
                    await asyncio.sleep(delay)
                else:
                    break

        # ── 所有重試耗盡，執行降級策略 ──
        return await self._handle_degradation(
            step, step_index, total_steps, accumulated_results, last_error
        )

    @staticmethod
    def _step_has_error(step_results: dict[str, Any]) -> bool:
        """檢查步驟結果中是否任一代理回報錯誤。"""
        for _agent_id, data in step_results.items():
            if isinstance(data, dict) and data.get("status") == "error":
                return True
        return False

    @staticmethod
    def _calc_retry_delay(cfg: RetryConfig, attempt: int) -> float:
        """計算重試等待時間（支援指數退避）。"""
        if cfg.exponential_backoff:
            return cfg.retry_delay * (2**attempt)
        return cfg.retry_delay

    async def _broadcast_retry(
        self, step: WorkflowStep, attempt: int, max_retries: int, delay: float
    ) -> None:
        """廣播重試事件至前端。"""
        log = self._create_log(
            "system",
            "系統",
            f"🔄 步驟「{step.name}」執行失敗，{delay:.0f}s 後第 {attempt}/{max_retries} 次重試",
            "warning",
        )
        await ws_manager.broadcast_work_log(log)
        await ws_manager.broadcast(
            {
                "type": "workflow_retry",
                "payload": {
                    "step_name": step.name,
                    "attempt": attempt,
                    "max_retries": max_retries,
                    "delay_seconds": delay,
                },
            }
        )

    async def _handle_degradation(
        self,
        step: WorkflowStep,
        step_index: int,
        total_steps: int,
        accumulated_results: dict[str, Any],
        last_error: Exception | None,
    ) -> tuple[dict[str, Any], bool]:
        """重試耗盡後執行降級策略。

        Returns:
            (step_results, should_continue)
        """
        strategy = step.retry.degradation
        step_label = f"[{step_index+1}/{total_steps}]"
        error_msg = str(last_error) if last_error else "步驟內部回報錯誤"

        if strategy == DegradationStrategy.SKIP:
            log = self._create_log(
                "system",
                "系統",
                f"⏭️ {step_label} 步驟「{step.name}」重試耗盡，已跳過 — {error_msg}",
                "warning",
            )
            await ws_manager.broadcast_work_log(log)
            await ws_manager.broadcast(
                {
                    "type": "workflow_degradation",
                    "payload": {
                        "step_name": step.name,
                        "strategy": "skip",
                        "reason": error_msg,
                    },
                }
            )
            return {}, True

        if strategy == DegradationStrategy.FALLBACK and step.retry.fallback_agent_ids:
            log = self._create_log(
                "system",
                "系統",
                f"🔀 {step_label} 步驟「{step.name}」降級至備用代理",
                "warning",
            )
            await ws_manager.broadcast_work_log(log)

            # 建立降級步驟：使用 fallback agents，清除 checkpoint 避免無限迴圈
            fallback_step = WorkflowStep(
                name=f"{step.name}（降級）",
                agent_ids=step.retry.fallback_agent_ids,
                description=f"（降級）{step.description}",
                duration=step.duration,
                step_type=step.step_type,
                sub_messages=step.sub_messages,
                progress_messages=step.progress_messages,
                task_template=step.task_template,
                task_parameters=step.task_parameters,
                collaborator_ids=step.collaborator_ids,
            )
            await ws_manager.broadcast(
                {
                    "type": "workflow_degradation",
                    "payload": {
                        "step_name": step.name,
                        "strategy": "fallback",
                        "fallback_agents": step.retry.fallback_agent_ids,
                    },
                }
            )
            try:
                fallback_results = await self._run_step(fallback_step, accumulated_results)
                return fallback_results, True
            except Exception as fb_err:
                logger.error(f"降級步驟也失敗：{fb_err}")
                log = self._create_log("system", "系統", f"❌ 降級步驟也失敗：{fb_err}", "error")
                await ws_manager.broadcast_work_log(log)
                return {}, False

        # ABORT（預設）
        log = self._create_log(
            "system",
            "系統",
            f"❌ {step_label} 步驟「{step.name}」重試耗盡，中止工作流程 — {error_msg}",
            "error",
        )
        await ws_manager.broadcast_work_log(log)
        await ws_manager.broadcast(
            {
                "type": "workflow_degradation",
                "payload": {
                    "step_name": step.name,
                    "strategy": "abort",
                    "reason": error_msg,
                },
            }
        )
        return {}, False

    # ── 總監 Checkpoint 機制 ─────────────────────────────────

    async def _run_checkpoint(
        self,
        step: WorkflowStep,
        step_index: int,
        total_steps: int,
        step_results: dict[str, Any],
        accumulated_results: dict[str, Any],
    ) -> tuple[dict[str, Any], CheckpointAction]:
        """執行總監品質檢查點。

        評估步驟產出是否達到品質門檻。若未達標，嘗試調參重跑。

        Returns:
            (final_step_results, action_taken)
        """
        cp = step.checkpoint
        if cp is None or not cp.enabled:
            return step_results, CheckpointAction.PASS

        step_label = f"[{step_index+1}/{total_steps}]"

        # 廣播 checkpoint 開始
        log = self._create_log(
            cp.evaluator_agent_id,
            "總監",
            f"🔍 {step_label} 品質檢查：{cp.description}",
            "info",
        )
        await ws_manager.broadcast_work_log(log)
        await ws_manager.broadcast(
            {
                "type": "workflow_checkpoint",
                "payload": {
                    "step_name": step.name,
                    "status": "evaluating",
                    "description": cp.description,
                    "quality_rules": cp.quality_rules,
                },
            }
        )

        # 評估品質
        action, violations = self._evaluate_quality(step_results, cp)

        if action == CheckpointAction.PASS:
            log = self._create_log(
                cp.evaluator_agent_id,
                "總監",
                f"✅ {step_label} 品質合格 — {cp.description}",
                "success",
            )
            await ws_manager.broadcast_work_log(log)
            await ws_manager.broadcast(
                {
                    "type": "workflow_checkpoint",
                    "payload": {
                        "step_name": step.name,
                        "status": "passed",
                        "description": cp.description,
                    },
                }
            )
            return step_results, CheckpointAction.PASS

        # 品質未達標，嘗試重跑
        violation_msg = "; ".join(
            f"{metric}: {value:.4f} < {threshold:.4f}" for metric, value, threshold in violations
        )
        log = self._create_log(
            cp.evaluator_agent_id,
            "總監",
            f"⚠️ {step_label} 品質未達標 — {violation_msg}",
            "warning",
        )
        await ws_manager.broadcast_work_log(log)

        # 調參重跑迴圈（使用副本避免污染原始步驟定義）
        current_params = dict(step.task_parameters)
        for rerun in range(1, cp.max_reruns + 1):
            adjusted_params = self._apply_param_adjustments(current_params, cp.param_adjustments)
            current_params = adjusted_params
            step.task_parameters = adjusted_params

            log = self._create_log(
                cp.evaluator_agent_id,
                "總監",
                f"🔄 {step_label} 調參重跑 ({rerun}/{cp.max_reruns})：{cp.description}",
                "warning",
            )
            await ws_manager.broadcast_work_log(log)
            await ws_manager.broadcast(
                {
                    "type": "workflow_checkpoint",
                    "payload": {
                        "step_name": step.name,
                        "status": "rerunning",
                        "rerun": rerun,
                        "max_reruns": cp.max_reruns,
                        "adjusted_params": adjusted_params,
                    },
                }
            )

            # 重跑步驟
            step_results = await self._run_step(step, accumulated_results)

            # 再次評估
            action, violations = self._evaluate_quality(step_results, cp)
            if action == CheckpointAction.PASS:
                log = self._create_log(
                    cp.evaluator_agent_id,
                    "總監",
                    f"✅ {step_label} 重跑後品質合格 — {cp.description}",
                    "success",
                )
                await ws_manager.broadcast_work_log(log)
                await ws_manager.broadcast(
                    {
                        "type": "workflow_checkpoint",
                        "payload": {
                            "step_name": step.name,
                            "status": "passed_after_rerun",
                            "rerun": rerun,
                        },
                    }
                )
                return step_results, CheckpointAction.PASS

        # 所有重跑都未達標
        violation_msg = "; ".join(
            f"{metric}: {value:.4f} < {threshold:.4f}" for metric, value, threshold in violations
        )
        log = self._create_log(
            cp.evaluator_agent_id,
            "總監",
            f"❌ {step_label} {cp.max_reruns} 次重跑後仍未達標 — {violation_msg}",
            "error",
        )
        await ws_manager.broadcast_work_log(log)
        await ws_manager.broadcast(
            {
                "type": "workflow_checkpoint",
                "payload": {
                    "step_name": step.name,
                    "status": "failed",
                    "violations": [
                        {"metric": m, "value": v, "threshold": t} for m, v, t in violations
                    ],
                },
            }
        )
        return step_results, CheckpointAction.RETRY  # 表示耗盡但未通過

    @staticmethod
    def _evaluate_quality(
        step_results: dict[str, Any],
        cp: CheckpointConfig,
    ) -> tuple[CheckpointAction, list[tuple[str, float, float]]]:
        """根據品質規則評估步驟結果。

        從 step_results 各代理的 data dict 中深度搜索指標值，
        與 quality_rules 門檻比對。

        Returns:
            (action, violations) — violations 為 (metric, actual_value, threshold) 列表。
        """
        if not cp.quality_rules:
            return CheckpointAction.PASS, []

        violations: list[tuple[str, float, float]] = []

        for metric, threshold in cp.quality_rules.items():
            # 在所有代理結果中搜索指標
            found_value = _deep_search_metric(step_results, metric)
            if found_value is not None and found_value < threshold:
                violations.append((metric, found_value, threshold))

        if violations:
            return CheckpointAction.RETRY, violations
        return CheckpointAction.PASS, []

    @staticmethod
    def _apply_param_adjustments(
        params: dict[str, Any],
        adjustments: dict[str, str],
    ) -> dict[str, Any]:
        """根據調整規則修改參數。

        支援的調整規則：
        - "increase_50pct": 增加 50%
        - "increase_100pct": 增加 100%（翻倍）
        - "decrease_50pct": 減少 50%
        - "double": 翻倍
        - "halve": 減半
        """
        adjusted = dict(params)
        for param_name, rule in adjustments.items():
            if param_name not in adjusted:
                continue

            value = adjusted[param_name]
            if not isinstance(value, int | float):
                continue

            if rule == "increase_50pct":
                adjusted[param_name] = value * 1.5
            elif rule == "increase_100pct" or rule == "double":
                adjusted[param_name] = value * 2
            elif rule == "decrease_50pct" or rule == "halve":
                adjusted[param_name] = value * 0.5
            # 整數參數保持整數
            if isinstance(value, int):
                adjusted[param_name] = int(adjusted[param_name])

        return adjusted

    # ── 工作流程主迴圈 ──────────────────────────────────────

    def _validate_workflow(self, workflow: Workflow) -> list[str]:
        """預檢驗證工作流程，回傳警告訊息列表。"""
        from src.agents.dynamic_registry import dynamic_registry

        warnings: list[str] = []
        for step in workflow.steps:
            for agent_id in step.agent_ids:
                model = get_agent(agent_id)
                if model is None:
                    warnings.append(f"步驟「{step.name}」的代理 {agent_id} 不存在於註冊表")
                elif dynamic_registry.get_instance(agent_id) is None:
                    warnings.append(f"步驟「{step.name}」的代理 {agent_id} 無實例，將使用模擬模式")
        return warnings

    async def execute_workflow(self, workflow: Workflow) -> str:
        """執行完整工作流程。"""
        task_id = str(uuid.uuid4())
        logger.info(f"開始執行工作流程：{workflow.name} (task_id={task_id})")

        # ── 預檢驗證 ──
        validation_warnings = self._validate_workflow(workflow)
        for warn in validation_warnings:
            logger.warning(f"工作流程預檢：{warn}")

        # 廣播工作流程開始
        log = self._create_log(
            "system", "系統", f"🚀 工作流程啟動：{workflow.name} — {workflow.description}", "info"
        )
        await ws_manager.broadcast_work_log(log)

        accumulated_results: dict[str, Any] = {}
        total_steps = len(workflow.steps)

        try:
            for i, step in enumerate(workflow.steps):
                # 合併 workflow 層級參數到步驟（使用副本避免污染原始步驟定義）
                merged_params = {**workflow.parameters, **step.task_parameters}
                step = WorkflowStep(
                    name=step.name,
                    agent_ids=step.agent_ids,
                    description=step.description,
                    duration=step.duration,
                    step_type=step.step_type,
                    sub_messages=step.sub_messages,
                    progress_messages=step.progress_messages,
                    task_template=step.task_template,
                    task_parameters=merged_params,
                    collaborator_ids=step.collaborator_ids,
                    retry=step.retry,
                    checkpoint=step.checkpoint,
                )

                step_label = f"[{i+1}/{total_steps}]"
                log = self._create_log("system", "系統", f"📋 {step_label} {step.name}", "info")
                await ws_manager.broadcast_work_log(log)

                # 使用帶重試的步驟執行
                step_results, should_continue = await self._run_step_with_retry(
                    step, i, total_steps, accumulated_results
                )

                if not should_continue:
                    # 降級策略判斷為中止
                    log = self._create_log(
                        "system", "系統", "⛔ 工作流程因步驟失敗而中止", "error"
                    )
                    await ws_manager.broadcast_work_log(log)
                    break

                accumulated_results.update(step_results)

                # ── 總監 Checkpoint ──
                if step.checkpoint and step.checkpoint.enabled:
                    step_results, cp_action = await self._run_checkpoint(
                        step, i, total_steps, step_results, accumulated_results
                    )
                    # 重跑後更新累積結果
                    accumulated_results.update(step_results)

                # 步驟間短暫停頓
                await asyncio.sleep(0.5)
            else:
                # for-else: 所有步驟正常完成（未 break）
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

        # 持久化：建立任務記錄
        db_task_id: str | None = None
        try:
            from src.core.database import get_database

            db = get_database()
            db_task_id = db.create_task(
                command=workflow.name,
                parameters=workflow.parameters,
                description=workflow.description,
            )
        except Exception as exc:
            logger.warning(f"資料庫寫入失敗（不影響執行）：{exc}")

        # 廣播任務開始事件 — 前端據此開啟新 task session
        effective_id = db_task_id or task_id
        await ws_manager.broadcast_task_lifecycle(
            "task_started",
            task_id=effective_id,
            workflow_name=workflow.name,
            description=workflow.description,
        )

        async def _run() -> None:
            try:
                await self.execute_workflow(workflow)
                # 持久化：標記完成 + 儲存分析結果
                agent_ids: list[str] = []
                agent_names: list[str] = []
                seen: set[str] = set()
                for log in self._work_logs[-200:]:
                    if log.agent_id != "system" and log.agent_id not in seen:
                        seen.add(log.agent_id)
                        agent_ids.append(log.agent_id)
                        agent_names.append(log.agent_name)

                if db_task_id:
                    try:
                        db = get_database()
                        db.complete_task(
                            db_task_id,
                            status="completed",
                            agent_ids=agent_ids,
                            agent_names=agent_names,
                        )
                    except Exception as exc:
                        logger.warning(f"任務完成記錄失敗：{exc}")

                # 取得此任務的分析結果（從 DB）
                task_results: list[dict[str, Any]] = []
                if db_task_id:
                    try:
                        db = get_database()
                        task_results = db.get_task_results(db_task_id)
                    except Exception:
                        pass

                # 告警規則引擎：檢查分析結果是否觸發告警
                if task_results:
                    try:
                        from src.services.alert_engine import get_alert_rule_engine

                        rule_engine = get_alert_rule_engine()
                        turbine_id = workflow.parameters.get("turbine_id")
                        alert_ids = await rule_engine.process_and_alert(
                            task_results, turbine_id=turbine_id, task_id=effective_id
                        )
                        if alert_ids:
                            log = self._create_log(
                                "system",
                                "系統",
                                f"⚠️ 規則引擎觸發 {len(alert_ids)} 個告警",
                                "warning",
                            )
                            await ws_manager.broadcast_work_log(log)
                    except Exception as exc:
                        logger.warning(f"告警規則引擎執行失敗：{exc}")

                # 廣播任務完成事件 — 前端據此封存 task session
                await ws_manager.broadcast_task_lifecycle(
                    "task_completed",
                    task_id=effective_id,
                    workflow_name=workflow.name,
                    description=workflow.description,
                    analysis_results=task_results,
                )

            except Exception as exc:
                if db_task_id:
                    try:
                        db = get_database()
                        db.complete_task(db_task_id, status="error", error_message=str(exc))
                    except Exception:
                        pass
                logger.error(f"工作流程執行失敗：{exc}")

                await ws_manager.broadcast_task_lifecycle(
                    "task_completed",
                    task_id=effective_id,
                    workflow_name=workflow.name,
                    description=f"失敗：{exc}",
                )
            finally:
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


# ── 工具函式 ────────────────────────────────────────────────


def _deep_search_metric(data: Any, metric: str) -> float | None:
    """在巢狀 dict 中深度搜索指標值。

    遞迴搜索所有層級的 dict，找到第一個匹配 metric 鍵的數值。
    """
    if isinstance(data, dict):
        if metric in data:
            val = data[metric]
            if isinstance(val, int | float):
                return float(val)
        for v in data.values():
            found = _deep_search_metric(v, metric)
            if found is not None:
                return found
    elif isinstance(data, list):
        for item in data:
            found = _deep_search_metric(item, metric)
            if found is not None:
                return found
    return None


# 全域單例
engine = OrchestrationEngine()
