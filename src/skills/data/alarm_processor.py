"""警報事件清單處理技能 — 將離散警報事件轉換為時間序列特徵。

風機 SCADA 系統產出的警報事件清單（event log）是離散事件：
每一行是一筆警報（時間戳 + 警報碼 + 持續時間 + 嚴重度 + 元件）。
這類資料無法直接用於時間序列分析或 ML 模型。

AlarmProcessorSkill 負責：
1. 自動偵測警報清單的欄位格式（時間、警報碼、持續時間等）
2. 解析並正規化警報事件
3. 轉換為時間序列特徵 DataFrame：
   - 每日/每時段警報次數
   - 每日/每時段警報持續時間
   - 警報類型 one-hot 編碼
   - MTBF（平均故障間隔時間）
   - 警報頻率趨勢
4. 產出警報統計摘要報告

輸出的 DataFrame 可直接與 SCADA 10min 資料合併，供下游分析使用。
"""

from __future__ import annotations

import asyncio
from typing import Any

import pandas as pd

from src.skills.base import BaseSkill, ProgressCallback, SkillInput, SkillOutput, SkillStatus

# ── 警報欄位自動偵測關鍵字 ────────────────────────────────────

_TIMESTAMP_KEYWORDS = ["time", "date", "timestamp", "start", "occurred", "發生時間"]
_END_TIME_KEYWORDS = ["end", "cleared", "reset", "結束時間", "復歸"]
_CODE_KEYWORDS = ["code", "alarm", "error", "fault", "event", "警報碼", "故障碼", "代碼"]
_DESCRIPTION_KEYWORDS = ["description", "message", "text", "desc", "說明", "描述", "訊息"]
_SEVERITY_KEYWORDS = ["severity", "level", "priority", "grade", "嚴重度", "等級"]
_COMPONENT_KEYWORDS = ["component", "subsystem", "system", "module", "元件", "子系統"]
_DURATION_KEYWORDS = ["duration", "持續時間", "持續"]

# 警報嚴重度正規化對照
_SEVERITY_MAP: dict[str, int] = {
    "info": 0,
    "information": 0,
    "low": 1,
    "minor": 1,
    "warning": 2,
    "medium": 2,
    "high": 3,
    "major": 3,
    "critical": 4,
    "emergency": 4,
    "fault": 3,
    "error": 3,
    "alarm": 2,
    "0": 0,
    "1": 1,
    "2": 2,
    "3": 3,
    "4": 4,
}


