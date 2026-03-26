"""WindAI Lab WebSocket 連線管理器。

負責管理所有 WebSocket 客戶端連線，支援即時廣播代理狀態更新、
工作日誌與任務進度等訊息至所有已連線的前端客戶端。
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import WebSocket

    from src.api.models import AgentModel, WorkLogEntry


class WebSocketManager:
    """WebSocket 連線管理器，追蹤並管理所有活躍連線。"""

    def __init__(self) -> None:
        """初始化連線管理器。"""
        self._active_connections: list[WebSocket] = []

    @property
    def active_count(self) -> int:
        """取得當前活躍連線數量。"""
        return len(self._active_connections)

    async def connect(self, websocket: WebSocket) -> None:
        """接受新的 WebSocket 連線並加入追蹤清單。"""
        await websocket.accept()
        self._active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """從追蹤清單中移除已斷開的連線。"""
        if websocket in self._active_connections:
            self._active_connections.remove(websocket)

    async def send_personal(self, websocket: WebSocket, data: dict[str, Any]) -> None:
        """向指定客戶端傳送訊息。"""
        await websocket.send_json(data)

    async def broadcast(self, data: dict[str, Any]) -> None:
        """向所有已連線客戶端廣播訊息。斷線的客戶端會自動移除。"""
        disconnected: list[WebSocket] = []
        for connection in self._active_connections:
            try:
                await connection.send_json(data)
            except Exception:
                disconnected.append(connection)
        # 清理已斷線的連線
        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_agent_status(self, agent: AgentModel) -> None:
        """廣播代理狀態更新訊息。"""
        message = {
            "type": "agent_status_update",
            "timestamp": datetime.now().isoformat(),
            "payload": agent.model_dump(mode="json"),
        }
        await self.broadcast(message)

    async def broadcast_work_log(self, entry: WorkLogEntry) -> None:
        """廣播工作日誌項目。"""
        message = {
            "type": "work_log_entry",
            "timestamp": datetime.now().isoformat(),
            "payload": entry.model_dump(mode="json"),
        }
        await self.broadcast(message)

    async def broadcast_task_progress(
        self,
        task_id: str,
        agent_id: str,
        progress: float,
        status: str,
    ) -> None:
        """廣播任務進度更新。"""
        message = {
            "type": "task_progress",
            "timestamp": datetime.now().isoformat(),
            "payload": {
                "task_id": task_id,
                "agent_id": agent_id,
                "progress": progress,
                "status": status,
            },
        }
        await self.broadcast(message)

    async def broadcast_agent_message(self, agent_message: dict[str, Any]) -> None:
        """廣播代理間訊息至前端，用於虛擬辦公室的訊息流視覺化。"""
        message = {
            "type": "agent_message",
            "timestamp": datetime.now().isoformat(),
            "payload": agent_message,
        }
        await self.broadcast(message)

    async def broadcast_file_event(self, event_data: dict[str, Any]) -> None:
        """廣播檔案監控事件（偵測到新檔案 / 處理完成 / 錯誤）。

        event_data 的 type 欄位：
        - "file_detected": 偵測到新檔案
        - "file_processed": 檔案已自動載入並分析完成
        - "file_error": 檔案處理失敗
        """
        await self.broadcast(event_data)


# 全域單例實例
manager = WebSocketManager()
