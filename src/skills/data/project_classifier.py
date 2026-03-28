"""專案檔案分類技能 — 智能分類資料夾中的混合格式檔案。

分類邏輯：
- PDF/TXT/MD/DOCX → 技術文件（RAG 向量化）
- CSV/Excel/Parquet → 讀取欄位名稱判斷：
  - 含 SCADA 特徵欄位（wind_speed, power, rotor_speed 等）→ 運轉資料
  - 不含 SCADA 特徵（如警報清單、備品清單）→ 歸為文件，應向量化
- 照片/未知 → 其他
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.skills.base import BaseSkill, ProgressCallback, SkillInput, SkillOutput, SkillStatus

# SCADA 運轉資料的特徵欄位關鍵字（只要欄位名含這些就是 SCADA）
_SCADA_KEYWORDS: set[str] = {
    "wind_speed",
    "windspeed",
    "wind speed",
    "ws_mean",
    "ws_avg",
    "active_power",
    "power_mean",
    "power_output",
    "p_avg",
    "power",
    "rotor_speed",
    "rotor speed",
    "rotorspeed",
    "gen_rpm",
    "rotor_rpm",
    "blade_pitch",
    "pitch_angle",
    "pitch",
    "nacelle_direction",
    "nacelle_dir",
    "yaw_angle",
    "yaw",
    "generator_temp",
    "gen_temp",
    "gen_bear_temp",
    "ambient_temp",
    "amb_temp",
    "wind_direction",
    "wind_dir",
}

# 純文件格式（不需要讀內容）
_DOC_EXTENSIONS: set[str] = {".pdf", ".txt", ".md", ".docx", ".doc"}

# 表格格式（需要讀欄位判斷）
_TABLE_EXTENSIONS: set[str] = {".csv", ".tsv", ".xlsx", ".xls", ".parquet", ".json"}

# 照片格式
_PHOTO_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff"}


class ProjectClassifierSkill(BaseSkill):
    """智能分類資料夾中的混合格式檔案。"""

    skill_id = "project_classifier"
    display_name = "專案檔案分類器"
    description = "掃描資料夾並智能分類（SCADA 資料 / 技術文件 / 其他），表格檔會讀取欄位判斷"
    version = "2.0.0"

    async def execute(
        self,
        inp: SkillInput,
        progress_cb: ProgressCallback = None,
    ) -> SkillOutput:
        """分類資料夾中的檔案。

        Parameters (inp.parameters):
            folder_path: str — 要分類的資料夾路徑
        """
        import asyncio

        folder_path = inp.parameters.get("folder_path", "")
        if not folder_path:
            return SkillOutput(status=SkillStatus.ERROR, errors=["未指定 folder_path"])

        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            return SkillOutput(
                status=SkillStatus.ERROR,
                errors=[f"資料夾不存在：{folder_path}"],
            )

        if progress_cb:
            await progress_cb(0.1, f"掃描資料夾：{folder.name}")

        # 掃描所有檔案
        all_files: list[dict[str, Any]] = []
        for f in sorted(folder.rglob("*")):
            if f.is_file() and not f.name.startswith(".") and not f.name.startswith("~"):
                all_files.append(
                    {
                        "path": str(f),
                        "name": f.name,
                        "extension": f.suffix.lower(),
                        "size_bytes": f.stat().st_size,
                    }
                )

        if not all_files:
            return SkillOutput(
                status=SkillStatus.ERROR,
                errors=[f"資料夾中無檔案：{folder_path}"],
            )

        if progress_cb:
            await progress_cb(0.3, f"發現 {len(all_files)} 個檔案，分析欄位中...")

        # 分類
        buckets: dict[str, list[dict[str, Any]]] = {
            "data_files": [],
            "documents": [],
            "other": [],
        }
        loop = asyncio.get_event_loop()

        for i, f_info in enumerate(all_files):
            ext = f_info["extension"]

            if ext in _DOC_EXTENSIONS:
                # PDF/TXT/MD/DOCX → 一律是文件
                f_info["category"] = "document"
                buckets["documents"].append(f_info)

            elif ext in _TABLE_EXTENSIONS:
                # CSV/Excel/Parquet → 讀欄位判斷
                is_scada = await loop.run_in_executor(
                    None, lambda p=f_info["path"], e=ext: _is_scada_file(p, e)
                )
                if is_scada:
                    f_info["category"] = "scada_data"
                    buckets["data_files"].append(f_info)
                else:
                    # 非 SCADA 的表格（警報清單、備品清單等）→ 當文件向量化
                    f_info["category"] = "tabular_doc"
                    buckets["documents"].append(f_info)

            elif ext in _PHOTO_EXTENSIONS:
                f_info["category"] = "photo"
                buckets["other"].append(f_info)

            else:
                f_info["category"] = "unknown"
                buckets["other"].append(f_info)

            # 每 20% 回報進度
            if progress_cb and (i + 1) % max(1, len(all_files) // 5) == 0:
                pct = 0.3 + 0.6 * (i + 1) / len(all_files)
                await progress_cb(pct, f"已分析 {i + 1}/{len(all_files)} 個檔案...")

        if progress_cb:
            await progress_cb(1.0, "分類完成")

        total = len(all_files)

        # 摘要
        parts: list[str] = []
        if buckets["data_files"]:
            parts.append(f"SCADA 資料 {len(buckets['data_files'])} 份")
        if buckets["documents"]:
            doc_types = {}
            for d in buckets["documents"]:
                cat = d.get("category", "document")
                doc_types[cat] = doc_types.get(cat, 0) + 1
            type_str = ", ".join(
                f"{'表格文件' if k == 'tabular_doc' else '技術文件'} {v} 份"
                for k, v in doc_types.items()
            )
            parts.append(type_str)
        if buckets["other"]:
            parts.append(f"其他 {len(buckets['other'])} 份")

        return SkillOutput(
            status=SkillStatus.SUCCESS,
            data={
                "data_files": buckets["data_files"],
                "documents": buckets["documents"],
                "other": buckets["other"],
                "total": total,
                "folder": folder_path,
            },
            summary=f"分類完成：{', '.join(parts)}（共 {total} 份）",
        )


def _is_scada_file(file_path: str, extension: str) -> bool:
    """讀取表格檔欄位名稱，判斷是否為 SCADA 運轉資料。

    判斷規則：欄位名稱中是否包含至少 2 個 SCADA 特徵關鍵字。
    """
    try:
        columns = _read_columns(file_path, extension)
        if not columns:
            return False

        # 將所有欄位名正規化（小寫、移除空白）
        normalized = [c.lower().strip().replace(" ", "_") for c in columns]

        # 計算匹配數
        matches = 0
        for col in normalized:
            for keyword in _SCADA_KEYWORDS:
                if keyword in col:
                    matches += 1
                    break  # 一個欄位只算一次

        # 至少匹配 2 個 SCADA 特徵欄位才算是運轉資料
        return matches >= 2

    except Exception:
        # 讀取失敗，保守歸為文件
        return False


def _read_columns(file_path: str, extension: str) -> list[str]:
    """快速讀取表格檔的欄位名稱（不載入全部資料）。"""
    import pandas as pd

    try:
        if extension in (".csv", ".tsv"):
            sep = "\t" if extension == ".tsv" else ","
            df = pd.read_csv(file_path, nrows=0, sep=sep, encoding="utf-8", on_bad_lines="skip")
            return list(df.columns)

        if extension in (".xlsx", ".xls"):
            df = pd.read_excel(file_path, nrows=0)
            return list(df.columns)

        if extension == ".parquet":
            df = pd.read_parquet(file_path, columns=[])  # 只讀 schema
            return list(pd.read_parquet(file_path, nrows=1).columns)

        if extension == ".json":
            df = pd.read_json(file_path, nrows=1)
            return list(df.columns)

    except Exception:
        pass

    return []
