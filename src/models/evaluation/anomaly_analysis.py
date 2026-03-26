"""風機異常偵測與健康評估模組。

使用統計方法對 SCADA 資料進行異常偵測，包括：
溫度異常偵測（溫度-功率正常行為模型）、功率曲線偏差分析
（分箱比較法）、綜合健康分數計算，以及完整故障診斷報告生成。

所有分析函式透過 ``TurbineProfile`` 接收風機參數，不再綁定特定風機型號。
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

from src.core.constants import TurbineProfile


def _find_col(df: pd.DataFrame, keywords: list[str], suffix: str = "_Mean") -> str | None:
    """根據關鍵字搜尋欄位名稱。

    Parameters
    ----------
    df : pd.DataFrame
        資料表。
    keywords : list[str]
        搜尋關鍵字。
    suffix : str
        優先匹配的後綴。

    Returns
    -------
    str or None
        匹配的欄位名稱。
    """
    for kw in keywords:
        for col in df.columns:
            if kw.lower() in col.lower() and suffix.lower() in col.lower():
                return col
    exclude = ["standard deviation", "minimum", "maximum", "min ", "max ", "std"]
    for kw in keywords:
        for col in df.columns:
            col_lower = col.lower()
            if kw.lower() in col_lower and not any(ex in col_lower for ex in exclude):
                return col
    for kw in keywords:
        for col in df.columns:
            if kw.lower() in col.lower():
                return col
    return None


def detect_temperature_anomalies(
    df: pd.DataFrame,
    threshold_std: float = 3.0,
) -> dict:
    """偵測齒輪箱與軸承溫度異常。

    建立溫度-功率正常行為模型：在各功率區間計算溫度的平均值與標準差，
    將超過 threshold_std 倍標準差的時間點標記為異常。

    Parameters
    ----------
    df : pd.DataFrame
        含溫度與功率欄位的 SCADA 資料。
    threshold_std : float
        異常判定門檻，以標準差倍數計，預設 3.0。

    Returns
    -------
    dict
        包含以下鍵值：
        - anomaly_count: 總異常數
        - anomalies: 異常事件列表，每項含 timestamp, component,
          actual_temp, expected_temp, deviation
        - components_checked: 已檢查的溫度元件列表
    """
    power_col = _find_col(df, ["power", "active power"])

    # 要檢查的溫度元件
    temp_configs = [
        (["gear oil temp", "gearoil temp", "gear oil"], "齒輪箱油溫"),
        (["generator bearing front", "gen bearing front"], "發電機前軸承"),
        (["generator bearing rear", "gen bearing rear"], "發電機後軸承"),
        (["front bearing temp"], "前軸承"),
        (["rear bearing temp"], "後軸承"),
    ]

    all_anomalies: list[dict] = []
    components_checked: list[str] = []

    if not power_col:
        return {"anomaly_count": 0, "anomalies": [], "components_checked": []}

    pwr = df[power_col].astype(float)

    for keywords, component_name in temp_configs:
        temp_col = _find_col(df, keywords)
        if temp_col is None:
            continue

        components_checked.append(component_name)
        temp = df[temp_col].astype(float)

        # 建立功率分箱的正常行為模型
        # 將功率分為 20 個區間
        power_bins = pd.cut(pwr, bins=20, labels=False)

        # 計算每個區間的溫度統計
        bin_stats = pd.DataFrame({"power_bin": power_bins, "temp": temp}).dropna()
        if len(bin_stats) == 0:
            continue

        stats = bin_stats.groupby("power_bin")["temp"].agg(["mean", "std", "count"])
        stats = stats[stats["count"] >= 10]  # 至少 10 筆才有統計意義

        if len(stats) == 0:
            continue

        # 對每筆資料計算期望值與偏差
        for idx, _row in df.iterrows():
            p_val = pwr.get(idx, np.nan)
            t_val = temp.get(idx, np.nan)
            pb = power_bins.get(idx, np.nan)

            if pd.isna(p_val) or pd.isna(t_val) or pd.isna(pb):
                continue
            if pb not in stats.index:
                continue

            expected = stats.loc[pb, "mean"]
            std = stats.loc[pb, "std"]

            if std < 0.1:  # 避免除以零
                continue

            deviation = (t_val - expected) / std

            if abs(deviation) > threshold_std:
                all_anomalies.append(
                    {
                        "timestamp": str(idx),
                        "component": component_name,
                        "actual_temp": round(float(t_val), 1),
                        "expected_temp": round(float(expected), 1),
                        "deviation": round(float(deviation), 2),
                    }
                )

        # 限制每個元件最多回報 50 個異常（取偏差最大的）
        comp_anomalies = [a for a in all_anomalies if a["component"] == component_name]
        if len(comp_anomalies) > 50:
            comp_anomalies.sort(key=lambda x: abs(x["deviation"]), reverse=True)
            kept = {a["timestamp"] for a in comp_anomalies[:50]}
            all_anomalies = [
                a
                for a in all_anomalies
                if a["component"] != component_name or a["timestamp"] in kept
            ]

    return {
        "anomaly_count": len(all_anomalies),
        "anomalies": all_anomalies,
        "components_checked": components_checked,
    }


def detect_power_curve_anomalies(
    df: pd.DataFrame,
    profile: TurbineProfile | None = None,
    *,
    rated_power: float | None = None,
) -> dict:
    """偵測功率曲線異常（分箱比較法）。

    將風速分為 0.5 m/s 的區間，比較實際功率與區間內的平均功率，
    找出明顯偏離正常功率曲線的風速區段。

    Parameters
    ----------
    df : pd.DataFrame
        含風速與功率欄位的 SCADA 資料。
    rated_power : float
        額定功率 (kW)，預設 2050。

    Returns
    -------
    dict
        包含以下鍵值：
        - mean_deviation_pct: 平均偏差百分比
        - worst_wind_speed_bin: 偏差最大的風速區間
        - efficiency_loss_pct: 估算效率損失百分比
        - bin_analysis: 各風速區間的詳細分析列表
    """
    if profile is None and rated_power is not None:
        p = TurbineProfile(rated_power_kw=rated_power)
    else:
        p = profile or TurbineProfile()
    rp = p.rated_power_kw
    cut_in = p.cut_in_speed_ms
    rated_wind = p.rated_wind_speed_ms
    cut_out = p.cut_out_speed_ms

    ws_col = _find_col(df, ["wind speed", "windspeed", "ws"])
    power_col = _find_col(df, ["power", "active power"])

    empty_result: dict = {
        "mean_deviation_pct": 0.0,
        "worst_wind_speed_bin": "N/A",
        "efficiency_loss_pct": 0.0,
        "bin_analysis": [],
    }

    if not ws_col or not power_col:
        return empty_result

    ws = df[ws_col].astype(float)
    pwr = df[power_col].astype(float)

    # 只分析正常運行區間
    mask = (ws >= cut_in) & (ws <= cut_out) & (pwr > 0)
    ws_valid = ws[mask]
    pwr_valid = pwr[mask]

    if len(ws_valid) == 0:
        return empty_result

    # 分箱分析（0.5 m/s 區間）
    bins = np.arange(0, 30.5, 0.5)
    ws_binned = pd.cut(ws_valid, bins=bins)
    bin_stats = pd.DataFrame({"ws_bin": ws_binned, "power": pwr_valid})
    grouped = bin_stats.groupby("ws_bin", observed=True)["power"].agg(["mean", "std", "count"])
    grouped = grouped[grouped["count"] >= 5]

    if len(grouped) == 0:
        return empty_result

    def _cubic_theoretical(ws_val: float) -> float:
        """三次方理論功率。"""
        if ws_val < cut_in:
            return 0.0
        if ws_val < rated_wind:
            divisor = rated_wind - cut_in
            return rp * ((ws_val - cut_in) / divisor) ** 3 if divisor > 0 else 0.0
        return rp

    # 建立理想功率曲線（使用三次方模型）
    bin_analysis: list[dict] = []
    deviations: list[float] = []
    worst_bin = ""
    worst_dev = 0.0

    for bin_interval, row in grouped.iterrows():
        bin_mid = (bin_interval.left + bin_interval.right) / 2
        actual_mean = row["mean"]
        theoretical = _cubic_theoretical(bin_mid)

        dev_pct = ((actual_mean - theoretical) / theoretical) * 100 if theoretical > 10 else 0.0

        deviations.append(dev_pct)

        if abs(dev_pct) > abs(worst_dev):
            worst_dev = dev_pct
            worst_bin = f"{bin_interval.left:.1f}-{bin_interval.right:.1f} m/s"

        bin_analysis.append(
            {
                "wind_speed_bin": f"{bin_interval.left:.1f}-{bin_interval.right:.1f}",
                "actual_mean_kw": round(actual_mean, 1),
                "theoretical_kw": round(theoretical, 1),
                "deviation_pct": round(dev_pct, 1),
                "sample_count": int(row["count"]),
            }
        )

    mean_dev = float(np.mean(deviations)) if deviations else 0.0

    # 估算效率損失：加權平均偏差
    total_actual = pwr_valid.sum()
    theoretical_total = 0.0
    for _, row_data in bin_stats.iterrows():
        ws_val = ws_valid.get(row_data.name, np.nan) if hasattr(row_data, "name") else np.nan
        if pd.notna(ws_val):
            theoretical_total += _cubic_theoretical(float(ws_val))

    if theoretical_total > 0:
        efficiency_loss = ((theoretical_total - total_actual) / theoretical_total) * 100
    else:
        efficiency_loss = 0.0

    return {
        "mean_deviation_pct": round(mean_dev, 2),
        "worst_wind_speed_bin": worst_bin,
        "efficiency_loss_pct": round(efficiency_loss, 2),
        "bin_analysis": bin_analysis[:30],  # 限制回傳筆數
    }


def compute_health_score(df: pd.DataFrame, profile: TurbineProfile | None = None) -> dict:
    """計算風機綜合健康分數。

    根據多個指標加權計算健康分數（0~100）：
    - 資料完整度（權重 15%）
    - 功率曲線符合度（權重 30%）
    - 溫度穩定度（權重 30%）
    - 可用率（權重 25%）

    Parameters
    ----------
    df : pd.DataFrame
        經特徵工程處理後的 SCADA 資料。

    Returns
    -------
    dict
        包含以下鍵值：
        - health_score: 綜合健康分數 (0~100)
        - data_completeness_score: 資料完整度分數
        - power_curve_score: 功率曲線符合度分數
        - temperature_score: 溫度穩定度分數
        - availability_score: 可用率分數
    """
    scores: dict[str, float] = {}

    # ── 1. 資料完整度分數 ──
    total_cells = df.shape[0] * df.shape[1]
    missing_pct = (df.isna().sum().sum() / total_cells * 100) if total_cells > 0 else 100
    scores["data_completeness_score"] = max(0, 100 - missing_pct * 2)

    # ── 2. 功率曲線符合度 ──
    if "power_curve_deviation_pct" in df.columns:
        valid_dev = df["power_curve_deviation_pct"].dropna()
        if len(valid_dev) > 0:
            abs_dev_mean = valid_dev.abs().mean()
            # 偏差 0% -> 100 分, 偏差 >50% -> 0 分
            scores["power_curve_score"] = max(0, 100 - abs_dev_mean * 2)
        else:
            scores["power_curve_score"] = 50.0
    else:
        # 嘗試直接計算
        pc_result = detect_power_curve_anomalies(df, profile=profile)
        abs_dev = abs(pc_result["mean_deviation_pct"])
        scores["power_curve_score"] = max(0, 100 - abs_dev * 2)

    # ── 3. 溫度穩定度 ──
    temp_score = 100.0
    if "gear_oil_temp_rolling_std" in df.columns:
        rolling_std = df["gear_oil_temp_rolling_std"].dropna()
        if len(rolling_std) > 0:
            mean_std = rolling_std.mean()
            # 標準差 <2 -> 100, >10 -> 0
            temp_score = max(0, min(100, 100 - (mean_std - 2) * 12.5))

    # 也檢查溫度差異
    delta_cols = [c for c in df.columns if "delta" in c.lower() and "temp" in c.lower()]
    if delta_cols:
        delta_stds = []
        for dc in delta_cols:
            s = df[dc].dropna().std()
            if not np.isnan(s):
                delta_stds.append(s)
        if delta_stds:
            mean_delta_std = np.mean(delta_stds)
            delta_score = max(0, min(100, 100 - (mean_delta_std - 3) * 10))
            temp_score = (temp_score + delta_score) / 2

    scores["temperature_score"] = temp_score

    # ── 4. 可用率 ──
    if "operating_state" in df.columns:
        total = len(df)
        operating = (df["operating_state"].isin(["partial", "full"])).sum()
        availability = (operating / total * 100) if total > 0 else 0
    else:
        power_col = _find_col(df, ["power", "active power"])
        if power_col:
            pwr = df[power_col].astype(float)
            total = len(pwr.dropna())
            operating = (pwr > 0).sum()
            availability = (operating / total * 100) if total > 0 else 0
        else:
            availability = 50.0
    scores["availability_score"] = min(100, availability * 1.1)  # 90% 可用率 -> ~99 分

    # ── 加權平均 ──
    health = (
        scores["data_completeness_score"] * 0.15
        + scores["power_curve_score"] * 0.30
        + scores["temperature_score"] * 0.30
        + scores["availability_score"] * 0.25
    )
    scores["health_score"] = round(max(0, min(100, health)), 1)

    # 四捨五入所有分數
    for k in scores:
        scores[k] = round(scores[k], 1)

    return scores


def generate_diagnosis_report(
    df: pd.DataFrame, turbine_id: str, profile: TurbineProfile | None = None
) -> dict:
    """產生完整的故障診斷報告。

    彙整溫度異常偵測、功率曲線分析、健康分數計算等結果，
    並根據分析結果生成警告與維護建議。

    Parameters
    ----------
    df : pd.DataFrame
        經特徵工程處理後的 SCADA 資料。
    turbine_id : str
        風機 ID。

    Returns
    -------
    dict
        完整診斷報告，包含：
        - turbine_id: 風機 ID
        - analysis_period: 分析期間
        - total_records: 總記錄數
        - health_score: 健康分數 (0~100)
        - temperature_anomalies: 溫度異常事件列表
        - power_curve_analysis: 功率曲線分析結果
        - operational_summary: 運行概況
        - warnings: 警告列表
        - recommendations: 建議列表
    """
    report: dict = {}

    # ── 基本資訊 ──
    report["turbine_id"] = turbine_id
    report["analysis_timestamp"] = datetime.now().isoformat()
    report["total_records"] = len(df)

    if isinstance(df.index, pd.DatetimeIndex) and len(df) > 0:
        valid_idx = df.index.dropna()
        if len(valid_idx) > 0:
            report["analysis_period"] = {
                "start": str(valid_idx.min()),
                "end": str(valid_idx.max()),
            }
        else:
            report["analysis_period"] = {"start": "N/A", "end": "N/A"}
    else:
        report["analysis_period"] = {"start": "N/A", "end": "N/A"}

    # ── 健康分數 ──
    health_result = compute_health_score(df, profile=profile)
    report["health_score"] = health_result["health_score"]
    report["health_details"] = health_result

    # ── 溫度異常 ──
    temp_result = detect_temperature_anomalies(df)
    report["temperature_anomalies"] = temp_result["anomalies"][:20]  # 限制筆數
    report["temperature_anomaly_count"] = temp_result["anomaly_count"]
    report["temperature_components_checked"] = temp_result["components_checked"]

    # ── 功率曲線分析 ──
    pc_result = detect_power_curve_anomalies(df, profile=profile)
    report["power_curve_analysis"] = {
        "mean_deviation_pct": pc_result["mean_deviation_pct"],
        "worst_wind_speed_bin": pc_result["worst_wind_speed_bin"],
        "efficiency_loss_pct": pc_result["efficiency_loss_pct"],
    }

    # ── 運行概況 ──
    power_col = _find_col(df, ["power", "active power"])
    ops: dict = {}

    if "operating_state" in df.columns:
        state_counts = df["operating_state"].value_counts()
        total = len(df)
        ops["operating_hours"] = (
            round(state_counts.get("partial", 0) + state_counts.get("full", 0)) * 10 / 60
        )  # 10 分鐘 -> 小時
        ops["idle_hours"] = round(state_counts.get("idle", 0) * 10 / 60, 1)
        operating_count = state_counts.get("partial", 0) + state_counts.get("full", 0)
        ops["availability"] = round(operating_count / total * 100, 1) if total > 0 else 0.0

    p = profile or TurbineProfile()
    if "capacity_factor" in df.columns:
        ops["capacity_factor"] = round(df["capacity_factor"].mean() * 100, 1)
    elif power_col:
        pwr = df[power_col].astype(float)
        ops["capacity_factor"] = round(pwr.mean() / p.rated_power_kw * 100, 1)
    else:
        ops["capacity_factor"] = 0.0

    if "availability" not in ops:
        if power_col:
            pwr = df[power_col].astype(float)
            total_valid = len(pwr.dropna())
            ops["availability"] = (
                round((pwr > 0).sum() / total_valid * 100, 1) if total_valid > 0 else 0.0
            )
        else:
            ops["availability"] = 0.0

    if "operating_hours" not in ops:
        ops["operating_hours"] = round(len(df) * 10 / 60 * ops.get("availability", 0) / 100, 1)

    report["operational_summary"] = ops

    # ── 警告 ──
    warnings: list[str] = []

    if report["health_score"] < 60:
        warnings.append(f"健康分數偏低 ({report['health_score']}/100)，建議優先排檢")
    elif report["health_score"] < 80:
        warnings.append(f"健康分數中等 ({report['health_score']}/100)，建議持續監控")

    if temp_result["anomaly_count"] > 10:
        warnings.append(f"偵測到 {temp_result['anomaly_count']} 個溫度異常事件，可能有過熱風險")
    elif temp_result["anomaly_count"] > 0:
        warnings.append(f"偵測到 {temp_result['anomaly_count']} 個溫度異常事件")

    if abs(pc_result["mean_deviation_pct"]) > 10:
        warnings.append(
            f"功率曲線平均偏差 {pc_result['mean_deviation_pct']:.1f}%，"
            f"效率損失約 {pc_result['efficiency_loss_pct']:.1f}%"
        )
    elif abs(pc_result["mean_deviation_pct"]) > 5:
        warnings.append(f"功率曲線偏差略高 ({pc_result['mean_deviation_pct']:.1f}%)")

    if ops.get("availability", 100) < 85:
        warnings.append(f"可用率偏低 ({ops.get('availability', 0):.1f}%)，建議檢查停機原因")

    if ops.get("capacity_factor", 100) < 20:
        warnings.append(f"容量因數偏低 ({ops.get('capacity_factor', 0):.1f}%)")

    report["warnings"] = warnings

    # ── 建議 ──
    recommendations: list[str] = []

    if temp_result["anomaly_count"] > 5:
        # 找出最常出現異常的元件
        comp_counts: dict[str, int] = {}
        for a in temp_result["anomalies"]:
            comp = a["component"]
            comp_counts[comp] = comp_counts.get(comp, 0) + 1
        worst_comp = max(comp_counts, key=comp_counts.get) if comp_counts else "未知元件"
        recommendations.append(f"建議對{worst_comp}進行詳細檢查與油液分析")

    if abs(pc_result["mean_deviation_pct"]) > 10:
        recommendations.append("建議檢查葉片狀態（結冰、髒汙、損傷）與 pitch 系統校正")
        recommendations.append("建議執行 yaw alignment 校正以改善發電效率")
    elif abs(pc_result["mean_deviation_pct"]) > 5:
        recommendations.append("建議在下次定期維護時檢查葉片清潔狀況")

    if ops.get("availability", 100) < 85:
        recommendations.append("建議分析停機事件紀錄，找出主要停機原因")

    if not recommendations:
        recommendations.append("風機運行狀況良好，建議維持目前定期維護排程")

    report["recommendations"] = recommendations

    return report
