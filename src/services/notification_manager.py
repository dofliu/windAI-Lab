"""通知渠道統一管理器。"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from pathlib import Path
from typing import Any

import yaml

from src.services.notifiers.base import BaseNotifier, NotificationPayload, NotificationResult
from src.services.notifiers.email import EmailNotifier
from src.services.notifiers.line import LineNotifier
from src.services.notifiers.webhook import WebhookNotifier

logger = logging.getLogger("windailab.notification_manager")

# 專案根目錄
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class NotificationManager:
    """統一管理通知渠道的註冊、配置載入與非同步分派。"""

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or (_PROJECT_ROOT / "configs" / "alerts" / "channels.yaml")
        self.notifiers: dict[str, BaseNotifier] = {}
        self.config: dict[str, Any] = {}
        self.load_config()

    def load_config(self) -> None:
        """載入通知設定檔並解析環境變數。"""
        if not self.config_path.exists():
            self._create_default_config()

        try:
            with self.config_path.open("r", encoding="utf-8") as stream:
                raw_cfg = yaml.safe_load(stream) or {}

            self.config = self._expand_env_vars(raw_cfg.get("channels", {}))
            self._initialize_notifiers()
        except Exception as e:
            logger.error(f"載入通知設定檔失敗：{e}")

    def register(self, notifier: BaseNotifier) -> None:
        """手動註冊通知渠道。"""
        self.notifiers[notifier.channel_name] = notifier
        logger.info(f"通知渠道註冊成功：{notifier.channel_name}")

    async def dispatch(
        self,
        payload: NotificationPayload,
        channels: list[str],
    ) -> list[NotificationResult]:
        """並行分派通知到指定的渠道。"""
        tasks = []
        for ch in channels:
            notifier = self.notifiers.get(ch)
            if notifier:
                tasks.append(self._send_with_perf(notifier, payload))
            else:
                logger.warning(f"嘗試分派至未啟用或未註冊的渠道：{ch}")

        if not tasks:
            return []

        results = await asyncio.gather(*tasks)
        for r in results:
            if not r.success:
                logger.warning(f"渠道 [{r.channel}] 通知發送失敗：{r.error}")
            else:
                logger.info(f"渠道 [{r.channel}] 通知發送成功（耗時 {r.latency_ms}ms）")

        return list(results)

    def get_all_status(self) -> dict[str, bool]:
        """取得所有渠道是否啟用的狀態。"""
        return {name: notifier.healthcheck() for name, notifier in self.notifiers.items()}

    async def _send_with_perf(
        self, notifier: BaseNotifier, payload: NotificationPayload
    ) -> NotificationResult:
        """包裝單一 Notifier 的異步發送與例外保護。"""
        try:
            return await notifier.send(payload)
        except Exception as e:
            return NotificationResult(
                channel=notifier.channel_name,
                success=False,
                latency_ms=0,
                error=f"Notifier 執行時崩潰：{e}",
            )

    def _initialize_notifiers(self) -> None:
        """根據設定檔初始化啟用的 Notifiers。"""
        self.notifiers.clear()

        # 1. Email Notifier
        email_cfg = self.config.get("email", {})
        if email_cfg.get("enabled", False):
            self.register(EmailNotifier(email_cfg))

        # 2. Webhook Notifier
        webhook_cfg = self.config.get("webhook", {})
        if webhook_cfg.get("enabled", False):
            self.register(WebhookNotifier(webhook_cfg))

        # 3. LINE Notifier
        line_cfg = self.config.get("line", {})
        if line_cfg.get("enabled", False):
            self.register(LineNotifier(line_cfg))

    def _expand_env_vars(self, data: Any) -> Any:
        """遞迴解析設定檔中的 ${VAR} 環境變數。"""
        if isinstance(data, dict):
            return {k: self._expand_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._expand_env_vars(item) for item in data]
        elif isinstance(data, str):
            # 尋找 ${VAR} 格式
            pattern = re.compile(r"\$\{(\w+)\}")
            matches = pattern.findall(data)
            for var in matches:
                env_val = os.getenv(var, "")
                data = data.replace(f"${{{var}}}", env_val)
            return data
        return data

    def _create_default_config(self) -> None:
        """建立預設的通知渠道設定檔。"""
        default_cfg = {
            "channels": {
                "email": {
                    "enabled": False,
                    "smtp_host": "smtp.example.com",
                    "smtp_port": 587,
                    "smtp_user": "${SMTP_USER}",
                    "smtp_password": "${SMTP_PASSWORD}",
                    "from_address": "windailab-alert@example.com",
                    "default_recipients": ["ops-team@example.com"],
                    "use_tls": True,
                    "timeout_seconds": 10,
                },
                "webhook": {
                    "enabled": False,
                    "default_url": "${WEBHOOK_URL}",
                    "default_headers": {"Content-Type": "application/json"},
                    "timeout_seconds": 5,
                    "retry": 2,
                },
                "line": {
                    "enabled": False,
                    "access_token": "${LINE_NOTIFY_TOKEN}",
                    "timeout_seconds": 5,
                },
            }
        }
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self.config_path.open("w", encoding="utf-8") as stream:
                yaml.safe_dump(default_cfg, stream, allow_unicode=True)
            logger.info(f"已建立預設通知渠道設定檔：{self.config_path.name}")
        except Exception as e:
            logger.error(f"建立預設通知設定檔失敗：{e}")


_manager: NotificationManager | None = None


def get_notification_manager() -> NotificationManager:
    """取得全域通知渠道管理器單例。"""
    global _manager
    if _manager is None:
        _manager = NotificationManager()
    return _manager
