"""WebSocketManager 測試。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.api.websocket_manager import WebSocketManager


def _make_mock_ws(*, should_fail: bool = False) -> AsyncMock:
    """建立模擬的 WebSocket 連線。"""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    if should_fail:
        ws.send_json = AsyncMock(side_effect=RuntimeError("connection closed"))
    else:
        ws.send_json = AsyncMock()
    return ws


class TestWebSocketManager:
    @pytest.fixture()
    def mgr(self) -> WebSocketManager:
        return WebSocketManager()

    @pytest.mark.asyncio
    async def test_connect(self, mgr: WebSocketManager) -> None:
        ws = _make_mock_ws()
        await mgr.connect(ws)
        assert mgr.active_count == 1
        ws.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_multiple(self, mgr: WebSocketManager) -> None:
        ws1 = _make_mock_ws()
        ws2 = _make_mock_ws()
        await mgr.connect(ws1)
        await mgr.connect(ws2)
        assert mgr.active_count == 2

    def test_disconnect(self, mgr: WebSocketManager) -> None:
        ws = _make_mock_ws()
        mgr._active_connections.append(ws)
        mgr.disconnect(ws)
        assert mgr.active_count == 0

    def test_disconnect_nonexistent(self, mgr: WebSocketManager) -> None:
        """斷開不存在的連線不應報錯。"""
        ws = _make_mock_ws()
        mgr.disconnect(ws)  # 不在列表中
        assert mgr.active_count == 0

    @pytest.mark.asyncio
    async def test_send_personal(self, mgr: WebSocketManager) -> None:
        ws = _make_mock_ws()
        data = {"type": "test", "payload": {}}
        await mgr.send_personal(ws, data)
        ws.send_json.assert_called_once_with(data)

    @pytest.mark.asyncio
    async def test_broadcast(self, mgr: WebSocketManager) -> None:
        ws1 = _make_mock_ws()
        ws2 = _make_mock_ws()
        mgr._active_connections = [ws1, ws2]

        data = {"type": "status_update"}
        await mgr.broadcast(data)
        ws1.send_json.assert_called_once_with(data)
        ws2.send_json.assert_called_once_with(data)

    @pytest.mark.asyncio
    async def test_broadcast_removes_dead_connections(self, mgr: WebSocketManager) -> None:
        ws_alive = _make_mock_ws()
        ws_dead = _make_mock_ws(should_fail=True)
        mgr._active_connections = [ws_alive, ws_dead]

        await mgr.broadcast({"type": "ping"})
        assert mgr.active_count == 1
        assert ws_alive in mgr._active_connections
        assert ws_dead not in mgr._active_connections

    @pytest.mark.asyncio
    async def test_broadcast_agent_status(self, mgr: WebSocketManager) -> None:
        ws = _make_mock_ws()
        mgr._active_connections = [ws]

        agent = MagicMock()
        agent.model_dump.return_value = {"id": "test-agent", "status": "idle"}

        await mgr.broadcast_agent_status(agent)
        ws.send_json.assert_called_once()
        call_data = ws.send_json.call_args[0][0]
        assert call_data["type"] == "agent_status_update"
        assert call_data["payload"]["id"] == "test-agent"

    @pytest.mark.asyncio
    async def test_broadcast_work_log(self, mgr: WebSocketManager) -> None:
        ws = _make_mock_ws()
        mgr._active_connections = [ws]

        entry = MagicMock()
        entry.model_dump.return_value = {
            "id": "log-1",
            "agent_id": "a1",
            "message": "hello",
        }

        await mgr.broadcast_work_log(entry)
        call_data = ws.send_json.call_args[0][0]
        assert call_data["type"] == "work_log_entry"

    @pytest.mark.asyncio
    async def test_broadcast_task_progress(self, mgr: WebSocketManager) -> None:
        ws = _make_mock_ws()
        mgr._active_connections = [ws]

        await mgr.broadcast_task_progress("task-1", "agent-1", 0.75, "working")
        call_data = ws.send_json.call_args[0][0]
        assert call_data["type"] == "task_progress"
        assert call_data["payload"]["progress"] == 0.75

    @pytest.mark.asyncio
    async def test_broadcast_agent_message(self, mgr: WebSocketManager) -> None:
        ws = _make_mock_ws()
        mgr._active_connections = [ws]

        msg = {"from": "agent-a", "to": "agent-b", "content": "hello"}
        await mgr.broadcast_agent_message(msg)
        call_data = ws.send_json.call_args[0][0]
        assert call_data["type"] == "agent_message"

    @pytest.mark.asyncio
    async def test_broadcast_file_event(self, mgr: WebSocketManager) -> None:
        ws = _make_mock_ws()
        mgr._active_connections = [ws]

        event = {"type": "file_detected", "path": "/data/new_file.csv"}
        await mgr.broadcast_file_event(event)
        ws.send_json.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_broadcast_empty_connections(self, mgr: WebSocketManager) -> None:
        """無連線時 broadcast 不報錯。"""
        await mgr.broadcast({"type": "test"})
        assert mgr.active_count == 0
