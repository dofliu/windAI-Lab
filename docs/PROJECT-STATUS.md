# WindAI Lab — 專案現況總覽

> 最後更新：2026-04-04 | Phase 10 完成

---

## 一頁式摘要

**WindAI Lab** 是一個風力發電 AI 研究協作平台，採用「技能拆分 + 聘用制」多代理架構，搭配虛擬辦公室 UI，讓研究人員可以丟入任意格式的風場資料，由 AI 代理自動執行清洗、特徵工程、模型訓練與報告生成。

---

## 完成度一覽

```
已完成 ██████████████████░░ 92%

Phase:  1  2  3  4  5  5.5  6a  6b  6c  7  8  9  10    11  12
        ✅ ✅ ✅ ✅ ✅  ✅   ✅  ✅   ✅  ✅  ✅  ✅  ✅  ←→  ⬜   ⬜
```

| 模組 | 已完成 | 目標 | 完成率 |
|------|--------|------|--------|
| 核心代理 | 12 (core) | 12 | 100% |
| 可聘用代理 | 10 (hirable YAML) | 10+ | 100% |
| 技能模組 | 12 | 12+ | 100% |
| ML 模型 | 5（KNN-NBM, XGBoost, RUL, Weibull, LSTM） | 6+ | 83% |
| REST API 端點 | 30+ | 35+ | 86% |
| 前端元件 | 28 | 30+ | 93% |
| Office Renderer | 3（pixel / modern / minimal） | 3+ | 100% |
| 測試 | 17 檔案 / 368 測試 | — | 良好 |

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
| Weibull 風速分佈 | PR#23 | MLE/矩量法 + AEP 估算 |
| LSTM 時序預測 | PR#23 | PyTorch LSTM + Ridge AR 降級 |
| 統計異常偵測技能 | PR#23 | Z-score + 功率曲線偏差 + 健康分數 |
| 報告生成技能 | PR#23 | 三種 Markdown 報告模板 |

### 待完成 (⬜)

| 功能 | 優先級 | 說明 |
|------|--------|------|
| MissionView 戰情中心 | 高 | 任務進行時自動切換，只顯示參與代理 |
| AnalysisDashboard 分析面板 | 高 | 右側即時圖表 + 報告清單 |
| ViewSwitcher 自動切換 | 高 | office ↔ mission 模式自動切換 |
| SQLite/PostgreSQL 持久化 | 低 | 任務記錄 + 工作日誌 |
| 更多 Renderer 風格 | 低 | 等距 3D / 賽博龐克等 |

---

## 已驗證的分析管線

| 管線 | 資料量 | 結果 |
|------|--------|------|
| 故障診斷 (diagnose) | Kelmarsh 52,416 筆 | F1 Macro = 1.0000 |
| 功率曲線 NBM (train-nbm) | Kelmarsh 52,416 筆 | R² = 0.9964, MAE = 15.3 kW |
| RUL 退化預測 (predict-rul) | Kelmarsh 52,416 筆 | 退化趨勢分析通過 |
| 自動實驗循環 | 合成 3,000 筆 | 4 輪, 最佳 R² = 0.9978 |

---

## 技能模組清單

| 技能 ID | 顯示名稱 | 類別 |
|---------|----------|------|
| `scada_ingestion` | SCADA 資料載入 | data |
| `scada_cleaning` | SCADA 資料清洗 | data |
| `turbine_profiler` | 風機參數推斷 | data |
| `data_inspector` | 資料檢視員 | data |
| `batch_load` | 批次載入器 | data |
| `alarm_processor` | 警報事件處理 | data |
| `domain_feature_extraction` | 領域特徵工程 | features |
| `fault_classification` | 故障分類 | ml |
| `nbm_training` | NBM 功率曲線訓練 | ml |
| `rul_prediction` | RUL 退化預測 | ml |
| `anomaly_detection` | 統計異常偵測 | ml |
| `report_generator` | 報告生成 | reporting |

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
| 10 | 2026-03-26~28 | UI 抽象 | 3 Renderers、統一 Workflow、Checkpoint |

詳細開發記錄見 [progress-report.md](progress-report.md)。
