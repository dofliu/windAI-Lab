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

    _MAX_LOG_BUFFER = 200

    def __init__(self) -> None:
        """初始化連線管理器。"""
        self._active_connections: list[WebSocket] = []
        self._work_log_buffer: list[dict[str, Any]] = []
        self._current_task_id: str | None = None

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

    @property
    def recent_work_logs(self) -> list[dict[str, Any]]:
        """取得最近的工作日誌（供 initial_state 使用）。"""
        return list(self._work_log_buffer)

    async def broadcast_work_log(self, entry: WorkLogEntry) -> None:
        """廣播工作日誌項目並儲存至緩衝區。"""
        payload = entry.model_dump(mode="json")
        # 儲存至緩衝區，確保 refresh 後仍可取得
        self._work_log_buffer.append(payload)
        if len(self._work_log_buffer) > self._MAX_LOG_BUFFER:
            self._work_log_buffer = self._work_log_buffer[-self._MAX_LOG_BUFFER :]
        message = {
            "type": "work_log_entry",
            "timestamp": datetime.now().isoformat(),
            "payload": payload,
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

    async def broadcast_task_lifecycle(
        self,
        event: str,
        task_id: str,
        workflow_name: str = "",
        description: str = "",
        analysis_results: list[dict[str, Any]] | None = None,
    ) -> None:
        """廣播任務生命週期事件（task_started / task_completed）。

        前端據此管理任務邊界：開始時清除舊狀態，完成時封存紀錄。
        """
        if event == "task_started":
            self._current_task_id = task_id
        elif event == "task_completed":
            self._current_task_id = None

        message = {
            "type": event,
            "timestamp": datetime.now().isoformat(),
            "payload": {
                "task_id": task_id,
                "workflow_name": workflow_name,
                "description": description,
            },
        }
        if analysis_results is not None:
            message["payload"]["analysis_results"] = analysis_results
        await self.broadcast(message)

    async def broadcast_analysis_result(self, result_data: dict[str, Any]) -> None:
        """廣播分析結果（圖表資料）至前端戰情中心，並存入 DB。

        result_data 應包含：
        - chart_type: str — 圖表類型（如 "power_curve", "health_score", "experiment"）
        - title: str — 圖表標題
        - data: list[dict] — 圖表資料點
        - metadata: dict — 額外資訊（如模型名稱、R² 等）
        """
        # 持久化至 DB（讓 refresh 後仍可顯示）
        if self._current_task_id:
            try:
                from src.core.database import get_database

                db = get_database()
                db.save_analysis_result(
                    task_id=self._current_task_id,
                    chart_type=result_data.get("chart_type", "unknown"),
                    title=result_data.get("title", ""),
                    data=result_data.get("data"),
                    metadata=result_data.get("metadata"),
                )
            except Exception:
                pass  # DB 不可用時靜默跳過，不影響即時廣播

        message = {
            "type": "analysis_result",
            "timestamp": datetime.now().isoformat(),
            "payload": result_data,
        }
        await self.broadcast(message)

    async def broadcast_alert(self, alert_data: dict[str, Any], is_new: bool = True) -> None:
        """廣播告警事件至前端。

        alert_data 應為完整的告警 dict（從 database 取得）。
        is_new=True 表示新告警，False 表示狀態更新。
        """
        message = {
            "type": "alert_new" if is_new else "alert_updated",
            "timestamp": datetime.now().isoformat(),
            "payload": alert_data,
        }
        await self.broadcast(message)

    async def broadcast_work_order_update(self, order_data: dict[str, Any]) -> None:
        """廣播工單更新事件至前端。"""
        message = {
            "type": "work_order_updated",
            "timestamp": datetime.now().isoformat(),
            "payload": order_data,
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
