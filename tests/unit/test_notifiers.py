"""單元測試 — 通知渠道與管理器。"""

from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch
import pytest

from src.services.notifiers.base import NotificationPayload, NotificationResult
from src.services.notifiers.email import EmailNotifier
from src.services.notifiers.webhook import WebhookNotifier
from src.services.notifiers.line import LineNotifier
from src.services.notification_manager import NotificationManager


@pytest.fixture
def sample_payload():
    return NotificationPayload(
        alert_id="ALERT-TEST-001",
        turbine_id="WT-01",
        rule_id="power_deviation_high",
        rule_name="功率偏差過大",
        severity="critical",
        metric="power_deviation_pct",
        metric_value=18.4,
        threshold=15.0,
        triggered_at=datetime.utcnow(),
        recommended_action="請檢查槳距角",
        work_order_id="WO-TEST-001",
    )


@pytest.mark.asyncio
async def test_email_notifier_send(sample_payload):
    config = {
        "smtp_host": "smtp.test.com",
        "smtp_port": 587,
        "smtp_user": "user@test.com",
        "smtp_password": "password",
        "from_address": "alert@windai.com",
        "default_recipients": ["ops@windai.com"],
        "use_tls": True,
        "timeout_seconds": 5,
    }
    
    notifier = EmailNotifier(config)
    
    # Mock to_thread 以避免真實發送郵件
    with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        result = await notifier.send(sample_payload)
        assert result.success is True
        assert result.channel == "email"
        mock_thread.assert_called_once()


@pytest.mark.asyncio
async def test_webhook_notifier_send(sample_payload):
    config = {
        "default_url": "https://webhook.test.com/alert",
        "default_headers": {"X-Custom": "test"},
        "timeout_seconds": 2,
        "retry": 0,
    }
    
    notifier = WebhookNotifier(config)
    
    # Mock httpx.AsyncClient.post
    mock_response = MagicMock()
    mock_response.status_code = 200
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await notifier.send(sample_payload)
        assert result.success is True
        assert result.channel == "webhook"
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_line_notifier_send(sample_payload):
    config = {
        "access_token": "LINE_TOKEN_123",
        "timeout_seconds": 2,
    }
    
    notifier = LineNotifier(config)
    
    # Mock httpx.AsyncClient.post
    mock_response = MagicMock()
    mock_response.status_code = 200
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await notifier.send(sample_payload)
        assert result.success is True
        assert result.channel == "line"
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_notification_manager_dispatch(sample_payload):
    manager = NotificationManager()
    
    # 建立三個 mock notifiers
    mock_email = AsyncMock()
    mock_email.channel_name = "email"
    mock_email.send.return_value = NotificationResult(channel="email", success=True, latency_ms=10)
    
    mock_webhook = AsyncMock()
    mock_webhook.channel_name = "webhook"
    mock_webhook.send.return_value = NotificationResult(channel="webhook", success=True, latency_ms=15)
    
    manager.register(mock_email)
    manager.register(mock_webhook)
    
    # 分派到這兩個 channels
    results = await manager.dispatch(sample_payload, ["email", "webhook"])
    assert len(results) == 2
    assert results[0].success is True
    assert results[1].success is True
    
    mock_email.send.assert_called_once()
    mock_webhook.send.assert_called_once()
