# WindAI Lab — 專案進度報告

> 最後更新：2026-03-26（Phase 9 — 資料泛化 + 多檔案載入 + 自動實驗 + 警報處理）

---

## 1. 整體進度概覽

| 項目 | 已完成 | 目標 | 完成率 |
|------|--------|------|--------|
| **核心代理** | 12 (core) | 12 | 100% |
| **可聘用代理** | 10 (hirable) | 10+ | 100% |
| **技能模組** | 10 | 12+ | 83% |
| **ML 模型** | 3 | 6+ | 50% |
| **REST API 端點** | 30+ | 35+ | 86% |
| **前端元件** | 21 | 25+ | 84% |
| **測試覆蓋** | 17 檔案 / 368 測試 | — | 良好 |
| **Docker 部署** | ✅ | ✅ | 100% |
| **WebSocket 即時通訊** | ✅ | ✅ | 100% |
| **RAG 知識庫** | ✅ | ✅ | 100% |
| **資料視覺化** | ✅ | ✅ | 100% |
| **檔案監控自動化** | ✅ | ✅ | 100% |
| **智慧資料載入** | ✅ | ✅ | 100% |
| **技能拆分架構** | ✅ | ✅ | 100% |
| **聘用/解聘制度** | ✅ | ✅ | 100% |
| **TurbineProfile 動態參數** | ✅ | ✅ | 100% |
| **多檔案批次載入** | ✅ | ✅ | 100% |
| **自動實驗循環** | ✅ | ✅ | 100% |
| **警報事件處理** | ✅ | ✅ | 100% |

**整體評估：約 85% 完成度**（資料泛化完成，新增 4 個技能，進入 RAG + 前端強化階段）

---

## 2. 開發歷程 (Development Chronicle)

以下按時間順序記錄每個 Phase 的開發過程、設計決策與解決的技術挑戰。

### Phase 1 — 基礎架構建置（2026-03-22）

**目標**：建立可運作的全端框架，定義 42 個代理的規格。

**開發過程**：
1. 以 FastAPI 建立後端 REST API，選用原因：async 支援佳、自動文件生成、型別安全
2. 前端採用 React 18 + TypeScript + Vite，搭配 Tailwind CSS + shadcn/ui
3. 定義 6 層代理階層 (6-Tier Hierarchy)，透過 YAML 設定檔描述 42 個代理的角色與能力
4. 實作 BaseAgent 抽象基底類別，統一生命週期管理（狀態更新、工作日誌、訊息收發）
5. MessageBus 模組實現代理間的 pub/sub 通訊
6. Docker Compose 整合 4 個服務：backend, frontend, Redis, MLflow

**關鍵設計決策**：
- 選擇 namespace convention（`wLab:`, `wData:`, `wAI:` 等）而非平面命名，確保跨系統整合不衝突
- 代理「定義」與「實作」分離：42 個代理在 UI 上全部可見，但邏輯僅在實作後才真正運作

**產出**：
- [x] FastAPI 後端框架
- [x] React + TypeScript + Vite 前端
- [x] WebSocket 即時通訊（代理狀態推播）
- [x] Docker Compose 部署設定
- [x] BaseAgent, MessageBus, Registry 核心模組
- [x] 42 個代理 YAML 設定檔

### Phase 2 — 虛擬辦公室 UI（2026-03-23）

**目標**：打造「虛擬辦公室」概念的前端介面，讓 42 個代理的狀態可視覺化互動。

**開發過程**：
1. 設計像素風格 (pixel art) 的虛擬辦公室主畫面 `OfficeWorld.tsx`
2. 實作 6 個團隊房間佈局：指揮中心、資料工程室、模型實驗室、領域知識庫、軟體工程室、研究室
3. 像素角色動畫系統 `PixelCharacter.tsx`：idle 搖擺、工作中閃爍、語音泡泡顯示
4. 語音泡泡策略優化 — 原始設計所有代理同時顯示泡泡導致視覺雜訊過重，改為限制同時顯示數量

