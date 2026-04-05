# WindAI Lab — 演進計畫：從研究平台到風場運維服務公司

> 建立日期：2026-04-04
> 追蹤代號：WLAB-EVOLUTION

本文件為可追蹤的執行計畫，每個 Phase 拆分為具體的工作項目（Work Item），可直接轉為開發任務。

---

## 現況基線

| 指標 | Step 1 前 | Step 1 後 ✅ | Step 2 後 | Step 3 後 |
|------|-----------|-------------|-----------|-----------|
| 資料來源 | 靜態檔案 | 靜態檔案 + **外部 API 推送** | 即時串流 + 檔案 | 即時串流 + 檔案 |
| 儲存 | 記憶體 | **SQLite 5 表** | 資料庫 | 資料庫 |
| 告警 | 無 | **告警 CRUD + Ingest API** | 即時告警 | 即時告警 + SLA |
| 工單 | 無 | **Kanban 工單 + 備註** | 工單 + 案例庫 | 工單 + 派工 + 備品 |
| 風場數 | 1（Kelmarsh） | 1+ | 多風場 | 多風場 + 多客戶 |
| 服務閉環 | 無 | **分析→告警→工單 ✅** | +案例學習 | +派工→結案→報告 |

---

## Step 1：打地基（Phase 11-13）

### Phase 11：前端戰情中心 + 分析面板

**目的**：任務執行時的 UI 體驗升級

| WI# | 工作項目 | 檔案/位置 | 驗收標準 | 狀態 |
|-----|---------|-----------|----------|------|
| 11-1 | MissionAgentPanel 代理面板 | `frontend/src/components/MissionAgentPanel.tsx` | 任務中只顯示參與代理，含即時進度、tier 標籤、最新日誌 | ✅ |
| 11-2 | WorkflowProgress 三欄佈局 | `frontend/src/components/WorkflowProgress.tsx` | 左：代理面板 / 中：進度+日誌 / 右：即時分析圖表 | ✅ |
| 11-3 | ViewSwitcher 邏輯 | `frontend/src/components/App.tsx` | header 顯示任務狀態 + 「返回辦公室」按鈕 | ✅ |
| 11-4 | 技能管線進度條 | `frontend/src/components/WorkflowProgress.tsx` | 步驟條已含 ✓/●/○ 狀態 + 代理個別進度條 | ✅ |
| 11-5 | 即時分析推播 | `src/api/main.py` (已有) | 後端已透過 WebSocket 推播 analysis_result，無需新增 API | ✅ |

**依賴**：無，可立即開始
**前置條件**：現有 WebSocket 推播機制

---

### Phase 12：持久化儲存

**目的**：讓所有分析結果、工作日誌、代理狀態不再因重啟而消失

| WI# | 工作項目 | 檔案/位置 | 驗收標準 | 狀態 |
|-----|---------|-----------|----------|------|
| 12-1 | 資料庫模組 | `src/core/database.py` | SQLite 3 張表 + 完整 CRUD + WAL 模式 | ✅ |
| 12-2 | 引擎整合 | `src/agents/orchestrator/engine.py` | workflow 自動 create_task/complete_task | ✅ |
| 12-3 | 歷史查詢 API | `src/api/main.py` | history / detail / stats 三個端點 | ✅ |
| 12-4 | 前端歷史合併 | `frontend/src/hooks/useTaskHistory.ts` | localStorage + 後端 API 雙層合併去重 | ✅ |

**技術選型**：Python 內建 sqlite3（零新依賴）

---

### Phase 13：告警系統 + 工單管理 ✅

**目的**：建立服務閉環 — 異常自動觸發告警並產生可追蹤的工單
**完成日期**：2026-04-05

