"""智慧型通用資料載入器 — 自動偵測任意風場 SCADA 資料。

此模組不需要針對每種資料來源撰寫專用 loader。
它會自動：
1. 偵測檔案格式（CSV / Parquet / Excel / ZIP 內的 CSV）
2. 智慧辨識欄位（風速、功率、溫度、轉速等）
3. 自動解析時間戳記（支援各種格式）
4. 產出統一的標準化 DataFrame

使用方式：
    df = smart_load("path/to/any_file.csv")
    df = smart_load("path/to/archive.zip")
    df = smart_load("path/to/data.parquet")
    turbines = discover_data_sources()  # 自動掃描所有可用資料
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd

# ── 專案路徑 ──

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DATA_DIRS = [
    _PROJECT_ROOT / "data" / "external",
    _PROJECT_ROOT / "data" / "raw",
    _PROJECT_ROOT / "data" / "processed",
]

# ── 欄位辨識規則 ──
# 每個標準欄位對應多組可能的關鍵字（不分大小寫），按優先度排列

COLUMN_PATTERNS: dict[str, list[str]] = {
    "wind_speed": [
        "wind_speed",
        "windspeed",
        "wind speed",
        "ws_mean",
        "ws_avg",
        "va_avg",
        "va_mean",  # ENGIE La Haute Borne
        "amb_windspeed",
        "amb_windspeed_avg",  # EDP
        "wind_speed_mean",  # Penmanshiel
        "mean_wind",
        "avg_wind",
        "ws",
        "windspeed(m/s)",  # 含單位格式
    ],
    "power": [
        "active_power",
        "active power",  # 最優先：明確的有功功率
        "power_mean",
        "power_output",
        "p_avg",
        "p_mean",  # ENGIE
        "grd_prod_pwr_avg",
        "grd_prod_pwr",  # EDP
        "active_power_mean",  # Penmanshiel
        "gen_power",
        "grid_power",
        "output_power",
        "power_kw",
        "power(kw)",
        "power",
    ],
    "rotor_speed": [
        "rotor_speed",
        "rotor speed",
        "rotorspeed",
        "rs_mean",
        "rs_avg",
        "omega",
        "gen_rpm",
        "rotor_rpm",
        "generator_speed",
        "genspeed",  # H05|GenSpeed 格式
    ],
    "blade_pitch": [
        "blade_pitch",
        "pitch_angle",
        "blade pitch",
        "pitch_mean",
        "pitch_avg",
        "pitch",
        "bladeangle",
        "blade1angle",
        "blade2angle",
        "blade3angle",
    ],
    "nacelle_direction": [
        "nacelle_direction",
        "nacelle_dir",
        "yaw_angle",
        "nacelle direction",
        "yaw",
        "nac_dir",
    ],
    "ambient_temp": [
        "ambient_temp",
        "ambient_temperature",
        "temperature",
        "amb_temp",
        "outdoor_temp",
        "ot_avg",
        "environmental_temp",
        "ext_temp",
    ],
    "generator_temp": [
        "generator_temp",
        "gen_temp",
        "generator_bearing",
        "gen_bear_temp",
        "gen_de_temp",
        "gen_nde_temp",
    ],
    "wind_direction": [
        "wind_direction",
        "wind_dir",
        "wd_mean",
        "wd_avg",
        "wind direction",
        "wdir",
    ],
}

# 時間戳記關鍵字
TIMESTAMP_KEYWORDS = [
    "timestamp",
    "time",
    "date_time",
    "datetime",
    "date",
    "pctimestamp",
    "time_stamp",
    "record_time",
    "ts",
]

# 常見時間格式（自動嘗試）
TIMESTAMP_FORMATS = [
    None,  # pandas 自動推斷
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M",
    "%Y/%m/%d %H:%M:%S",
    "%Y%m%d%H%M",
]


def _match_column(
    columns: list[str],
    patterns: list[str],
    exclude_suffixes: list[str] | None = None,
) -> str | None:
    """在欄位列表中找到最佳匹配。

    Parameters
    ----------
    columns : list[str]
        DataFrame 的欄位名稱。
    patterns : list[str]
        要搜尋的關鍵字模式（不分大小寫）。
    exclude_suffixes : list[str] | None
        排除包含這些子字串的欄位。

    Returns
    -------
    str | None
        匹配到的欄位名稱。
    """
    exclude = exclude_suffixes or [
        "std",
        "standard deviation",
        "minimum",
        "maximum",
        "reactive",  # 排除無功功率
    ]

    def _normalize(s: str) -> str:
        """正規化欄位名稱：去除前綴（如 H05|）、單位（如 (kW)）、統一分隔符。"""
        # 去除設備前綴（如 "H05|Power(kW)" → "Power(kW)"）
        if "|" in s:
            s = s.split("|", 1)[-1]
        # 去除括號內的單位（如 "Power(kW)" → "Power"）
        s = re.sub(r"\([^)]*\)", "", s)
        return s.lower().replace(" ", "_").strip("_")

    # 建立正規化後的欄位映射
    norm_cols = {col: _normalize(col) for col in columns}

    # 第一輪：完全匹配（正規化後的欄位名 == 關鍵字）
    for pat in patterns:
        pat_n = pat.lower().replace(" ", "_")
        for col, nc in norm_cols.items():
            if nc == pat_n:
                return col

    # 第二輪：包含匹配（排除統計量欄位），優先 _mean/_avg
    for pat in patterns:
        pat_n = pat.lower()
        for col, nc in norm_cols.items():
            if (pat_n in nc or pat_n.replace("_", "") in nc) and any(
                s in nc for s in ["_mean", "_avg", "mean_", "avg_"]
            ):
                return col

    # 第三輪：包含匹配（排除統計量）
    for pat in patterns:
        pat_n = pat.lower()
        for col, nc in norm_cols.items():
            if (pat_n in nc or pat_n.replace("_", "") in nc) and not any(
                ex in nc for ex in exclude
            ):
                return col

    # 第四輪：原始欄位名包含匹配（fallback）
    for pat in patterns:
        for col in columns:
            if pat.lower() in col.lower():
                return col

    return None


def _detect_timestamp_column(df: pd.DataFrame) -> str | None:
    """自動偵測時間戳記欄位。"""
    columns = df.columns.tolist()

    # 先找索引
    if isinstance(df.index, pd.DatetimeIndex) and df.index.name:
        return df.index.name

    # 用關鍵字找
    for kw in TIMESTAMP_KEYWORDS:
        for col in columns:
            if kw.lower() in col.lower():
                return col

    # 嘗試找看起來像日期的欄位（object 型別且可解析）
    for col in columns:
        if df[col].dtype == object:
            try:
                sample = df[col].dropna().head(5)
                if len(sample) > 0:
                    pd.to_datetime(sample)
                    return col
            except (ValueError, TypeError):
                continue

    return None


def _parse_timestamp(df: pd.DataFrame, ts_col: str) -> pd.DataFrame:
    """嘗試多種格式解析時間戳記。"""
    if pd.api.types.is_datetime64_any_dtype(df[ts_col]):
        return df  # 已經是 datetime

    for fmt in TIMESTAMP_FORMATS:
        try:
            df[ts_col] = pd.to_datetime(df[ts_col], format=fmt)
            return df
        except (ValueError, TypeError):
            continue

    # 最後用 pandas 的混合模式
    df[ts_col] = pd.to_datetime(df[ts_col], infer_datetime_format=True, errors="coerce")
    return df


def _smart_read_csv(file_or_path: Any) -> pd.DataFrame:
    """智慧 CSV 解析：自動跳過 comment 行、偵測分隔符。

    支援以 # 開頭的 comment 行（如 Kelmarsh / Greenbyte 格式），
    自動嘗試 , 和 ; 作為分隔符。

    特殊處理：Greenbyte 格式的 header 以 "# Date and time" 開頭，
    需要先手動找到 header 行再讀取。
    """
    import io

    def _read_bytes(fp: Any) -> bytes:
        if hasattr(fp, "seek"):
            fp.seek(0)
        if hasattr(fp, "read"):
            return fp.read()
        with open(fp, "rb") as f:
            return f.read()

    raw = _read_bytes(file_or_path)
    lines = raw.decode("utf-8", errors="replace").splitlines()

    # 找到真正的 header 行（第一個有 ≥2 個逗號的行）
    # 特殊處理：header 可能以 "# " 開頭（Greenbyte 格式）
    header_idx = 0
    for i, line in enumerate(lines):
        stripped = line.lstrip("# ").strip()
        if not stripped:
            continue
        # 如果這行包含常見欄位關鍵字，它就是 header
        lower_line = stripped.lower()
        is_header = any(
            kw in lower_line
            for kw in [
                "date",
                "time",
                "wind",
                "power",
                "speed",
                "temp",
                "rotor",
                "pitch",
                "nacelle",
                "timestamp",
            ]
        )
        if is_header and stripped.count(",") >= 2:
            # 清理 header 行的 # 前綴
            lines[i] = stripped
            header_idx = i
            break
        # 如果這行不以 # 開頭且有逗號，可能是 header 或第一行資料
        if not line.startswith("#") and "," in line:
            header_idx = i
            break

    # 跳過 header 前的 comment 行
    clean_lines = lines[header_idx:]
    # 再過濾掉剩餘的純 comment 行（但保留 header）
    final_lines = [clean_lines[0]]  # header
    for line in clean_lines[1:]:
        if not line.startswith("#"):
            final_lines.append(line)

    clean_csv = "\n".join(final_lines)

    # 嘗試不同分隔符
    for sep in [",", ";"]:
        try:
            df = pd.read_csv(io.StringIO(clean_csv), sep=sep)
            if len(df.columns) >= 2 and len(df) >= 10:
                return df
        except Exception:
            continue

    # 最後一搏
    return pd.read_csv(io.StringIO(clean_csv), on_bad_lines="skip")


def _read_file(path: Path) -> pd.DataFrame:
    """根據副檔名智慧讀取檔案。"""
    suffix = path.suffix.lower()

    if suffix == ".parquet":
        return pd.read_parquet(path)
    elif suffix == ".xlsx" or suffix == ".xls":
        return pd.read_excel(path)
    elif suffix in (".csv", ".tsv"):
        return _smart_read_csv(path)
    elif suffix == ".json":
        return pd.read_json(path)
    else:
        # 預設嘗試 CSV
        return _smart_read_csv(path)


def _read_zip(zip_path: Path) -> dict[str, pd.DataFrame]:
    """讀取 ZIP 中所有 CSV / Parquet 檔案，回傳 {檔名: DataFrame}。"""
    results: dict[str, pd.DataFrame] = {}

    with zipfile.ZipFile(zip_path, "r") as zf:
        csv_files = [
            n
            for n in zf.namelist()
            if n.lower().endswith((".csv", ".parquet"))
            and not n.startswith("__MACOSX")
            and not Path(n).name.startswith(".")
        ]

        for name in csv_files:
            try:
                with zf.open(name) as f:
                    if name.lower().endswith(".parquet"):
                        import io

                        results[Path(name).stem] = pd.read_parquet(io.BytesIO(f.read()))
                    else:
                        # 智慧 CSV 解析：自動跳過 comment 行、偵測分隔符
                        results[Path(name).stem] = _smart_read_csv(f)
            except Exception:
                continue

    return results


def detect_columns(df: pd.DataFrame) -> dict[str, str | None]:
    """自動偵測 DataFrame 中的標準欄位映射。

    Returns
    -------
    dict[str, str | None]
        標準名稱 → 實際欄位名稱（找不到則為 None）。

    範例
    ----
    >>> detect_columns(df)
    {
        'wind_speed': 'Va_avg',
        'power': 'P_avg',
        'rotor_speed': 'Rt_avg',
        'timestamp': 'Date_time',
        ...
    }
    """
    columns = df.columns.tolist()
    mapping: dict[str, str | None] = {}

    for std_name, patterns in COLUMN_PATTERNS.items():
        mapping[std_name] = _match_column(columns, patterns)

    # 時間戳記
    mapping["timestamp"] = _detect_timestamp_column(df)

    return mapping


def smart_load(
    path: str | Path,
    turbine_id: str | None = None,
    column_mapping: dict[str, str] | None = None,
) -> pd.DataFrame:
    """智慧載入任意格式的風場 SCADA 資料。

    自動偵測檔案格式、欄位映射、時間戳記格式，回傳標準化的 DataFrame。

    Parameters
    ----------
    path : str | Path
        檔案路徑（支援 CSV / Parquet / Excel / ZIP）。
    turbine_id : str | None
        若為 ZIP 檔，指定要載入的子檔案（部分匹配）。
        若為 None，載入第一個找到的檔案。
    column_mapping : dict[str, str] | None
        手動指定欄位映射，會覆蓋自動偵測的結果。
        格式：{"wind_speed": "Va_avg", "power": "P_avg"}

    Returns
    -------
    pd.DataFrame
        標準化後的資料，包含自動偵測的欄位映射資訊（存於 df.attrs）。
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"找不到資料檔案：{path}")

    # ── 讀取檔案 ──
    if path.suffix.lower() == ".zip":
        dfs = _read_zip(path)
        if not dfs:
            raise ValueError(f"ZIP 檔案中找不到可讀取的資料：{path}")

        if turbine_id:
            # 模糊匹配 turbine_id
            matched = {k: v for k, v in dfs.items() if turbine_id.lower() in k.lower()}
            if matched:
                name, df = next(iter(matched.items()))
            else:
                available = list(dfs.keys())
                raise ValueError(f"ZIP 中找不到 '{turbine_id}'。可用的檔案：{available}")
        else:
            name, df = next(iter(dfs.items()))
    else:
        df = _read_file(path)
        name = path.stem

    # ── 自動偵測欄位 ──
    auto_mapping = detect_columns(df)

    # 套用手動映射（覆蓋自動偵測）
    if column_mapping:
        for std_name, actual_col in column_mapping.items():
            if actual_col in df.columns:
                auto_mapping[std_name] = actual_col

    # ── 解析時間戳記 ──
    ts_col = auto_mapping.get("timestamp")
    if ts_col and ts_col in df.columns:
        df = _parse_timestamp(df, ts_col)
        if pd.api.types.is_datetime64_any_dtype(df[ts_col]):
            df = df.set_index(ts_col).sort_index()

    # ── 存儲映射資訊到 attrs（方便下游使用）──
    df.attrs["column_mapping"] = auto_mapping
    df.attrs["source_file"] = str(path)
    df.attrs["source_name"] = name
    df.attrs["detected_fields"] = {k: v for k, v in auto_mapping.items() if v is not None}

    return df