**技術挑戰**：
- 泡泡在上方區域被裁切 → 所有房間位置下移 7%，調整 overflow 設定
- 模擬模式被 WebSocket 靜態資料覆蓋 → 設計「模擬模式優先」的狀態管理邏輯

**產出**：
- [x] OfficeWorld, OfficeFloorMap, PixelCharacter
- [x] AgentCard, AgentDetail, CommandBar
- [x] WorkLogPanel, StatusBadge
- [x] 語音泡泡策略優化

### Phase 3 — 混合架構 + 真實代理（2026-03-24）

**目標**：讓「模擬模式」與「真實後端執行」共存，UI 可無縫切換。

**開發過程**：
1. 設計混合架構：前端預設以模擬模式運行（角色隨機閒聊），偵測到後端連線時啟用真實任務分派
2. 實作 OrchestrationEngine — 指令路由引擎，根據 slash command 將任務分配至對應代理
3. 建立 16 個代理的完整 Python 邏輯（Leadership 4 + Data 2 + AI 3 + Domain 2 + Eng 3 + Research 2）
4. 撰寫 36 個代理框架測試，驗證 BaseAgent 子類別的介面合規性

**關鍵設計決策**：
- 採用「確認後執行」(Confirm Before Execute) 原則：所有修改性操作需等待確認
- 代理間通訊使用統一 JSON 格式，包含 correlation_id 以追蹤因果鏈

**產出**：
- [x] 混合架構（模擬 + 真實共存）
- [x] OrchestrationEngine 指令路由
- [x] 16 個代理邏輯實作
- [x] 36 個框架合規測試

### Phase 4 — ML 模型整合（2026-03-24 ~ 03-25）

**目標**：將三大 ML 模型接入系統，建立統一的訓練/推論 pipeline。

**開發過程**：
1. **PowerCurveNBM** (正常行為模型)：基於 KNN 回歸，學習正常運轉時的風速-功率關係，偏差超過閾值即為異常
2. **FaultClassifier**：XGBoost 多類別故障分類器，基於 SCADA 特徵預測故障類型（正常/齒輪箱/發電機/葉片/軸承）
3. **RULModel** (剩餘使用壽命)：退化趨勢分析，支援 linear/polynomial/exponential 三種退化模型
4. ML Pipeline Service 統一 API 層：`/api/ml/train`, `/api/ml/predict`, `/api/ml/status`
5. 前端 ML Dashboard 面板：顯示模型訓練結果、R²/MAE/F1 指標

**技術挑戰**：
- Kelmarsh 風場真實 SCADA 資料整合（6 台風機、2016 年資料、ZIP 格式內含多個 CSV）
- 模型訓練需在 async API 中以 `run_in_executor` 包裝，避免阻塞事件循環
- CORS 跨域問題：前端 localhost:3000 呼叫後端 localhost:8000 被瀏覽器攔截

**產出**：
- [x] 3 個 ML 模型 + ML Pipeline Service
- [x] ML Pipeline API 端點
- [x] 前端 ML Dashboard
- [x] CORS 設定

### Phase 5 — 資料視覺化 + RAG 知識庫（2026-03-25）

**目標**：強化前端資料呈現能力、建構 RAG 知識庫、新增 5 個代理。

**開發過程**：
1. SCADA 儀表板 `ScadaDashboard.tsx`：風速-功率散佈圖、90 天趨勢圖、統計量長條圖（Recharts）
2. RAG 知識庫 `RAGService`：ChromaDB 向量資料庫、文件嵌入 pipeline、語意搜尋 API
3. 新增 5 個代理：experiment-tracker, feature-engineer, etl-engineer, frontend-dev, rag-curator

**技術挑戰**：
- ChromaDB 與 SQLite 的併發問題 → 設定 single-threaded 模式
- SCADA 資料量過大 → 前端取樣限制 2000 筆 + 趨勢圖改用每日平均

**產出**：
- [x] SCADA 資料視覺化（3 種圖表）
- [x] RAG 知識庫完整 pipeline
- [x] 5 個新代理實作（16→21）

