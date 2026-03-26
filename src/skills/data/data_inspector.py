"""資料檢視技能 — 掃描資料夾、評估檔案特性、推薦載入策略。

當廠商或使用者提供一批資料檔案時，DataInspectorSkill 扮演「資料秘書」角色：
1. 掃描指定資料夾，統計檔案數、大小、格式
2. 抽樣讀取代表性檔案，推斷取樣頻率、欄位結構、時間跨度
3. 結合使用者的分析需求（指令或需求文件），推薦最佳載入策略

載入策略：
- direct_concat：少量檔案 + 合理大小 → 直接合併
- aggregate_then_merge：大量高頻檔案 → 先降頻聚合再合併
- per_file_processing：需保持原始頻率 → 逐檔獨立處理
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd

from src.skills.base import BaseSkill, ProgressCallback, SkillInput, SkillOutput, SkillStatus

# ── 常數 ──────────────────────────────────────────────────────

SUPPORTED_EXTENSIONS = {".csv", ".parquet", ".xlsx", ".xls", ".tsv", ".zip"}

# 載入策略門檻
_MAX_DIRECT_CONCAT_FILES = 50
_MAX_DIRECT_CONCAT_MB = 500
_HIGH_FREQ_THRESHOLD_SECONDS = 5  # ≤5s 視為高頻資料

# 分析類型與偏好策略的對應
_ANALYSIS_STRATEGY_HINTS: dict[str, str] = {
    # 需要高頻原始資料的分析
    "vibration_analysis": "per_file_processing",
    "振動分析": "per_file_processing",
    # 可降頻的分析
    "power_curve": "aggregate_then_merge",
    "功率曲線": "aggregate_then_merge",
    "turbulence_analysis": "aggregate_then_merge",
    "紊流分析": "aggregate_then_merge",
    "wake_analysis": "aggregate_then_merge",
    "尾流分析": "aggregate_then_merge",
    # 偏好完整合併的分析
    "fault_diagnosis": "direct_concat",
    "故障診斷": "direct_concat",
    "health_assessment": "direct_concat",
    "健康評估": "direct_concat",
    "predictive_maintenance": "direct_concat",
    "預測性維護": "direct_concat",
}


class DataInspectorSkill(BaseSkill):
    """掃描資料夾、推斷資料特性、推薦載入策略。"""

    skill_id = "data_inspector"
    display_name = "資料檢視員"
    description = "掃描資料夾並結合分析需求推薦最佳載入策略"
    version = "1.0.0"

    async def execute(
        self,
        inp: SkillInput,
        progress_cb: ProgressCallback = None,
    ) -> SkillOutput:
        """執行資料檢視。

        Parameters (inp.parameters):
            folder_path: str — 要掃描的資料夾路徑
            analysis_purpose: str | None — 分析目的（如 "power_curve"、"故障診斷"）
            requirement_file: str | None — 需求文件路徑（替代 analysis_purpose）
        """
        import asyncio

        folder_path = inp.parameters.get("folder_path")
        if not folder_path:
            return SkillOutput(
                status=SkillStatus.ERROR,
                errors=["未指定 folder_path"],
            )

        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            return SkillOutput(
                status=SkillStatus.ERROR,
                errors=[f"資料夾不存在或非目錄：{folder_path}"],
            )

        # ── 讀取分析需求 ──
        analysis_purpose = inp.parameters.get("analysis_purpose", "")
        requirement_file = inp.parameters.get("requirement_file")
        requirement_text = ""

        if requirement_file:
            req_path = Path(requirement_file)
            if req_path.exists() and req_path.is_file():
                requirement_text = req_path.read_text(encoding="utf-8", errors="replace")
                if not analysis_purpose:
                    analysis_purpose = _extract_purpose_from_text(requirement_text)

        if progress_cb:
            await progress_cb(0.1, f"掃描資料夾 {folder.name}...")

        loop = asyncio.get_event_loop()

        # ── Step 1：掃描檔案 ──
        file_report = await loop.run_in_executor(None, lambda: _scan_folder(folder))

        if file_report["file_count"] == 0:
            return SkillOutput(
                status=SkillStatus.ERROR,
                errors=[f"資料夾中未找到支援的資料檔案：{folder_path}"],
                data={"file_report": file_report},
            )

        if progress_cb:
            await progress_cb(0.4, f"找到 {file_report['file_count']} 個檔案，抽樣分析中...")

        # ── Step 2：抽樣分析代表性檔案 ──
        sample_report = await loop.run_in_executor(
            None, lambda: _sample_files(file_report["files"])
        )

        if progress_cb:
            await progress_cb(0.7, "推斷載入策略...")

        # ── Step 3：結合需求推薦策略 ──
        strategy = _recommend_strategy(
            file_report=file_report,
            sample_report=sample_report,
            analysis_purpose=analysis_purpose,
        )

        if progress_cb:
            await progress_cb(1.0, "檢視完成")

        # ── 組合結果 ──
        inspection_result: dict[str, Any] = {
            "file_report": file_report,
            "sample_report": sample_report,
            "analysis_purpose": analysis_purpose,
            "requirement_text": requirement_text[:500] if requirement_text else "",
            "strategy": strategy,
        }

        # 摘要
        freq_display = sample_report.get("sampling_display", "未知")
        strategy_name = strategy["strategy"]
        strategy_names_zh = {
            "direct_concat": "直接合併",
            "aggregate_then_merge": "降頻聚合再合併",
            "per_file_processing": "逐檔獨立處理",
        }

        summary = (
            f"{file_report['file_count']} 個檔案, "
            f"共 {file_report['total_size_display']}, "
            f"取樣 {freq_display}, "
            f"策略：{strategy_names_zh.get(strategy_name, strategy_name)}"
        )

        return SkillOutput(
            status=SkillStatus.SUCCESS,
            data=inspection_result,
            summary=summary,
        )


# ── 輔助函式 ──────────────────────────────────────────────────


def _scan_folder(folder: Path) -> dict[str, Any]:
    """掃描資料夾，統計檔案資訊。"""
    files: list[dict[str, Any]] = []
    total_size = 0
    format_counts: dict[str, int] = {}

    for item in sorted(folder.rglob("*")):
        if not item.is_file():
            continue
        ext = item.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            continue
        if item.name.startswith(".") or item.name.startswith("~"):
            continue

        size = item.stat().st_size
        total_size += size
        format_counts[ext] = format_counts.get(ext, 0) + 1
        files.append({
            "path": str(item),
            "name": item.name,
            "size_bytes": size,
            "extension": ext,
        })

    return {
        "folder": str(folder),
        "file_count": len(files),
        "total_size_bytes": total_size,
        "total_size_display": _format_size(total_size),
        "format_distribution": format_counts,
        "files": files,
    }


def _sample_files(files: list[dict[str, Any]], max_samples: int = 5) -> dict[str, Any]:
    """抽樣讀取檔案，推斷取樣頻率、欄位結構、時間跨度等。"""
    if not files:
        return {}

    # 選取抽樣檔案：首、尾、及均勻間隔
    n = len(files)
    if n <= max_samples:
        sample_indices = list(range(n))
    else:
        step = n / max_samples
        sample_indices = [int(i * step) for i in range(max_samples)]

    all_columns: list[set[str]] = []
    sampling_intervals: list[float] = []
    total_rows_sampled = 0
    time_min = None
    time_max = None
    sample_details: list[dict[str, Any]] = []

    for idx in sample_indices:
        file_info = files[idx]
        path = Path(file_info["path"])

        try:
            df = _quick_read(path, nrows=500)
            if df is None or df.empty:
                continue
        except Exception:
            continue

        cols = set(df.columns.tolist())
        all_columns.append(cols)
        total_rows_sampled += len(df)

        # 推斷取樣頻率
        interval = _infer_sampling_interval(df)
        if interval is not None:
            sampling_intervals.append(interval)

        # 時間範圍
        ts_min, ts_max = _get_time_range(df)
        if ts_min is not None:
            time_min = min(time_min, ts_min) if time_min else ts_min
        if ts_max is not None:
            time_max = max(time_max, ts_max) if time_max else ts_max

        sample_details.append({
            "file": file_info["name"],
            "rows_sampled": len(df),
            "columns": len(cols),
            "sampling_seconds": interval,
        })

    # 欄位一致性檢查
    schema_consistent = True
    if len(all_columns) >= 2:
        ref = all_columns[0]
        schema_consistent = all(c == ref for c in all_columns[1:])

    # 中位數取樣間隔
    median_interval: float | None = None
    if sampling_intervals:
        sampling_intervals.sort()
        mid = len(sampling_intervals) // 2
        median_interval = sampling_intervals[mid]

    # 欄位偵測
    detected_fields: dict[str, str] = {}
    if all_columns:
        union_cols = set()
        for c in all_columns:
            union_cols |= c
        detected_fields = _detect_field_types(union_cols)

    report: dict[str, Any] = {
        "samples_count": len(sample_details),
        "total_files": len(files),
        "schema_consistent": schema_consistent,
        "column_count": len(all_columns[0]) if all_columns else 0,
        "detected_fields": detected_fields,
        "sampling_interval_seconds": median_interval,
        "sampling_display": _format_interval(median_interval),
        "time_range": {
            "start": str(time_min) if time_min else None,
            "end": str(time_max) if time_max else None,
        },
        "sample_details": sample_details,
    }

    return report


def _recommend_strategy(
    file_report: dict[str, Any],
    sample_report: dict[str, Any],
    analysis_purpose: str,
) -> dict[str, Any]:
    """根據檔案特性與分析需求推薦載入策略。"""
    n_files = file_report["file_count"]
    total_mb = file_report["total_size_bytes"] / (1024 * 1024)
    interval = sample_report.get("sampling_interval_seconds")
    is_high_freq = interval is not None and interval <= _HIGH_FREQ_THRESHOLD_SECONDS

    # ── 1. 先看分析需求是否有明確偏好 ──
    purpose_hint = None
    purpose_lower = analysis_purpose.lower().strip()
    for keyword, strategy in _ANALYSIS_STRATEGY_HINTS.items():
        if keyword.lower() in purpose_lower:
            purpose_hint = strategy
            break

    # ── 2. 根據資料特性決定基礎策略 ──
    if n_files <= _MAX_DIRECT_CONCAT_FILES and total_mb <= _MAX_DIRECT_CONCAT_MB:
        data_strategy = "direct_concat"
    elif is_high_freq and n_files > _MAX_DIRECT_CONCAT_FILES:
        data_strategy = "aggregate_then_merge"
    elif is_high_freq:
        data_strategy = "aggregate_then_merge"
    else:
        data_strategy = "direct_concat"

    # ── 3. 需求偏好 override 資料策略（部分情況）──
    final_strategy = data_strategy
    if purpose_hint:
        if purpose_hint == "per_file_processing":
            # 使用者要求保持原始頻率，尊重需求
            final_strategy = "per_file_processing"
        elif purpose_hint == "aggregate_then_merge" and is_high_freq:
            final_strategy = "aggregate_then_merge"
        elif purpose_hint == "direct_concat" and not is_high_freq:
            final_strategy = "direct_concat"
        elif purpose_hint == "direct_concat" and is_high_freq and n_files <= 10:
            # 檔案很少即使高頻也可以直接合併
            final_strategy = "direct_concat"
        else:
            final_strategy = purpose_hint

    # ── 4. 策略參數 ──
    params: dict[str, Any] = {
        "strategy": final_strategy,
        "reason": _explain_strategy(final_strategy, n_files, total_mb, interval, analysis_purpose),
    }

    if final_strategy == "aggregate_then_merge":
        params["target_interval_seconds"] = 600  # 預設降至 10 分鐘
        params["aggregation_methods"] = ["mean", "std", "min", "max"]
        # 如果分析目的需要特定聚合方式
        if "turbulence" in purpose_lower or "紊流" in purpose_lower:
            params["aggregation_methods"] = ["mean", "std"]
            params["extra_features"] = ["turbulence_intensity"]

    if final_strategy == "direct_concat":
        params["sort_by_time"] = True
        params["remove_duplicates"] = True

    if final_strategy == "per_file_processing":
        params["output_mode"] = "dict"  # {filename: result}

    return params


def _explain_strategy(
    strategy: str,
    n_files: int,
    total_mb: float,
    interval: float | None,
    purpose: str,
) -> str:
    """產生策略選擇的說明。"""
    freq = _format_interval(interval) if interval else "未知"

    if strategy == "direct_concat":
        return (
            f"{n_files} 個檔案（共 {total_mb:.1f} MB），取樣 {freq}，"
            f"資料量適中，直接合併為單一 DataFrame"
        )
    if strategy == "aggregate_then_merge":
        return (
            f"{n_files} 個檔案（共 {total_mb:.1f} MB），取樣 {freq}，"
            f"高頻資料量大，建議先降頻聚合（→ 10min）再合併"
        )
    if strategy == "per_file_processing":
        return (
            f"{n_files} 個檔案（共 {total_mb:.1f} MB），取樣 {freq}，"
            f"分析需求需保持原始頻率，逐檔獨立處理"
        )
    return f"策略：{strategy}"


# ── 低階工具函式 ──────────────────────────────────────────────


def _quick_read(path: Path, nrows: int = 500) -> pd.DataFrame | None:
    """快速讀取檔案前 N 行。"""
    ext = path.suffix.lower()
    try:
        if ext == ".csv":
            return pd.read_csv(path, nrows=nrows)
        if ext == ".tsv":
            return pd.read_csv(path, sep="\t", nrows=nrows)
        if ext == ".parquet":
            df = pd.read_parquet(path)
            return df.head(nrows)
        if ext in (".xlsx", ".xls"):
            return pd.read_excel(path, nrows=nrows)
    except Exception:
        return None
    return None


def _infer_sampling_interval(df: pd.DataFrame) -> float | None:
    """從 DataFrame 推斷取樣間隔（秒）。"""
    # 嘗試找時間欄位
    time_col = None
    for col in df.columns:
        col_lower = col.lower()
        if any(kw in col_lower for kw in ["time", "date", "timestamp"]):
            time_col = col
            break

    if time_col is None and df.index.name and "time" in str(df.index.name).lower():
        # 索引是時間
        try:
            idx = pd.to_datetime(df.index)
            diffs = idx.to_series().diff().dropna()
            if len(diffs) > 1:
                return float(diffs.median().total_seconds())
        except Exception:
            pass
        return None

    if time_col is None:
        return None

    try:
        ts = pd.to_datetime(df[time_col], errors="coerce")
        diffs = ts.diff().dropna()
        if len(diffs) > 1:
            return float(diffs.median().total_seconds())
    except Exception:
        pass

    return None


def _get_time_range(df: pd.DataFrame) -> tuple[Any, Any]:
    """取得 DataFrame 的時間範圍。"""
    # 嘗試索引
    if isinstance(df.index, pd.DatetimeIndex) and len(df) > 0:
        return df.index.min(), df.index.max()

    # 嘗試欄位
    for col in df.columns:
        if any(kw in col.lower() for kw in ["time", "date", "timestamp"]):
            try:
                ts = pd.to_datetime(df[col], errors="coerce").dropna()
                if len(ts) > 0:
                    return ts.min(), ts.max()
            except Exception:
                pass

    return None, None


def _detect_field_types(columns: set[str]) -> dict[str, str]:
    """根據欄位名稱偵測資料類型。"""
    from src.data_pipeline.ingestion.smart_loader import COLUMN_PATTERNS

    detected: dict[str, str] = {}
    for col in columns:
        col_lower = col.lower()
        for field_name, patterns in COLUMN_PATTERNS.items():
            if any(p.lower() in col_lower for p in patterns):
                detected[col] = field_name
                break

    return detected


def _extract_purpose_from_text(text: str) -> str:
    """從需求文件文字中推斷分析目的。"""
    text_lower = text.lower()
    for keyword in _ANALYSIS_STRATEGY_HINTS:
        if keyword.lower() in text_lower:
            return keyword
    return ""


def _format_size(size_bytes: int) -> str:
    """格式化檔案大小。"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def _format_interval(seconds: float | None) -> str:
    """格式化取樣間隔。"""
    if seconds is None:
        return "未知"
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{seconds / 60:.0f}min"
    return f"{seconds / 3600:.1f}h"
