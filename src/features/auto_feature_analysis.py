"""自動特徵分析模組 — 零配置探索任意 SCADA 資料。

給任何 DataFrame，不需要預先知道欄位名稱或意義，自動產出：
1. 基礎統計摘要（均值、標準差、缺失率、偏態、峰態）
2. 欄位間相關性矩陣（Pearson + Spearman）
3. 特徵重要度排序（對目標變數的預測能力）
4. 異常值偵測與分佈分析
5. 時序穩定性分析（概念漂移偵測）

使用方式：
    from src.features.auto_feature_analysis import analyze_features
    report = analyze_features(df)
    # report 包含所有分析結果，可直接傳給前端視覺化
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def analyze_features(
    df: pd.DataFrame,
    target_col: str | None = None,
    max_features: int = 50,
    sample_size: int = 10000,
) -> dict[str, Any]:
    """對 DataFrame 執行全自動特徵分析。

    Parameters
    ----------
    df : pd.DataFrame
        任意資料表（不限欄位名稱或格式）。
    target_col : str | None
        目標變數（用於計算特徵重要度）。
        若為 None，自動偵測（優先選功率欄位）。
    max_features : int
        分析的最大欄位數（避免記憶體過大）。
    sample_size : int
        用於分析的取樣筆數（大資料集自動取樣）。

    Returns
    -------
    dict[str, Any]
        完整分析報告，包含：
        - summary: 基礎統計摘要
        - correlations: 相關性矩陣
        - feature_importance: 特徵重要度排序
        - anomalies: 異常值分析
        - distributions: 分佈特徵
        - drift: 時序穩定性
        - recommendations: 分析建議
    """
    # 準備資料
    df_work = _prepare_data(df, max_features, sample_size)

    if df_work.empty or len(df_work.columns) == 0:
        return {"error": "資料為空或沒有數值欄位", "summary": {}, "correlations": {},
                "feature_importance": [], "anomalies": {}, "distributions": {},
                "drift": {}, "recommendations": []}

    # 自動偵測目標變數
    if target_col is None:
        target_col = _auto_detect_target(df_work)

    # 執行各項分析
    report: dict[str, Any] = {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "numeric_columns": len(df_work.columns),
        "target_column": target_col,
    }

    report["summary"] = _compute_summary(df_work)
    report["correlations"] = _compute_correlations(df_work)
    report["feature_importance"] = _compute_importance(df_work, target_col)
    report["anomalies"] = _detect_anomalies(df_work)
    report["distributions"] = _analyze_distributions(df_work)
    report["drift"] = _analyze_drift(df_work)
    report["recommendations"] = _generate_recommendations(report)

    return report


def _prepare_data(
    df: pd.DataFrame, max_features: int, sample_size: int,
) -> pd.DataFrame:
    """準備分析用資料：只保留數值欄位、取樣、處理無限值。"""
    # 只保留數值欄位
    numeric = df.select_dtypes(include=[np.number])

    # 排除全為 NaN 或常數的欄位
    valid_cols = []
    for col in numeric.columns:
        if numeric[col].notna().sum() > 10:  # 至少 10 個有效值
            if numeric[col].std() > 0:  # 非常數
                valid_cols.append(col)

    numeric = numeric[valid_cols[:max_features]]

    # 取樣
    if len(numeric) > sample_size:
        numeric = numeric.sample(n=sample_size, random_state=42)

    # 處理無限值
    numeric = numeric.replace([np.inf, -np.inf], np.nan)

    return numeric


def _auto_detect_target(df: pd.DataFrame) -> str | None:
    """自動偵測最可能的目標變數。

    優先順序：功率 > 發電量 > 轉速 > 風速
    """
    priority_keywords = [
        ["active_power", "active power", "power_mean", "power (kw)", "p_avg", "power_output"],
        ["power", "generation", "energy"],
        ["rotor_speed", "rotor speed", "rotor_rpm"],
        ["wind_speed", "wind speed", "windspeed"],
    ]

    cols_lower = {c.lower(): c for c in df.columns}

    for keyword_group in priority_keywords:
        for kw in keyword_group:
            for cl, original in cols_lower.items():
                if kw in cl and "reactive" not in cl and "std" not in cl:
                    return original

    # 如果都找不到，選變異數最大的欄位
    variances = df.var().dropna()
    if not variances.empty:
        return str(variances.idxmax())

    return None


def _safe_float(val: Any, decimals: int = 4) -> float | None:
    """安全轉換為 JSON 可序列化的 float。"""
    try:
        v = float(val)
        if np.isfinite(v):
            return round(v, decimals)
        return None
    except (TypeError, ValueError):
        return None


def _compute_summary(df: pd.DataFrame) -> list[dict[str, Any]]:
    """計算每個欄位的統計摘要。"""
    summaries = []

    for col in df.columns:
        series = df[col].dropna()
        n_total = len(df[col])
        n_valid = len(series)
        n_missing = n_total - n_valid

        entry: dict[str, Any] = {
            "column": col,
            "count": n_valid,
            "missing": n_missing,
            "missing_pct": _safe_float(n_missing / n_total * 100 if n_total > 0 else 0, 1),
            "mean": _safe_float(series.mean()),
            "std": _safe_float(series.std()),
            "min": _safe_float(series.min()),
            "q25": _safe_float(series.quantile(0.25)),
            "median": _safe_float(series.median()),
            "q75": _safe_float(series.quantile(0.75)),
            "max": _safe_float(series.max()),
        }

        # 偏態與峰態
        if n_valid > 20:
            entry["skewness"] = _safe_float(series.skew())
            entry["kurtosis"] = _safe_float(series.kurtosis())

        summaries.append(entry)

    return summaries


def _compute_correlations(df: pd.DataFrame) -> dict[str, Any]:
    """計算欄位間相關性（Pearson + Spearman），回傳 top 相關欄位對。"""
    n_cols = len(df.columns)

    # 對小資料集計算完整矩陣，大資料集只算 top pairs
    if n_cols > 100:
        # 太多欄位，只取前 50 個（按方差排序）
        top_cols = df.var().nlargest(50).index.tolist()
        df_sub = df[top_cols]
    else:
        df_sub = df

    # Pearson 相關性
    try:
        pearson = df_sub.corr(method="pearson")
    except Exception:
        return {"top_pairs": [], "matrix_size": 0}

    # 提取 top 相關對（排除自相關）
    pairs = []
    cols = pearson.columns.tolist()
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            r = _safe_float(pearson.iloc[i, j])
            if r is not None:
                pairs.append({
                    "col_a": cols[i],
                    "col_b": cols[j],
                    "pearson": r,
                    "abs_pearson": _safe_float(abs(pearson.iloc[i, j])),
                })

    # 按絕對值排序，取 top 30
    pairs.sort(key=lambda x: x.get("abs_pearson", 0) or 0, reverse=True)
    top_pairs = pairs[:30]

    # 也產出完整矩陣（只在欄位數 ≤ 20 時）
    matrix: dict[str, dict[str, float | None]] = {}
    if n_cols <= 20:
        for col in pearson.columns:
            matrix[col] = {
                c: _safe_float(pearson.loc[col, c]) for c in pearson.columns
            }

    return {
        "top_pairs": top_pairs,
        "matrix": matrix,
        "matrix_size": len(df_sub.columns),
    }


def _compute_importance(
    df: pd.DataFrame, target_col: str | None,
) -> list[dict[str, Any]]:
    """計算特徵重要度（使用多種方法）。

    方法 1：與目標的相關性（快速）
    方法 2：互信息（Information Gain）
    方法 3：若可用，Random Forest 特徵重要度
    """
    if target_col is None or target_col not in df.columns:
        return []

    results = []
    target = df[target_col].dropna()
    feature_cols = [c for c in df.columns if c != target_col]

    for col in feature_cols:
        feature = df[col].dropna()

        # 取兩者的交集索引
        common_idx = target.index.intersection(feature.index)
        if len(common_idx) < 30:
            continue

        t = target.loc[common_idx]
        f = feature.loc[common_idx]

        entry: dict[str, Any] = {"column": col}

        # 方法 1：Pearson 相關性
        try:
            corr = t.corr(f)
            entry["correlation"] = _safe_float(corr)
            entry["abs_correlation"] = _safe_float(abs(corr))
        except Exception:
            entry["correlation"] = None
            entry["abs_correlation"] = None

        # 方法 2：Spearman 相關性（捕捉非線性單調關係）
        try:
            spearman = t.corr(f, method="spearman")
            entry["spearman"] = _safe_float(spearman)
        except Exception:
            entry["spearman"] = None

        # 方法 3：簡易互信息估計（離散化後的 MI）
        try:
            mi = _estimate_mutual_info(f.values, t.values)
            entry["mutual_info"] = _safe_float(mi)
        except Exception:
            entry["mutual_info"] = None

        # 綜合分數（加權平均）
        scores = []
        if entry.get("abs_correlation") is not None:
            scores.append(entry["abs_correlation"])
        if entry.get("spearman") is not None:
            scores.append(abs(entry["spearman"]))
        if entry.get("mutual_info") is not None:
            scores.append(min(entry["mutual_info"], 1.0))  # 正規化

        entry["composite_score"] = _safe_float(
            sum(scores) / len(scores) if scores else 0
        )

        results.append(entry)

    # 按綜合分數排序
    results.sort(key=lambda x: x.get("composite_score", 0) or 0, reverse=True)
    return results


def _estimate_mutual_info(x: np.ndarray, y: np.ndarray, n_bins: int = 20) -> float:
    """簡易互信息估計（基於直方圖離散化）。"""
    # 去除 NaN
    mask = ~(np.isnan(x) | np.isnan(y))
    x, y = x[mask], y[mask]

    if len(x) < 30:
        return 0.0

    # 離散化
    x_bins = np.clip(np.digitize(x, np.linspace(np.nanmin(x), np.nanmax(x), n_bins)), 0, n_bins)
    y_bins = np.clip(np.digitize(y, np.linspace(np.nanmin(y), np.nanmax(y), n_bins)), 0, n_bins)

    # 計算聯合分佈和邊際分佈
    n = len(x)
    joint = np.zeros((n_bins + 1, n_bins + 1))
    for xi, yi in zip(x_bins, y_bins):
        joint[xi, yi] += 1
    joint /= n

    px = joint.sum(axis=1)
    py = joint.sum(axis=0)

    # MI = sum p(x,y) * log(p(x,y) / (p(x)*p(y)))
    mi = 0.0
    for i in range(n_bins + 1):
        for j in range(n_bins + 1):
            if joint[i, j] > 0 and px[i] > 0 and py[j] > 0:
                mi += joint[i, j] * np.log2(joint[i, j] / (px[i] * py[j]))

    return max(mi, 0.0)


def _detect_anomalies(df: pd.DataFrame) -> dict[str, Any]:
    """偵測每個欄位的異常值（IQR 方法 + Z-score）。"""
    results: list[dict[str, Any]] = []

    for col in df.columns:
        series = df[col].dropna()
        if len(series) < 30:
            continue

        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1

        if iqr == 0:
            continue

        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outliers = series[(series < lower) | (series > upper)]

        # Z-score 異常
        mean = series.mean()
        std = series.std()
        if std > 0:
            z_outliers = series[((series - mean) / std).abs() > 3]
        else:
            z_outliers = pd.Series(dtype=float)

        results.append({
            "column": col,
            "iqr_outliers": len(outliers),
            "iqr_outlier_pct": _safe_float(len(outliers) / len(series) * 100, 2),
            "zscore_outliers": len(z_outliers),
            "lower_bound": _safe_float(lower),
            "upper_bound": _safe_float(upper),
        })

    # 按異常比例排序
    results.sort(key=lambda x: x.get("iqr_outlier_pct", 0) or 0, reverse=True)

    return {
        "columns": results,
        "total_columns_with_outliers": sum(
            1 for r in results if (r.get("iqr_outlier_pct") or 0) > 0
        ),
    }


def _analyze_distributions(df: pd.DataFrame) -> list[dict[str, Any]]:
    """分析每個欄位的分佈特徵（直方圖 bins、分佈類型判斷）。"""
    results = []

    for col in df.columns:
        series = df[col].dropna()
        if len(series) < 30:
            continue

        # 產出直方圖 bins（給前端畫圖用）
        try:
            counts, bin_edges = np.histogram(series, bins=30)
            histogram = [
                {
                    "bin_start": _safe_float(bin_edges[i]),
                    "bin_end": _safe_float(bin_edges[i + 1]),
                    "count": int(counts[i]),
                }
                for i in range(len(counts))
            ]
        except Exception:
            histogram = []

        # 分佈特徵判斷
        skew = series.skew()
        kurt = series.kurtosis()

        if abs(skew) < 0.5 and abs(kurt) < 1:
            dist_type = "近似常態"
        elif skew > 1:
            dist_type = "右偏"
        elif skew < -1:
            dist_type = "左偏"
        elif kurt > 3:
            dist_type = "尖峰"
        elif kurt < -1:
            dist_type = "平坦"
        else:
            dist_type = "中等偏態"

        results.append({
            "column": col,
            "distribution_type": dist_type,
            "skewness": _safe_float(skew),
            "kurtosis": _safe_float(kurt),
            "histogram": histogram,
            "n_unique": int(series.nunique()),
            "zero_pct": _safe_float((series == 0).sum() / len(series) * 100, 2),
        })

    return results


def _analyze_drift(df: pd.DataFrame) -> dict[str, Any]:
    """分析時序穩定性（概念漂移偵測）。

    將資料分成 4 個時間段，比較統計量變化。
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        return {"available": False, "reason": "索引非時間序列"}

    n = len(df)
    quarter = n // 4
    if quarter < 20:
        return {"available": False, "reason": "資料量不足以分段"}

    segments = [
        df.iloc[:quarter],
        df.iloc[quarter:quarter * 2],
        df.iloc[quarter * 2:quarter * 3],
        df.iloc[quarter * 3:],
    ]
    segment_labels = ["Q1", "Q2", "Q3", "Q4"]

    drift_results: list[dict[str, Any]] = []

    for col in df.columns[:20]:  # 限制分析欄位數
        means = [_safe_float(seg[col].mean()) for seg in segments]
        stds = [_safe_float(seg[col].std()) for seg in segments]

        # 判斷是否有漂移（均值變化 > 2 倍標準差）
        overall_std = df[col].std()
        mean_range = max(m or 0 for m in means) - min(m or 0 for m in means)

        has_drift = False
        if overall_std > 0:
            has_drift = mean_range > 2 * overall_std

        drift_results.append({
            "column": col,
            "segment_means": dict(zip(segment_labels, means)),
            "segment_stds": dict(zip(segment_labels, stds)),
            "has_drift": bool(has_drift),
            "drift_magnitude": _safe_float(
                mean_range / overall_std if overall_std > 0 else 0
            ),
        })

    # 按漂移程度排序
    drift_results.sort(
        key=lambda x: x.get("drift_magnitude", 0) or 0, reverse=True
    )

    return {
        "available": True,
        "columns": drift_results,
        "drifted_count": sum(1 for r in drift_results if r.get("has_drift")),
    }