### Phase 5.5 — Bug 修復與穩定性強化（2026-03-25）

**目標**：修復 SCADA 儀表板 NaN 序列化 crash。

**問題**：前端 SCADA 面板顯示 `Out of range float values are not JSON compliant: nan`

**根因分析**：
```
pandas to_numeric(errors="coerce") → NaN 值
    ↓
float(np.nan) → Python float('nan')
    ↓
JSONResponse 序列化 → JSON 標準不支援 NaN → 前端 crash
```

**修復方案**：
- 新增 `_safe_float()` 輔助函式：`math.isfinite()` 驗證、NaN/Inf 轉 `None`（JSON null）
- 修復三處：scatter_data、trend_data、statistics

### Phase 6a — 進階分析代理（2026-03-25，當前）

**目標**：擴充 4 個進階分析代理。

**新增代理**：

| 代理 | 核心演算法/技術 | 程式碼行數 |
|------|-----------------|-----------|
| `wAI:hyperparameter-tuner` | Optuna 貝葉斯最佳化、KNN cross-validation、搜尋空間建議 | ~240 行 |
| `wAI:anomaly-detector` | Z-score、IQR、Isolation Forest、功率曲線殘差偵測 | ~250 行 |
| `wDomain:wake-analyst` | Jensen (Park) 尾流模型、RSS 疊加、多風向佈局分析 | ~230 行 |
| `wRes:report-generator` | Markdown 報告生成、健康/模型/品質報告模板 | ~220 行 |

**技術亮點**：
- 尾流模型支援 Kelmarsh 風場 6 台風機的真實佈局模擬
- 異常偵測採用 4 種獨立方法交叉驗證，降低誤報率
- 超參數調整整合 Optuna 框架，自動 pruning 無效試驗

### Phase 6b — 前端強化 + 智慧資料載入（2026-03-25）

**目標**：解決前端空間問題、新增互動房間、建立通用資料載入器。

**開發過程**：
1. **前端佈局重構**：左側研究室改為可拖拉調整寬度的 sidebar，加寬時顯示完整辦公室動畫
2. **虛擬辦公室新增房間**：遊戲間 🎮（代理可去打電動）、「私密室」改名「小房間」🚪
3. **代理頭像簡稱**：每個代理頭像下方顯示 1 個代表性漢字（總、研、專等），解決辨識問題
4. **smart_loader 智慧資料載入器**：不需要為每種資料來源寫專用 loader
   - 自動偵測檔案格式（CSV/Parquet/Excel/ZIP）
   - 模糊匹配欄位名稱（60+ 關鍵字覆蓋主流格式）
   - 支援 `H05|WindSpeed(m/s)` 等帶前綴/單位的欄位名（正規化匹配）
   - 自動跳過 comment 行（Greenbyte `# Date and time` 格式）
   - 嘗試多種時間格式解析

**技術亮點**：
- `_normalize()` 函式：去除設備前綴 `H05|`、括號單位 `(kW)`，統一為 `snake_case` 再匹配
- 測試：Kelmarsh（Greenbyte 格式）、ENGIE（`Va_avg`）、自有風場（`H05|` 前綴）全部自動辨識

**產出**：
- [x] smart_loader.py — 通用資料載入器
- [x] `/api/scada/discover` — 自動掃描資料來源
- [x] 遊戲間 + 小房間 + 代理簡稱
- [x] 可拖拉寬度 sidebar

### Phase 6c — 檔案監控自動任務系統（2026-03-25）

**目標**：丟檔案進 data/raw/ 就自動觸發代理工作流程。

**開發過程**：
1. **FileWatcherService**：asyncio 定期輪詢（30 秒），偵測新檔案或修改的檔案
2. **自動處理流程**：偵測 → smart_load → detect_columns → 特徵分析 → WebSocket 廣播
3. **與 orchestration engine 串接**：偵測到新檔案後自動派任代理工作流程
4. **前端 FileWatcherStatus 元件**：監控狀態、開關按鈕、強制掃描、歷史記錄