def discover_data_sources() -> list[dict[str, Any]]:
    """掃描所有資料目錄，自動發現可用的資料來源。

    Returns
    -------
    list[dict]
        每個資料來源的資訊：
        {
            "id": "Kelmarsh_1",
            "file": "data/external/Kelmarsh_SCADA_2016.zip",
            "format": "zip/csv",
            "turbine_count": 6,
            "detected_columns": {...},
        }
    """
    sources: list[dict[str, Any]] = []

    for data_dir in _DATA_DIRS:
        if not data_dir.exists():
            continue

        # 掃描 ZIP 檔案
        for zip_path in data_dir.glob("*.zip"):
            try:
                dfs = _read_zip(zip_path)
                for name, df in dfs.items():
                    mapping = detect_columns(df)
                    has_minimum = mapping.get("wind_speed") and mapping.get("power")
                    sources.append(
                        {
                            "id": name,
                            "file": str(zip_path.relative_to(_PROJECT_ROOT)),
                            "format": "zip/csv",
                            "records": len(df),
                            "columns": list(df.columns),
                            "detected_fields": {k: v for k, v in mapping.items() if v},
                            "usable": bool(has_minimum),
                        }
                    )
            except Exception:
                continue

        # 掃描單一檔案 (CSV / Parquet / Excel)
        for ext in ["*.csv", "*.parquet", "*.xlsx"]:
            for file_path in data_dir.glob(ext):
                try:
                    df = _read_file(file_path)
                    mapping = detect_columns(df)
                    has_minimum = mapping.get("wind_speed") and mapping.get("power")
                    sources.append(
                        {
                            "id": file_path.stem,
                            "file": str(file_path.relative_to(_PROJECT_ROOT)),
                            "format": file_path.suffix.lstrip("."),
                            "records": len(df),
                            "columns": list(df.columns),
                            "detected_fields": {k: v for k, v in mapping.items() if v},
                            "usable": bool(has_minimum),
                        }
                    )
                except Exception:
                    continue

    return sources


