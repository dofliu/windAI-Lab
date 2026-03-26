# WindAI Lab — 使用場景與應用範例

> 本文件說明 WindAI Lab 系統適用的場合、目標使用者，以及各功能模組的具體應用範例。

---

## 1. 系統定位

WindAI Lab 是一個**風力發電領域的 AI 研究協作平台**，採用「技能拆分 + 聘用制」架構，讓研究人員、工程師與學生可以：

- 丟入**任意格式**的風場資料，系統自動偵測、清洗、分析
- **12 位核心 AI 代理**各司其職，需要時可**聘用額外 10+ 位專才**
- 獨立的**技能模組**可自由組合，形成資料分析管線
- 透過虛擬辦公室**即時視覺化**監控代理工作狀態

**一句話描述**：一間可擴充的 AI 研究室——12 位核心研究員 + 隨時可聘的專家，把 CSV 丟進去就自動分析。

---

## 2. 目標使用者

| 使用者角色 | 典型需求 | 適用模組 |
|-----------|---------|---------|
| **風電研究員** | SCADA 資料分析、功率曲線建模、尾流效應研究 | AI/ML + Domain Knowledge |
| **運維工程師** | 故障診斷、預測性維護排程、異常偵測 | AI/ML + Domain + Reports |
| **資料科學家** | 特徵工程、超參數調整、模型實驗追蹤 | AI/ML + Data Engineering |
| **碩博士研究生** | 文獻回顧、論文撰寫、實驗結果整理 | Research & Docs + RAG |
| **風場管理者** | 風場效率分析、健康狀態總覽、營運報告 | Domain + Reports + Dashboard |
| **軟體開發者** | API 整合、系統擴展、新代理開發 | Engineering + API |

---

## 3. 核心使用場景

### 場景 A：風機健康監測與預測性維護

**適用對象**：運維工程師、風場管理者

**情境描述**：
某風場運維團隊需要持續監控 6 台風機的健康狀態，提前偵測潛在故障以安排維護排程，避免非計畫性停機造成的發電量損失。

**使用流程**：

```
步驟 1：載入 SCADA 資料
使用者 → /data:load turbine=Kelmarsh_1
系統 → wData:scada-processor 載入 CSV/Parquet 資料
系統 → wData:quality-checker 自動檢查資料品質

步驟 2：訓練正常行為模型
使用者 → /ai:train model=power_curve_nbm
系統 → wAI:feature-engineer 提取特徵
系統 → wDomain:power-curve-expert 訓練 NBM 模型
結果 → R² = 0.996，MAE = 15.3 kW

步驟 3：異常偵測
使用者 → /ai:detect anomalies turbine=Kelmarsh_3
系統 → wAI:anomaly-detector 執行 4 種偵測方法
結果 → 發現 127 個異常點（2.3%），功率曲線殘差分析顯示近期偏移

步驟 4：故障分類
使用者 → /ai:predict fault turbine=Kelmarsh_3
系統 → wAI:fault-diagnostician 推論故障類型
結果 → 齒輪箱異常機率 73%，建議排程檢查

步驟 5：生成維護報告
使用者 → /res:report health turbine=Kelmarsh_3
系統 → wRes:report-generator 整合分析結果
結果 → 自動生成 Markdown 格式健康報告
```

**實際產出**：
- 功率曲線異常評分
- 故障類型與嚴重度分級
- 維護排程建議
- Markdown 格式報告

---

### 場景 B：功率曲線分析與效能評估

**適用對象**：風電研究員、風場管理者

**情境描述**：
研究員需要分析風場各風機的功率曲線是否符合理論預期，找出效能退化的風機。

**使用流程**：

```
步驟 1：視覺化 SCADA 資料
使用者 → 開啟前端 SCADA Dashboard
系統 → 顯示風速-功率散佈圖、趨勢圖、統計量

步驟 2：功率曲線建模
使用者 → /ai:train model=power_curve_nbm turbine=all
系統 → 依序訓練 6 台風機的 NBM 模型
結果 → 各風機 R²、MAE 比較表

步驟 3：殘差分析
使用者 → /domain:analyze power_curve residuals
系統 → wDomain:power-curve-expert 分析實際 vs 預測偏差
結果 → Kelmarsh_4 功率偏低 8%，建議檢查葉片結冰或汙損

步驟 4：RUL 退化追蹤
使用者 → /ai:predict rul turbine=Kelmarsh_4
系統 → wAI:predictive-modeler 追蹤效能退化趨勢
結果 → 線性退化模型顯示預計 6 個月後需大修
```

