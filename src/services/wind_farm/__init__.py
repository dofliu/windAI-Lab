"""風場運維服務核心資料模型。

定義風場、工單、監控紀錄等核心業務實體。
WindAI Lab 扮演一間風場運維公司，管理多個客戶風場，
透過定期監控、告警判斷、自動派工提供專業服務。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

# ════════════════════════════════════════════════════════════════
# 風場（客戶）
# ════════════════════════════════════════════════════════════════


class DataSourceType(StrEnum):
    """資料來源類型。"""

    LOCAL_FILE = "local_file"
    """本地檔案 / 資料夾（開發或離線分析用）。"""

    REST_API = "rest_api"
    """遠端 REST API。"""

    OPC_UA = "opc_ua"
    """OPC UA 即時連線（PLC / SCADA 系統）。"""

    SFTP = "sftp"
    """SFTP 檔案傳輸。"""


class WindFarmStatus(StrEnum):
    """風場連線與監控狀態。"""

    ACTIVE = "active"
    """正常監控中。"""

    PAUSED = "paused"
    """暫停監控（手動暫停或維護中）。"""

    ERROR = "error"
    """連線異常（無法取得資料）。"""

    ONBOARDING = "onboarding"
    """新客戶上線中，尚未完成初始設定。"""


class HealthLevel(StrEnum):
    """風機健康等級。"""

    HEALTHY = "healthy"
    """健康分數 >= 80，綠燈。"""

    WARNING = "warning"
    """健康分數 60~79，黃燈。"""

    CRITICAL = "critical"
    """健康分數 < 60，紅燈。"""

    UNKNOWN = "unknown"
    """尚未進行健康評估。"""


@dataclass
class DataSourceConfig:
    """資料來源連線設定。"""

    source_type: DataSourceType = DataSourceType.LOCAL_FILE
    path: str = ""
    """本地路徑 / API URL / OPC UA endpoint。"""

    auth_token: str = ""
    """API 認證令牌（不寫入日誌）。"""

    username: str = ""
    password: str = ""
    extra: dict[str, Any] = field(default_factory=dict)
    """額外設定（如 OPC UA node IDs、SFTP port 等）。"""


@dataclass
class TurbineStatus:
    """單台風機的即時狀態快照。"""

    turbine_id: str = ""
    health_score: float = -1.0
    health_level: HealthLevel = HealthLevel.UNKNOWN
    last_check_at: str = ""
    anomaly_count: int = 0
    power_curve_deviation_pct: float = 0.0
    active_ticket_id: str | None = None


@dataclass
class WindFarm:
    """風場（客戶）實體。

    代表一個受 WindAI Lab 監控的風場。
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    """風場名稱（如「彰芳西島海上風場」）。"""

    location: str = ""
    """風場位置描述。"""

    turbine_count: int = 0
    """風機數量。"""

    rated_power_mw: float = 0.0
    """風場總額定容量 (MW)。"""

    data_source: DataSourceConfig = field(default_factory=DataSourceConfig)
    """SCADA 資料來源設定。"""

    status: WindFarmStatus = WindFarmStatus.ONBOARDING
    poll_interval_min: int = 60
    """資料輪詢間隔（分鐘）。"""

    alert_threshold_warning: float = 80.0
    """健康分數低於此值 → 黃色告警。"""

    alert_threshold_critical: float = 60.0
    """健康分數低於此值 → 紅色告警，自動派工。"""

    auto_diagnose: bool = True
    """紅色告警時是否自動觸發 /diagnose 工作流程。"""

    turbines: dict[str, TurbineStatus] = field(default_factory=dict)
    """各風機的即時狀態，鍵為 turbine_id。"""

    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_poll_at: str = ""
    last_health_check_at: str = ""
    consecutive_errors: int = 0

    tags: list[str] = field(default_factory=list)
    """標籤（如 "offshore", "onshore", "VIP"）。"""

    notes: str = ""
    """備註。"""


# ════════════════════════════════════════════════════════════════
# 服務工單
# ════════════════════════════════════════════════════════════════


class TicketPriority(StrEnum):
    """工單優先級。"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketStatus(StrEnum):
    """工單狀態。"""

    OPEN = "open"
    """新建，等待分派。"""

    ASSIGNED = "assigned"
    """已分派給代理團隊。"""

    IN_PROGRESS = "in_progress"
    """處理中。"""

    PENDING_REVIEW = "pending_review"
    """待總監審核。"""

    RESOLVED = "resolved"
    """已解決（報告已交付）。"""

    CLOSED = "closed"
    """已關閉。"""


class TicketTrigger(StrEnum):
    """工單觸發來源。"""

    AUTO_MONITOR = "auto_monitor"
    """自動監控告警觸發。"""

    MANUAL = "manual"
    """客戶或操作員手動建立。"""

    SCHEDULED = "scheduled"
    """排程任務（如月度評估）。"""


@dataclass
class ServiceTicket:
    """服務工單。

    記錄一次完整的服務事件：從問題發現到診斷、報告、交付。
    """

    id: str = field(
        default_factory=lambda: f"TK-{datetime.now(UTC).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    )
    wind_farm_id: str = ""
    wind_farm_name: str = ""
    turbine_id: str = ""

    title: str = ""
    description: str = ""

    priority: TicketPriority = TicketPriority.MEDIUM
    status: TicketStatus = TicketStatus.OPEN
    trigger: TicketTrigger = TicketTrigger.MANUAL

    assigned_agents: list[str] = field(default_factory=list)
    """負責的代理 ID 列表。"""

    workflow_id: str | None = None
    """關聯的 workflow 執行 ID。"""

    health_score_at_creation: float | None = None
    anomaly_summary: str = ""

    # ── 時間軸 ──
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    assigned_at: str | None = None
    started_at: str | None = None
    resolved_at: str | None = None
    closed_at: str | None = None

    # ── 結果 ──
    resolution: str = ""
    """解決方案摘要。"""

    report_markdown: str = ""
    """交付的報告內容。"""

    findings: dict[str, Any] = field(default_factory=dict)
    """診斷發現（結構化資料）。"""

    comments: list[dict[str, str]] = field(default_factory=list)
    """工單留言紀錄 [{agent_id, message, timestamp}]。"""


# ════════════════════════════════════════════════════════════════
# 監控紀錄
# ════════════════════════════════════════════════════════════════


class AlertSeverity(StrEnum):
    """告警嚴重度。"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class MonitorRecord:
    """單次監控紀錄。"""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    wind_farm_id: str = ""
    turbine_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    health_score: float = -1.0
    anomaly_count: int = 0
    power_curve_deviation_pct: float = 0.0
    efficiency_loss_pct: float = 0.0
    alert_severity: AlertSeverity | None = None
    ticket_id: str | None = None
    """若觸發了工單，記錄工單 ID。"""

    details: dict[str, Any] = field(default_factory=dict)