| WI# | 工作項目 | 檔案/位置 | 驗收標準 | 狀態 |
|-----|---------|-----------|----------|------|
| **告警子系統** | | | | |
| 13-1 | alerts 資料表 + CRUD | `src/core/database.py` | alerts 表含 severity/status/source_system/去重索引 | ✅ |
| 13-2 | Pydantic 模型 | `src/api/models.py` | AlertIngestRequest + CreateAlertRequest + UpdateAlertRequest | ✅ |
| 13-3 | 告警 REST API | `src/api/main.py` | 6 端點：list/get/create/ingest/update/create-work-order | ✅ |
| 13-4 | WebSocket 推播 | `src/api/websocket_manager.py` | broadcast_alert（alert_new / alert_updated） | ✅ |
| 13-5 | 前端告警面板 | `frontend/src/components/AlertPanel.tsx` | 篩選 + 確認/解決/駁回 + 手動建立 + 一鍵建工單 | ✅ |
| 13-6 | 外部 Ingest API | `POST /api/alerts/ingest` | 標準化格式供外部廠商推送，source_alert_id 自動去重 | ✅ |
| **工單子系統** | | | | |
| 13-7 | work_orders 資料表 + CRUD | `src/core/database.py` | work_orders 表含 priority/status/notes/assigned_agents | ✅ |
| 13-8 | 工單 REST API | `src/api/main.py` | 6 端點：list/get/create/update/notes/stats | ✅ |
| 13-9 | WebSocket 推播 | `src/api/websocket_manager.py` | broadcast_work_order_update | ✅ |
| 13-10 | 告警→工單自動建立 | `POST /api/alerts/{id}/create-work-order` | 預填告警資訊 + 雙向關聯 | ✅ |
| 13-11 | 工單 Kanban 面板 | `frontend/src/components/WorkOrderPanel.tsx` | 待處理/進行中/已完成 三欄 + 詳情 + 備註時間線 | ✅ |
| **前端整合** | | | | |
| 13-12 | DashboardView 整合 | `frontend/src/components/DashboardView.tsx` | 新增「警報」tab + 活躍告警數量 badge | ✅ |
| 13-13 | useWebSocket 更新 | `frontend/src/hooks/useWebSocket.ts` | 處理 alert_new/alert_updated/work_order_updated | ✅ |
| 13-14 | TaskLauncher 重構 | `frontend/src/components/TaskLauncher.tsx` | 精簡底部列 + 向上滑出抽屜（釋放主內容空間） | ✅ |
| **後續增強（未來）** | | | | |
| 13-E1 | 告警規則引擎 | `src/services/alert_engine.py` | 可配置閾值規則 + 複合條件 + 靜默期 | 🔜 |
| 13-E2 | 通知渠道 | `src/services/notifiers/` | Email / Webhook / LINE Notify | 🔜 |
| 13-E3 | 告警規則 YAML 設定 | `configs/alerts/rules.yaml` | YAML 定義規則，支援熱更新 | 🔜 |

**依賴**：Phase 12（需要資料庫）✅ 已滿足
**整合點**：REST API + WebSocket 雙通道，外部廠商可透過 Ingest API 推送

---

## Step 2：接真實風場（Phase 14-16）

### Phase 14：即時資料連接器

**目的**：從「丟檔案」升級為「即時接收風場 SCADA」

| WI# | 工作項目 | 檔案/位置 | 驗收標準 | 狀態 |
|-----|---------|-----------|----------|------|
| 14-1 | DataConnector 抽象介面 | `src/data_pipeline/connectors/base.py` | 定義 connect / pull / health_check 介面 | ⬜ |
| 14-2 | FileConnector | `src/data_pipeline/connectors/file.py` | 封裝現有 smart_loader 為 Connector | ⬜ |
| 14-3 | RESTConnector | `src/data_pipeline/connectors/rest.py` | 定時拉取外部 REST API 的 SCADA 資料 | ⬜ |
| 14-4 | OPCUAConnector | `src/data_pipeline/connectors/opcua.py` | OPC UA client 接收 PLC 即時資料 | ⬜ |
| 14-5 | MQTTConnector | `src/data_pipeline/connectors/mqtt.py` | 訂閱 MQTT topic 接收即時資料 | ⬜ |
| 14-6 | 排程器 | `src/services/data_scheduler.py` | 定時（每 10 分鐘）觸發拉取 → 清洗 → 分析 → 告警 | ⬜ |
| 14-7 | 連線健康監控 | `src/services/connector_monitor.py` | 斷線偵測 + 自動重連 + 告警 | ⬜ |
| 14-8 | Connector YAML 設定 | `configs/connectors/` | 每個資料來源一個 YAML 設定檔 | ⬜ |
| 14-9 | 連線管理 API | `src/api/main.py` | 新增/編輯/刪除/測試連線 | ⬜ |
| 14-10 | 前端連線管理 | `frontend/src/components/ConnectorManager.tsx` | 連線清單 + 狀態指示 + 新增精靈 | ⬜ |

**依賴**：Phase 12（資料存入資料庫）、Phase 13（觸發告警）

---

### Phase 15：多風場管理

**目的**：從「分析一個風場」升級為「同時管理 N 個風場」

| WI# | 工作項目 | 檔案/位置 | 驗收標準 | 狀態 |
|-----|---------|-----------|----------|------|
| 15-1 | WindFarm 資料模型 | `src/models/db/wind_farm.py` | 風場 → 風機群組 → 單機，階層式管理 | ⬜ |
| 15-2 | 風場 CRUD API | `src/api/main.py` | 新增/編輯/刪除風場 + 綁定連接器 | ⬜ |
| 15-3 | 風場總覽儀表板 | `frontend/src/components/FarmOverview.tsx` | 多風場卡片式總覽（發電量、可利用率、告警數） | ⬜ |
| 15-4 | 跨風機比較 | `frontend/src/components/TurbineComparison.tsx` | 同風場多風機健康/效能並列比較 | ⬜ |
| 15-5 | 風場級 KPI 計算 | `src/services/farm_kpi_service.py` | 可利用率、容量因子、尾流損失 | ⬜ |
| 15-6 | 客戶資料模型 | `src/models/db/customer.py` | 客戶 → 合約 → 風場 | ⬜ |
| 15-7 | 使用者認證 | `src/api/auth.py` | OAuth2 / JWT 登入 + 角色權限（管理員/工程師/客戶） | ⬜ |

