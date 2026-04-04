# WindAI Lab — TODO 路線圖與下一步工作規劃

> 最後更新：2026-04-04
> 目前進度：Phase 10 完成（92%）
> **核心願景：打造一間真實的風場運維 AI 服務公司**

---

## 1. 當前狀態摘要

```
研究平台階段 ██████████████████░░ 92%（Phase 1-10 完成）
運維服務演進 ░░░░░░░░░░░░░░░░░░░░  0%（Phase 11-19 待開始）

Phase:  1  2  3  4  5  5.5  6a  6b  6c  7  8  9  10  │  11  12  13  14  15  16  17  18  19
        ✅ ✅ ✅ ✅ ✅  ✅   ✅  ✅   ✅  ✅  ✅  ✅  ✅  │  ⬜   ⬜   ⬜   ⬜   ⬜   ⬜   ⬜   ⬜   ⬜
        ─────── 研究平台（已完成）──────────────────── │ ── Step1 ── ── Step2 ── ── Step3 ──
                                                       │  打地基      接真實風場    完整服務
```

| 類別 | 已完成 | 剩餘 |
|------|--------|------|
| 核心代理 | 12 | 0 |
| 可聘用代理 | 10 (YAML 定義) | 按需新增 |
| 技能模組 | 12 | 依需求新增 |
| ML 模型 | 5 | 1+（Transformer 等） |
| API 端點 | 30+ | 20+（告警/工單/連接器等） |
| 前端元件 | 28 | 10+（戰情中心/工單/告警等） |
| Office Renderer | 3（pixel / modern / minimal） | 可擴充 |

### 架構狀態

| 系統 | 狀態 | 說明 |
|------|------|------|
| 舊系統（42 人固定） | ⚠️ 並行中 | 仍在運行，待切換 |
| 新系統（12 核心 + 聘用制） | ✅ 就緒 | DynamicRegistry + Skills + YAML |

---

## 2. 三步走演進路線

### 🔴 Step 1：打地基 — 持久化 + 服務閉環（Phase 11-13）

> 讓系統「記得住」、「能追蹤」、「會通知」

#### Phase 11 — 前端戰情中心 + 分析面板

| 項目 | 說明 | 狀態 |
|------|------|------|
| MissionView 戰情中心 | 任務進行時自動切換，只顯示參與代理 | ⬜ |
| AnalysisDashboard 分析面板 | 右側即時圖表 + 報告清單 | ⬜ |
| ViewSwitcher 自動切換 | office ↔ mission 自動切換 | ⬜ |
| 技能管線進度條 | 每個 skill 獨立進度 | ⬜ |

#### Phase 12 — 持久化儲存

| 項目 | 說明 | 狀態 |
|------|------|------|
| SQLite/PostgreSQL 資料庫 | Task / WorkLog / AnalysisResult / AgentStatus | ⬜ |
| 歷史查詢 API | `GET /api/tasks/history` 分頁查詢 | ⬜ |
| 前端歷史面板 | 可回溯過去的任務結果與報告 | ⬜ |
| 分析結果快照 | 完整輸入/輸出/參數存檔 | ⬜ |

#### Phase 13 — 告警系統 + 工單管理

| 項目 | 說明 | 狀態 |
|------|------|------|
| 告警規則引擎 | 閾值規則 + 複合條件 + 靜默期 | ⬜ |
| 通知渠道 | Email / Webhook / LINE Notify | ⬜ |
| 工單系統 | 診斷結果 → 自動產生工單 → 狀態追蹤 | ⬜ |
| 工單 Kanban 面板 | 待處理/進行中/完成 三欄拖拉 | ⬜ |

### 🟡 Step 2：接真實風場 — 即時串接 + 多風場管理（Phase 14-16）

> 讓系統「看得到」真實風場、「管得了」多個客戶

#### Phase 14 — 即時資料連接器

| 項目 | 說明 | 狀態 |
|------|------|------|
| DataConnector 抽象層 | 統一介面（File / REST / OPC UA / MQTT） | ⬜ |
| 串流處理管線 | 定時拉取 → 清洗 → 分析 → 告警 | ⬜ |
| 連線健康監控 | 斷線偵測 + 自動重連 | ⬜ |
| Connector YAML 設定 | 一個資料來源一個 YAML | ⬜ |

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

詳細記錄見 [progress-report.md](progress-report.md)。

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
| [FUTURE-ROADMAP.md](FUTURE-ROADMAP.md) | 願景定位 + 三步走路線圖 + 決策記錄 |
| [EVOLUTION-PLAN.md](EVOLUTION-PLAN.md) | 詳細執行計畫（70+ 工作項目，含檔案位置與驗收標準） |
| [PROJECT-STATUS.md](PROJECT-STATUS.md) | 專案現況一頁式摘要 |
| [architecture-design.md](architecture-design.md) | 系統架構設計 |
| [progress-report.md](progress-report.md) | Phase 1-10 開發歷程 |
