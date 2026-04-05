# WindAI Lab — 專案現況總覽

> 最後更新：2026-04-05 | Phase 13 完成 + Epic C (ML 模型進化) 完成
> **核心願景：打造一間真實的風場運維 AI 服務公司**

---

## 一頁式摘要

**WindAI Lab** 是一個風力發電 AI 研究協作平台，採用「技能拆分 + 聘用制」多代理架構，搭配虛擬辦公室 UI，讓研究人員可以丟入任意格式的風場資料，由 AI 代理自動執行清洗、特徵工程、模型訓練與報告生成。

系統正從「研究平台」演進為「風場運維服務公司」，**Step 1（打地基）已完成**，Phase 11-13 全數到位。服務閉環已建立：分析 → 告警 → 工單。

---

## 完成度一覽

```
研究平台階段 ██████████████████░░ 92%（Phase 1-10）
運維服務演進 ████████░░░░░░░░░░░░ 33%（Phase 11-13 / 11-19）

Phase:  1  2  3  4  5  5.5  6a  6b  6c  7  8  9  10  │  11  12  13  │  14  15  16  17  18  19
        ✅ ✅ ✅ ✅ ✅  ✅   ✅  ✅   ✅  ✅  ✅  ✅  ✅  │  ✅   ✅   ✅  │  ⬜   ⬜   ⬜   ⬜   ⬜   ⬜
        ─────── 研究平台（已完成）──────────────────── │ Step1 完成 ✅ │ ──── Step2 → Step3 ─────────
```

| 模組 | 已完成 | 新增 (Phase 13) | 完成率 |
|------|--------|-----------------|--------|
| 核心代理 | 12 (core) | — | 100% |
| 可聘用代理 | 10 (hirable YAML) | — | 100% |
| 技能模組 | 12 | — | 100% |
| ML 模型 | 5 → **7** | **+2**（LSTM pipeline 整合 + PatchTST Transformer） | 100% |
| 技能模組 | 12 → **14** | **+2**（transformer_forecast + model_benchmark） | 100% |
| REST API 端點 | 33+ | **+12**（告警 + 工單 + Ingest） | 95% |
| 前端元件 | 29 | **+2**（AlertPanel + WorkOrderPanel） | 98% |
| Office Renderer | 3 | — | 100% |
| 測試 | 20 檔案 / 427 測試 | **+3 檔案 / +59 測試** | 良好 |
| 持久化儲存 | SQLite 3 表 | **+2 表**（alerts + work_orders） | ✅ |
| **告警系統** | — | **完整告警 CRUD + Ingest API** | ✅ 新增 |
| **工單管理** | — | **Kanban 看板 + 備註時間線** | ✅ 新增 |

---

## 最新完成 — Phase 13

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

### 下一步 — GitHub Issues 追蹤

開發方向已調整，以 GitHub Issues 追蹤（共 6 個 Epic、15 個子 Issue）：

| Epic | Issue | 優先度 | 狀態 |
|------|-------|--------|------|
| [Epic C] ML 模型進化 | #32 | High | ✅ 完成 |
| [Epic E] 告警規則引擎 | #33 | High | ⬜ |
| [Epic D] 報告與追蹤 | #34 | High | ⬜ |
| [Epic A] 案例學習系統 | #35 | Medium | ⬜ |
| [Epic B] 故障知識體系 | #36 | Medium | ⬜ |
| [Epic F] 學術論文規劃 | #37 | Ongoing | ⬜ |

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

---

## 相關文件

| 文件 | 說明 |
|------|------|
| [FUTURE-ROADMAP.md](FUTURE-ROADMAP.md) | 願景定位 + Phase 11-19 三步走路線圖 |
| [EVOLUTION-PLAN.md](EVOLUTION-PLAN.md) | 詳細執行計畫（70+ 工作項目） |
| [TODO-roadmap.md](TODO-roadmap.md) | 總覽路線圖 + 待辦清單 |
| [progress-report.md](progress-report.md) | Phase 1-10 開發歷程 |
| [architecture-design.md](architecture-design.md) | 系統架構設計 |

詳細開發記錄見 [progress-report.md](progress-report.md)。
