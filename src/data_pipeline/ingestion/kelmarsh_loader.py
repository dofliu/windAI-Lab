"""Kelmarsh 風場 SCADA 資料載入模組。

從 zip 壓縮檔中讀取 Kelmarsh 風場六座 Senvion MM92 風機的 SCADA 資料，
自動發現 CSV 檔案並解析時間戳記，提供單機與全場載入功能。

資料來源：Kelmarsh 風場（6 x Senvion MM92, 2050 kW, 92m 轉子直徑）
資料間隔：10 分鐘
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

import pandas as pd

# 專案根目錄與資料目錄
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DATA_DIR = _PROJECT_ROOT / "data" / "external"

# 風機靜態資訊
_TURBINE_INFO = {
    "manufacturer": "Senvion",
    "model": "MM92",
    "rated_power_kw": 2050,
    "rotor_diameter_m": 92,
    "hub_height_m": 80,
    "cut_in_wind_speed_ms": 3.0,
    "rated_wind_speed_ms": 12.5,
    "cut_out_wind_speed_ms": 25.0,
    "num_turbines": 6,
}


def _find_zip_path(year: int = 2016) -> Path:
    """尋找指定年份的 SCADA 資料壓縮檔。

    Parameters
    ----------
    year : int
        資料年份，預設為 2016。

    Returns
    -------
    Path
        壓縮檔的完整路徑。

    Raises
    ------
    FileNotFoundError
        找不到對應的壓縮檔時拋出。
    """
    zip_path = _DATA_DIR / f"Kelmarsh_SCADA_{year}.zip"
    if not zip_path.exists():
        raise FileNotFoundError(
            f"找不到 SCADA 資料檔案：{zip_path}\n"
            f"請確認資料已下載至 {_DATA_DIR}"
        )
    return zip_path


def _discover_csv_files(zip_path: Path) -> dict[str, str]:
    """自動探索壓縮檔中的 SCADA 資料 CSV 檔案並對應至風機編號。

    實際檔名格式：Turbine_Data_Kelmarsh_1_2016-01-03_-_2017-01-01_228.csv
    排除 Status_ 開頭的狀態檔案。

    Parameters
    ----------
    zip_path : Path
        壓縮檔路徑。

    Returns
    -------
    dict[str, str]
        風機 ID 對應 zip 內 CSV 檔名的字典，
        例如 {"Kelmarsh_1": "Turbine_Data_Kelmarsh_1_2016-01-03_-_2017-01-01_228.csv"}。
    """
    turbine_map: dict[str, str] = {}
    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            if not name.lower().endswith(".csv"):
                continue
            # 排除狀態檔案（只要 Turbine_Data_ 開頭的）
            basename = Path(name).name
            if basename.startswith("Status_"):
                continue
            # 匹配 Turbine_Data_Kelmarsh_N 或 Kelmarsh_N 模式
            m = re.search(r"Kelmarsh[_\-](\d+)", basename, re.IGNORECASE)
            if m:
                turbine_id = f"Kelmarsh_{int(m.group(1))}"
                turbine_map[turbine_id] = name
    return turbine_map


def load_turbine_data(turbine_id: str, year: int = 2016) -> pd.DataFrame:
    """載入單座風機的 SCADA 資料。

    從 zip 壓縮檔中讀取指定風機的 CSV 資料，自動解析時間戳記並設為索引。
    欄位名稱保留原始格式（如 "Wind Speed_Mean", "Power_Mean" 等）。

    Parameters
    ----------
    turbine_id : str
        風機 ID，例如 "Kelmarsh_1" 或 "Kelmarsh_6"。
    year : int
        資料年份，預設為 2016。

    Returns
    -------
    pd.DataFrame
        以時間戳記為索引的 SCADA 資料表。

    Raises
    ------
    FileNotFoundError
        找不到壓縮檔時拋出。
    ValueError
        找不到指定風機的 CSV 檔案時拋出。
    """
    zip_path = _find_zip_path(year)
    csv_map = _discover_csv_files(zip_path)

    if turbine_id not in csv_map:
        available = list(csv_map.keys())
        raise ValueError(
            f"找不到風機 '{turbine_id}' 的資料。"
            f"可用的風機：{available}"
        )

    csv_name = csv_map[turbine_id]

    with zipfile.ZipFile(zip_path, "r") as zf:
        with zf.open(csv_name) as f:
            # Kelmarsh CSV 格式：前數行以 '#' 開頭為註解，
            # 最後一行 '#' 行是 header（格式：# Date and time,Wind speed (m/s),...）
            import csv
            import io

            raw = f.read().decode("utf-8", errors="replace")
            lines = raw.splitlines(keepends=True)

            # 找出 header 行（最後一個 # 開頭的行）和資料起始行
            header_idx = 0
            for i, line in enumerate(lines):
                if line.startswith("#"):
                    header_idx = i
                else:
                    break

            # Header 行去掉 '# ' 前綴
            header_line = lines[header_idx].lstrip("# ").strip()

            # 用 csv reader 正確解析含逗號的帶引號欄位名
            reader = csv.reader(io.StringIO(header_line))
            columns = next(reader)

            # 讀取資料行
            data_text = "".join(lines[header_idx + 1:])
            df = pd.read_csv(
                io.StringIO(data_text),
                header=None,
                names=columns,
                low_memory=False,
            )

    # 第一個欄位是 "Date and time"
    ts_col = columns[0]  # "Date and time"
    df[ts_col] = pd.to_datetime(df[ts_col], errors="coerce")
    df = df.set_index(ts_col)
    df.index.name = "Timestamp"

    # 將數值欄位轉為 float（有些可能因 NaN 字串而成為 object）
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.sort_index()
    return df


def load_all_turbines(year: int = 2016) -> dict[str, pd.DataFrame]:
    """載入全場所有風機的 SCADA 資料。

    自動探索壓縮檔中的所有 CSV 檔案，並逐一載入。

    Parameters
    ----------
    year : int
        資料年份，預設為 2016。

    Returns
    -------
    dict[str, pd.DataFrame]
        風機 ID 對應其 SCADA 資料表的字典。
    """
    zip_path = _find_zip_path(year)
    csv_map = _discover_csv_files(zip_path)

    all_data: dict[str, pd.DataFrame] = {}
    for tid in sorted(csv_map.keys()):
        all_data[tid] = load_turbine_data(tid, year)
    return all_data


def get_turbine_info() -> pd.DataFrame:
    """取得 Kelmarsh 風場風機的靜態規格資訊。

    回傳包含風機製造商、型號、額定功率、轉子直徑等規格的資料表。
    同時嘗試讀取隨附的靜態資訊 CSV（若存在）。

    Returns
    -------
    pd.DataFrame
        風機靜態資訊。若有外部靜態資訊檔案，會合併回傳。
    """
    # 先嘗試讀取附帶的靜態資訊檔
    static_csv = _DATA_DIR / "Kelmarsh_WT_static.csv"
    if static_csv.exists():
        try:
            return pd.read_csv(static_csv)
        except Exception:
            pass

    # 回退至內建資訊
    rows = []
    for i in range(1, _TURBINE_INFO["num_turbines"] + 1):
        row = {
            "turbine_id": f"Kelmarsh_{i}",
            "manufacturer": _TURBINE_INFO["manufacturer"],
            "model": _TURBINE_INFO["model"],
            "rated_power_kw": _TURBINE_INFO["rated_power_kw"],
            "rotor_diameter_m": _TURBINE_INFO["rotor_diameter_m"],
            "hub_height_m": _TURBINE_INFO["hub_height_m"],
            "cut_in_ms": _TURBINE_INFO["cut_in_wind_speed_ms"],
            "rated_wind_ms": _TURBINE_INFO["rated_wind_speed_ms"],
            "cut_out_ms": _TURBINE_INFO["cut_out_wind_speed_ms"],
        }
        rows.append(row)
    return pd.DataFrame(rows)