---

### 場景 C：風場尾流效應模擬

**適用對象**：風電研究員、風場設計師

**情境描述**：
風場設計團隊需要評估現有佈局在不同風向條件下的尾流損失，找出效率最差的風向區間。

**使用流程**：

```
步驟 1：單一風向模擬
使用者 → /domain:simulate wake wind_speed=10 wind_direction=270
系統 → wDomain:wake-analyst 執行 Jensen 模型
結果 → 風場效率 92.3%，Kelmarsh_5 受 Kelmarsh_2 尾流影響最大

步驟 2：全風向佈局分析
使用者 → /domain:analyze layout
系統 → wDomain:wake-analyst 模擬 0°-360° 每 30° 一次
結果 →
  - 平均效率：94.7%
  - 最差風向：210°（88.1%，南偏西風使 3 台風機串聯受影響）
  - 最佳風向：330°（99.2%，橫向排列幾乎無遮蔽）

步驟 3：最佳化建議
系統 → 建議調整 Kelmarsh_5 的偏航角以減少尾流影響
```

**輸出範例**：
```json
{
  "model": "Jensen (Park)",
  "farm_efficiency_pct": 92.3,
  "total_wake_loss_pct": 7.7,
  "effective_wind_speeds": {
    "Kelmarsh_1": 10.0,
    "Kelmarsh_2": 9.85,
    "Kelmarsh_5": 8.72
  }
}
```

---

### 場景 D：ML 實驗管理與超參數調整

**適用對象**：資料科學家、碩博士研究生

**情境描述**：
研究生正在進行故障分類模型的改良實驗，需要系統化管理多組實驗的超參數與結果。

**使用流程**：

```
步驟 1：搜尋空間建議
使用者 → /ai:suggest hyperparameters model=fault_classifier
系統 → wAI:hyperparameter-tuner 提供搜尋空間建議
結果 → n_estimators: [50,500], max_depth: [3,12], learning_rate: [0.01,0.3]

步驟 2：自動超參數搜尋
使用者 → /ai:tune model=power_curve_nbm n_trials=50
系統 → wAI:hyperparameter-tuner 執行 Optuna 貝葉斯最佳化
系統 → wAI:experiment-tracker 自動記錄每次試驗結果
結果 → 最佳 R²=0.9971，n_neighbors=23, weights=distance, p=1

步驟 3：特徵工程
使用者 → /ai:features extract turbine=Kelmarsh_1
系統 → wAI:feature-engineer 自動提取領域特徵
結果 → 12 個新特徵（功率曲線、溫度、運轉特徵）

步驟 4：特徵選擇
使用者 → /ai:features select correlation_threshold=0.9
系統 → 移除低方差 + 高相關性特徵
結果 → 25 → 18 個特徵保留
```

---

### 場景 E：研究文獻管理與論文撰寫

**適用對象**：碩博士研究生、研究員

**情境描述**：
碩士生正在準備風力發電預測性維護領域的碩士論文，需要快速回顧相關文獻並撰寫文獻回顧章節。

**使用流程**：

```
步驟 1：文獻匯入 RAG 知識庫
使用者 → /res:ingest paper=reference_papers/
系統 → wRes:rag-curator 將論文切片、嵌入向量資料庫
結果 → 已嵌入 45 篇論文、1,200 個文字片段

步驟 2：語意搜尋
使用者 → /res:search "SCADA-based fault detection deep learning"
系統 → ChromaDB 語意搜尋 + 相關度排序
結果 → 找到 5 篇高度相關論文片段

步驟 3：文獻綜述草稿
使用者 → /res:review topic="predictive maintenance wind turbine"
系統 → wRes:literature-reviewer 彙整相關文獻
結果 → 輸出結構化文獻分類（方法論、資料集、評估指標）

步驟 4：論文段落撰寫
使用者 → /res:write section=methodology
系統 → wRes:paper-writer 根據知識庫內容產出初稿
結果 → 繁體中文學術寫作風格的方法論章節草稿
```

---

### 場景 F：團隊教學與培訓

**適用對象**：教授、研究室學長姐、新進研究生

**情境描述**：
研究室有新進碩士生加入，教授希望透過系統讓學生熟悉風力發電資料分析的標準流程。

