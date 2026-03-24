"""WindAI Lab 全域常數定義。

集中管理系統中使用的常數值，包含代理層級定義、
風機運行參數預設值、以及任務 ID 格式等。
"""

from __future__ import annotations

# ── 代理 Namespace 定義 ──
AGENT_NAMESPACES: dict[str, str] = {
    "wLab": "WindAI Lab Leadership",
    "wData": "WindAI Data Engineering",
    "wAI": "WindAI AI/ML",
    "wDomain": "WindAI Domain Knowledge",
    "wEng": "WindAI Software Engineering",
    "wRes": "WindAI Research & Docs",
}

# ── 代理層級 ──
AGENT_TIERS: dict[str, int] = {
    "leadership": 1,
    "data": 2,
    "ai-ml": 3,
    "domain": 4,
    "engineering": 5,
    "research": 6,
}

# ── 代理狀態顏色 ──
STATUS_COLORS: dict[str, str] = {
    "idle": "#9ca3af",  # 灰色
    "working": "#22c55e",  # 綠色
    "waiting": "#eab308",  # 黃色
    "completed": "#3b82f6",  # 藍色
    "error": "#ef4444",  # 紅色
    "offline": "#6b7280",  # 深灰
}

# ── 風機運行參數預設值（Senvion MM92） ──
DEFAULT_RATED_POWER_KW: float = 2050.0
DEFAULT_ROTOR_DIAMETER_M: float = 92.0
DEFAULT_CUT_IN_SPEED_MS: float = 3.0
DEFAULT_RATED_WIND_SPEED_MS: float = 12.5
DEFAULT_CUT_OUT_SPEED_MS: float = 25.0
DEFAULT_AIR_DENSITY_KGM3: float = 1.225

# ── SCADA 資料 ──
SCADA_SAMPLING_INTERVAL_MIN: int = 10
SCADA_REQUIRED_COLUMNS: list[str] = [
    "wind_speed",
    "power_output",
    "rotor_speed",
    "blade_pitch_angle",
    "nacelle_direction",
]

# ── 任務 ID 格式 ──
TASK_ID_PREFIX: str = "WLAB"

# ── 訊息類型 ──
WS_MESSAGE_TYPES: dict[str, str] = {
    "INITIAL_STATE": "initial_state",
    "AGENT_STATUS_UPDATE": "agent_status_update",
    "WORK_LOG_ENTRY": "work_log_entry",
    "TASK_PROGRESS": "task_progress",
    "WORKFLOW_START": "workflow_start",
    "WORKFLOW_COMPLETE": "workflow_complete",
    "WORKFLOW_ERROR": "workflow_error",
}
