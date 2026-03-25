# WindAI Lab — 專案進度報告

> 最後更新：2026-03-25（Phase 6a 完成 — 25/42 代理）

---

## 1. 整體進度概覽

| 項目 | 已完成 | 目標 | 完成率 |
|------|--------|------|--------|
| **代理實作** | 25 | 42 | 60% |
| **ML 模型** | 3 | 6+ | 50% |
| **REST API 端點** | 22+ | 30+ | 73% |
| **前端元件** | 16 | 20+ | 80% |
| **測試覆蓋** | 13 檔案 / 3,400+ 行 | — | 良好 |
| **Docker 部署** | ✅ | ✅ | 100% |
| **WebSocket 即時通訊** | ✅ | ✅ | 100% |
| **RAG 知識庫** | ✅ | ✅ | 100% |
| **資料視覺化** | ✅ | ✅ | 100% |

**整體評估：約 60% 完成度**

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

---

## 3. 已實作代理清單（25/42）

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
| Python 原始碼檔案 | 73 |
| 前端元件 (TSX/TS) | 21 |
| 測試檔案 / 行數 | 13 / 3,400+ |
| 代理邏輯程式碼 | 3,641 行 |
| 後端核心 (API + Service + Model) | 3,545 行 |
| 前端元件 (TSX) | 2,636 行 |
| YAML 設定檔 | 6 |
| ML 模型 | 3 (NBM, FaultClassifier, RUL) |
| Docker 服務 | 4 (backend, frontend, Redis, MLflow) |
| 型別覆蓋率 | 100% (type hints) |
| Linter | ruff (strict) |
| Formatter | black (99 chars) |
| 預估總程式碼行數 | ~12,000+ 行 |

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