def _generate_recommendations(report: dict[str, Any]) -> list[dict[str, str]]:
    """根據分析結果產出智慧建議。"""
    recs: list[dict[str, str]] = []

    # 檢查缺失值
    summaries = report.get("summary", [])
    high_missing = [
        s for s in summaries
        if (s.get("missing_pct") or 0) > 20
    ]
    if high_missing:
        cols = ", ".join(s["column"] for s in high_missing[:3])
        recs.append({
            "type": "warning",
            "title": "高缺失率欄位",
            "detail": f"以下欄位缺失率 >20%：{cols}。建議檢查感測器是否故障或資料擷取是否中斷。",
        })

    # 檢查高相關性（多重共線性）
    top_pairs = report.get("correlations", {}).get("top_pairs", [])
    high_corr = [p for p in top_pairs if (p.get("abs_pearson") or 0) > 0.95]
    if high_corr:
        pair = high_corr[0]
        recs.append({
            "type": "info",
            "title": "高度相關欄位",
            "detail": f"{pair['col_a']} 與 {pair['col_b']} 相關性 {pair['pearson']}。"
                      f"若用於建模，可考慮移除其中之一以避免多重共線性。",
        })

    # 檢查重要特徵
    importance = report.get("feature_importance", [])
    if importance:
        top3 = importance[:3]
        cols = ", ".join(f["column"] for f in top3)
        recs.append({
            "type": "success",
            "title": "最重要特徵 Top 3",
            "detail": f"對目標變數影響最大的欄位：{cols}。建議優先用於建模。",
        })

    # 檢查異常值
    anomalies = report.get("anomalies", {})
    high_outliers = [
        c for c in anomalies.get("columns", [])
        if (c.get("iqr_outlier_pct") or 0) > 10
    ]
    if high_outliers:
        cols = ", ".join(c["column"] for c in high_outliers[:3])
        recs.append({
            "type": "warning",
            "title": "高異常值比例",
            "detail": f"以下欄位異常值超過 10%：{cols}。可能是感測器範圍設定問題或極端工況。",
        })

    # 檢查漂移
    drift = report.get("drift", {})
    if drift.get("available") and drift.get("drifted_count", 0) > 0:
        drifted = [c for c in drift.get("columns", []) if c.get("has_drift")][:3]
        cols = ", ".join(c["column"] for c in drifted)
        recs.append({
            "type": "warning",
            "title": "偵測到概念漂移",
            "detail": f"以下欄位在不同時間段有顯著統計變化：{cols}。"
                      f"可能是風機老化、季節效應或感測器校正問題。",
        })

    if not recs:
        recs.append({
            "type": "success",
            "title": "資料品質良好",
            "detail": "未偵測到明顯的資料品質問題。可直接用於建模。",
        })

    return recs
