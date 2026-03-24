# 實驗計畫書

> WindAI Lab - ML Experiment Plan

---

## 基本資訊

| 欄位 | 內容 |
|------|------|
| **實驗名稱** | `[例：SCADA 異常偵測 - Transformer vs. LSTM 比較實驗]` |
| **實驗編號** | `EXP-YYYY-NNN` |
| **日期** | YYYY-MM-DD |
| **負責人** | `[姓名]` |
| **指導教授** | `[姓名]` |
| **預計完成日期** | YYYY-MM-DD |
| **狀態** | `[ ] 規劃中 / [ ] 進行中 / [ ] 已完成 / [ ] 已中止` |

---

## 1. 研究假說 (Research Hypothesis)

**主要假說：**
> `[明確陳述你預期的結果，例：基於 Transformer 架構的模型在風機 SCADA 資料異常偵測任務中，將優於傳統 LSTM 模型，特別是在長序列依賴的情境下。]`

**虛無假說 (H₀)：**
> `[例：Transformer 模型與 LSTM 模型在異常偵測準確率上無顯著差異。]`

**對立假說 (H₁)：**
> `[例：Transformer 模型的 F1-score 顯著高於 LSTM 模型（p < 0.05）。]`

---

## 2. 資料集描述 (Dataset Description)

| 欄位 | 內容 |
|------|------|
| **資料來源** | `[例：某風場 SCADA 系統 / 公開資料集名稱]` |
| **資料大小** | `[例：500,000 筆記錄 / 2.3 GB]` |
| **時間範圍** | `[例：2020-01-01 ~ 2023-12-31]` |
| **時間解析度** | `[例：10 分鐘]` |
| **風機型號** | `[例：Vestas V110-2.0 MW]` |
| **風機數量** | `[例：15 台]` |
| **特徵數量** | `[例：58 個 SCADA 參數]` |

**主要特徵列表：**

| 特徵名稱 | 說明 | 單位 | 資料型態 |
|----------|------|------|----------|
| `wind_speed` | 風速 | m/s | float |
| `power_output` | 發電功率 | kW | float |
| `rotor_speed` | 轉子轉速 | rpm | float |
| `[...]` | `[...]` | `[...]` | `[...]` |

**資料前處理：**
- [ ] 缺失值處理方法：`[例：線性插值 / 刪除 / KNN imputation]`
- [ ] 異常值處理方法：`[例：IQR 方法 / Z-score]`
- [ ] 正規化方法：`[例：Min-Max / Z-score normalization]`
- [ ] 資料切分比例：Train `___`% / Validation `___`% / Test `___`%
- [ ] 時間序列切分策略：`[例：chronological split / time-series cross-validation]`

---

## 3. 模型架構 (Model Architecture)

### 3.1 Baseline 模型

| 項目 | 內容 |
|------|------|
| **模型名稱** | `[例：LSTM Autoencoder]` |
| **選擇理由** | `[為何選擇此 baseline]` |
| **參考文獻** | `[論文引用]` |
| **架構摘要** | `[簡述模型架構]` |

### 3.2 Proposed 模型

| 項目 | 內容 |
|------|------|
| **模型名稱** | `[例：Wind-Transformer with Attention]` |
| **創新點** | `[與 baseline 的主要差異]` |
| **架構摘要** | `[簡述模型架構]` |

**架構圖：**
> `[插入或連結模型架構圖]`

---

## 4. 超參數設定 (Hyperparameter Configuration)

### 共同超參數

| 超參數 | 值 | 搜尋範圍 | 搜尋方法 |
|--------|-----|---------|----------|
| Learning rate | `[例：1e-4]` | `[1e-5, 1e-3]` | `[Grid / Random / Bayesian]` |
| Batch size | `[例：64]` | `[32, 64, 128]` | |
| Epochs | `[例：100]` | | |
| Optimizer | `[例：AdamW]` | | |
| Sequence length | `[例：144 (24hr)]` | `[72, 144, 288]` | |
| Early stopping patience | `[例：10]` | | |
| Weight decay | `[例：1e-5]` | | |

### 模型特定超參數

