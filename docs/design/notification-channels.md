# 通知渠道設計文件（Notification Channels Design）

> **對應 Issue**：[#42 [E2] 通知渠道](https://github.com/dofliu/windai-lab/issues/42)
> **父 Epic**：[#33 [Epic E] 告警規則引擎](https://github.com/dofliu/windai-lab/issues/33)
> **依賴**：✅ #41 告警規則引擎核心（已完成）
> **文件版本**：v0.1（規劃階段）
> **建立日期**：2026-04-20
> **作者**：wLab:director + wEng:backend-dev（AI 輔助）

---

## 1. 目標與範圍

### 目標

為 WindAI Lab 的告警規則引擎（#41）補上「外部通知」能力。當告警規則觸發時，能透過多種渠道將告警內容即時送達運維人員與相關關係人，縮短告警響應時間。

### 範圍（v1 本次實作）

| 渠道 | 納入 | 備註 |
|------|------|------|
| **Email（SMTP）** | ✅ | 首選渠道，依賴 SMTP 設定，跨平台 |
| **Webhook** | ✅ | 通用 HTTP POST，可串 Slack / Teams / 自訂接收端 |
| **LINE Notify** | ✅ | 台灣現場常用，適合第一線運維手機告警 |

### 不在本次範圍（v2+）

- 電話語音通報（Twilio / Asterisk）
- SMS（簡訊）
- 推播通知（行動 App）
- 告警升級（Escalation）多層通知流程

---

## 2. 架構概覽

```
┌──────────────────────┐
│  AlertRuleEngine     │  (#41 已實作)
│  - evaluate()        │
│  - _trigger_alert()  │
└──────────┬───────────┘
           │ Notification event
           ▼
┌──────────────────────┐
│  NotificationManager │  (新增)
│  - dispatch(alert)   │
│  - register(n)       │
│  - list_channels()   │
└──────────┬───────────┘
           │ fan-out
  ┌────────┼────────────────────────┐
  ▼        ▼                        ▼
┌─────┐ ┌──────────┐ ┌───────────────┐
│Email│ │ Webhook  │ │ LINE Notify   │
└─────┘ └──────────┘ └───────────────┘
```

- **AlertRuleEngine**（已存在）不直接知道渠道實作，僅發佈「告警事件」
- **NotificationManager**（新增）負責根據規則的 `notify_channels` 欄位分派
- 每個 **Notifier** 實作統一的抽象介面，遵循 Liskov 替換原則

---

## 3. 介面定義

### 3.1 抽象基底類別

```python
# src/services/notifiers/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class NotificationPayload:
    """通知載荷 — 任何 Notifier 都能消費此結構。"""

    alert_id: int
    turbine_id: str
    rule_id: str
    rule_name: str
    severity: str          # info / warning / critical
    metric: str
    metric_value: float
    threshold: float
    triggered_at: datetime
    recommended_action: str | None = None
    work_order_id: int | None = None


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
    def send(self, payload: NotificationPayload) -> NotificationResult: ...

    def healthcheck(self) -> bool:
        """可選：渠道健檢（如 SMTP 連線測試）。"""
        return True
```

### 3.2 Notifier 實作清單

| 類別 | 檔案 | 主要依賴 | 設定來源 |
|------|------|----------|----------|
| `EmailNotifier` | `src/services/notifiers/email.py` | `smtplib`（標準庫） | `configs/alerts/channels.yaml` |
| `WebhookNotifier` | `src/services/notifiers/webhook.py` | `httpx` | 同上 |
| `LineNotifier` | `src/services/notifiers/line.py` | `httpx` | 同上 |

### 3.3 NotificationManager

```python
# src/services/notification_manager.py
class NotificationManager:
    """統一派送告警通知。

    由 AlertRuleEngine 呼叫 dispatch()，根據 rule.notify_channels 分派給對應 Notifier。
    """

    def __init__(self, notifiers: dict[str, BaseNotifier]) -> None: ...

    def dispatch(
        self,
        payload: NotificationPayload,
        channels: list[str],
    ) -> list[NotificationResult]: ...

    def register(self, notifier: BaseNotifier) -> None: ...
```

---

## 4. 設定檔 Schema

### 4.1 `configs/alerts/channels.yaml`（新增）

```yaml
# 通知渠道全域設定
# 機密資訊（SMTP 密碼、LINE Token）透過環境變數注入，此處僅放預留位置。

channels:
  email:
    enabled: true
    smtp_host: "smtp.example.com"
    smtp_port: 587
    smtp_user: "${SMTP_USER}"
    smtp_password: "${SMTP_PASSWORD}"
    from_address: "windailab-alert@example.com"
    default_recipients:
      - "ops-team@example.com"
    use_tls: true
    timeout_seconds: 10

  webhook:
    enabled: true
    default_url: "${WEBHOOK_URL}"
    default_headers:
      Content-Type: "application/json"
    timeout_seconds: 5
    retry: 2

  line:
    enabled: false
    access_token: "${LINE_NOTIFY_TOKEN}"
    timeout_seconds: 5
```

### 4.2 規則層覆寫（`configs/alerts/rules.yaml` 擴充，配合 #43）

```yaml
rules:
  - id: power_deviation_high
    name: 功率偏差過大
    enabled: true
    severity: critical
    notify_channels:
      - email
      - webhook
    notify_overrides:
      email:
        recipients:
          - "site-manager@example.com"
      webhook:
        url: "https://hooks.slack.com/services/XXX/YYY/ZZZ"
```

---

## 5. 訊息模板

### 5.1 Email

```
Subject: [WindAI Alert][{severity_upper}] {rule_name} — {turbine_id}

風機編號：{turbine_id}
規則名稱：{rule_name}
嚴重程度：{severity}
觸發指標：{metric} = {metric_value}
閾值：{threshold}
觸發時間：{triggered_at}（UTC）
建議動作：{recommended_action}
工單編號：{work_order_id}

此郵件由 WindAI Lab 自動發送，請勿直接回覆。
```

### 5.2 Webhook（JSON）

```json
{
  "source": "windai-lab",
  "version": "1",
  "alert": {
    "id": 123,
    "turbine_id": "WTG-01",
    "rule_id": "power_deviation_high",
    "rule_name": "功率偏差過大",
    "severity": "critical",
    "metric": "power_deviation_pct",
    "metric_value": 18.4,
    "threshold": 15,
    "triggered_at": "2026-04-20T08:30:00Z",
    "recommended_action": "檢查槳距角與功率曲線偏差",
    "work_order_id": 45
  }
}
```

### 5.3 LINE Notify

```
[WindAI][CRITICAL] 功率偏差過大
風機 WTG-01 power_deviation_pct=18.4% 超過閾值 15%
時間：2026-04-20 16:30（本地）
工單：#45
```

---

## 6. 與告警引擎整合

在 `src/services/alert_engine.py` 的 `_trigger_alert()` 尾端插入：

```python
# pseudo-code
if rule.notify_channels:
    payload = NotificationPayload.from_alert(alert, rule, work_order_id)
    results = notification_manager.dispatch(payload, rule.notify_channels)
    for r in results:
        if not r.success:
            logger.warning("notification_failed", extra={"channel": r.channel, "error": r.error})
```

關鍵原則：
- **非阻塞**：通知失敗不影響告警產生與工單建立
- **可觀測**：每筆通知成敗寫入結構化 log，供 `/api/metrics` 聚合（#45 依賴）
- **可重試**：Webhook / LINE 採用指數退避（2s → 4s → 放棄）

---

## 7. 測試策略

| 類別 | 範圍 | 工具 |
|------|------|------|
| **單元測試** | 每個 Notifier 的 send() — mock SMTP / httpx | `pytest` + `pytest-mock` |
| **整合測試** | NotificationManager 的分派邏輯、多渠道 fan-out | `pytest` |
| **契約測試** | Webhook payload JSON Schema 驗證 | `jsonschema` |
| **手動驗證** | 實際寄送到測試信箱 / LINE Notify 測試 Token | 人工 |

測試檔案：
- `tests/unit/test_notifiers_email.py`
- `tests/unit/test_notifiers_webhook.py`
- `tests/unit/test_notifiers_line.py`
- `tests/unit/test_notification_manager.py`

目標覆蓋率：≥ 85%（新增模組）。

---

## 8. 安全與合規

| 風險 | 緩解 |
|------|------|
| SMTP 密碼外洩 | 一律透過環境變數注入，不寫入 YAML |
| LINE Token 外洩 | 同上，且設定檔 `.gitignore` 已覆蓋 `.env` |
| Webhook URL 被盜用 | 以簽名 header（`X-WindAI-Signature`）做 HMAC-SHA256 驗證（v1.1） |
| 告警風暴 | 仰賴 #41 已實作的靜默期（`silence_minutes`）與 rule 層 debounce |
| 個資外洩 | 訊息模板僅包含風機編號、指標數值，不包含人員個資 |

---

## 9. 驗收標準（對應 #42）

- [ ] `BaseNotifier` 抽象類別實作完成
- [ ] `EmailNotifier` / `WebhookNotifier` / `LineNotifier` 三個渠道可運作
- [ ] `NotificationManager` 可根據規則分派
- [ ] `configs/alerts/channels.yaml` 可被正確載入
- [ ] 單元測試覆蓋率 ≥ 85%
- [ ] 實際寄送一封測試告警到本地 MailHog / 測試 Webhook
- [ ] 文件（本檔）與 API 變更紀錄同步更新

---

## 10. 時程建議

| 階段 | 預估工時 | 產出 |
|------|----------|------|
| **設計定稿**（本文件） | 1h | 本設計文件 v0.1 |
| **介面 + Email** | 3h | `base.py` + `email.py` + 測試 |
| **Webhook + LINE** | 3h | 兩個 Notifier + 測試 |
| **Manager + 告警引擎整合** | 2h | `notification_manager.py` + integration test |
| **文件 + API 更新** | 1h | 更新 `daily_report.md` + `docs/work-logs/*` |
| **合計** | **10h** | — |

建議切分為 **2 個 PR**（每個 ≤ 150 行變更）：
- PR A：`base` + `EmailNotifier` + 測試
- PR B：`Webhook` + `LINE` + `NotificationManager` + 整合

---

## 11. 延伸閱讀

- #41 告警規則引擎核心（已完成）
- #43 告警規則 YAML 設定（配合 `notify_channels` 欄位）
- #45 系統效能追蹤（通知延遲指標來源）
- `docs/architecture-design.md` — 整體架構
- `docs/work-logs/2026-04/WLAB-20260420-01-notification-design.md` — 本文件工作紀錄

---

*本設計文件由 wEng:backend-dev 於 2026-04-20 起草，經 wLab:director 審閱。*
