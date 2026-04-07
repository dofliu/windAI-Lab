"""共用的 WebSocket manager mock，解決 MagicMock 不支援 await 的問題。"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


def _create_ws_mock() -> AsyncMock:
    """建立完整的 ws_manager AsyncMock。"""
    mock = AsyncMock()
    mock.broadcast = AsyncMock()
    mock.broadcast_work_log = AsyncMock()
    mock.broadcast_agent_status = AsyncMock()
    mock.broadcast_agent_message = AsyncMock()
    mock.broadcast_analysis_result = AsyncMock()
    mock.broadcast_task_lifecycle = AsyncMock()
    return mock


@pytest.fixture(autouse=True)
def mock_ws_manager():
    """自動 mock 所有 ws_manager 引用，避免 await MagicMock 錯誤。

    ws_manager 被引用於三個地方：
    1. src.agents.orchestrator.engine — module-level import
    2. src.agents.base — module-level import
    3. src.api.websocket_manager.manager — 被 message_bus.py 和 skill_composing_agent.py lazy import
    """
    ws_mock = _create_ws_mock()
    with (
        patch("src.agents.orchestrator.engine.ws_manager", ws_mock),
        patch("src.agents.base.ws_manager", ws_mock),
        patch("src.api.websocket_manager.manager", ws_mock),
    ):
        yield ws_mock
