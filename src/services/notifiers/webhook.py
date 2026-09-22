"""Webhook 通知渠道實作。"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from src.services.notifiers.base import BaseNotifier, NotificationPayload, NotificationResult

logger = logging.getLogger("windailab.notifiers.webhook")


class WebhookNotifier(BaseNotifier):
    """Webhook 通知渠道 — 透過 HTTP POST 發送 JSON 數據。"""

    channel_name: str = "webhook"

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.default_url = config.get("default_url", "")
        self.default_headers = config.get("default_headers", {})
        self.timeout = float(config.get("timeout_seconds", 5))
        self.retry = int(config.get("retry", 2))

    async def send(self, payload: NotificationPayload) -> NotificationResult:
        start_time = time.time()

        # 決定 URL (支援覆寫)
        url = self.default_url
        if not url:
            return NotificationResult(
                channel=self.channel_name,
                success=False,
                latency_ms=int((time.time() - start_time) * 1000),
                error="未配置 Webhook 接收端 URL",
            )

        # 組裝 JSON payload
        data = {
            "source": "windai-lab",
            "version": "1",
            "alert": {
                "id": payload.alert_id,
                "turbine_id": payload.turbine_id,
                "rule_id": payload.rule_id,
                "rule_name": payload.rule_name,
                "severity": payload.severity,
                "metric": payload.metric,
                "metric_value": payload.metric_value,
                "threshold": payload.threshold,
                "triggered_at": payload.triggered_at.isoformat(),
                "recommended_action": payload.recommended_action,
                "work_order_id": payload.work_order_id,
            },
        }

        # 異步發送 POST，帶重試機制
        headers = {"Content-Type": "application/json"}
        headers.update(self.default_headers)

        attempt = 0
        last_error = ""
        while attempt <= self.retry:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, json=data, headers=headers)
                    if response.status_code in (200, 201, 202, 204):
                        return NotificationResult(
                            channel=self.channel_name,
                            success=True,
                            latency_ms=int((time.time() - start_time) * 1000),
                        )
                    else:
                        last_error = f"HTTP 狀態碼：{response.status_code}"
            except Exception as e:
                last_error = str(e)

            attempt += 1
            if attempt <= self.retry:
                # 指數退避等待
                await asyncio.sleep(attempt * 2)

        return NotificationResult(
            channel=self.channel_name,
            success=False,
            latency_ms=int((time.time() - start_time) * 1000),
            error=f"Webhook 發送失敗，重試耗盡。最後錯誤：{last_error}",
        )