**安全機制**：
- 檔案 `路徑+大小` 為唯一鍵，不重複處理
- 最後修改時間超過 5 秒才處理（避免讀到半寫檔案）
- 啟動時記錄現有檔案，只對之後新增的觸發

**產出**：
- [x] FileWatcherService（自動監控 + 處理）
- [x] 5 個 API 端點（start/stop/status/scan/history）
- [x] WebSocket 廣播 file_detected/processed/error
- [x] 前端 FileWatcherStatus 元件（監控開關 + 歷史記錄）
- [x] 自動派任代理工作流程

### Phase 7 — 架構重構：技能拆分 + 聘用制 + YAML 驅動（2026-03-25）

**目標**：從 42 人固定團隊改為「12 核心 + 按需聘用」的模組化架構。

**問題分析**：
- 42 個代理中只有 ~12 個有真正核心邏輯
- 技能邏輯綁死在代理 class 內（如 `FaultDiagnostician._run_diagnosis` 直接 import 所有 ML 模組）
- 同一段資料載入/清洗邏輯重複出現在 6+ 個代理中
- 新增代理需改 3 個檔案（Python class + registry + mockData）

**架構重構內容**：

1. **技能模組拆分** (`src/skills/`)：
   - BaseSkill 抽象介面（統一 SkillInput/SkillOutput）
   - 6 個獨立技能：scada_ingestion, scada_cleaning, fault_classification, nbm_training, rul_prediction, domain_feature_extraction
   - SkillRegistry 自動發現（掃描 `src/skills/` 子目錄）

2. **YAML 驅動代理定義** (`configs/agents/registry/`)：
   - 一個代理一個 YAML 檔，可直接編輯
   - 定義 skills 列表、task_routing（關鍵字 → 技能管線）
   - `core: true/false` 控制啟動時是否自動載入

3. **DynamicAgentRegistry** (`src/agents/dynamic_registry.py`)：
   - 統一管理代理「定義」「狀態」「實例」
   - `hire(agent_id)` / `fire(agent_id)` / `upgrade_skills()`
   - 向下相容舊版 API（`get_agent()`, `update_agent_status()`）

4. **SkillComposingAgent** (`src/agents/skill_composing_agent.py`)：
   - 通用代理 class，根據 YAML 的 task_routing 自動組合技能
   - 大多數代理不再需要獨立的 Python class

5. **前端人事管理面板** (`AgentManagement.tsx`)：
   - 「👥 人事管理」Tab
   - 可聘用人員清單 + 聘用按鈕
   - 技能模組清單

**關鍵設計決策**：
| 決策 | 原因 |
|------|------|
| 技能獨立於代理 | 避免邏輯重複，一個技能可被多個代理共用 |
| YAML 定義而非硬編碼 | 新增代理只需 1 個 YAML 檔，不改程式碼 |
| 12 核心 + 按需聘用 | 減少啟動負擔，聚焦真正有用的代理 |
| 新舊系統並行 | 漸進式遷移，不一次性破壞現有功能 |

**產出**：
- [x] `src/skills/` — 6 個技能模組 + BaseSkill + SkillRegistry
- [x] `configs/agents/registry/` — 22 個 YAML 代理定義
- [x] DynamicAgentRegistry — hire/fire/upgrade
- [x] SkillComposingAgent — 通用技能組合代理
- [x] 5 個新 API（hire/fire/available/skills/update-skills）
- [x] 前端 AgentManagement 人事管理面板

### Phase 8 — 技能管線實戰驗證 + 系統切換（2026-03-26）

**目標**：讓新架構真正取代舊系統，技能管線能端到端執行真實 ML 分析。

**開發過程**：
1. **切換主資料來源**：`agent_registry.py` 的 `get_all_agents()` / `get_agent()` 委託給 `DynamicAgentRegistry`
2. **移除舊系統**：lifespan 不再呼叫 `bootstrap_agents()`（42 個硬編碼）
3. **mockData 精簡**：687 行 → ~200 行，只保留 12 核心代理
4. **修復技能 API 映射**：
   - `FaultClassifier.train()` 而非 `train_and_evaluate()`
   - `PowerCurveNBM.train()` → 回傳 `NBMResult` dataclass
   - `RULModel`: 先 `compute_health_index()` 再 `.fit()`
   - `fault_classifier` 路徑修正: `src.models.classification.fault_classifier`
