"""通知渠道抽象基底類別與資料結構。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class NotificationPayload:
    """通知載荷 — 任何 Notifier 都能消費此結構。"""

    alert_id: str
    turbine_id: str
    rule_id: str
    rule_name: str
    severity: str          # info / warning / critical
    metric: str
    metric_value: float
    threshold: float
    triggered_at: datetime
    recommended_action: str | None = None
    work_order_id: str | None = None


@dataclass
class NotificationResult:
    """通知結果 — 供呼叫端記錄與重試判斷。"""

    channel: str
    success: bool
    latency_ms: int
    error: str | None = None


class BaseNotifier(ABC):
    """Notifier 抽象基底類別。

    子類別必須實作 send()，輸入 NotificationPayload，回傳 NotificationResult。
    禁止在 send() 中 raise — 所有例外應捕捉並轉為 result.error。
    """

    channel_name: str = "base"

    @abstractmethod
    async def send(self, payload: NotificationPayload) -> NotificationResult:
        """異步發送通知。"""
        pass

    def healthcheck(self) -> bool:
        """可選：渠道健檢（如連線測試）。"""
        return True