class AlarmProcessorSkill(BaseSkill):
    """將警報事件清單轉換為時間序列特徵。"""

    skill_id = "alarm_processor"
    display_name = "警報事件處理"
    description = "解析警報事件清單，產出每日警報次數、持續時間、MTBF 等時間序列特徵"
    version = "1.0.0"

    async def execute(
        self,
        inp: SkillInput,
        progress_cb: ProgressCallback = None,
    ) -> SkillOutput:
        """處理警報事件清單。

        Parameters (inp.parameters):
            resample_freq: str — 聚合頻率（預設 "1D" 每日，可設 "1h" 每小時）
            top_n_codes: int — one-hot 編碼的前 N 種警報碼（預設 20）
            merge_with_scada: bool — 是否嘗試與 context 中的 SCADA DataFrame 合併
        Input (inp.dataframe or inp.data):
            警報事件清單 DataFrame
        """
        df = inp.dataframe if inp.dataframe is not None else inp.data
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            return SkillOutput(status=SkillStatus.ERROR, errors=["未收到警報事件資料"])

        resample_freq = inp.parameters.get("resample_freq", "1D")
        top_n = inp.parameters.get("top_n_codes", 20)

        if progress_cb:
            await progress_cb(0.05, f"解析警報事件（{len(df)} 筆）...")

        loop = asyncio.get_event_loop()

        try:
            # ── Step 1：偵測欄位 ──
            col_map = _detect_alarm_columns(df)

            if not col_map.get("timestamp"):
                return SkillOutput(
                    status=SkillStatus.ERROR,
                    errors=["找不到時間戳記欄位，無法解析警報事件"],
                    data={"columns_found": list(df.columns)},
                )

            if progress_cb:
                await progress_cb(0.15, "欄位偵測完成，正規化中...")

            # ── Step 2：正規化事件 ──
            events = await loop.run_in_executor(None, lambda: _normalize_events(df, col_map))

            if events.empty:
                return SkillOutput(
                    status=SkillStatus.ERROR,
                    errors=["正規化後無有效事件"],
                )

            if progress_cb:
                await progress_cb(0.35, f"已正規化 {len(events)} 筆事件，產出統計...")

            # ── Step 3：警報統計摘要 ──
            summary_report = await loop.run_in_executor(
                None, lambda: _compute_alarm_summary(events)
            )

            if progress_cb:
                await progress_cb(0.55, "產出時間序列特徵...")

            # ── Step 4：轉換為時間序列特徵 ──
            ts_features = await loop.run_in_executor(
                None, lambda: _events_to_timeseries(events, resample_freq, top_n)
            )

            if progress_cb:
                await progress_cb(0.8, "計算 MTBF...")

            # ── Step 5：計算 MTBF ──
            mtbf_report = _compute_mtbf(events)
            summary_report["mtbf"] = mtbf_report

            if progress_cb:
                await progress_cb(1.0, "警報處理完成")

            # 摘要文字
            total_events = len(events)
            unique_codes = events["alarm_code"].nunique()
            time_range = f"{events['timestamp'].min()} ~ {events['timestamp'].max()}"
            summary_text = (
                f"處理 {total_events} 筆警報事件, "
                f"{unique_codes} 種警報碼, "
                f"MTBF {mtbf_report.get('mtbf_hours', 'N/A')}h, "
                f"產出 {len(ts_features)} 筆 × {len(ts_features.columns)} 欄位時間序列"
            )

            return SkillOutput(
                status=SkillStatus.SUCCESS,
                data={
                    "alarm_summary": summary_report,
                    "column_mapping": col_map,
                    "total_events": total_events,
                    "unique_codes": unique_codes,
                    "time_range": time_range,
                    "timeseries_shape": list(ts_features.shape),
                },
                summary=summary_text,
                dataframe=ts_features,
            )

        except Exception as e:
            return SkillOutput(status=SkillStatus.ERROR, errors=[str(e)])


# ── 欄位偵測 ──────────────────────────────────────────────────


def _detect_alarm_columns(df: pd.DataFrame) -> dict[str, str | None]:
    """自動偵測警報事件清單的欄位映射。"""

    def _find(keywords: list[str]) -> str | None:
        for kw in keywords:
            for col in df.columns:
                if kw.lower() in col.lower():
                    return col
        return None

    return {
        "timestamp": _find(_TIMESTAMP_KEYWORDS),
        "end_time": _find(_END_TIME_KEYWORDS),
        "alarm_code": _find(_CODE_KEYWORDS),
        "description": _find(_DESCRIPTION_KEYWORDS),
        "severity": _find(_SEVERITY_KEYWORDS),
        "component": _find(_COMPONENT_KEYWORDS),
        "duration": _find(_DURATION_KEYWORDS),
    }


# ── 事件正規化 ────────────────────────────────────────────────