5. **修復 DataFrame 傳遞**：`SkillInput` 加入 `dataframe` 欄位，避免 dict 覆蓋 DataFrame
6. **新增 WebSocket 指令**：`diagnose-real`、`train-nbm`、`predict-rul` 直接走技能管線
7. **驗證結果**（真實 Kelmarsh 52,416 筆 SCADA 資料）：
   - `fault-diagnostician`: ingestion → cleaning → features → classification → **F1=1.0000** ✅
   - `power-curve-expert`: ingestion → cleaning → features → NBM → **R²=0.9964, MAE=15.3** ✅
   - `predictive-modeler`: ingestion → cleaning → features → RUL → 退化趨勢分析 ✅

**已知問題（Phase 9 已修復）**：
- ~~所有 ML 模型硬編碼 Senvion MM92 參數~~ → Phase 9 引入 TurbineProfile
- ~~滾動視窗固定 144 筆~~ → Phase 8 已改為自適應
- ~~不支援警報事件清單~~ → Phase 9 新增 AlarmProcessorSkill

**產出**：
- [x] 舊→新系統切換完成
- [x] 3 條技能管線端到端驗證通過
- [x] `docs/architecture-design.md` 完整架構設計文件
- [x] `docs/TODO-roadmap.md` + `docs/progress-report.md` 更新

### Phase 9 — 資料泛化 + 多檔案載入 + 自動實驗 + 警報處理（2026-03-26）

**目標**：解除風場硬編碼、支援多檔案批次載入、自動化 ML 實驗、處理警報事件清單。

**開發過程**：

1. **解除 Kelmarsh 硬編碼**（27 檔案，+1530 / -168 行）：
   - 新增 `TurbineProfile` dataclass 於 `constants.py`，統一風機參數傳遞
   - 重構 `wind_features.py`、`anomaly_analysis.py`、`fault_classifier.py`、`power_curve_nbm.py`
   - 消除 `detect_power_curve_anomalies()` 中硬寫的 `12.5` m/s 額定風速
   - 移除 `real_workflows.py` 的 `TURBINE_MAP` 與 Kelmarsh 風場描述
   - 所有代理與 API 的預設 turbine_id 從 `"Kelmarsh_1"` 改為 `"WT-01"`

2. **多檔案智慧載入**（2 個新技能）：
   - `DataInspectorSkill`（資料檢視員）：掃描資料夾 + 讀取分析需求（指令或文件）→ 推薦載入策略
   - `BatchLoadSkill`（批次載入器）：依策略執行 direct_concat / aggregate_then_merge / per_file_processing
   - 設計理念：需求驅動資料處理，先評估再決定策略，策略跟下游分析目的有關

3. **自動實驗技能**：
   - `AutoExperimentSkill`：自動規劃網格搜尋 → 逐輪訓練+評估 → 記錄到 JSONL → 排行榜
   - 支援 `power_curve_nbm`、`fault_classifier`、`model_comparison` 三種模式
   - 與 ExperimentTracker 的 JSONL 格式相容

4. **警報事件清單處理**：
   - `AlarmProcessorSkill`：將離散警報事件轉為時間序列特徵
   - 自動偵測欄位格式（時間戳、警報碼、嚴重度、元件、持續時間）
   - 產出：每期間警報次數/持續時間、嚴重度統計、MTBF、one-hot 編碼
   - 輸出可直接與 SCADA 資料合併

**端到端整合驗證**（合成 3000 筆資料）：
```
合成 SCADA → TurbineProfiler（2071 kW, 5.5 m/s）
  → 特徵工程（8 → 21 欄位）
  → DataInspector（3 檔案, 策略: aggregate_then_merge）
  → BatchLoad（3/3 合併成功）
  → AutoExperiment（4 輪, 最佳 R²=0.9978）
  → 排行榜 + JSONL 記錄 ✅
```

