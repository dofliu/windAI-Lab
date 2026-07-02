"""Email 通知渠道實作。"""

from __future__ import annotations

import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import smtplib
import time
from typing import Any

from src.services.notifiers.base import BaseNotifier, NotificationPayload, NotificationResult

logger = logging.getLogger("windailab.notifiers.email")


class EmailNotifier(BaseNotifier):
    """Email 通知渠道 — 使用 smtplib 發送郵件。"""

    channel_name: str = "email"

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.smtp_host = config.get("smtp_host", "localhost")
        self.smtp_port = int(config.get("smtp_port", 25))
        self.smtp_user = config.get("smtp_user", "")
        self.smtp_password = config.get("smtp_password", "")
        self.from_address = config.get("from_address", "windailab-alert@example.com")
        self.default_recipients = config.get("default_recipients", [])
        self.use_tls = config.get("use_tls", False)
        self.timeout = float(config.get("timeout_seconds", 10))

    async def send(self, payload: NotificationPayload) -> NotificationResult:
        start_time = time.time()
        
        # 決定收件者 (支援從額外 metadata 中傳入 recipients，否則用預設值)
        recipients = self.default_recipients
        
        if not recipients:
            return NotificationResult(
                channel=self.channel_name,
                success=False,
                latency_ms=int((time.time() - start_time) * 1000),
                error="未配置收件者郵箱",
            )

        try:
            # 建立郵件訊息
            msg = MIMEMultipart()
            msg["From"] = self.from_address
            msg["To"] = ", ".join(recipients)
            
            severity_upper = payload.severity.upper()
            msg["Subject"] = f"[WindAI Alert][{severity_upper}] {payload.rule_name} — {payload.turbine_id}"
            
            # 渲染郵件內文
            body_text = (
                f"風機編號：{payload.turbine_id}\n"
                f"規則名稱：{payload.rule_name}\n"
                f"嚴重程度：{payload.severity}\n"
                f"觸發指標：{payload.metric} = {payload.metric_value}\n"
                f"臨界值：{payload.threshold}\n"
                f"觸發時間：{payload.triggered_at.strftime('%Y-%m-%d %H:%M:%S')} (UTC)\n"
            )
            if payload.recommended_action:
                body_text += f"建議動作：{payload.recommended_action}\n"
            if payload.work_order_id:
                body_text += f"工單編號：{payload.work_order_id}\n"
                
            body_text += "\n此郵件由 WindAI Lab 自動發送，請勿直接回覆。"
            msg.attach(MIMEText(body_text, "plain", "utf-8"))
            
            # 異步執行同步 smtplib 寄送
            await asyncio.to_thread(self._send_sync, msg, recipients)
            
            return NotificationResult(
                channel=self.channel_name,
                success=True,
                latency_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            logger.error(f"EmailNotifier 發送失敗：{e}")
            return NotificationResult(
                channel=self.channel_name,
                success=False,
                latency_ms=int((time.time() - start_time) * 1000),
                error=str(e),
            )

    def _send_sync(self, msg: MIMEMultipart, recipients: list[str]) -> None:
        """同步寄送郵件邏輯。"""
        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=self.timeout) as server:
            if self.use_tls:
                server.starttls()
            if self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.from_address, recipients, msg.as_string())
