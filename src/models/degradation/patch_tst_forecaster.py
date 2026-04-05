"""PatchTST 時序預測模型 — 基於 Transformer 的風速與功率預測。

實作簡化版 PatchTST (A Time Series is Worth 64 Words, ICLR 2023)：
- 將時間序列切成固定長度的 patches
- 透過 Transformer Encoder 學習 patch 間的時序依賴
- 支援多步預測（multi-step forecasting）

若 PyTorch 不可用，自動降級至 Ridge 回歸 AR 模型。

Reference:
    Nie et al., "A Time Series is Worth 64 Words: Long-term Forecasting
    with Transformers", ICLR 2023.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class PatchTSTForecastResult:
    """PatchTST 預測結果。

    Attributes:
        predictions: 預測值序列。
        horizon_steps: 預測步數。
        train_loss: 訓練損失（MSE）。
        val_loss: 驗證損失（MSE）。
        rmse: 預測 RMSE。
        mae: 預測 MAE。
        r2: 決定係數（R²），用於跨模型對比。
        model_type: 模型類型（"patch_tst" / "ridge_ar"）。
        feature_name: 預測目標欄位名稱。
        sequence_length: 輸入序列長度。
        patch_length: 每個 patch 的長度。
        num_patches: patch 數量。
        epochs_trained: 實際訓練 epoch 數。
    """

    predictions: list[float] = field(default_factory=list)
    horizon_steps: int = 0
    train_loss: float = 0.0
    val_loss: float = 0.0
    rmse: float = 0.0
    mae: float = 0.0
    r2: float = 0.0
    model_type: str = "patch_tst"
    feature_name: str = ""
    sequence_length: int = 48
    patch_length: int = 8
    num_patches: int = 6
    epochs_trained: int = 0


class PatchTSTForecaster:
    """PatchTST 時序預測器。

    將輸入序列切成 patches，透過 Transformer Encoder 捕捉長距離時序依賴。

    支援兩種後端：
    1. PyTorch PatchTST（首選，需 torch 可用）
    2. Ridge AR（降級，純 scikit-learn）
    """

    def __init__(
        self,
        sequence_length: int = 48,
        forecast_horizon: int = 12,
        patch_length: int = 8,
        stride: int = 8,
        d_model: int = 64,
        n_heads: int = 4,
        n_layers: int = 2,
        d_ff: int = 128,
        dropout: float = 0.1,
    ) -> None:
        self._seq_len = sequence_length
        self._horizon = forecast_horizon
        self._patch_len = patch_length
        self._stride = stride
        self._d_model = d_model
        self._n_heads = n_heads
        self._n_layers = n_layers
        self._d_ff = d_ff
        self._dropout = dropout
        self._model: Any = None
        self._scaler: Any = None
        self._model_type = "patch_tst"

        # 計算 patch 數量
        self._num_patches = (sequence_length - patch_length) // stride + 1

    def save(self, path: str | Path) -> None:
        """儲存已訓練的模型至磁碟。

        Args:
            path: 儲存目錄路徑。
        """
        save_dir = Path(path)
        save_dir.mkdir(parents=True, exist_ok=True)

        import joblib

        meta = {
            "seq_len": self._seq_len,
            "horizon": self._horizon,
            "patch_len": self._patch_len,
            "stride": self._stride,
            "d_model": self._d_model,
            "n_heads": self._n_heads,
            "n_layers": self._n_layers,
            "d_ff": self._d_ff,
            "dropout": self._dropout,
            "model_type": self._model_type,
            "num_patches": self._num_patches,
        }
        joblib.dump({"meta": meta, "scaler": self._scaler}, save_dir / "meta.joblib")

        if self._model_type == "patch_tst":
            import torch

            torch.save(self._model.state_dict(), save_dir / "patch_tst_weights.pt")
        elif self._model is not None:
            joblib.dump(self._model, save_dir / "ridge_model.joblib")

    @classmethod
    def load(cls, path: str | Path) -> "PatchTSTForecaster":
        """從磁碟載入已訓練的模型。

        Args:
            path: 儲存目錄路徑。

        Returns:
            已載入的 PatchTSTForecaster 實例。
        """
        import joblib

        load_dir = Path(path)
        saved = joblib.load(load_dir / "meta.joblib")
        meta = saved["meta"]

        instance = cls(
            sequence_length=meta["seq_len"],
            forecast_horizon=meta["horizon"],
            patch_length=meta["patch_len"],
            stride=meta["stride"],
            d_model=meta["d_model"],
            n_heads=meta["n_heads"],
            n_layers=meta["n_layers"],
            d_ff=meta["d_ff"],
            dropout=meta["dropout"],
        )
        instance._scaler = saved["scaler"]
        instance._model_type = meta["model_type"]

        if meta["model_type"] == "patch_tst":
            import torch

            model = _build_patch_tst_model(
                num_patches=meta["num_patches"],
                patch_len=meta["patch_len"],
                d_model=meta["d_model"],
                n_heads=meta["n_heads"],
                n_layers=meta["n_layers"],
                d_ff=meta["d_ff"],
                dropout=meta["dropout"],
                horizon=meta["horizon"],
            )
            model.load_state_dict(
                torch.load(load_dir / "patch_tst_weights.pt", weights_only=True)
            )
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
    ) -> PatchTSTForecastResult:
        """訓練並預測。

        Parameters
        ----------
        series : np.ndarray
            一維時間序列，至少需要 seq_len + horizon + 10 筆。
        epochs : int
            訓練 epoch 數。
        learning_rate : float
            學習率。
        val_ratio : float
            驗證集比例。

        Returns
        -------
        PatchTSTForecastResult
            預測結果。
        """
        series = np.asarray(series, dtype=np.float32)
        series = series[np.isfinite(series)]

        if len(series) < self._seq_len + self._horizon + 10:
            return PatchTSTForecastResult(
                model_type="insufficient_data",
                sequence_length=self._seq_len,
                horizon_steps=self._horizon,
                patch_length=self._patch_len,
                num_patches=self._num_patches,
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

        # 嘗試 PyTorch PatchTST
        try:
            return self._train_patch_tst(
                x_train, y_train, x_val, y_val, scaled, epochs, learning_rate
            )
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

    def _create_patches(self, x: "torch.Tensor") -> "torch.Tensor":
        """將序列切成 patches。

        Args:
            x: shape (batch, seq_len)

        Returns:
            patches: shape (batch, num_patches, patch_len)
        """
        import torch

        batch_size = x.shape[0]
        patches = x.unfold(dimension=1, size=self._patch_len, step=self._stride)
        return patches

    def _train_patch_tst(
        self,
        x_train: np.ndarray,
        y_train: np.ndarray,
        x_val: np.ndarray,
        y_val: np.ndarray,
        full_scaled: np.ndarray,
        epochs: int,
        lr: float,
    ) -> PatchTSTForecastResult:
        """PyTorch PatchTST 訓練。"""
        import torch
        import torch.nn as nn

        device = torch.device("cpu")

        model = _build_patch_tst_model(
            num_patches=self._num_patches,
            patch_len=self._patch_len,
            d_model=self._d_model,
            n_heads=self._n_heads,
            n_layers=self._n_layers,
            d_ff=self._d_ff,
            dropout=self._dropout,
            horizon=self._horizon,
        )
        model.to(device)

        optimizer = torch.optim.Adam(model.parameters(), lr=lr)
        criterion = nn.MSELoss()

        # 轉 tensor 並建立 patches
        x_t = torch.FloatTensor(x_train).to(device)
        y_t = torch.FloatTensor(y_train).to(device)
        x_v = torch.FloatTensor(x_val).to(device)
        y_v = torch.FloatTensor(y_val).to(device)

        x_t_patches = self._create_patches(x_t)
        x_v_patches = self._create_patches(x_v)

        # 訓練
        train_loss = 0.0
        for _epoch in range(epochs):
            model.train()
            optimizer.zero_grad()
            pred = model(x_t_patches)
            loss = criterion(pred, y_t)
            loss.backward()
            optimizer.step()
            train_loss = loss.item()

        # 驗證
        model.eval()
        with torch.no_grad():
            val_pred = model(x_v_patches)
            val_loss = criterion(val_pred, y_v).item()

        # 預測未來
        last_seq = torch.FloatTensor(full_scaled[-self._seq_len :]).unsqueeze(0).to(device)
        last_patches = self._create_patches(last_seq)
        with torch.no_grad():
            future_scaled = model(last_patches).cpu().numpy().flatten()

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
        self._model_type = "patch_tst"

        return PatchTSTForecastResult(
            predictions=[round(float(v), 3) for v in future],
            horizon_steps=self._horizon,
            train_loss=round(train_loss, 6),
            val_loss=round(val_loss, 6),
            rmse=round(rmse, 3),
            mae=round(mae, 3),
            r2=round(r2, 4),
            model_type="patch_tst",
            sequence_length=self._seq_len,
            patch_length=self._patch_len,
            num_patches=self._num_patches,
            epochs_trained=epochs,
        )

    def _train_ridge_ar(
        self,
        x_train: np.ndarray,
        y_train: np.ndarray,
        x_val: np.ndarray,
        y_val: np.ndarray,
        full_scaled: np.ndarray,
    ) -> PatchTSTForecastResult:
        """Ridge 自回歸降級方案。"""
        from sklearn.linear_model import Ridge
        from sklearn.metrics import mean_absolute_error, mean_squared_error

        model = Ridge(alpha=1.0)
        model.fit(x_train, y_train)

        val_pred = model.predict(x_val)
        val_loss = float(mean_squared_error(y_val, val_pred))

        train_pred = model.predict(x_train)
        train_loss = float(mean_squared_error(y_train, train_pred))

        last_seq = full_scaled[-self._seq_len :].reshape(1, -1)
        future_scaled = model.predict(last_seq).flatten()

        future = self._scaler.inverse_transform(future_scaled.reshape(-1, 1)).flatten()

        y_val_first = self._scaler.inverse_transform(y_val[:, :1]).flatten()
        pred_first = self._scaler.inverse_transform(val_pred[:, :1]).flatten()
        rmse = float(np.sqrt(mean_squared_error(y_val_first, pred_first)))
        mae = float(mean_absolute_error(y_val_first, pred_first))
        ss_res = float(np.sum((y_val_first - pred_first) ** 2))
        ss_tot = float(np.sum((y_val_first - np.mean(y_val_first)) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

        self._model = model
        self._model_type = "ridge_ar"

        return PatchTSTForecastResult(
            predictions=[round(float(v), 3) for v in future],
            horizon_steps=self._horizon,
            train_loss=round(train_loss, 6),
            val_loss=round(val_loss, 6),
            rmse=round(rmse, 3),
            mae=round(mae, 3),
            r2=round(r2, 4),
            model_type="ridge_ar",
            sequence_length=self._seq_len,
            patch_length=self._patch_len,
            num_patches=self._num_patches,
            epochs_trained=0,
        )


def _build_patch_tst_model(
    num_patches: int,
    patch_len: int,
    d_model: int,
    n_heads: int,
    n_layers: int,
    d_ff: int,
    dropout: float,
    horizon: int,
) -> "torch.nn.Module":
    """建構 PatchTST 模型。"""
    import torch
    import torch.nn as nn

    class _PatchEmbedding(nn.Module):
        """將 patches 線性投影至 d_model 維度並加入位置編碼。"""

        def __init__(self, patch_len: int, d_model: int, num_patches: int, dropout: float):
            super().__init__()
            self.proj = nn.Linear(patch_len, d_model)
            self.pos_embed = nn.Parameter(torch.randn(1, num_patches, d_model) * 0.02)
            self.dropout = nn.Dropout(dropout)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            # x: (batch, num_patches, patch_len)
            x = self.proj(x)  # (batch, num_patches, d_model)
            x = x + self.pos_embed
            return self.dropout(x)

    class _PatchTSTModel(nn.Module):
        """簡化版 PatchTST 模型。

        Architecture:
            Input patches → Linear projection + Positional encoding
            → Transformer Encoder (N layers)
            → Flatten → Linear → Forecast
        """

        def __init__(
            self,
            num_patches: int,
            patch_len: int,
            d_model: int,
            n_heads: int,
            n_layers: int,
            d_ff: int,
            dropout: float,
            horizon: int,
        ):
            super().__init__()
            self.patch_embed = _PatchEmbedding(patch_len, d_model, num_patches, dropout)
            encoder_layer = nn.TransformerEncoderLayer(
                d_model=d_model,
                nhead=n_heads,
                dim_feedforward=d_ff,
                dropout=dropout,
                batch_first=True,
                activation="gelu",
            )
            self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)
            self.head = nn.Sequential(
                nn.Flatten(),
                nn.Linear(num_patches * d_model, d_model),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(d_model, horizon),
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            # x: (batch, num_patches, patch_len)
            x = self.patch_embed(x)    # (batch, num_patches, d_model)
            x = self.encoder(x)        # (batch, num_patches, d_model)
            return self.head(x)        # (batch, horizon)

    return _PatchTSTModel(
        num_patches=num_patches,
        patch_len=patch_len,
        d_model=d_model,
        n_heads=n_heads,
        n_layers=n_layers,
        d_ff=d_ff,
        dropout=dropout,
        horizon=horizon,
    )