**產出**：
- [x] `TurbineProfile` dataclass + `from_profiler_dict()` 工廠方法
- [x] `DataInspectorSkill` + `BatchLoadSkill`（多檔案載入）
- [x] `AutoExperimentSkill`（自動實驗循環）
- [x] `AlarmProcessorSkill`（警報事件處理）
- [x] 新增 62 個測試，全套 368 passed
- [x] PR #17 合併

**下一步規劃**：
- RAG 知識庫（BGE-3 本地嵌入模型 + ChromaDB，串接風機手冊）
- 戰情中心介面（MissionView — 任務進行時自動切換，右側即時圖表面板）
- 主題系統（Theme Pack — 頭像/圖標/配色/底圖獨立可替換）

---

## 3. 代理架構（新制）

### 核心代理（12 個，啟動時自動載入）

| # | ID | 顯示名稱 | 技能 |
|---|-----|---------|------|
| 1 | scada-processor | SCADA 資料工程師 | scada_ingestion, scada_cleaning |
| 2 | quality-checker | 品質檢查師 | scada_cleaning |
| 3 | fault-diagnostician | 故障診斷師 | fault_classification, nbm_training |
| 4 | predictive-modeler | 預測模型師 | rul_prediction |
| 5 | anomaly-detector | 異常偵測師 | scada_ingestion, scada_cleaning |
| 6 | feature-engineer | 特徵工程師 | domain_feature_extraction |
| 7 | power-curve-expert | 功率曲線專家 | nbm_training |
| 8 | project-director | 專案總監 | （自訂 class） |
| 9 | project-manager | 專案經理 | （自訂 class） |
| 10 | rag-architect | RAG 架構師 | — |
| 11 | maintenance-planner | 維護規劃師 | rul_prediction |
| 12 | paper-writer | 論文撰寫員 | — |

### 可聘用代理（10 個，透過 API 動態啟用）

| ID | 顯示名稱 | 部門 |
|-----|---------|------|
| etl-engineer | ETL 工程師 | 資料 |
| experiment-tracker | 實驗追蹤師 | 模型 |
| hyperparameter-tuner | 超參數調整師 | 模型 |
| wake-analyst | 尾流分析師 | 領域 |
| literature-reviewer | 文獻審閱員 | 研究 |
| research-lead | 研究主管 | 指揮 |
| tech-lead | 技術主管 | 指揮 |
| backend-dev | 後端開發師 | 工程 |
| frontend-dev | 前端開發師 | 工程 |
| report-generator | 報告產生器 | 研究 |

### 已實作代理清單（舊制 25/42，已由新制取代）

### Tier 1 — Leadership（4/4 ✅）
| 代理 | 狀態 | 說明 |
|------|------|------|
| `wLab:director` | ✅ 已實作 | 專案統籌、任務分派 |
| `wLab:project-manager` | ✅ 已實作 | 團隊排程、資源分配 |
| `wLab:tech-lead` | ✅ 已實作 | 技術審查、架構監督 |
| `wLab:research-lead` | ✅ 已實作 | 研究方向、論文審查 |

### Tier 2 — Data Engineering（3/8）
| 代理 | 狀態 | 說明 |
|------|------|------|
| `wData:scada-processor` | ✅ 已實作 | SCADA 資料載入與解析 |
| `wData:quality-checker` | ✅ 已實作 | 資料驗證與品質標記 |
| `wData:etl-engineer` | ✅ 已實作 | ETL pipeline 設計與執行 |
| `wData:data-validator` | ❌ 未實作 | 資料格式驗證 |
| `wData:stream-processor` | ❌ 未實作 | 即時串流處理 |
| `wData:storage-manager` | ❌ 未實作 | 儲存策略管理 |
| `wData:metadata-curator` | ❌ 未實作 | 後設資料管理 |
| `wData:pipeline-monitor` | ❌ 未實作 | Pipeline 監控 |

