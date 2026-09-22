# WindAI Lab — 專案現況總覽

> 最後更新：2026-09-22（專案健檢 + 文件校準） | Phase 14 功能完成，但 **CI 紅燈待修**
> **核心願景：打造一間真實的風場運維 AI 服務公司**

---

## 一頁式摘要

**WindAI Lab** 是一個風力發電 AI 研究協作平台，採用「技能拆分 + 聘用制」多代理架構，搭配虛擬辦公室 UI，讓研究人員可以丟入任意格式 of 風場資料，由 AI 代理自動執行清洗、特徵工程、模型訓練與報告生成。

系統正從「研究平台」演進為「風場運維服務公司」，**Step 1（打地基）已完成**，Phase 11-13 全數到位。Phase 14 功能面已大功告成：整合了 WindGuard AI、通知與派工、YAML 熱重載、MQTT 雙軌對接與自動報告排程生成。

**但功能完成 ≠ 可交付**：2026-07-03 的大型功能 commit（5,315 行）直接進入 master 且未通過 CI，導致主幹自 2026-07-10 起持續紅燈至今（73 天）。下一階段的第一優先事項是恢復 CI 綠燈與修掉隨之暴露的實際缺陷，而非新增功能。

---

## 專案健康度（2026-09-22 實測）

> 以下數據皆由指令實測產出，非人工估計。

### 🔴 CI 狀態：紅燈（自 2026-07-10 起）

| Job | 結果 | 說明 |
|-----|------|------|
| Lint & Format | ❌ **failure** | `ruff check src/` 失敗 → `black --check` 被 skip |
| Tests | ⏭️ **skipped** | 因 `needs: lint`，**自 2026-04-30 起未曾在 CI 執行過** |
| Frontend Build | ✅ success | `tsc --noEmit` + `vite build` 皆通過 |