**使用方式**：
- 虛擬辦公室提供視覺化的代理協作流程，學生可觀察 AI 代理如何分工合作
- 每個代理的工作日誌即時顯示分析過程與決策依據
- 學生可透過 slash commands 逐步操作，系統會解釋每個步驟的意義
- 未來 `wRes:teaching-assistant` 代理將提供互動式教學

---

## 4. 適用領域延伸

WindAI Lab 的架構設計具有通用性，可延伸至以下領域：

| 延伸領域 | 替換要素 | 核心能力重用 |
|---------|---------|-------------|
| **太陽能發電** | SCADA → 逆變器資料，功率曲線 → 日照-發電模型 | 異常偵測、預測性維護、報告生成 |
| **工廠設備監控** | 風機感測器 → 工廠 IoT 感測器 | 故障分類、RUL 預測、品質監控 |
| **電力系統** | 風場 → 變電站/電網 | 尾流分析 → 負載預測，資料視覺化 |
| **水處理設施** | SCADA 協議相容 | 異常偵測、維護排程、報告自動化 |

---

## 5. 系統整合方式

### 5.1 作為獨立研究工具

```
研究生筆電
    ↓ docker compose up
WindAI Lab (localhost:3000 + localhost:8000)
    ↓
匯入 CSV/Parquet 資料 → 分析 → 報告
```

### 5.2 與既有 SCADA 系統整合

```
風場 SCADA 系統
    ↓ OPC UA / REST API
wData:stream-processor（即時串流）
    ↓
WindAI Lab 分析 pipeline
    ↓
營運儀表板 / 告警通知
```

### 5.3 嵌入既有研究工作流程

```
Jupyter Notebook
    ↓ import windailab
WindAI Lab Python SDK（API client）
    ↓
模型訓練 / 特徵工程 / 文獻搜尋
    ↓
結果匯出至 LaTeX / Markdown 論文
```

---

## 6. 快速入門範例

### 啟動系統

```bash
# 1. 克隆專案
git clone https://github.com/dofliu/windAILab.git
cd windAILab

# 2. 啟動所有服務
docker compose up -d

# 3. 開啟瀏覽器
#    前端：http://localhost:3000
#    API 文件：http://localhost:8000/docs
```

### API 快速測試

```bash
# 查看所有代理狀態
curl http://localhost:8000/api/agents

# 查看風機列表
curl http://localhost:8000/api/scada/turbines

# 取得 SCADA 資料概覽
curl http://localhost:8000/api/scada/Kelmarsh_1/overview

# 訓練 ML 模型
curl -X POST http://localhost:8000/api/ml/train \
  -H "Content-Type: application/json" \
  -d '{"model_type": "power_curve_nbm", "turbine_id": "Kelmarsh_1"}'

# 語意搜尋知識庫
curl -X POST http://localhost:8000/api/knowledge-base/search \
  -H "Content-Type: application/json" \
  -d '{"query": "wind turbine fault detection"}'
```

### 虛擬辦公室操作

在前端 CommandBar 中輸入 slash commands：

| 指令 | 功能 |
|------|------|
| `/data:load` | 載入 SCADA 資料 |
| `/ai:train` | 訓練 ML 模型 |
| `/ai:predict` | 執行推論 |
| `/res:search` | 語意搜尋文獻 |
| `/lab:status` | 查看系統狀態 |
| `/domain:simulate wake` | 尾流模擬 |

---

## 7. 常見問答 (FAQ)

**Q：WindAI Lab 需要 GPU 嗎？**
A：目前使用的模型（KNN, XGBoost, Isolation Forest）均為 CPU 友好型，不需要 GPU。未來若整合深度學習模型（LSTM, Transformer）則建議配備 GPU。

**Q：可以使用自己的風場資料嗎？**
A：可以。只需將 CSV/Parquet 檔案放入 `data/raw/` 目錄，並確保包含 `wind_speed` 和 `power` 欄位。系統會自動偵測可用欄位。

**Q：系統支援哪些語言？**
A：介面與輸出以繁體中文為主，技術術語保留英文原文。程式碼註解使用繁體中文 Google style docstring。

**Q：42 個代理都需要實作才能使用嗎？**
A：不需要。未實作的代理會在虛擬辦公室中以「待命」狀態顯示，不影響已實作代理的功能。
