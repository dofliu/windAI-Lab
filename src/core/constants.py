"""WindAI Lab 全域常數定義。

集中管理系統中使用的常數值，包含代理層級定義、
風機運行參數預設值、以及任務 ID 格式等。
"""

from __future__ import annotations

from dataclasses import dataclass

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

# ── 風機運行參數預設值（通用保守值） ──
DEFAULT_RATED_POWER_KW: float = 2050.0
DEFAULT_ROTOR_DIAMETER_M: float = 92.0
DEFAULT_CUT_IN_SPEED_MS: float = 3.0
DEFAULT_RATED_WIND_SPEED_MS: float = 12.5
DEFAULT_CUT_OUT_SPEED_MS: float = 25.0
DEFAULT_AIR_DENSITY_KGM3: float = 1.225


@dataclass
class TurbineProfile:
    """風機參數描述，供下游模組動態使用。

    由 TurbineProfilerSkill 從 SCADA 資料自動推斷，
    或由使用者手動指定。所有下游分析模組應透過此結構
    取得風機參數，避免各自硬編碼。

    Attributes
    ----------
    rated_power_kw : float
        額定功率 (kW)。
    rotor_diameter_m : float | None
        轉子直徑 (m)，若無法推斷則為 None。
    cut_in_speed_ms : float
        切入風速 (m/s)。
    rated_wind_speed_ms : float
        額定風速 (m/s)。
    cut_out_speed_ms : float
        切出風速 (m/s)。
    air_density_kgm3 : float
        空氣密度 (kg/m³)。
    """

    rated_power_kw: float = DEFAULT_RATED_POWER_KW
    rotor_diameter_m: float | None = DEFAULT_ROTOR_DIAMETER_M
    cut_in_speed_ms: float = DEFAULT_CUT_IN_SPEED_MS
    rated_wind_speed_ms: float = DEFAULT_RATED_WIND_SPEED_MS
    cut_out_speed_ms: float = DEFAULT_CUT_OUT_SPEED_MS
    air_density_kgm3: float = DEFAULT_AIR_DENSITY_KGM3

    @classmethod
    def from_profiler_dict(cls, d: dict) -> TurbineProfile:
        """從 TurbineProfilerSkill 輸出的 dict 建構。"""
        return cls(
            rated_power_kw=d.get("rated_power_kw", DEFAULT_RATED_POWER_KW),
            rotor_diameter_m=d.get("rotor_diameter_m"),
            cut_in_speed_ms=d.get("cut_in_speed_ms", DEFAULT_CUT_IN_SPEED_MS),
            rated_wind_speed_ms=d.get("rated_wind_speed_ms", DEFAULT_RATED_WIND_SPEED_MS),
            cut_out_speed_ms=d.get("cut_out_speed_ms", DEFAULT_CUT_OUT_SPEED_MS),
        )

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
    "AGENT_MESSAGE": "agent_message",
    "WORKFLOW_START": "workflow_start",
    "WORKFLOW_COMPLETE": "workflow_complete",
    "WORKFLOW_ERROR": "workflow_error",
}

# ── 代理間訊息類型 ──
AGENT_MESSAGE_TYPES: dict[str, str] = {
    "task_request": "請求代理執行任務",
    "task_result": "任務結果回報",
    "task_progress": "任務進度更新",
    "task_error": "任務失敗通知",
    "query": "查詢訊息",
    "response": "回覆訊息",
    "notification": "通知訊息",
    "delegation": "任務委派",
}
