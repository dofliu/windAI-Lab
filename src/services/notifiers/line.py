"""LINE Notify 通知渠道實作。"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any
import httpx

from src.services.notifiers.base import BaseNotifier, NotificationPayload, NotificationResult

logger = logging.getLogger("windailab.notifiers.line")


class LineNotifier(BaseNotifier):
    """LINE Notify 通知渠道 — 透過 LINE Notify API 發送即時通報。"""

    channel_name: str = "line"

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.access_token = config.get("access_token", "")
        self.timeout = float(config.get("timeout_seconds", 5))

    async def send(self, payload: NotificationPayload) -> NotificationResult:
        start_time = time.time()
        
        token = self.access_token
        if not token:
            return NotificationResult(
                channel=self.channel_name,
                success=False,
                latency_ms=int((time.time() - start_time) * 1000),
                error="未配置 LINE Notify Access Token",
            )

        # 組裝 LINE Notify 純文字訊息
        severity_upper = payload.severity.upper()
        msg_lines = [
            f"\n[WindAI][{severity_upper}] {payload.rule_name}",
            f"風機：{payload.turbine_id}",
            f"指標：{payload.metric} = {payload.metric_value}",
            f"臨界值：{payload.threshold}",
            f"時間：{payload.triggered_at.strftime('%Y-%m-%d %H:%M:%S')} (UTC)",
        ]
        if payload.work_order_id:
            msg_lines.append(f"工單：#{payload.work_order_id}")
        if payload.recommended_action:
            msg_lines.append(f"建議動作：{payload.recommended_action}")
            
        message = "\n".join(msg_lines)

        # LINE Notify 採用 Form Data 傳遞 message
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {"message": message}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    "https://notify-api.line.me/api/notify",
                    data=data,
                    headers=headers,
                )
                if response.status_code == 200:
                    return NotificationResult(
                        channel=self.channel_name,
                        success=True,
                        latency_ms=int((time.time() - start_time) * 1000),
                    )
                else:
                    return NotificationResult(
                        channel=self.channel_name,
                        success=False,
                        latency_ms=int((time.time() - start_time) * 1000),
                        error=f"LINE API 回傳狀態碼：{response.status_code} — {response.text}",
                    )
        except Exception as e:
            logger.error(f"LineNotifier 發送失敗：{e}")
            return NotificationResult(
                channel=self.channel_name,
                success=False,
                latency_ms=int((time.time() - start_time) * 1000),
                error=str(e),
            )