**依賴**：Phase 14（資料連接器）

---

### Phase 16：歷史案例學習

**目的**：讓系統越用越聰明 — 每次故障處理都成為未來的知識

| WI# | 工作項目 | 檔案/位置 | 驗收標準 | 狀態 |
|-----|---------|-----------|----------|------|
| 16-1 | 案例自動記錄 | `src/services/case_learning.py` | 工單結案時自動提取：故障類型+症狀+解決方案 → RAG | ⬜ |
| 16-2 | 相似案例推薦 | `src/skills/rag/case_recommender.py` | 新告警觸發時，語意搜尋歷史案例 Top-5 | ⬜ |
| 16-3 | 案例推薦 API | `src/api/main.py` | `GET /api/cases/similar?alert_id=xxx` | ⬜ |
| 16-4 | 故障知識圖譜 | `src/services/knowledge_graph.py` | 故障類型→根因→症狀→解法 的 Graph 結構 | ⬜ |
| 16-5 | 前端案例面板 | `frontend/src/components/CaseRecommendation.tsx` | 工單頁面內嵌「相似歷史案例」推薦 | ⬜ |
| 16-6 | 維護效果追蹤 | `src/services/maintenance_tracker.py` | 自動對比維修前後 30 天的效能變化 | ⬜ |

**依賴**：Phase 13（工單系統）、Phase 12（持久化）

---

## Step 3：完整運維服務（Phase 17-19）

### Phase 17：派工與排程

| WI# | 工作項目 | 驗收標準 | 狀態 |
|-----|---------|----------|------|
| 17-1 | 技術員資料模型 | 技術員清單 + 技能標籤 + 可用時段 | ⬜ |
| 17-2 | 自動派工引擎 | 工單→根據技能/距離/排程推薦技術員 | ⬜ |
| 17-3 | 維護排程最佳化 | 考慮天氣窗口+備品到貨+人力的排程 | ⬜ |
| 17-4 | 行動端界面 | 技術員手機查看工單/回報/拍照 | ⬜ |

### Phase 18：備品庫存

| WI# | 工作項目 | 驗收標準 | 狀態 |
|-----|---------|----------|------|
| 18-1 | 備品資料庫 | 零件清單+適用型號+庫存量+存放位置 | ⬜ |
| 18-2 | 故障→備品關聯 | 故障類型自動推薦所需零件 | ⬜ |
| 18-3 | 庫存預警 | 低於安全水位自動通知 | ⬜ |
| 18-4 | 需求預測 | 根據故障頻率預測未來備品需求 | ⬜ |

### Phase 19：報告自動化 + SLA

| WI# | 工作項目 | 驗收標準 | 狀態 |
|-----|---------|----------|------|
| 19-1 | 自動報告排程 | 週報/月報自動產生+寄送客戶 | ⬜ |
| 19-2 | SLA 追蹤引擎 | 回應時間/解決時間/可利用率保證 | ⬜ |
| 19-3 | 客戶入口 | 客戶登入查看風場狀態/報告/工單 | ⬜ |
| 19-4 | 團隊績效儀表板 | 回應時間/結案率/客戶滿意度 KPI | ⬜ |

---

## 追蹤方式

### 狀態定義

| 圖示 | 狀態 | 說明 |
|------|------|------|
| ⬜ | 待開始 | 尚未開始 |
| 🔧 | 進行中 | 開發中 |
| 🔍 | 審查中 | 程式碼審查 / 測試中 |
| ✅ | 已完成 | 已合併至主分支 |
| ❌ | 取消 | 需求變更或不再需要 |

### 更新頻率

- 每完成一個 Work Item 更新此文件
- 每個 Phase 完成時更新 `TODO-roadmap.md` 和 `PROJECT-STATUS.md`
- 重大設計決策記錄於 `FUTURE-ROADMAP.md` 的「關鍵決策記錄」

---

## 變更記錄

| 日期 | 變更 |
|------|------|
| 2026-04-04 | 初版建立：Phase 11-19 共 70+ 工作項目，三步走架構 |
| 2026-04-04 | Phase 11 完成（5/5 WI）：戰情中心三欄佈局 |
| 2026-04-04 | Phase 12 完成（4/4 WI）：SQLite 持久化 + 歷史 API |
