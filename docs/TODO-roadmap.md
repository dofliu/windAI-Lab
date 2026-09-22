# WindAI Lab — TODO 路線圖與下一步工作規劃

> 最後更新：2026-09-22（專案健檢 + 文件校準）
> 目前進度：Phase 14 全數完成（14a / 14b / 14c ✅）+ Epic C ✅ + Epic E ✅ + OMC 文件層整合 ✅
> **核心願景：打造一間真實的風場運維 AI 服務公司**
> **追蹤方式**：GitHub Issues（6 Epic / 15 子 Issue）+ 派工系統（#96）
> ⚠️ **當前阻塞**：master CI 自 2026-07-10 起紅燈（lint 未過 → 測試 job 被 skip）。詳見 [PROJECT-STATUS.md](PROJECT-STATUS.md#專案健康度2026-09-22-實測)

---

## 1. 當前狀態摘要

```
研究平台階段 ██████████████████░░ 92%（Phase 1-10 完成）
運維服務演進 ████████████░░░░░░░░ 50%（Phase 11-14 / 11-19）

Phase:  1  2  3  4  5  5.5  6a  6b  6c  7  8  9  10  │  11  12  13  │  14  15  16  17  18  19
        ✅ ✅ ✅ ✅ ✅  ✅   ✅  ✅   ✅  ✅  ✅  ✅  ✅  │  ✅   ✅   ✅  │  🔨   ⬜   ⬜   ⬜   ⬜   ⬜
        ─────── 研究平台（已完成）──────────────────── │ Step1 完成 ✅ │ ── Step2 ── ── Step3 ──
                                                       │  打地基       │ 接真實風場    完整服務
```

| 類別 | 已完成（2026-09-22 實測） | 剩餘 |
|------|--------------------------|------|
| 核心代理 | 25 個 agent 模組（6 團隊） | 按需新增 |
| 可聘用代理 | 10 (YAML 定義) | 按需新增 |
| 技能模組 | 29 個 BaseSkill 實作（28 模組） | 依需求新增 |
| ML 模型 | 7（含 LSTM v2 + PatchTST） | GNN / 遷移學習 |
| 對比實驗框架 | 1（ModelBenchmark） | — |
| REST API 端點 | 73（main.py 62 + director.py 11）+ 1 WebSocket | 風場管理等 |
| 前端元件 | 40 個 `.tsx` | 多風場儀表板等 |
| Office Renderer | 3（pixel / modern / minimal） | 可擴充 |
| DB 資料表 | 9（tasks / work_logs / analysis_results / alerts / work_orders / reports / allocations / daily_sheets / work_records） | 按需新增 |
| 測試 | 35 檔案 / 877 案例（868 pass、4 fail、5 skip） | 修掉 4 個失敗 |
| 後端程式碼 | 141 個 `.py` / 30,302 行 | — |

> 註：以上為 2026-09-22 以指令實測所得（`find` / `grep` / `pytest --collect-only`），取代先前人工填寫的估計值。

### 架構狀態

| 系統 | 狀態 | 說明 |
|------|------|------|
| 舊系統（42 人固定） | ⚠️ 並行中 | 仍在運行，待切換 |
| 新系統（12 核心 + 聘用制） | ✅ 就緒 | DynamicRegistry + Skills + YAML |

---

## 2. 三步走演進路線

### 🔴 Step 1：打地基 — 持久化 + 服務閉環（Phase 11-13）✅

> 讓系統「記得住」、「能追蹤」、「會通知」

#### Phase 11 — 前端戰情中心 + 分析面板 ✅

| 項目 | 說明 | 狀態 |
|------|------|------|
| MissionAgentPanel 代理面板 | 任務中只顯示參與代理 + 即時進度 | ✅ |
| WorkflowProgress 三欄佈局 | 代理面板 / 進度+日誌 / 即時分析圖表 | ✅ |
| ViewSwitcher 自動切換 | header 狀態標籤 + 「返回辦公室」按鈕 | ✅ |
| 技能管線進度條 | 步驟條 + 代理個別進度條 | ✅ |

#### Phase 12 — 持久化儲存 ✅

| 項目 | 說明 | 狀態 |
|------|------|------|
| SQLite 資料庫模組 | 3 張表 + CRUD + WAL 模式（零新依賴） | ✅ |
| 引擎整合持久化 | workflow 自動寫入/更新任務記錄 | ✅ |
| 歷史查詢 API | history / detail / stats 三個端點 | ✅ |
| 前端歷史合併 | localStorage + 後端 API 雙層去重 | ✅ |

#### Phase 13 — 告警系統 + 工單管理 ✅

| 項目 | 說明 | 狀態 |
|------|------|------|
| alerts + work_orders 資料表 | SQLite 含完整索引、外部去重 | ✅ |
| 告警 REST API（6 端點） | CRUD + Ingest + stats + 從告警建工單 | ✅ |
| 工單 REST API（6 端點） | CRUD + notes + stats | ✅ |
| AlertIngestRequest | 標準化外部推送格式（source_alert_id 去重） | ✅ |
| WebSocket 即時推播 | alert_new / alert_updated / work_order_updated | ✅ |
| AlertPanel 前端 | 告警列表 + 篩選 + 確認/解決/駁回 + 手動建立 | ✅ |
| WorkOrderPanel 前端 | Kanban 看板 + 詳情 + 備註時間線 | ✅ |
| DashboardView 整合 | 新增「警報」tab + 活躍告警數量 badge | ✅ |
| TaskLauncher 重構 | 精簡底部列 + 向上滑出抽屜（釋放主內容空間） | ✅ |
| **告警規則引擎核心 (#41)** | **閾值規則 + 複合條件 + 靜默期 + 自動工單 + 5 API** | **✅ 完成** |
| 通知渠道 | Email / Webhook / LINE Notify | ✅ 完成 |
| 告警規則 YAML 設定 | YAML 定義規則，熱更新 | ✅ 完成 |

---

### Epic C：ML 模型進化 ✅ (2026-04-05)

> GitHub Issues: #32 (Epic), #38 (C1), #39 (C2), #40 (C3)

| 項目 | 說明 | 狀態 |
|------|------|------|
| C1: LSTM skill pipeline 整合 | R² 指標 + 模型持久化 + JSONL/MLflow 實驗記錄 | ✅ |
| C2: PatchTST Transformer | 官方簡化版 PatchTST (ICLR 2023) + skill 封裝 | ✅ |
| C3: 模型對比實驗框架 | ModelBenchmark + LaTeX 表格 + 統一評估 | ✅ |

---

### 待辦 Epics（以 GitHub Issues 追蹤）

| Epic | Issue | 優先度 | 子任務 |
|------|-------|--------|--------|
| [Epic E] 告警規則引擎 | #33 | High | #41 規則核心 ✅ / #42 通知渠道 ✅ / #43 YAML 設定 ✅ |
| [Epic D] 報告與追蹤 | #34 | High | #44 報告排程 ✅ / #45 效能追蹤 / #46 儀表板 |
| [Epic A] 案例學習系統 | #35 | Medium | #47 自動記錄 / #48 案例推薦 / #49 API+前端 |
| [Epic B] 故障知識體系 | #36 | Medium | #50 知識圖譜 / #51 維護效果追蹤 |
| [Epic F] 學術論文規劃 | #37 | Ongoing | #52 投稿策略 |

---

### 🟡 Step 2：接真實風場 — 即時串接 + 多風場管理（Phase 14-16）

> 讓系統「看得到」真實風場、「管得了」多個客戶

#### Phase 14 — WindGuard AI 整合 + 即時資料連接器

**Phase 14a：WindGuard AI 整合 ✅**

| 項目 | 說明 | 狀態 |
|------|------|------|
| WindGuard 診斷推理 | LLM 深層推理，產出故障類型、物理機制、維護建議 | ✅ |
| Agentic Function Calling | LLM 自主決定呼叫診斷工具，多輪對話式調查 | ✅ |
| 風場級別掃描 | 多執行緒並行掃描多台風機，自動風險排序 | ✅ |
| 功率曲線散佈圖 | NBM 訓練後產出風速 vs 功率散佈圖 | ✅ |
| 報告下載 API | `GET /api/reports/{id}/download` | ✅ |

**Phase 14b：前端任務生命週期重構 ✅ (#61)**

| 項目 | 說明 | 狀態 |
|------|------|------|
| Task Session 架構 | 後端事件驅動，解決重複紀錄/圖表累積/進度異常 | ✅ |
| 圖表持久化 | broadcast_analysis_result 同時存入 SQLite | ✅ |
| 工作日誌保留 | WebSocketManager 內建 log buffer | ✅ |

**Phase 14c：診斷報告輸出 ✅ + 即時資料連接器 ✅ (#64 ✅, #75 ✅)**

| 項目 | 說明 | 狀態 |
|------|------|------|
| 診斷報告輸出功能 | P0 context 扁平化 + P1 報告預覽 Modal + P2 SQLite 持久化 + P3 PDF 列印 (#64 PR #90) | ✅ |
| DataConnector 抽象層 | 統一介面（File / REST / OPC UA / MQTT）(#75) | ✅ |
| 串流處理管線 | 定時拉取 → 清洗 → 分析 → 告警 | ✅ |
| 連線健康監控 | 斷線偵測 + 自動重連 | ✅ |
| Connector YAML 設定 | 一個資料來源一個 YAML | ✅ |

#### Phase 15 — 多風場管理

| 項目 | 說明 | 狀態 |
|------|------|------|
| WindFarm 階層式資料模型 | 風場 → 風機群組 → 單機 | ⬜ |
| 風場總覽儀表板 | 多風場卡片（發電量、可利用率、告警數） | ⬜ |
| 跨風機比較 | 同風場多風機健康/效能並列比較 | ⬜ |
| 客戶管理 + 使用者認證 | OAuth2/JWT + 角色權限 | ⬜ |

#### Phase 16 — 歷史案例學習

| 項目 | 說明 | 狀態 |
|------|------|------|
| 案例自動記錄 | 工單結案 → 故障+解法寫入 RAG | ⬜ |
| 相似案例推薦 | 新告警 → 語意搜尋歷史 Top-5 | ⬜ |
| 故障知識圖譜 | 故障→根因→症狀→解法 Graph | ⬜ |
| 維護效果追蹤 | 維修前後 30 天效能對比 | ⬜ |

### 🟢 Step 3：完整運維服務 — 派工 + 備品 + 報告（Phase 17-19）

> 讓系統能「派人去做」、「知道需要什麼零件」、「自動向客戶報告」

#### Phase 17 — 派工與排程

| 項目 | 說明 | 狀態 |
|------|------|------|
| 技術員管理 | 清單 + 技能標籤 + 可用時段 | ⬜ |
| 自動派工引擎 | 技能/距離/排程自動推薦 | ⬜ |
| 行動端界面 | 手機查看工單/回報/拍照 | ⬜ |

#### Phase 18 — 備品庫存

| 項目 | 說明 | 狀態 |
|------|------|------|
| 備品資料庫 | 零件 + 型號 + 庫存 + 位置 | ⬜ |
| 故障→備品關聯 | 故障類型自動推薦零件 | ⬜ |
| 庫存預警 + 需求預測 | 安全水位告警 + 歷史趨勢預測 | ⬜ |

#### Phase 19 — 報告自動化 + SLA

| 項目 | 說明 | 狀態 |
|------|------|------|
| 自動報告排程 | 週報/月報自動產生 + 寄送客戶 | ⬜ |
| SLA 追蹤 | 回應時間/解決時間/可利用率保證 | ⬜ |
| 客戶入口 | 客戶登入看風場狀態/報告/工單 | ⬜ |

---

### 🛠 研發工具基礎建設（Tooling）

> 提升內部開發效率與多代理協作品質的工具整合

#### oh-my-claudecode (OMC) 整合（2026-04-27 啟動）

| 項目 | 說明 | 狀態 |
|------|------|------|
| AGENTS.md 協作組態 | 定義 OMC agent 與 windAI 6 層 namespace 的對應 | ✅ |
| `.claude/windailab-skills.md` 速查 | 開發者常用 OMC 指令速查表 | ✅ |
| `docs/omc-integration-guide.md` 整合指南 | 安裝步驟 / 環境需求 / 工作流範例 | ✅ |
| Plugin 安裝（互動式） | `/plugin install oh-my-claudecode` | ⬜（需人工執行） |
| omc-doctor 驗證 | 全項目綠燈 | ⬜（需人工執行） |
| Smoke test 模組地圖 | scientist agent 跑首個任務 | ⬜（需人工執行） |
| OMC `wiki` ↔ windAI RAG 對接 | 持久化記憶銜接 ChromaDB | ⬜（W19+ 評估） |
| 自訂 Skill：故障報告自動化 | skillify 包裝既有工作流 | ⬜（W19+ 評估） |

詳見 [`docs/omc-integration-guide.md`](omc-integration-guide.md) 與 [`AGENTS.md`](../AGENTS.md)。

---

## 3. 已完成的 Phase（摘要）

| Phase | 主題 | 關鍵產出 |
|-------|------|----------|
| 1 | 基礎架構 | FastAPI + React + Docker + 42 代理 YAML |
| 2 | 虛擬辦公室 UI | 像素風格、6 團隊房間、代理動畫 |
| 3 | 混合架構 | 模擬+真實共存、OrchestrationEngine |
| 4 | ML 模型 | NBM + FaultClassifier + RUL |
| 5 | 視覺化+RAG | SCADA 儀表板、ChromaDB 知識庫 |
| 6a-c | 進階分析 | 尾流模擬、smart_loader、FileWatcher |
| 7 | 架構重構 | 技能拆分、聘用制、YAML 驅動 |
| 8 | 系統切換 | 舊→新架構、端到端驗證 |
| 9 | 資料泛化 | TurbineProfile、BatchLoad、AutoExperiment |
| 10 | UI 抽象+品控 | 3 Renderers、統一 Workflow、Checkpoint、重試/降級 |

詳細記錄見 [progress-report.md](archived/progress-report.md) ⚠️ 已歸檔。

---

## 4. 新增代理 / 技能方式（新制）

### 新增代理

```yaml
# configs/agents/registry/my-new-agent.yaml
id: "my-new-agent"
name: "wAI:my-new-agent"
display_name: "我的新代理"
tier: "ai-ml"
core: false
skills: ["scada_ingestion", "scada_cleaning"]
task_routing:
  - match: ["分析"]
    pipeline: ["scada_ingestion", "scada_cleaning"]
```

```bash
curl -X POST "http://localhost:8000/api/agents/hire?agent_id=my-new-agent"
```

### 新增技能

```python
# src/skills/ml/my_skill.py
class MySkill(BaseSkill):
    skill_id = "my_skill"
    display_name = "我的技能"

    async def execute(self, inp, progress_cb=None):
        return SkillOutput(status=SkillStatus.SUCCESS, data={...})
```

技能會被 `SkillRegistry.auto_discover()` 自動發現並註冊。

---

## 5. 相關文件

| 文件 | 說明 |
|------|------|
| [FUTURE-ROADMAP.md](archived/FUTURE-ROADMAP.md) ⚠️ 已歸檔 | 願景定位 + 三步走路線圖 + 決策記錄 |
| [EVOLUTION-PLAN.md](archived/EVOLUTION-PLAN.md) ⚠️ 已歸檔 | 詳細執行計畫（70+ 工作項目，含檔案位置與驗收標準） |
| [PROJECT-STATUS.md](PROJECT-STATUS.md) | 專案現況一頁式摘要 |
| [architecture-design.md](architecture-design.md) | 系統架構設計 |
| [progress-report.md](archived/progress-report.md) ⚠️ 已歸檔 | Phase 1-10 開發歷程 |