最後一次綠燈：`7069ced`（2026-04-30）。相關 run：[#303](https://github.com/dofliu/windAI-Lab/actions/runs/29087577821)

### 程式碼品質實測

| 指標 | 文件先前聲稱 | 2026-09-22 實測 | 落差 |
|------|-------------|----------------|------|
| `ruff check .` | 0 錯誤（連續 7 日綠燈） | **185 錯誤**（src/ 146、tests/ 39） | 🔴 |
| `black --check src/` | 通過 | **13 檔需重新格式化** | 🔴 |
| `pytest tests/` | 849 案例通過 | **877 案例：868 pass / 4 fail / 5 skip** | 🟡 |
| Python TODO/FIXME | 0 | 0 | ✅ |
| 前端 TODO | 1 | 1（`useWebSocket.ts`） | ✅ |

ruff 錯誤分佈：`W293` 空白行尾空格 122、`F401` 未使用 import 17、`I001` import 排序 15、`N815` 命名 6、`F841` 未使用區域變數 5、`E741` 模糊變數名 4、其餘 16。**其中 158 項可由 `ruff check --fix` 自動修復**。

### 實測資產盤點

| 項目 | 文件先前聲稱 | 實測 |
|------|-------------|------|
| REST API 端點 | 56 | **73**（main.py 62 + director.py 11）+ 1 WebSocket |
| 前端元件 | 32 | **40** 個 `.tsx` |
| 技能模組 | 28 | **29** 個 BaseSkill 實作（28 模組） |
| Agent 模組 | 25（CLAUDE.md §2） | **25** ✅ |
| DB 資料表 | 6 | **9**（新增 allocations / daily_sheets / work_records） |
| 測試檔案 | 33 | **35** |
| 後端規模 | — | 141 個 `.py` / 30,302 行 |

### 🐛 CI 紅燈底下暴露的實際缺陷

以下皆為 2026-07-03 commit `bfca6a7` 引入、被 lint 攔下但從未修復的問題：

| # | 位置 | 問題 | 影響 |
|---|------|------|------|
| 1 | `src/api/director.py:240,287` | 使用 `re.sub` / `re.match` 但**從未 `import re`**（F821） | L287 無 try/except 保護 → 工作紀錄匯入端點必定 `NameError` 崩潰 |
| 2 | `src/services/director_allocation/converter.py:288-297` | `parse_record()` 解析出 `title` / `issue` / `assignee` / `status` 後**全部丟棄**，`WorkRecord` 亦無對應欄位（4× F841） | 該 commit 的招牌功能「Markdown ↔ DB 雙向**無損**同步」實際上每次往返都掉 4 個中介資料欄位 |
| 3 | `src/services/report_scheduler.py:302` | 組好通知訊息 `message` 後未帶入 `NotificationPayload`（F841） | 報告自動生成的 Email / LINE 通知內容為空 |
| 4 | `src/api/main.py:2008 & 2197` | `GET /api/reports` 註冊兩次、函式同名 `api_list_reports`（F811） | 後者成為無效程式碼 |
| 5 | `src/api/main.py:177` | 模組層 import 置於 app 設定之後（E402） | 與 2026-07-10 熱修的 `BaseModel` NameError 同一類型風險 |

### 🧪 4 個失敗測試的根因

`tests/unit/test_alert_engine.py` 的 4 個測試斷言「預設載入 5 條規則」，但 `AlertRuleEngine()` 現在會優先讀 `configs/alerts/rules.yaml`（含 6 條，多了 `connector_offline`），僅在讀取失敗時才回退到程式內建的 5 條。

**這是測試過期，不是程式錯誤**。建議修法不是把 5 改成 6——那會讓測試繼續綁死一份維運人員本就該自由編輯的生產設定檔——而是讓測試以自備 fixture YAML 或空設定建構引擎，與 repo 設定解耦。

### 📄 文件面問題

| 問題 | 狀態 |
|------|------|
| `docs/TODO-roadmap.md` 位元組損壞（全 repo 唯一非法 UTF-8 檔案）、遺失 `## 2. 三步走演進路線` / Step 1 / Phase 11-13 章節、且重複貼上一份過期的 Step 2 區段 | ✅ 本次已修復 |
| `docs/cursor.md`（CLAUDE.md §6 每日工作流指定的段間交接介面）從未建立 | ✅ 本次已建立 |
| 三份狀態文件日期互相矛盾（STATUS.yaml 4/21、daily_report 4/27、PROJECT-STATUS 7/03） | ✅ 本次已對齊 |
| GitHub Issue 狀態與文件不符：#42 / #43 / #44 / #75 / #96 文件標 ✅ 完成，GitHub 上仍為 OPEN（共 18 個 Open Issue） | ⬜ 待人工關閉 |
| CLAUDE.md 章節編號重複（出現兩組 §5 / §6 / §7）、§10 仍寫「42 個代理」（實為 25） | ⬜ 待修 |
| daily_report「Hackathon 截止 2026-05-18，剩 21 天」已過期 4 個月 | ✅ 本次已移除 |

---

## 完成度一覽

```
研究平台階段 ██████████████████░░ 92%（Phase 1-10）
運維服務演進 ███████████████░░░░░ 75%（Phase 11-14 / 11-19）

Phase:  1  2  3  4  5  5.5  6a  6b  6c  7  8  9  10  │  11  12  13  14  │  15  16  17  18  19
        ✅ ✅ ✅ ✅ ✅  ✅   ✅  ✅   ✅  ✅  ✅  ✅  ✅  │  ✅   ✅   ✅  ✅  │  ⬜   ⬜   ⬜   ⬜   ⬜
        ─────── 研究平台（已完成）──────────────────── │ Step1-2 ✅   │ ──── Step2 → Step3 ─────────
```

| 模組 | 已完成 | 新增 (Phase 14) | 完成率 |
|------|--------|-----------------|--------|
| 核心代理 | 12 (core) | — | 100% |
| 可聘用代理 | 10 (hirable YAML) | — | 100% |
| 技能模組 | 29（實測） | **+14**（偏航分析、降載偵測、功率曲線分箱等） | 100% |
| ML 模型 | 7 | — | 100% |
| REST API 端點 | 73（實測） | **+4** 報告下載/HTML、**+5** 告警規則、**+11** 派工 API | 98% |
| 前端元件 | 40（實測） | **功率曲線散佈圖、ReportPreview Modal、ConnectorManager、ReportManagementPanel** | 98% |
| Office Renderer | 3 | — | 100% |
| 測試 | 35 檔案 / 877 案例（實測） | **+5 檔案 / +560 行**（連接器 + 通知 + 派工 + 報告排程） | 🟡 4 個失敗待修 |
| 持久化儲存 | SQLite **9 表**（實測） | **+ allocations / daily_sheets / work_records** | ✅ |
| **WindGuard AI** | — | **LLM 推理 + Agentic Calling + Fleet Scanner** | ✅ 新增 |
| **任務生命週期** | — | **Task Session 架構重構** | ✅ 新增 |

---

## 最新進展 — Phase 14（進行中）

### Phase 14a：WindGuard AI 整合 ✅

將 Kaggle WindGuard AI 專案驗證的能力整合進 windAI-Lab：

| 項目 | 說明 |
|------|------|
| WindGuard 診斷推理 | `windguard_diagnosis.py` — 統計/ML 報告送入 LLM 深層推理，產出具體故障類型、物理機制、維護建議 |
| Agentic Function Calling | LLM 自主決定呼叫哪些診斷工具（異常偵測、功率曲線、故障分類等），多輪對話式調查 |
| 風場級別掃描 | `fleet_scanner.py` — 多執行緒並行掃描多台風機，自動風險排序（Critical/High/Medium/Low）|
| FaultDiagnostician 升級 | 新增 llm_reasoning + fleet_scanning 能力，支援 WindGuard 模式 |
| 功率曲線散佈圖 | NBM 訓練後產出風速 vs 功率散佈圖（實際 vs 預測），前端雙色散佈圖渲染 |
| 報告下載 API | `GET /api/reports/{id}/download`，ReportGeneratorSkill 產出 Markdown 報告 |

### Phase 14b：前端任務生命週期重構 ✅ (#61)

解決任務紀錄、圖表、步驟在多次執行間互相污染的系統性問題：

| 問題 | 根因 | 修正 |
|------|------|------|
| 單次診斷產生 3 筆紀錄 | 前端 sim + backend 雙重執行 + isActivelyWorking debounce 失效 | Task Session 架構：後端 task_started/task_completed 事件驅動 |
| 新任務串接舊步驟 | WorkflowProgress 讀取全域 workLogs | 只傳當前任務的 logs（slice from start） |
| 圖表跨任務累積 | analysisResults 全域累積，無 task scope | task_started 自動清除，每次乾淨開始 |
| Refresh 後圖表消失 | `db.save_analysis_result()` 從未被呼叫 | broadcast_analysis_result 時同時存入 SQLite |
| 進度顯示 8700% / 小數點 | 雙重乘法 + simulation 未取整 | 統一 Math.round() |
| 工作日誌 refresh 消失 | broadcast_work_log 只廣播不儲存 | WebSocketManager 內建 log buffer |

### Phase 14c：診斷報告輸出 ✅ (#64, PR #90)

| 項目 | 說明 | 狀態 |
|------|------|------|
| P0 報告可見性 | PaperWriter context 扁平化修正，report_link 正確廣播 | ✅ |
| P1 報告內嵌預覽 | ReportPreview Modal — Markdown 渲染 + 前端即時預覽 | ✅ |
| P2 報告持久化 | reports 表寫入 SQLite，重啟後仍可查看/下載 | ✅ |
| P3 PDF 列印模式 | HTML 報告模板 + `GET /api/reports/{id}/html` + 瀏覽器列印 | ✅ |

---

## 先前已完成 — Phase 13

### Phase 13：告警系統 + 工單管理 ✅

| 項目 | 說明 |
|------|------|
| alerts 資料表 | 含嚴重程度、來源、狀態追蹤、外部系統去重 |
| work_orders 資料表 | 含優先程度、指派代理、備註時間線 |
| AlertIngestRequest | 標準化外部推送格式（source_system + source_alert_id 去重） |
| 12 個 REST API | alerts CRUD + ingest + stats / work-orders CRUD + notes + stats |
| WebSocket 即時推播 | alert_new / alert_updated / work_order_updated |
| AlertPanel 前端 | 告警列表 + 嚴重程度/狀態篩選 + 確認/解決/駁回 + 手動建立 |
| WorkOrderPanel 前端 | Kanban 看板（待處理/進行中/已完成）+ 工單詳情 + 備註 |
| DashboardView 整合 | 新增「警報」tab（含活躍告警數量 badge） |
| TaskLauncher 重構 | 精簡底部列 + 向上滑出抽屜式面板（釋放主內容空間） |

### 外部 API 接口（給廠商）

```
POST /api/alerts/ingest
{
  "source_system": "vestas_cms",
  "source_alert_id": "CMS-2024-00123",
  "turbine_id": "Kelmarsh_1",
  "severity": "warning",
  "title": "齒輪箱溫度異常",
  "description": "主軸承溫度連續 2 小時超過 85°C",
  "occurred_at": "2026-04-05T08:30:00Z",
  "metrics": { "temperature": 87.3, "threshold": 80.0, "unit": "°C" },
  "tags": ["gearbox", "temperature"]
}
```

---

## 先前已完成

### Phase 11：戰情中心升級 ✅

| 項目 | 說明 |
|------|------|
| MissionAgentPanel | 參與代理即時狀態面板（進度條、tier 標籤、最新日誌） |
| WorkflowProgress 三欄佈局 | 左：代理面板 / 中：進度+日誌 / 右：即時分析圖表 |
| ViewSwitcher | Header 任務狀態標籤 + 「返回辦公室」按鈕 |
| 即時分析顯示 | 分析結果在任務進行中即時顯示（不再等完成才看到） |

### Phase 12：持久化儲存 ✅

| 項目 | 說明 |
|------|------|
| SQLite 資料庫模組 | 3 張表（tasks / work_logs / analysis_results）+ WAL 模式 |
| 引擎整合 | Workflow 執行自動 create_task → complete_task |
| 歷史查詢 API | `GET /api/tasks/history` + `/api/tasks/{id}` + `/api/tasks/stats/summary` |
| 前端雙層儲存 | localStorage + 後端 API 合併去重（30 秒輪詢） |

---

## 核心功能狀態

### 已完成 (✅)

| 功能 | Phase | 說明 |
|------|-------|------|
| FastAPI + React 全端架構 | 1 | REST API + WebSocket 即時推播 |
| 虛擬辦公室 UI | 2 | 像素風格、代理動畫、語音泡泡 |
| 混合模式（模擬 + 真實） | 3 | 前端自動偵測後端連線狀態 |
| ML 模型整合 | 4 | PowerCurveNBM, FaultClassifier, RULModel |
| SCADA 資料視覺化 | 5 | 散佈圖、趨勢圖、統計量 |
| RAG 知識庫 | 5+PR#23 | BGE-3 嵌入 + ChromaDB + MMR 檢索 |
| 進階分析代理 | 6a | 超參數調整、異常偵測、尾流模擬、報告生成 |
| 通用資料載入 (smart_loader) | 6b | 自動偵測格式、模糊匹配 60+ 欄位關鍵字 |
| 檔案監控自動任務 | 6c | FileWatcher → 自動觸發分析管線 |
| 技能拆分 + 聘用制 | 7 | BaseSkill + SkillRegistry + YAML 驅動 |
| 技能管線端到端驗證 | 8 | F1=1.0, R²=0.997, RUL 退化趨勢 |
| 資料泛化 + 自動實驗 | 9 | TurbineProfile 動態參數、BatchLoad、AutoExperiment |
| UI 抽象層 + Renderer | 10 | 3 種可插拔辦公室風格 |
| Workflow 統一架構 | 10 | 所有指令走 AVAILABLE_WORKFLOWS 單一路徑 |
| 總監 Checkpoint 機制 | 10 | 品質規則 + 自動調參重跑 |
| 錯誤重試/降級 | 10 | RetryConfig + SKIP/FALLBACK/ABORT 三策略 |
| **戰情中心三欄佈局** | **11** | **代理面板 + 進度日誌 + 即時分析圖表** |
| **SQLite 持久化儲存** | **12** | **任務記錄 + 工作日誌 + 分析結果不再消失** |
| **歷史查詢 API** | **12** | **分頁查詢 + 單筆詳情 + 統計摘要** |
| **告警系統 + Ingest API** | **13** | **告警 CRUD + 外部推送標準格式 + WebSocket 即時推播** |
| **工單管理 + Kanban** | **13** | **工單 CRUD + 備註 + 告警→工單自動建立** |
| **TaskLauncher 精簡版** | **13** | **底部列精簡化 + 滑出抽屜 — 主內容空間最大化** |

### 最新完成 — Epic C：ML 模型進化 ✅

| 項目 | 說明 |
|------|------|
| LSTM skill pipeline 整合 (C1) | LSTM v2.0：R² 指標 + 模型持久化 + JSONL/MLflow 實驗記錄 |
| PatchTST Transformer (C2) | 簡化版 PatchTST (ICLR 2023)：Patch embedding + Transformer Encoder |
| 模型對比框架 (C3) | ModelBenchmark：統一 train/test 分割 + NBM vs LSTM vs PatchTST + LaTeX 表格 |

### 已驗證的 ML 模型

| 模型 | 架構 | 用途 | 指標 |
|------|------|------|------|
| PowerCurveNBM | GradientBoosting | 正常行為模型 | R²=0.9964 |
| FaultClassifier | XGBoost | 故障分類 | F1=1.0000 |
| RUL Prediction | 退化模型 | 剩餘壽命預測 | 趨勢驗證通過 |
| Weibull Analysis | 統計分佈 | 風速分佈 + AEP | 統計驗證通過 |
| LSTM Forecaster | PyTorch LSTM | 時序預測 | R², RMSE, MAE |
| PatchTST Forecaster | Transformer | 時序預測（學術前沿） | R², RMSE, MAE |
| Model Benchmark | 對比框架 | 多模型統一評估 | 自動化 LaTeX 報告 |
| **WindGuard AI** | **LLM + Agentic** | **LLM 故障推理 + 風場掃描** | **Kaggle 驗證通過** |

### 下一步 — GitHub Issues 追蹤

| Epic / Issue | 優先度 | 狀態 |
|-------------|--------|------|
| [Epic C] ML 模型進化 #32 | High | ✅ 完成 |
| 任務生命週期重構 #61 | Critical | ✅ 完成（報告部分移至 #64） |
| 專案總監 LLM 審核 #67 | High | ✅ 完成 |
| 新增風機分析技能 #68 | Medium | ✅ 完成 |
| Lint 清理 #73 + ruff 遷移 #76 | Low | ✅ 完成（錯誤 54→0） |
| **診斷報告輸出功能 #64** | **High** | **✅ 完成（PR #90）** |
| 對接外部 API #75 | High | ✅ 程式完成（GitHub Issue 仍 OPEN，待關閉） |
| 移除舊版 registry 雙軌 #69 | Medium | ⬜ 技術債 |
| **告警規則引擎核心 #41** | **High** | **✅ 完成（commit 03440d3）** |
| [Epic E] 告警規則引擎 #33 | High | ✅ 程式完成 (#41, #42, #43)（#33/#42/#43 GitHub 仍 OPEN） |
| [Epic D] 報告與追蹤 #34 | High | 🔨 進行中 (#44 程式完成待關閉, #45/#46 待啟動) |
| [Epic A] 案例學習系統 #35 | Medium | ⬜ |
| [Epic B] 故障知識體系 #36 | Medium | ⬜ |
| [Epic F] 學術論文規劃 #37 | Ongoing | ⬜ |

---

## 已驗證的分析管線

| 管線 | 資料量 | 結果 |
|------|--------|------|
| 故障診斷 (diagnose) | Kelmarsh 52,416 筆 | F1 Macro = 1.0000 |
| 功率曲線 NBM (train-nbm) | Kelmarsh 52,416 筆 | R² = 0.9964, MAE = 15.3 kW |
| RUL 退化預測 (predict-rul) | Kelmarsh 52,416 筆 | 退化趨勢分析通過 |
| 自動實驗循環 | 合成 3,000 筆 | 4 輪, 最佳 R² = 0.9978 |

---

## 開發歷程摘要

| Phase | 日期 | 主題 | 關鍵產出 |
|-------|------|------|----------|
| 1 | 2026-03-22 | 基礎架構 | FastAPI + React + Docker + 42 代理 YAML |
| 2 | 2026-03-23 | 虛擬辦公室 UI | 像素風格、6 團隊房間、代理動畫 |
| 3 | 2026-03-24 | 混合架構 | 模擬+真實共存、OrchestrationEngine |
| 4 | 2026-03-24~25 | ML 模型 | NBM + FaultClassifier + RUL |
| 5 | 2026-03-25 | 視覺化+RAG | SCADA 儀表板、ChromaDB 知識庫 |
| 6a-c | 2026-03-25 | 進階分析 | 尾流模擬、smart_loader、FileWatcher |
| 7 | 2026-03-25 | 架構重構 | 技能拆分、聘用制、YAML 驅動 |
| 8 | 2026-03-26 | 系統切換 | 舊→新架構、端到端驗證 |
| 9 | 2026-03-26 | 資料泛化 | TurbineProfile、BatchLoad、AutoExperiment |
| 10 | 2026-03-26~28 | UI 抽象+品控 | 3 Renderers、統一 Workflow、Checkpoint |
| **11** | **2026-04-04** | **戰情中心** | **MissionAgentPanel、三欄佈局、即時分析** |
| **12** | **2026-04-04** | **持久化儲存** | **SQLite 資料庫、歷史 API、前後端整合** |
| **13** | **2026-04-05** | **告警+工單** | **告警 Ingest API、AlertPanel、WorkOrderPanel Kanban、TaskLauncher 重構** |
| **Epic C** | **2026-04-05** | **ML 模型進化** | **LSTM v2.0 + PatchTST Transformer + 模型對比框架 + 59 個新測試** |
| **#67** | **2026-04-07** | **總監 LLM 審核** | **5 維度品質評分 + 跨風機比較 + 維護排程 + 2 個新工作流** |
| **#68** | **2026-04-07** | **新增風機技能** | **偏航分析、降載偵測、功率曲線分箱、季節性分解等 +14 技能** |
| **#73-79** | **2026-04-13~15** | **程式碼品質** | **Lint 錯誤 54→0、ruff 配置遷移、TYPE_CHECKING 修正** |
| **#64** | **2026-04-17** | **診斷報告輸出** | **P0 context 扁平化 + P1 報告預覽 Modal + P2 SQLite 持久化 + P3 PDF 列印** |
| **#41** | **2026-04-18** | **告警規則引擎核心** | **5 條預設規則 + 複合條件 + 靜默期 + 自動工單 + 5 個 API + 37 個測試** |
| **#42/#96** | **2026-04-27** | **通知渠道與派工服務** | **Email/Webhook/LINE Notifier + sqlite3 派工庫 + AI 派工建議 + Markdown 雙向無損同步** |
| **#43/#75/#44** | **2026-04-28** | **告警重載、連接器與報告排程** | **YAML 規則熱重載 + MQTT 雙軌連接器與離線健康告警 + HTML/PDF 報告排程生成與通知聯動** |

---

## 相關文件

| 文件 | 說明 |
|------|------|
| [FUTURE-ROADMAP.md](archived/FUTURE-ROADMAP.md) ⚠️ 已歸檔 | 願景定位 + Phase 11-19 三步走路線圖 |
| [EVOLUTION-PLAN.md](archived/EVOLUTION-PLAN.md) ⚠️ 已歸檔 | 詳細執行計畫（70+ 工作項目） |
| [TODO-roadmap.md](TODO-roadmap.md) | 總覽路線圖 + 待辦清單 |
| [progress-report.md](archived/progress-report.md) ⚠️ 已歸檔 | Phase 1-10 開發歷程 |
| [architecture-design.md](architecture-design.md) | 系統架構設計 |

詳細開發記錄見 [progress-report.md](archived/progress-report.md) ⚠️ 已歸檔。