def get_column_report(df: pd.DataFrame) -> str:
    """產出人類可讀的欄位偵測報告。

    Parameters
    ----------
    df : pd.DataFrame
        載入的資料。

    Returns
    -------
    str
        格式化的報告文字。
    """
    mapping = detect_columns(df)

    lines = ["╔══ 欄位自動偵測報告 ══╗", ""]

    for std_name, actual_col in mapping.items():
        if actual_col:
            lines.append(f"  ✅ {std_name:20s} → {actual_col}")
        else:
            lines.append(f"  ❌ {std_name:20s} → （未找到）")

    lines.append("")
    lines.append(f"  📊 總欄位數: {len(df.columns)}")
    lines.append(f"  📊 總筆數:   {len(df):,}")

    detected = sum(1 for v in mapping.values() if v)
    lines.append(f"  📊 辨識率:   {detected}/{len(mapping)}")

    # 列出未識別的欄位
    used = {v for v in mapping.values() if v}
    unused = [c for c in df.columns if c not in used]
    if unused:
        lines.append("")
        lines.append("  📋 未識別欄位:")
        for col in unused[:15]:
            dtype = str(df[col].dtype)
            lines.append(f"     - {col} ({dtype})")
        if len(unused) > 15:
            lines.append(f"     ... 還有 {len(unused) - 15} 個")

    lines.append("")
    lines.append("╚══════════════════════╝")
    return "\n".join(lines)