### Tier 3 — AI/ML（7/10）
| 代理 | 狀態 | 說明 |
|------|------|------|
| `wAI:fault-diagnostician` | ✅ 已實作 | 故障分類（FaultClassifier） |
| `wAI:predictive-modeler` | ✅ 已實作 | RUL 退化模型 |
| `wAI:rag-architect` | ✅ 已實作 | RAG 系統設計 |
| `wAI:experiment-tracker` | ✅ 已實作 | 實驗追蹤 (MLflow + JSON) |
| `wAI:feature-engineer` | ✅ 已實作 | 自動特徵工程 + 選擇 |
| `wAI:hyperparameter-tuner` | ✅ 已實作 | Optuna 超參數搜尋 + 搜尋空間建議 |
| `wAI:anomaly-detector` | ✅ 已實作 | 多策略異常偵測 (Z-score, IQR, IF, 殘差) |
| `wAI:model-trainer` | ❌ 未實作 | 模型訓練管理 |
| `wAI:model-evaluator` | ❌ 未實作 | 模型評估 |
| `wAI:inference-deployer` | ❌ 未實作 | 推論部署 |

### Tier 4 — Domain Knowledge（3/6）
| 代理 | 狀態 | 說明 |
|------|------|------|
| `wDomain:power-curve-expert` | ✅ 已實作 | 功率曲線 NBM |
| `wDomain:maintenance-planner` | ✅ 已實作 | 預測性維護 |
| `wDomain:wake-analyst` | ✅ 已實作 | Jensen 尾流模型模擬 + 佈局分析 |
| `wDomain:wind-resource-analyst` | ❌ 未實作 | 風資源評估 |
| `wDomain:iec-specialist` | ❌ 未實作 | IEC 標準合規 |
| `wDomain:regulatory-advisor` | ❌ 未實作 | 法規諮詢 |

### Tier 5 — Software Engineering（4/8）
| 代理 | 狀態 | 說明 |
|------|------|------|
| `wEng:backend-dev` | ✅ 已實作 | API 開發 |
| `wEng:test-engineer` | ✅ 已實作 | 測試策略 |
| `wEng:devops-engineer` | ✅ 已實作 | CI/CD 與基礎設施 |
| `wEng:frontend-dev` | ✅ 已實作 | 前端元件開發 |
| `wEng:api-designer` | ❌ 未實作 | API 設計 |
| `wEng:database-admin` | ❌ 未實作 | 資料庫管理 |
| `wEng:security-analyst` | ❌ 未實作 | 安全分析 |
| `wEng:infra-manager` | ❌ 未實作 | 基礎設施管理 |

### Tier 6 — Research & Docs（4/6）
| 代理 | 狀態 | 說明 |
|------|------|------|
| `wRes:paper-writer` | ✅ 已實作 | 論文撰寫 |
| `wRes:literature-reviewer` | ✅ 已實作 | 文獻綜述 |
| `wRes:rag-curator` | ✅ 已實作 | RAG 知識庫管理 |
| `wRes:report-generator` | ✅ 已實作 | 自動化報告生成（健康、模型、品質報告） |
| `wRes:teaching-assistant` | ❌ 未實作 | 教學輔助 |
| `wRes:data-storyteller` | ❌ 未實作 | 資料敘事 |

---

## 4. Git 提交歷程

| PR | 內容 | 日期 |
|----|------|------|
| #17 | Phase 6a：4 個進階代理 + NaN Bug 修復 + 使用場景文件 | 2026-03-25 |
| #16 | 修復 SCADA NaN JSON 序列化 Bug + 進度報告更新 | 2026-03-25 |
| #15 | CORS 新增 localhost:3000 允許前端跨域存取 | 2026-03-25 |
| #14 | ML Pipeline API 端點 + 前端 ML Dashboard | 2026-03-25 |
| #13 | 重新設計氣泡顯示策略，減少視覺雜訊 | 2026-03-24 |
| #12 | 接入真實 ML Pipeline（NBM、故障分類器、RUL） | 2026-03-24 |
| #11 | ruff lint 與 black 格式化修正 | 2026-03-24 |
| #10 | 模擬模式與真實後端共存的混合架構 | 2026-03-24 |
| #9 | 修正指令路由與泡泡裁切問題 | 2026-03-23 |
| #8 | 修正模擬模式被 WebSocket 覆蓋 | 2026-03-23 |
| #7 | 虛擬辦公室 UI 基礎建構 | 2026-03-23 |