def _normalize_events(df: pd.DataFrame, col_map: dict[str, str | None]) -> pd.DataFrame:
    """將原始警報清單正規化為統一格式。"""
    events = pd.DataFrame()

    # 時間戳
    ts_col = col_map["timestamp"]
    if ts_col:
        events["timestamp"] = pd.to_datetime(df[ts_col], errors="coerce")

    # 結束時間
    end_col = col_map.get("end_time")
    if end_col:
        events["end_time"] = pd.to_datetime(df[end_col], errors="coerce")

    # 警報碼
    code_col = col_map.get("alarm_code")
    if code_col:
        events["alarm_code"] = df[code_col].astype(str).str.strip()
    else:
        events["alarm_code"] = "UNKNOWN"

    # 描述
    desc_col = col_map.get("description")
    if desc_col:
        events["description"] = df[desc_col].astype(str).str.strip()
    else:
        events["description"] = ""

    # 嚴重度
    sev_col = col_map.get("severity")
    if sev_col:
        events["severity"] = df[sev_col].astype(str).str.strip().str.lower().map(_SEVERITY_MAP)
        events["severity"] = events["severity"].fillna(2).astype(int)
    else:
        events["severity"] = 2  # 預設 medium

    # 元件
    comp_col = col_map.get("component")
    if comp_col:
        events["component"] = df[comp_col].astype(str).str.strip()
    else:
        events["component"] = "unknown"

    # 持續時間（秒）
    dur_col = col_map.get("duration")
    if dur_col:
        events["duration_seconds"] = pd.to_numeric(df[dur_col], errors="coerce").fillna(0)
    elif "end_time" in events.columns:
        # 從開始/結束時間計算
        diff = events["end_time"] - events["timestamp"]
        events["duration_seconds"] = diff.dt.total_seconds().clip(lower=0).fillna(0)
    else:
        events["duration_seconds"] = 0.0

    # 移除無效時間戳
    events = events.dropna(subset=["timestamp"])
    events = events.sort_values("timestamp").reset_index(drop=True)

    return events


# ── 警報統計摘要 ──────────────────────────────────────────────


def _compute_alarm_summary(events: pd.DataFrame) -> dict[str, Any]:
    """計算警報統計摘要。"""
    total = len(events)

    # 警報碼分佈
    code_counts = events["alarm_code"].value_counts()
    top_codes = [
        {"code": code, "count": int(count), "ratio": round(count / total, 4)}
        for code, count in code_counts.head(10).items()
    ]

    # 嚴重度分佈
    severity_counts = events["severity"].value_counts().sort_index()
    severity_names = {0: "info", 1: "low", 2: "medium", 3: "high", 4: "critical"}
    severity_dist = {
        severity_names.get(k, f"level_{k}"): int(v) for k, v in severity_counts.items()
    }

    # 元件分佈
    component_counts = events["component"].value_counts()
    top_components = [
        {"component": comp, "count": int(count)}
        for comp, count in component_counts.head(10).items()
    ]

    # 時間分佈
    events_with_hour = events.copy()
    events_with_hour["hour"] = events["timestamp"].dt.hour
    hourly_dist = events_with_hour["hour"].value_counts().sort_index()

    # 每日統計
    events_with_date = events.copy()
    events_with_date["date"] = events["timestamp"].dt.date
    daily_counts = events_with_date.groupby("date").size()

    # 持續時間統計
    dur = events["duration_seconds"]
    duration_stats = {
        "mean_seconds": round(float(dur.mean()), 1),
        "median_seconds": round(float(dur.median()), 1),
        "max_seconds": round(float(dur.max()), 1),
        "total_hours": round(float(dur.sum() / 3600), 2),
    }

    return {
        "total_events": total,
        "unique_codes": int(events["alarm_code"].nunique()),
        "unique_components": int(events["component"].nunique()),
        "top_alarm_codes": top_codes,
        "severity_distribution": severity_dist,
        "top_components": top_components,
        "daily_event_stats": {
            "mean": round(float(daily_counts.mean()), 1),
            "max": int(daily_counts.max()),
            "min": int(daily_counts.min()),
        },
        "peak_hour": int(hourly_dist.idxmax()) if not hourly_dist.empty else None,
        "duration_stats": duration_stats,
    }


# ── 時間序列轉換 ──────────────────────────────────────────────


