"""WindAI Lab 代理基底類別。

定義所有 42 個代理共用的抽象介面與生命週期管理，
包含任務執行、訊息處理、狀態廣播等核心功能。
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from src.api.agent_registry import get_agent, update_agent_status
from src.api.models import AgentModel, AgentStatus, WorkLogEntry
from src.api.websocket_manager import manager as ws_manager
from src.utils.logger import get_logger


# ── 代理間訊息模型 ─────────────────────────────────────────────


class MessageType(StrEnum):
    """代理間訊息類型。"""

    TASK_REQUEST = "task_request"
    TASK_RESULT = "task_result"
    TASK_PROGRESS = "task_progress"
    TASK_ERROR = "task_error"
    QUERY = "query"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    DELEGATION = "delegation"


@dataclass
class AgentMessage:
    """代理間通訊的統一訊息格式。

    遵循 CLAUDE.md 定義的 JSON 訊息協議。
    """

    from_agent: str
    to_agent: str
    type: MessageType
    payload: dict[str, Any] = field(default_factory=dict)
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    correlation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """序列化為 dict（相容 WebSocket 廣播）。"""
        return {
            "message_id": self.message_id,
            "from": self.from_agent,
            "to": self.to_agent,
            "type": self.type.value,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
        }


@dataclass
class TaskContext:
    """任務執行上下文，攜帶執行所需的參數與中間結果。"""

    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parameters: dict[str, Any] = field(default_factory=dict)
    results: dict[str, Any] = field(default_factory=dict)
    collaborators: list[str] = field(default_factory=list)
    parent_task_id: str | None = None


# ── 任務結果 ─────────────────────────────────────────────────


class TaskStatus(StrEnum):
    """任務執行結果狀態。"""

    SUCCESS = "success"
    PARTIAL = "partial"
    ERROR = "error"


@dataclass
class TaskResult:
    """代理任務執行結果。"""

    status: TaskStatus
    data: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    errors: list[str] = field(default_factory=list)


# ── BaseAgent 抽象基底類別 ───────────────────────────────────


class BaseAgent(ABC):
    """所有 WindAI Lab 代理的抽象基底類別。

    子類別必須實作：
    - ``execute``: 核心任務執行邏輯
    - ``capabilities``: 宣告代理能力列表

    框架自動處理：
    - 狀態管理與 WebSocket 廣播
    - 工作日誌記錄
    - 訊息收發
    """

    def __init__(self, agent_id: str) -> None:
        self._id = agent_id
        self._logger = get_logger(f"agent.{agent_id}")
        self._message_handlers: dict[MessageType, Any] = {}
        self._register_default_handlers()

    # ── 唯讀屬性 ──

    @property
    def id(self) -> str:
        """代理唯一識別碼。"""
        return self._id

    @property
    def model(self) -> AgentModel | None:
        """從 registry 取得當前代理狀態模型。"""
        return get_agent(self._id)

    @property
    def display_name(self) -> str:
        """代理中文顯示名稱。"""
        m = self.model
        return m.display_name if m else self._id

    @property
    def namespace_name(self) -> str:
        """代理完整命名空間名稱（如 wAI:fault-diagnostician）。"""
        m = self.model
        return m.name if m else self._id

    @property
    @abstractmethod
    def capabilities(self) -> list[str]:
        """宣告此代理具備的能力列表。"""
        ...

    @property
    def description(self) -> str:
        """代理的職責描述，子類別可覆寫提供更詳細說明。"""
        return f"{self.display_name} ({self.namespace_name})"

    # ── 核心抽象方法 ──

    @abstractmethod
    async def execute(self, task: str, context: TaskContext) -> TaskResult:
        """執行指定任務。

        Args:
            task: 任務描述字串。
            context: 任務執行上下文，包含參數與協作資訊。

        Returns:
            任務執行結果。
        """
        ...

    # ── 訊息處理 ──

    def _register_default_handlers(self) -> None:
        """註冊預設訊息處理器。"""
        self._message_handlers[MessageType.QUERY] = self._handle_query
        self._message_handlers[MessageType.TASK_REQUEST] = self._handle_task_request

    async def handle_message(self, message: AgentMessage) -> AgentMessage | None:
        """處理收到的訊息，根據類型分派至對應處理器。

        Args:
            message: 收到的代理訊息。

        Returns:
            回覆訊息，若無需回覆則回傳 None。
        """
        handler = self._message_handlers.get(message.type)
        if handler:
            return await handler(message)

        self._logger.warning(f"未處理的訊息類型：{message.type}")
        return None

    async def _handle_query(self, message: AgentMessage) -> AgentMessage:
        """處理查詢訊息，預設回傳能力列表。子類別可覆寫。"""
        return AgentMessage(
            from_agent=self._id,
            to_agent=message.from_agent,
            type=MessageType.RESPONSE,
            payload={
                "capabilities": self.capabilities,
                "status": self.model.status if self.model else "unknown",
            },
            correlation_id=message.message_id,
        )

    async def _handle_task_request(self, message: AgentMessage) -> AgentMessage:
        """處理任務請求訊息。"""
        task = message.payload.get("task", "")
        ctx = TaskContext(
            parameters=message.payload.get("parameters", {}),
            collaborators=message.payload.get("collaborators", []),
            parent_task_id=message.correlation_id,
        )

        result = await self.run_task(task, ctx)

        return AgentMessage(
            from_agent=self._id,
            to_agent=message.from_agent,
            type=MessageType.TASK_RESULT,
            payload={
                "task": task,
                "result": {
                    "status": result.status.value,
                    "data": result.data,
                    "summary": result.summary,
                    "errors": result.errors,
                },
            },
            correlation_id=message.message_id,
        )

    # ── 任務執行包裝（含狀態管理） ──

    async def run_task(self, task: str, context: TaskContext) -> TaskResult:
        """執行任務的完整生命週期：更新狀態 → 執行 → 廣播結果。

        Args:
            task: 任務描述。
            context: 任務上下文。

        Returns:
            任務執行結果。
        """
        await self._set_status(AgentStatus.WORKING, task, 0.0, context.collaborators)
        await self._log(f"開始：{task}")

        try:
            result = await self.execute(task, context)

            if result.status == TaskStatus.SUCCESS:
                await self._set_status(AgentStatus.COMPLETED, f"已完成：{task}", 1.0)
                await self._log(f"完成：{task}", "success")
            elif result.status == TaskStatus.PARTIAL:
                await self._set_status(AgentStatus.COMPLETED, f"部分完成：{task}", 1.0)
                await self._log(f"部分完成：{task}", "warning")
            else:
                err_msg = "; ".join(result.errors) if result.errors else "未知錯誤"
                await self._set_status(AgentStatus.ERROR, f"失敗：{task}")
                await self._log(f"失敗：{task} — {err_msg}", "error")

            return result

        except Exception as e:
            self._logger.exception(f"任務執行異常：{task}")
            await self._set_status(AgentStatus.ERROR, f"異常：{task}")
            await self._log(f"執行異常：{task} — {str(e)}", "error")
            return TaskResult(status=TaskStatus.ERROR, errors=[str(e)])

    # ── 狀態與廣播工具方法 ──

    async def _set_status(
        self,
        status: AgentStatus,
        task: str | None = None,
        progress: float = 0.0,
        collaborators: list[str] | None = None,
    ) -> None:
        """更新代理狀態並透過 WebSocket 廣播。"""
        updated = update_agent_status(
            self._id,
            status=status,
            current_task=task,
            progress=progress,
            collaborating_with=collaborators or [],
        )
        if updated:
            await ws_manager.broadcast_agent_status(updated)

    async def update_progress(self, progress: float, message: str | None = None) -> None:
        """更新任務進度（供子類別在 execute 中呼叫）。

        Args:
            progress: 進度值（0.0 ~ 1.0）。
            message: 選填的進度訊息，會寫入工作日誌。
        """
        model = self.model
        updated = update_agent_status(
            self._id,
            progress=progress,
            current_task=message or (model.current_task if model else None),
        )
        if updated:
            await ws_manager.broadcast_agent_status(updated)
        if message:
            await self._log(message)

    async def _log(self, message: str, log_type: str = "info") -> None:
        """寫入工作日誌並廣播。"""
        entry = WorkLogEntry(
            id=str(uuid.uuid4()),
            agent_id=self._id,
            agent_name=self.display_name,
            message=message,
            type=log_type,
        )
        await ws_manager.broadcast_work_log(entry)

    async def send_message(self, message: AgentMessage) -> None:
        """將訊息發送至 MessageBus（需 MessageBus 已初始化）。"""
        from src.agents.message_bus import bus

        await bus.publish(message)

    async def reset(self) -> None:
        """重設代理至待命狀態。"""
        await self._set_status(AgentStatus.IDLE, None, 0.0)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self._id}>"