---

## 5. 技術指標

| 指標 | 數值 |
|------|------|
| Python 原始碼檔案 | 90+ |
| 前端元件 (TSX/TS) | 23 |
| 測試檔案 / 測試數 | 17 / 368 |
| 技能模組 | 10 (scada_ingestion, scada_cleaning, turbine_profiler, domain_feature_extraction, fault_classification, nbm_training, rul_prediction, data_inspector, batch_load, auto_experiment, alarm_processor) |
| YAML 代理定義 | 22 (12 core + 10 hirable) |
| ML 模型 | 3 (NBM, FaultClassifier, RUL) |
| REST API 端點 | 30+ |
| Docker 服務 | 4 (backend, frontend, Redis, MLflow) |
| 型別覆蓋率 | 100% (type hints) |
| Linter | ruff (strict) |
| Formatter | black (99 chars) |
| 預估總程式碼行數 | ~18,000+ 行 |

---

## 6. 架構決策紀錄 (ADR 摘要)

| 編號 | 決策 | 原因 |
|------|------|------|
| ADR-01 | 6 層代理階層 | 對齊真實研究團隊組織架構，便於指派與管理 |
| ADR-02 | Namespace convention (`wLab:`, `wData:` ...) | 與 iWrite/PLC 代理系統共存不衝突 |
| ADR-03 | 模擬/真實混合架構 | 前端可獨立展示，後端連線後自動升級為真實執行 |
| ADR-04 | BaseAgent 抽象基底 | 統一生命週期管理，減少重複程式碼 |
| ADR-05 | `_safe_float()` NaN 防護 | pandas 資料流中 NaN 不可避免，需在 API 層統一處理 |
| ADR-06 | Jensen (Park) 尾流模型 | 業界標準、計算效率高、適合初期驗證 |
| ADR-07 | Optuna 超參數搜尋 | 貝葉斯最佳化優於 Grid/Random Search，pruning 節省運算 |
| ADR-08 | ChromaDB 向量資料庫 | 輕量內嵌式、Python 原生支援、適合研究環境 |
| ADR-09 | smart_loader 通用載入器 | 不為每種資料來源寫專用 loader，模糊匹配欄位名自動辨識 |
| ADR-10 | FileWatcher asyncio 輪詢 | 不用 watchdog/watchfiles 第三方套件，簡單可靠 |
| ADR-11 | 技能拆分（Skill modules） | 技能獨立於代理，一個技能可被多個代理共用，避免邏輯重複 |
| ADR-12 | YAML 驅動代理定義 | 新增代理只需 1 個 YAML 檔，不改程式碼 |
| ADR-13 | 12 核心 + 按需聘用 | 42→12 核心精簡，其餘按需聘用，減少啟動負擔 |
| ADR-14 | SkillComposingAgent 通用代理 | 大多數代理不需獨立 class，由 YAML task_routing 驅動 |
| ADR-15 | 新舊系統並行 | 漸進式遷移，不一次性破壞現有功能 |
| ADR-16 | TurbineProfile dataclass | 統一風機參數傳遞，消除各模組各自硬編碼 |
| ADR-17 | DataInspector + BatchLoad 分離 | 先檢視再載入，策略由分析目的驅動 |
| ADR-18 | AutoExperiment 網格搜尋 | 自動化實驗循環，JSONL 記錄與 ExperimentTracker 相容 |
| ADR-19 | AlarmProcessor 事件→時間序列 | 離散警報轉為固定頻率 DataFrame，可與 SCADA 合併 |
