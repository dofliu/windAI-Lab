"""模型對比實驗框架 — 統一評估 NBM、LSTM、PatchTST 在相同資料集上的表現。

提供：
- 統一的時間序列 train/test 分割
- 多模型並行評估
- 標準化指標輸出（RMSE、MAE、R²、訓練時間、推論速度）
- 對比報告自動產生（表格 + LaTeX 格式）
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class BenchmarkResult:
    """單一模型的評估結果。

    Attributes:
        model_name: 模型名稱。
        model_type: 實際使用的模型類型（如 lstm / ridge_ar / patch_tst）。
        rmse: Root Mean Squared Error。
        mae: Mean Absolute Error。
        r2: 決定係數 R²。
        train_time_sec: 訓練耗時（秒）。
        predict_time_sec: 推論耗時（秒）。
        n_train: 訓練樣本數。
        n_test: 測試樣本數。
        extra: 模型特有的額外資訊。
    """

    model_name: str = ""
    model_type: str = ""
    rmse: float = 0.0
    mae: float = 0.0
    r2: float = 0.0
    train_time_sec: float = 0.0
    predict_time_sec: float = 0.0
    n_train: int = 0
    n_test: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ComparisonReport:
    """多模型對比報告。

    Attributes:
        results: 各模型評估結果列表。
        dataset_info: 資料集資訊。
        best_model: 依 R² 排序的最佳模型名稱。
        comparison_table: 對比表格（DataFrame）。
        latex_table: LaTeX 格式表格字串。
    """

    results: list[BenchmarkResult] = field(default_factory=list)
    dataset_info: dict[str, Any] = field(default_factory=dict)
    best_model: str = ""
    comparison_table: Any = None  # pd.DataFrame
    latex_table: str = ""


class ModelBenchmark:
    """模型對比實驗框架。

    用法：
        benchmark = ModelBenchmark(df, target="power", test_ratio=0.2)
        report = benchmark.run_all(epochs=50)
        print(report.comparison_table)
        print(report.latex_table)
    """

    def __init__(
        self,
        df: pd.DataFrame,
        target: str = "power",
        test_ratio: float = 0.2,
        sequence_length: int = 48,
        forecast_horizon: int = 12,
    ) -> None:
        self._df = df
        self._target = target
        self._test_ratio = test_ratio
        self._seq_len = sequence_length
        self._horizon = forecast_horizon

        # 找目標欄位
        self._target_col = self._find_target_col(df, target)
        if self._target_col is None:
            raise ValueError(f"未找到 {target} 相關欄位，可用欄位：{list(df.columns)}")

        # 準備時序資料
        self._series = df[self._target_col].dropna().values.astype(np.float32)

        # 時間序列 train/test 分割（保持時序順序）
        split_idx = int(len(self._series) * (1 - test_ratio))
        self._train_series = self._series[:split_idx]
        self._test_series = self._series[split_idx:]
        self._split_idx = split_idx

    def run_all(
        self,
        epochs: int = 50,
        include_nbm: bool = True,
        include_lstm: bool = True,
        include_patch_tst: bool = True,
        patch_length: int = 8,
        stride: int = 8,
    ) -> ComparisonReport:
        """執行所有模型的對比評估。

        Args:
            epochs: LSTM/PatchTST 訓練 epoch 數。
            include_nbm: 是否包含 NBM 模型。
            include_lstm: 是否包含 LSTM 模型。
            include_patch_tst: 是否包含 PatchTST 模型。
            patch_length: PatchTST patch 長度。
            stride: PatchTST patch 步進。

        Returns:
            ComparisonReport 含完整對比結果。
        """
        results: list[BenchmarkResult] = []

        if include_nbm:
            nbm_result = self._run_nbm()
            if nbm_result is not None:
                results.append(nbm_result)

        if include_lstm:
            results.append(self._run_lstm(epochs=epochs))

        if include_patch_tst:
            results.append(
                self._run_patch_tst(epochs=epochs, patch_length=patch_length, stride=stride)
            )

        return self._build_report(results)

    def _run_nbm(self) -> BenchmarkResult | None:
        """執行 NBM (Normal Behavior Model) 評估。"""
        try:
            from src.models.nbm.power_curve_nbm import PowerCurveNBM
        except ImportError:
            return None

        # NBM 需要完整 SCADA DataFrame（多變量）
        split_idx = int(len(self._df) * (1 - self._test_ratio))
        df_train = self._df.iloc[:split_idx]
        df_test = self._df.iloc[split_idx:]

        model = PowerCurveNBM()

        # 訓練
        t0 = time.perf_counter()
        try:
            train_result = model.train(df_train)
        except Exception as e:
            return BenchmarkResult(
                model_name="NBM (GBR)",
                model_type="nbm_error",
                extra={"error": str(e)},
            )
        train_time = time.perf_counter() - t0

        # 推論
        t0 = time.perf_counter()
        try:
            predictions = model.predict(df_test)
        except Exception as e:
            return BenchmarkResult(
                model_name="NBM (GBR)",
                model_type="nbm_error",
                extra={"error": str(e)},
            )
        predict_time = time.perf_counter() - t0

        # 計算測試集指標
        actual = df_test[self._target_col].values
        valid_mask = np.isfinite(predictions.values) & np.isfinite(actual)
        if valid_mask.sum() < 10:
            return BenchmarkResult(
                model_name="NBM (GBR)",
                model_type="nbm_insufficient_valid",
                extra={"valid_count": int(valid_mask.sum())},
            )

        y_true = actual[valid_mask]
        y_pred = predictions.values[valid_mask]
        rmse, mae, r2 = _compute_metrics(y_true, y_pred)

        return BenchmarkResult(
            model_name="NBM (GBR)",
            model_type="gradient_boosting",
            rmse=rmse,
            mae=mae,
            r2=r2,
            train_time_sec=round(train_time, 3),
            predict_time_sec=round(predict_time, 3),
            n_train=len(df_train),
            n_test=int(valid_mask.sum()),
            extra={
                "feature_importances": train_result.feature_importances,
                "r2_train": train_result.r2,
            },
        )

    def _run_lstm(self, epochs: int = 50) -> BenchmarkResult:
        """執行 LSTM 評估。"""
        from src.models.degradation.lstm_forecaster import LSTMForecaster

        forecaster = LSTMForecaster(
            sequence_length=self._seq_len,
            forecast_horizon=self._horizon,
        )

        t0 = time.perf_counter()
        result = forecaster.fit_and_predict(self._train_series, epochs=epochs)
        train_time = time.perf_counter() - t0

        # 在測試集上滑動窗口評估
        t0 = time.perf_counter()
        test_rmse, test_mae, test_r2 = self._sliding_eval(
            forecaster, self._test_series, result.model_type
        )
        predict_time = time.perf_counter() - t0

        return BenchmarkResult(
            model_name="LSTM",
            model_type=result.model_type,
            rmse=test_rmse,
            mae=test_mae,
            r2=test_r2,
            train_time_sec=round(train_time, 3),
            predict_time_sec=round(predict_time, 3),
            n_train=len(self._train_series),
            n_test=len(self._test_series),
            extra={
                "train_loss": result.train_loss,
                "val_loss": result.val_loss,
                "epochs_trained": result.epochs_trained,
                "val_rmse": result.rmse,
                "val_r2": result.r2,
            },
        )

    def _run_patch_tst(
        self,
        epochs: int = 50,
        patch_length: int = 8,
        stride: int = 8,
    ) -> BenchmarkResult:
        """執行 PatchTST 評估。"""
        from src.models.degradation.patch_tst_forecaster import PatchTSTForecaster

        forecaster = PatchTSTForecaster(
            sequence_length=self._seq_len,
            forecast_horizon=self._horizon,
            patch_length=patch_length,
            stride=stride,
        )

        t0 = time.perf_counter()
        result = forecaster.fit_and_predict(self._train_series, epochs=epochs)
        train_time = time.perf_counter() - t0

        # 在測試集上滑動窗口評估
        t0 = time.perf_counter()
        test_rmse, test_mae, test_r2 = self._sliding_eval(
            forecaster, self._test_series, result.model_type
        )
        predict_time = time.perf_counter() - t0

        return BenchmarkResult(
            model_name="PatchTST",
            model_type=result.model_type,
            rmse=test_rmse,
            mae=test_mae,
            r2=test_r2,
            train_time_sec=round(train_time, 3),
            predict_time_sec=round(predict_time, 3),
            n_train=len(self._train_series),
            n_test=len(self._test_series),
            extra={
                "train_loss": result.train_loss,
                "val_loss": result.val_loss,
                "epochs_trained": result.epochs_trained,
                "patch_length": patch_length,
                "num_patches": result.num_patches,
                "val_rmse": result.rmse,
                "val_r2": result.r2,
            },
        )

    def _sliding_eval(
        self,
        forecaster: Any,
        test_series: np.ndarray,
        model_type: str,
    ) -> tuple[float, float, float]:
        """在測試集上以滑動窗口進行多步預測評估。

        取測試集前面的 seq_len 筆作為初始窗口，
        逐步向前預測 horizon 步，與真實值比較。

        Returns:
            (rmse, mae, r2) 在測試集上的指標。
        """
        if len(test_series) < self._seq_len + self._horizon:
            # 資料不足，用訓練時的驗證指標作為估計
            return 0.0, 0.0, 0.0

        all_true: list[float] = []
        all_pred: list[float] = []

        # 合併 train 尾部 + test 以提供足夠的初始窗口
        full_series = np.concatenate([self._train_series[-self._seq_len :], test_series])

        step = max(1, self._horizon)
        for start in range(self._seq_len, len(full_series) - self._horizon, step):
            window = full_series[start - self._seq_len : start]
            predictions = self._predict_with_trained_model(forecaster, window)

            if predictions is not None and len(predictions) > 0:
                actual = full_series[start : start + len(predictions)]
                n = min(len(predictions), len(actual))
                all_true.extend(actual[:n].tolist())
                all_pred.extend(predictions[:n])

        if len(all_true) < 2:
            return 0.0, 0.0, 0.0

        return _compute_metrics(np.array(all_true), np.array(all_pred))

    def _predict_with_trained_model(
        self,
        forecaster: Any,
        window: np.ndarray,
    ) -> list[float] | None:
        """使用已訓練模型對窗口進行預測。"""
        if forecaster._model is None or forecaster._scaler is None:
            return None

        try:
            scaled = forecaster._scaler.transform(window.reshape(-1, 1)).flatten()

            if hasattr(forecaster, "_create_patches"):
                # PatchTST
                import torch

                x = torch.FloatTensor(scaled).unsqueeze(0)
                patches = forecaster._create_patches(x)
                forecaster._model.eval()
                with torch.no_grad():
                    pred_scaled = forecaster._model(patches).cpu().numpy().flatten()
            else:
                # LSTM
                import torch

                x = torch.FloatTensor(scaled).unsqueeze(0).unsqueeze(-1)
                forecaster._model.eval()
                with torch.no_grad():
                    pred_scaled = forecaster._model(x).cpu().numpy().flatten()

            predictions = forecaster._scaler.inverse_transform(
                pred_scaled.reshape(-1, 1)
            ).flatten()
            return [round(float(v), 3) for v in predictions]
        except Exception:
            # Ridge AR fallback
            try:
                scaled = forecaster._scaler.transform(window.reshape(-1, 1)).flatten()
                pred_scaled = forecaster._model.predict(scaled.reshape(1, -1)).flatten()
                predictions = forecaster._scaler.inverse_transform(
                    pred_scaled.reshape(-1, 1)
                ).flatten()
                return [round(float(v), 3) for v in predictions]
            except Exception:
                return None

    def _build_report(self, results: list[BenchmarkResult]) -> ComparisonReport:
        """建構對比報告。"""
        if not results:
            return ComparisonReport()

        # 建立對比表格
        rows = []
        for r in results:
            rows.append(
                {
                    "Model": r.model_name,
                    "Type": r.model_type,
                    "RMSE": round(r.rmse, 4),
                    "MAE": round(r.mae, 4),
                    "R²": round(r.r2, 4),
                    "Train (s)": r.train_time_sec,
                    "Predict (s)": r.predict_time_sec,
                    "N_train": r.n_train,
                    "N_test": r.n_test,
                }
            )

        table = pd.DataFrame(rows)
        table = table.sort_values("R²", ascending=False).reset_index(drop=True)

        # 最佳模型
        best = table.iloc[0]["Model"] if len(table) > 0 else ""

        # LaTeX 表格
        latex = self._to_latex(table)

        # 資料集資訊
        dataset_info = {
            "target": self._target,
            "target_column": self._target_col,
            "total_samples": len(self._series),
            "train_samples": len(self._train_series),
            "test_samples": len(self._test_series),
            "test_ratio": self._test_ratio,
            "sequence_length": self._seq_len,
            "forecast_horizon": self._horizon,
        }

        return ComparisonReport(
            results=results,
            dataset_info=dataset_info,
            best_model=str(best),
            comparison_table=table,
            latex_table=latex,
        )

    def _to_latex(self, table: pd.DataFrame) -> str:
        """將對比表格轉為 LaTeX 格式。"""
        header = (
            "\\begin{table}[htbp]\n"
            "\\centering\n"
            "\\caption{Model Comparison Results}\n"
            "\\label{tab:model_comparison}\n"
            "\\begin{tabular}{lcccccc}\n"
            "\\hline\n"
            "Model & Type & RMSE & MAE & R$^2$ & Train (s) & Predict (s) \\\\\n"
            "\\hline\n"
        )
        rows = ""
        for _, row in table.iterrows():
            rows += (
                f"{row['Model']} & {row['Type']} & "
                f"{row['RMSE']:.4f} & {row['MAE']:.4f} & {row['R²']:.4f} & "
                f"{row['Train (s)']:.3f} & {row['Predict (s)']:.3f} \\\\\n"
            )
        footer = "\\hline\n\\end{tabular}\n\\end{table}"
        return header + rows + footer

    @staticmethod
    def _find_target_col(df: pd.DataFrame, target: str) -> str | None:
        """搜尋目標欄位。"""
        target_keywords: dict[str, list[str]] = {
            "wind_speed": ["wind speed", "windspeed", "ws"],
            "power": ["power", "active power"],
            "temperature": ["gear oil temp", "bearing temp"],
        }
        keywords = target_keywords.get(target, [target])
        for kw in keywords:
            for col in df.columns:
                if kw.lower() in col.lower():
                    return col
        return None


def _compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float, float]:
    """計算 RMSE、MAE、R²。"""
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    mae = float(np.mean(np.abs(y_true - y_pred)))
    ss_res = float(np.sum((y_true - y_pred) ** 2))
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return round(rmse, 4), round(mae, 4), round(r2, 4)