| 超參數 | Baseline | Proposed | 備註 |
|--------|----------|----------|------|
| Hidden size | `[例：128]` | `[例：256]` | |
| Number of layers | `[例：2]` | `[例：4]` | |
| Dropout rate | `[例：0.2]` | `[例：0.1]` | |
| `[...]` | | | |

---

## 5. 評估指標 (Evaluation Metrics)

### 主要指標

| 指標 | 公式/說明 | 適用任務 |
|------|----------|----------|
| **MAE** | Mean Absolute Error | 回歸 |
| **RMSE** | Root Mean Squared Error | 回歸 |
| **R²** | Coefficient of Determination | 回歸 |
| **F1-score** | 2 × (Precision × Recall) / (Precision + Recall) | 分類/偵測 |
| **Precision** | TP / (TP + FP) | 分類/偵測 |
| **Recall** | TP / (TP + FN) | 分類/偵測 |

### 次要指標

| 指標 | 說明 |
|------|------|
| **推論時間** | 單筆資料推論所需時間 (ms) |
| **模型大小** | 參數量與儲存空間 |
| **訓練時間** | 完整訓練所需時間 |
| **收斂速度** | 達到最佳結果所需 epoch 數 |

### 統計顯著性檢定

- 使用方法：`[例：paired t-test / Wilcoxon signed-rank test]`
- 重複實驗次數：`[例：5 次，不同 random seed]`
- 顯著性水準 (α)：`[例：0.05]`

---

## 6. 對照實驗設計 (Ablation Study)

| 實驗編號 | 移除/修改的元件 | 目的 | 預期影響 |
|----------|----------------|------|----------|
| Ablation-1 | `[例：移除 attention mechanism]` | `[驗證 attention 的貢獻]` | `[F1 下降]` |
| Ablation-2 | `[例：減少 encoder layers]` | `[驗證深度的影響]` | `[效能略降]` |
| Ablation-3 | `[例：替換 feature engineering]` | `[驗證特徵工程的效果]` | `[...]` |
| `[...]` | | | |

---

## 7. 預期結果 (Expected Results)

### 量化預期

| 模型 | MAE | RMSE | R² | F1 | 備註 |
|------|-----|------|-----|-----|------|
| Baseline | `[...]` | `[...]` | `[...]` | `[...]` | |
| Proposed | `[...]` | `[...]` | `[...]` | `[...]` | |
| 改善幅度 | `[...]%` | `[...]%` | `[...]` | `[...]%` | |

### 質化預期
> `[描述預期在何種情境下模型表現最好/最差，例：在高風速情境下 proposed model 應有更好的表現]`

---

## 8. 時程規劃 (Timeline)

| 階段 | 工作項目 | 開始日期 | 結束日期 | 狀態 |
|------|---------|---------|---------|------|
| 第 1 週 | 資料收集與前處理 | MM-DD | MM-DD | `[ ]` |
| 第 2 週 | Baseline 模型實作與訓練 | MM-DD | MM-DD | `[ ]` |
| 第 3 週 | Proposed 模型實作 | MM-DD | MM-DD | `[ ]` |
| 第 4 週 | 超參數調整與訓練 | MM-DD | MM-DD | `[ ]` |
| 第 5 週 | Ablation study | MM-DD | MM-DD | `[ ]` |
| 第 6 週 | 結果分析與報告撰寫 | MM-DD | MM-DD | `[ ]` |

---

## 9. 實驗環境記錄 (Environment)

```
Python version:     [例：3.10.12]
PyTorch version:    [例：2.1.0]
CUDA version:       [例：11.8]
GPU:                [例：NVIDIA A100 80GB × 1]
OS:                 [例：Ubuntu 22.04]
RAM:                [例：64 GB]
```

### 主要套件版本

| Package | Version |
|---------|---------|
| `numpy` | `[...]` |
| `pandas` | `[...]` |
| `scikit-learn` | `[...]` |
| `pytorch` / `tensorflow` | `[...]` |
| `transformers` | `[...]` |
| `wandb` / `mlflow` | `[...]` |

> 提示：可使用 `pip freeze > requirements.txt` 完整記錄環境。

---

## 附註

`[任何額外備註、參考連結、相關實驗編號等]`

---

*模板版本：v1.0 | WindAI Lab | 最後更新：2026-03-24*
