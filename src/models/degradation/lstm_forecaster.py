"""LSTM 時序預測模型 — 風速與功率短期預測。

使用 PyTorch LSTM 進行單步或多步時序預測：
- 風速短期預測（1~48 步，每步 10 分鐘 → 最多 8 小時）
- 功率短期預測
- 健康指標趨勢預測

若 PyTorch 不可用，自動降級至基於 scikit-learn 的 Ridge 回歸 AR 模型。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class LSTMForecastResult:
    """LSTM 預測結果。

    Attributes:
        predictions: 預測值序列。
        horizon_steps: 預測步數。
        train_loss: 訓練損失（MSE）。
        val_loss: 驗證損失（MSE）。
        rmse: 預測 RMSE。
        mae: 預測 MAE。
        r2: 決定係數（R²），用於跨模型對比。
        model_type: 模型類型（"lstm" / "ridge_ar"）。
        feature_name: 預測目標欄位名稱。
        sequence_length: 輸入序列長度。
        epochs_trained: 實際訓練 epoch 數。
    """

    predictions: list[float] = field(default_factory=list)
    horizon_steps: int = 0
    train_loss: float = 0.0
    val_loss: float = 0.0
    rmse: float = 0.0
    mae: float = 0.0
    r2: float = 0.0
    model_type: str = "lstm"
    feature_name: str = ""
    sequence_length: int = 48
    epochs_trained: int = 0


class LSTMForecaster:
    """LSTM 時序預測器。

    支援兩種後端：
    1. PyTorch LSTM（首選，需 torch 可用）
    2. Ridge AR（降級，純 scikit-learn）
    """

    def __init__(
        self,
        sequence_length: int = 48,
        hidden_dim: int = 64,
        num_layers: int = 2,
        dropout: float = 0.2,
        forecast_horizon: int = 12,
    ) -> None:
        self._seq_len = sequence_length
        self._hidden_dim = hidden_dim
        self._num_layers = num_layers
        self._dropout = dropout
        self._horizon = forecast_horizon
        self._model: Any = None
        self._scaler: Any = None
        self._model_type = "lstm"

    def save(self, path: str | Path) -> None:
        """儲存已訓練的模型至磁碟。

        Args:
            path: 儲存目錄路徑。
        """
        from pathlib import Path as _Path

        save_dir = _Path(path)
        save_dir.mkdir(parents=True, exist_ok=True)

        import joblib

        # 儲存 scaler 與超參數
        meta = {
            "seq_len": self._seq_len,
            "hidden_dim": self._hidden_dim,
            "num_layers": self._num_layers,
            "dropout": self._dropout,
            "horizon": self._horizon,
            "model_type": self._model_type,
        }
        joblib.dump({"meta": meta, "scaler": self._scaler}, save_dir / "meta.joblib")

        # 儲存模型
        if self._model_type == "lstm":
            import torch

            torch.save(self._model.state_dict(), save_dir / "lstm_weights.pt")
        elif self._model is not None:
            joblib.dump(self._model, save_dir / "ridge_model.joblib")

    @classmethod
    def load(cls, path: str | Path) -> "LSTMForecaster":
        """從磁碟載入已訓練的模型。

        Args:
            path: 儲存目錄路徑。

        Returns:
            已載入的 LSTMForecaster 實例。
        """
        from pathlib import Path as _Path

        import joblib

        load_dir = _Path(path)
        saved = joblib.load(load_dir / "meta.joblib")
        meta = saved["meta"]

        instance = cls(
            sequence_length=meta["seq_len"],
            hidden_dim=meta["hidden_dim"],
            num_layers=meta["num_layers"],
            dropout=meta["dropout"],
            forecast_horizon=meta["horizon"],
        )
        instance._scaler = saved["scaler"]
        instance._model_type = meta["model_type"]

        if meta["model_type"] == "lstm":
            import torch
            import torch.nn as nn

            class _LSTMModel(nn.Module):
                def __init__(self, input_dim: int, hidden: int, layers: int, out: int, drop: float):
                    super().__init__()
                    self.lstm = nn.LSTM(input_dim, hidden, layers, batch_first=True, dropout=drop)
                    self.fc = nn.Linear(hidden, out)

                def forward(self, x: torch.Tensor) -> torch.Tensor:
                    o, _ = self.lstm(x)
                    return self.fc(o[:, -1, :])

            model = _LSTMModel(
                1, meta["hidden_dim"], meta["num_layers"], meta["horizon"], meta["dropout"]
            )
            model.load_state_dict(torch.load(load_dir / "lstm_weights.pt", weights_only=True))
            model.eval()
            instance._model = model
        else:
            instance._model = joblib.load(load_dir / "ridge_model.joblib")

        return instance

    def fit_and_predict(
        self,
        series: np.ndarray,
        epochs: int = 50,
        learning_rate: float = 0.001,
        val_ratio: float = 0.2,
    ) -> LSTMForecastResult:
        """訓練並預測。

        Parameters
        ----------
        series : np.ndarray
            一維時間序列（如風速、功率），至少需要 seq_len + horizon 筆。
        epochs : int
            訓練 epoch 數。
        learning_rate : float
            學習率。
        val_ratio : float
            驗證集比例。

        Returns
        -------
        LSTMForecastResult
            預測結果。
        """
        series = np.asarray(series, dtype=np.float32)
        series = series[np.isfinite(series)]

        if len(series) < self._seq_len + self._horizon + 10:
            return LSTMForecastResult(
                model_type="insufficient_data",
                sequence_length=self._seq_len,
                horizon_steps=self._horizon,
            )

        # 正規化
        from sklearn.preprocessing import MinMaxScaler

        self._scaler = MinMaxScaler()
        scaled = self._scaler.fit_transform(series.reshape(-1, 1)).flatten()

        # 建立序列
        x_seqs, y_seqs = self._create_sequences(scaled)

        # 訓練/驗證分割
        val_size = max(1, int(len(x_seqs) * val_ratio))
        x_train, x_val = x_seqs[:-val_size], x_seqs[-val_size:]
        y_train, y_val = y_seqs[:-val_size], y_seqs[-val_size:]

        # 嘗試 PyTorch LSTM
        try:
            return self._train_lstm(x_train, y_train, x_val, y_val, scaled, epochs, learning_rate)
        except Exception:
            # 降級至 Ridge AR
            return self._train_ridge_ar(x_train, y_train, x_val, y_val, scaled)

    def _create_sequences(self, data: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """建立滑動窗口序列。"""
        x_list, y_list = [], []
        for i in range(len(data) - self._seq_len - self._horizon + 1):
            x_list.append(data[i : i + self._seq_len])
            y_list.append(data[i + self._seq_len : i + self._seq_len + self._horizon])
        return np.array(x_list), np.array(y_list)

    def _train_lstm(
        self,
        x_train: np.ndarray,
        y_train: np.ndarray,
        x_val: np.ndarray,
        y_val: np.ndarray,
        full_scaled: np.ndarray,
        epochs: int,
        lr: float,
    ) -> LSTMForecastResult:
        """PyTorch LSTM 訓練。"""
        import torch
        import torch.nn as nn

        class _LSTMModel(nn.Module):
            def __init__(self, input_dim: int, hidden: int, layers: int, out: int, drop: float):
                super().__init__()
                self.lstm = nn.LSTM(input_dim, hidden, layers, batch_first=True, dropout=drop)
                self.fc = nn.Linear(hidden, out)

            def forward(self, x: torch.Tensor) -> torch.Tensor:
                out, _ = self.lstm(x)
                return self.fc(out[:, -1, :])

        device = torch.device("cpu")
        model = _LSTMModel(1, self._hidden_dim, self._num_layers, self._horizon, self._dropout)
        model.to(device)

        optimizer = torch.optim.Adam(model.parameters(), lr=lr)
        criterion = nn.MSELoss()

        # 轉 tensor
        x_t = torch.FloatTensor(x_train).unsqueeze(-1).to(device)
        y_t = torch.FloatTensor(y_train).to(device)
        x_v = torch.FloatTensor(x_val).unsqueeze(-1).to(device)
        y_v = torch.FloatTensor(y_val).to(device)

        # 訓練
        train_loss = 0.0
        for _epoch in range(epochs):
            model.train()
            optimizer.zero_grad()
            pred = model(x_t)
            loss = criterion(pred, y_t)
            loss.backward()
            optimizer.step()
            train_loss = loss.item()

        # 驗證
        model.eval()
        with torch.no_grad():
            val_pred = model(x_v)
            val_loss = criterion(val_pred, y_v).item()

        # 預測未來
        last_seq = torch.FloatTensor(full_scaled[-self._seq_len :]).unsqueeze(0).unsqueeze(-1)
        with torch.no_grad():
            future_scaled = model(last_seq.to(device)).cpu().numpy().flatten()

        # 反正規化
        future = self._scaler.inverse_transform(future_scaled.reshape(-1, 1)).flatten()

        # 計算驗證集上的 RMSE / MAE / R²
        val_pred_np = val_pred.cpu().numpy()
        y_val_inv = self._scaler.inverse_transform(y_val.reshape(-1, 1)[:, :1]).flatten()
        pred_inv = self._scaler.inverse_transform(val_pred_np.reshape(-1, 1)[:, :1]).flatten()
        rmse = float(np.sqrt(np.mean((y_val_inv - pred_inv) ** 2)))
        mae = float(np.mean(np.abs(y_val_inv - pred_inv)))
        ss_res = float(np.sum((y_val_inv - pred_inv) ** 2))
        ss_tot = float(np.sum((y_val_inv - np.mean(y_val_inv)) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

        self._model = model
        self._model_type = "lstm"

        return LSTMForecastResult(
            predictions=[round(float(v), 3) for v in future],
            horizon_steps=self._horizon,
            train_loss=round(train_loss, 6),
            val_loss=round(val_loss, 6),
            rmse=round(rmse, 3),
            mae=round(mae, 3),
            r2=round(r2, 4),
            model_type="lstm",
            sequence_length=self._seq_len,
            epochs_trained=epochs,
        )

    def _train_ridge_ar(
        self,
        x_train: np.ndarray,
        y_train: np.ndarray,
        x_val: np.ndarray,
        y_val: np.ndarray,
        full_scaled: np.ndarray,
    ) -> LSTMForecastResult:
        """Ridge 自回歸降級方案。"""
        from sklearn.linear_model import Ridge
        from sklearn.metrics import mean_absolute_error, mean_squared_error

        # 多輸出 Ridge 回歸
        model = Ridge(alpha=1.0)
        model.fit(x_train, y_train)

        # 驗證
        val_pred = model.predict(x_val)
        val_loss = float(mean_squared_error(y_val, val_pred))

        train_pred = model.predict(x_train)
        train_loss = float(mean_squared_error(y_train, train_pred))

        # 預測未來
        last_seq = full_scaled[-self._seq_len :].reshape(1, -1)
        future_scaled = model.predict(last_seq).flatten()

        # 反正規化
        future = self._scaler.inverse_transform(future_scaled.reshape(-1, 1)).flatten()

        # 計算真實尺度的誤差
        y_val_first = self._scaler.inverse_transform(y_val[:, :1]).flatten()
        pred_first = self._scaler.inverse_transform(val_pred[:, :1]).flatten()
        rmse = float(np.sqrt(mean_squared_error(y_val_first, pred_first)))
        mae = float(mean_absolute_error(y_val_first, pred_first))
        ss_res = float(np.sum((y_val_first - pred_first) ** 2))
        ss_tot = float(np.sum((y_val_first - np.mean(y_val_first)) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

        self._model = model
        self._model_type = "ridge_ar"

        return LSTMForecastResult(
            predictions=[round(float(v), 3) for v in future],
            horizon_steps=self._horizon,
            train_loss=round(train_loss, 6),
            val_loss=round(val_loss, 6),
            rmse=round(rmse, 3),
            mae=round(mae, 3),
            r2=round(r2, 4),
            model_type="ridge_ar",
            sequence_length=self._seq_len,
            epochs_trained=0,
        )