def _events_to_timeseries(
    events: pd.DataFrame,
    freq: str = "1D",
    top_n_codes: int = 20,
) -> pd.DataFrame:
    """將離散事件轉換為固定頻率的時間序列 DataFrame。"""
    events = events.copy()
    events = events.set_index("timestamp").sort_index()

    # 確定時間範圍
    start = events.index.min().floor(freq)
    end = events.index.max().ceil(freq)
    time_index = pd.date_range(start, end, freq=freq)

    result = pd.DataFrame(index=time_index)
    result.index.name = "timestamp"

    # ── 1. 每期間警報總次數 ──
    counts = events.resample(freq).size()
    result["alarm_count"] = counts.reindex(time_index, fill_value=0)

    # ── 2. 每期間警報總持續時間（小時）──
    duration = events["duration_seconds"].resample(freq).sum() / 3600
    result["alarm_duration_hours"] = duration.reindex(time_index, fill_value=0.0)

    # ── 3. 每期間平均嚴重度 ──
    severity_mean = events["severity"].resample(freq).mean()
    result["alarm_severity_mean"] = severity_mean.reindex(time_index, fill_value=0.0)

    # ── 4. 每期間最高嚴重度 ──
    severity_max = events["severity"].resample(freq).max()
    result["alarm_severity_max"] = severity_max.reindex(time_index, fill_value=0)

    # ── 5. 每期間不重複警報碼數 ──
    unique_codes = events["alarm_code"].resample(freq).nunique()
    result["alarm_unique_codes"] = unique_codes.reindex(time_index, fill_value=0)

    # ── 6. 高嚴重度警報次數（severity >= 3）──
    high_sev = events[events["severity"] >= 3].resample(freq).size()
    result["alarm_high_severity_count"] = high_sev.reindex(time_index, fill_value=0)

    # ── 7. Top N 警報碼 one-hot 編碼（每期間出現次數）──
    top_codes = events["alarm_code"].value_counts().head(top_n_codes).index.tolist()
    for code in top_codes:
        code_events = events[events["alarm_code"] == code].resample(freq).size()
        safe_name = str(code).replace(" ", "_").replace("/", "_")[:30]
        result[f"alarm_{safe_name}"] = code_events.reindex(time_index, fill_value=0)

    # ── 8. 元件別警報次數（前 10 個元件）──
    top_components = events["component"].value_counts().head(10).index.tolist()
    for comp in top_components:
        if comp == "unknown":
            continue
        comp_events = events[events["component"] == comp].resample(freq).size()
        safe_name = str(comp).replace(" ", "_").replace("/", "_")[:30]
        result[f"comp_{safe_name}"] = comp_events.reindex(time_index, fill_value=0)

    return result


# ── MTBF 計算 ─────────────────────────────────────────────────


def _compute_mtbf(events: pd.DataFrame) -> dict[str, Any]:
    """計算平均故障間隔時間 (MTBF)。"""
    if len(events) < 2:
        return {"mtbf_hours": None, "total_failures": len(events)}

    # 只算高嚴重度事件（severity >= 3）的 MTBF
    high_sev = events[events["severity"] >= 3].copy()
    if len(high_sev) < 2:
        # 降級：用所有事件
        high_sev = events.copy()

    sorted_ts = high_sev["timestamp"].sort_values()
    intervals = sorted_ts.diff().dropna()

    if intervals.empty:
        return {"mtbf_hours": None, "total_failures": len(high_sev)}

    mtbf_seconds = intervals.dt.total_seconds().median()
    mtbf_hours = round(mtbf_seconds / 3600, 1)

    return {
        "mtbf_hours": mtbf_hours,
        "mtbf_days": round(mtbf_hours / 24, 1),
        "total_failures": len(high_sev),
        "observation_period_days": round(
            (sorted_ts.max() - sorted_ts.min()).total_seconds() / 86400, 1
        ),
    }
