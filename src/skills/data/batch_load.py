"""批次載入技能 — 依據 DataInspector 推薦的策略載入多個檔案。

三種載入策略：
- direct_concat：逐檔讀取 → pd.concat → 按時間排序去重
- aggregate_then_merge：逐檔讀取 → 降頻聚合（如 1s→10min）→ concat
- per_file_processing：逐檔讀取 → 各自回傳，不合併

支援進度回報、記憶體控管（分批載入）、品質摘要。
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.skills.base import BaseSkill, ProgressCallback, SkillInput, SkillOutput, SkillStatus


class BatchLoadSkill(BaseSkill):
    """依策略批次載入多個資料檔案。"""

    skill_id = "batch_load"
    display_name = "批次載入器"
    description = "依據檢視策略批次載入多個 SCADA 資料檔案"
    version = "1.0.0"

    async def execute(
        self,
        inp: SkillInput,
        progress_cb: ProgressCallback = None,
    ) -> SkillOutput:
        """執行批次載入。

        Parameters (inp.parameters):
            strategy: str — 載入策略 (direct_concat / aggregate_then_merge / per_file_processing)
            files: list[dict] — 檔案清單（來自 DataInspector 的 file_report["files"]）
            folder_path: str | None — 或直接指定資料夾路徑
            target_interval_seconds: int — 降頻目標（aggregate 模式用，預設 600）
            aggregation_methods: list[str] — 聚合方式（預設 ["mean", "std"]）
            sort_by_time: bool — 合併後按時間排序（預設 True）
            remove_duplicates: bool — 去除重複時間戳（預設 True）
        """
        strategy = inp.parameters.get("strategy", "direct_concat")
        files = inp.parameters.get("files")
        folder_path = inp.parameters.get("folder_path")

        # 如果沒有 files 清單，從 folder_path 掃描
        if not files and folder_path:
            files = _scan_files(Path(folder_path))

        # 也可以從 context 中取得（DataInspector 傳過來的）
        if not files and inp.context:
            inspector_data = inp.context.get("data", {})
            file_report = inspector_data.get("file_report", {})
            files = file_report.get("files", [])
            if not strategy or strategy == "direct_concat":
                s = inspector_data.get("strategy", {})
                strategy = s.get("strategy", strategy)

        if not files:
            return SkillOutput(
                status=SkillStatus.ERROR,
                errors=["未指定檔案清單或資料夾路徑"],
            )

        loop = asyncio.get_event_loop()

        if strategy == "direct_concat":
            return await self._direct_concat(files, inp.parameters, progress_cb, loop)
        if strategy == "aggregate_then_merge":
            return await self._aggregate_then_merge(files, inp.parameters, progress_cb, loop)
        if strategy == "per_file_processing":
            return await self._per_file_processing(files, inp.parameters, progress_cb, loop)

        return SkillOutput(
            status=SkillStatus.ERROR,
            errors=[f"不支援的載入策略：{strategy}"],
        )

    # ── 策略 A：直接合併 ──────────────────────────────────────

    async def _direct_concat(
        self,
        files: list[dict[str, Any]],
        params: dict[str, Any],
        progress_cb: ProgressCallback,
        loop: asyncio.AbstractEventLoop,
    ) -> SkillOutput:
        """逐檔讀取後直接 concat。"""
        sort_by_time = params.get("sort_by_time", True)
        remove_duplicates = params.get("remove_duplicates", True)
        total = len(files)

        if progress_cb:
            await progress_cb(0.05, f"直接合併：載入 {total} 個檔案...")

        dfs: list[pd.DataFrame] = []
        errors: list[str] = []
        loaded = 0

        for i, f in enumerate(files):
            path = Path(f["path"]) if isinstance(f, dict) else Path(f)
            try:
                df = await loop.run_in_executor(None, lambda p=path: _read_file(p))
                if df is not None and not df.empty:
                    dfs.append(df)
                    loaded += 1
            except Exception as e:
                errors.append(f"{path.name}: {e}")

            if progress_cb and (i + 1) % max(1, total // 20) == 0:
                pct = 0.05 + 0.8 * (i + 1) / total
                await progress_cb(pct, f"已載入 {loaded}/{total} 個檔案...")

        if not dfs:
            return SkillOutput(
                status=SkillStatus.ERROR,
                errors=errors or ["所有檔案載入失敗"],
            )

        if progress_cb:
            await progress_cb(0.85, "合併中...")

        merged = await loop.run_in_executor(
            None,
            lambda: _concat_dataframes(dfs, sort_by_time, remove_duplicates),
        )

        if progress_cb:
            await progress_cb(1.0, "合併完成")

        summary_data = _build_summary(merged, loaded, total, errors, "direct_concat")

        return SkillOutput(
            status=SkillStatus.SUCCESS if not errors else SkillStatus.PARTIAL,
            data=summary_data,
            dataframe=merged,
            summary=(
                f"直接合併完成：{loaded}/{total} 檔案 → "
                f"{len(merged)} 筆資料, {len(merged.columns)} 欄位"
            ),
            errors=errors,
        )

    # ── 策略 B：降頻聚合再合併 ─────────────────────────────────

    async def _aggregate_then_merge(
        self,
        files: list[dict[str, Any]],
        params: dict[str, Any],
        progress_cb: ProgressCallback,
        loop: asyncio.AbstractEventLoop,
    ) -> SkillOutput:
        """逐檔讀取 → 降頻聚合 → concat。"""
        target_seconds = params.get("target_interval_seconds", 600)
        agg_methods = params.get("aggregation_methods", ["mean", "std"])
        total = len(files)
        freq_str = f"{target_seconds}s"

        if progress_cb:
            await progress_cb(0.05, f"降頻聚合模式：{total} 個檔案 → {target_seconds}s...")

        dfs: list[pd.DataFrame] = []
        errors: list[str] = []
        loaded = 0

        for i, f in enumerate(files):
            path = Path(f["path"]) if isinstance(f, dict) else Path(f)
            try:
                df = await loop.run_in_executor(None, lambda p=path: _read_file(p))
                if df is None or df.empty:
                    continue

                # 確保有 DatetimeIndex
                df = _ensure_datetime_index(df)

                # 降頻聚合
                agg_df = await loop.run_in_executor(
                    None,
                    lambda d=df: _resample_aggregate(d, freq_str, agg_methods),
                )
                if agg_df is not None and not agg_df.empty:
                    dfs.append(agg_df)
                    loaded += 1
            except Exception as e:
                errors.append(f"{path.name}: {e}")

            if progress_cb and (i + 1) % max(1, total // 20) == 0:
                pct = 0.05 + 0.8 * (i + 1) / total
                await progress_cb(pct, f"已聚合 {loaded}/{total} 個檔案...")

        if not dfs:
            return SkillOutput(
                status=SkillStatus.ERROR,
                errors=errors or ["所有檔案聚合失敗"],
            )

        if progress_cb:
            await progress_cb(0.85, "合併聚合結果...")

        merged = await loop.run_in_executor(
            None,
            lambda: _concat_dataframes(dfs, sort_by_time=True, remove_duplicates=True),
        )

        if progress_cb:
            await progress_cb(1.0, "聚合合併完成")

        summary_data = _build_summary(merged, loaded, total, errors, "aggregate_then_merge")
        summary_data["target_interval_seconds"] = target_seconds
        summary_data["aggregation_methods"] = agg_methods

        return SkillOutput(
            status=SkillStatus.SUCCESS if not errors else SkillStatus.PARTIAL,
            data=summary_data,
            dataframe=merged,
            summary=(
                f"聚合合併完成：{loaded}/{total} 檔案, "
                f"{freq_str} 降頻 → {len(merged)} 筆資料"
            ),
            errors=errors,
        )

    # ── 策略 C：逐檔獨立處理 ──────────────────────────────────

    async def _per_file_processing(
        self,
        files: list[dict[str, Any]],
        params: dict[str, Any],
        progress_cb: ProgressCallback,
        loop: asyncio.AbstractEventLoop,
    ) -> SkillOutput:
        """逐檔讀取，各自獨立回傳。"""
        total = len(files)

        if progress_cb:
            await progress_cb(0.05, f"逐檔模式：載入 {total} 個檔案...")

        results: dict[str, dict[str, Any]] = {}
        errors: list[str] = []
        loaded = 0
        total_rows = 0

        for i, f in enumerate(files):
            path = Path(f["path"]) if isinstance(f, dict) else Path(f)
            try:
                df = await loop.run_in_executor(None, lambda p=path: _read_file(p))
                if df is not None and not df.empty:
                    results[path.name] = {
                        "rows": len(df),
                        "columns": len(df.columns),
                        "path": str(path),
                    }
                    total_rows += len(df)
                    loaded += 1
            except Exception as e:
                errors.append(f"{path.name}: {e}")

            if progress_cb and (i + 1) % max(1, total // 20) == 0:
                pct = 0.05 + 0.9 * (i + 1) / total
                await progress_cb(pct, f"已讀取 {loaded}/{total} 個檔案...")

        if progress_cb:
            await progress_cb(1.0, "逐檔讀取完成")

        summary_data: dict[str, Any] = {
            "strategy": "per_file_processing",
            "files_loaded": loaded,
            "files_total": total,
            "total_rows": total_rows,
            "file_results": results,
            "errors": errors,
        }

        return SkillOutput(
            status=SkillStatus.SUCCESS if not errors else SkillStatus.PARTIAL,
            data=summary_data,
            summary=f"逐檔讀取完成：{loaded}/{total} 檔案, 共 {total_rows} 筆資料",
            errors=errors,
        )


# ── 輔助函式 ──────────────────────────────────────────────────


def _scan_files(folder: Path) -> list[dict[str, Any]]:
    """掃描資料夾取得檔案清單。"""
    from src.skills.data.data_inspector import SUPPORTED_EXTENSIONS

    files: list[dict[str, Any]] = []
    for item in sorted(folder.rglob("*")):
        if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS:
            if not item.name.startswith(".") and not item.name.startswith("~"):
                files.append({"path": str(item), "name": item.name})
    return files


def _read_file(path: Path) -> pd.DataFrame | None:
    """讀取單一資料檔案。"""
    ext = path.suffix.lower()
    if ext == ".csv":
        return pd.read_csv(path, low_memory=False)
    if ext == ".tsv":
        return pd.read_csv(path, sep="\t", low_memory=False)
    if ext == ".parquet":
        return pd.read_parquet(path)
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(path)
    return None


def _ensure_datetime_index(df: pd.DataFrame) -> pd.DataFrame:
    """確保 DataFrame 有 DatetimeIndex。"""
    if isinstance(df.index, pd.DatetimeIndex):
        return df

    # 嘗試找時間欄位
    for col in df.columns:
        if any(kw in col.lower() for kw in ["time", "date", "timestamp"]):
            try:
                df = df.copy()
                df[col] = pd.to_datetime(df[col], errors="coerce")
                df = df.dropna(subset=[col])
                df = df.set_index(col).sort_index()
                return df
            except Exception:
                continue

    return df


def _resample_aggregate(
    df: pd.DataFrame, freq: str, methods: list[str]
) -> pd.DataFrame | None:
    """降頻聚合 DataFrame。"""
    if not isinstance(df.index, pd.DatetimeIndex):
        return None

    # 只對數值欄位聚合
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        return None

    df_numeric = df[numeric_cols]

    # 建立聚合字典
    agg_dict: dict[str, list[str]] = {col: methods for col in numeric_cols}
    resampled = df_numeric.resample(freq).agg(agg_dict)

    # 將多層欄位名稱攤平：(col, method) → col_method
    if isinstance(resampled.columns, pd.MultiIndex):
        resampled.columns = [
            f"{col}_{method}" if method != "mean" else col
            for col, method in resampled.columns
        ]

    # 移除全空的列
    resampled = resampled.dropna(how="all")

    return resampled


def _concat_dataframes(
    dfs: list[pd.DataFrame],
    sort_by_time: bool = True,
    remove_duplicates: bool = True,
) -> pd.DataFrame:
    """合併多個 DataFrame。"""
    merged = pd.concat(dfs, axis=0)

    if sort_by_time and isinstance(merged.index, pd.DatetimeIndex):
        merged = merged.sort_index()

    if remove_duplicates and isinstance(merged.index, pd.DatetimeIndex):
        merged = merged[~merged.index.duplicated(keep="first")]

    return merged


def _build_summary(
    df: pd.DataFrame,
    loaded: int,
    total: int,
    errors: list[str],
    strategy: str,
) -> dict[str, Any]:
    """建構載入結果摘要。"""
    summary: dict[str, Any] = {
        "strategy": strategy,
        "files_loaded": loaded,
        "files_total": total,
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "errors_count": len(errors),
    }

    if isinstance(df.index, pd.DatetimeIndex) and len(df) > 0:
        summary["time_range"] = {
            "start": str(df.index.min()),
            "end": str(df.index.max()),
        }

    # 記憶體使用
    mem_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)
    summary["memory_mb"] = round(mem_mb, 1)

    return summary
