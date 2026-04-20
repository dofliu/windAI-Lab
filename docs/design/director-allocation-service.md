# 設計文件 — 總監派工服務 `DirectorAllocationService`

> **版本**：v0.1（設計階段）
> **對應 Issue**：[#96 總監工作分配與紀錄系統](https://github.com/dofliu/windai-lab/issues/96) — 階段二（服務層）
> **作者**：wLab:director（規劃）+ wEng:backend-dev（介面）+ wRes:rag-curator（文件）
> **建立日期**：2026-04-20
> **狀態**：設計 ✅（待實作，預計 4/26 之後啟動）

---

## 1. 背景與目標

### 1.1 使用者核心需求（重複強調）

> **確認各種工作，總監可以確實分配（AI 輔助），然後所有流程、工作細節、成果都可以如實詳細紀錄、存成文件，產生正式美觀報告。**

### 1.2 現況（階段一已完成）

- ✅ 派工單模板 `docs/templates/tmpl-work-assignment.md`
- ✅ 工作紀錄模板 `docs/templates/tmpl-work-record.md`
- ✅ 正式報告模板 `docs/templates/tmpl-formal-report.md`
- ✅ 月索引 `docs/work-logs/README.md`
- ✅ 兩次實戰驗證（4/19 #41 + 4/20 #42）

**缺口**：派工決策目前依賴人工（Claude Code）撰寫 Markdown，未有結構化資料、API、自動化派工建議、與前端面板連動。

### 1.3 階段二目標

| 目標 | 說明 |
|------|------|
| **結構化派工資料** | 派工決策以 Pydantic model 表達，寫入 SQLite，可查詢、可統計 |
| **AI 輔助派工演算法** | 根據任務屬性、團隊負載、依賴鏈、Hackathon 倒數，自動產出派工建議 |
| **REST API** | 派工單 CRUD、派工建議查詢、工作紀錄讀寫 |
| **Markdown ↔ DB 雙向同步** | 既有 Markdown 紀錄可匯入 DB，DB 內容可匯出為 Markdown 派工單 |
| **前端整合** | 為現有 `WorkOrderPanel` 新增派工面板 tab（階段三範圍，本階段預留介面） |

### 1.4 不在本階段範圍

- ❌ 前端 UI（留待階段三）
- ❌ HTML / PDF 正式報告產出（留待階段三，與 #44 整合）
- ❌ LLM 驅動的自然語言派工（留待 v1.1；本階段採規則式 AI 輔助）

---

## 2. 整體架構

```
┌──────────────────────────────────────────────────────────────┐
│           使用者 / Issue Webhook / 每日例行工作流              │
└───────────────┬──────────────────────────────────────────────┘
                │  新任務事件
                ▼
┌──────────────────────────────────────────────────────────────┐
│                 DirectorAllocationService                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ TaskAnalyzer     → 分類 (domain/eng/ai/data/res)       │  │
│  │ LoadEstimator    → 團隊 WIP / 待辦量                   │  │
│  │ PriorityScorer   → P1-P5（依 Hackathon / 依賴 / 使用者期待）│  │
│  │ AllocationEngine → 產出派工建議（含理由）              │  │
│  │ RecordWriter     → 寫 DB + Markdown（雙向同步）        │  │
│  └────────────────────────────────────────────────────────┘  │
└───────────────┬──────────────────────────────────────────────┘
                │
        ┌───────┴────────┐
        ▼                ▼
┌───────────────┐  ┌────────────────────────────────────┐
│  SQLite       │  │  docs/work-logs/YYYY-MM/           │
│  allocations  │  │  YYYY-MM-DD-allocation.md          │
│  work_records │  │  WLAB-YYYYMMDD-NN-{slug}.md        │
└───────────────┘  └────────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────────┐
│  FastAPI REST                                                │
│  /api/director/allocations  (CRUD)                           │
│  /api/director/suggest      (AI 輔助派工建議)                │
│  /api/director/work-records (工作紀錄 CRUD)                  │
│  /api/director/load-snapshot (團隊負載快照)                  │
└───────────────┬──────────────────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────────┐
│  前端：WorkOrderPanel 新增「派工面板」tab（階段三）          │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. 核心介面與資料模型

### 3.1 Pydantic Model（`src/services/director_allocation/models.py`）

```python
from datetime import date, datetime
from enum import Enum
from pydantic import BaseModel, Field


class Priority(str, Enum):
    P0 = "P0"  # 例行（每日掃描、日報）
    P1 = "P1"  # Hackathon 關鍵路徑
    P2 = "P2"  # Epic 推進
    P3 = "P3"  # 平行推進
    P4 = "P4"  # 使用者需求 / 技術債
    P5 = "P5"  # 待排程


class TeamNamespace(str, Enum):
    wLab = "wLab"
    wData = "wData"
    wAI = "wAI"
    wDomain = "wDomain"
    wEng = "wEng"
    wRes = "wRes"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Allocation(BaseModel):
    """單一派工紀錄。對應 Markdown 派工單中的一個任務欄位。"""

    task_id: str = Field(..., description="WLAB-YYYYMMDD-NN")
    github_issue: int | None = None
    title: str
    assignee_agent: str = Field(..., description="namespace:role")
    collaborators: list[str] = Field(default_factory=list)
    priority: Priority
    estimated_hours: float
    dependencies: list[str] = Field(default_factory=list)
    deadline: date
    acceptance_criteria: list[str]
    rationale: str = Field(..., description="派工理由")
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TeamLoadSnapshot(BaseModel):
    namespace: TeamNamespace
    wip_count: int
    backlog_count: int
    load_level: str = Field(..., pattern=r"^(idle|low|medium|high|critical)$")
    suggestion: str


class DailyAllocationSheet(BaseModel):
    """一日派工單 — 對應 YYYY-MM-DD-allocation.md。"""

    date: date
    hackathon_days_remaining: int
    decision_summary: str
    load_snapshot: list[TeamLoadSnapshot]
    allocations: list[Allocation]
    ai_advice: "AiAdvice"
    signed_off: bool = False


class AiAdvice(BaseModel):
    bottlenecks: list[str]
    risks: list[str]
    resource_suggestions: list[str]
    schedule_suggestions: list[str]
    lessons_learned: list[str] = Field(default_factory=list)


class WorkRecord(BaseModel):
    """工作紀錄 — 對應 WLAB-*.md 檔案。"""

    task_id: str
    allocation_id: str
    summary: str
    execution_steps: list[str]
    commits: list[str] = Field(default_factory=list)
    prs: list[int] = Field(default_factory=list)
    test_results: dict[str, str]
    deliverables: list[str]
    learnings: list[str]
    follow_up_actions: list[str]
    closed_at: datetime | None = None
```

### 3.2 資料庫 Schema（SQLite）

```sql
CREATE TABLE allocations (
    task_id TEXT PRIMARY KEY,            -- WLAB-YYYYMMDD-NN
    sheet_date DATE NOT NULL,            -- 派工單日期
    github_issue INTEGER,
    title TEXT NOT NULL,
    assignee_agent TEXT NOT NULL,
    collaborators TEXT,                   -- JSON array
    priority TEXT NOT NULL CHECK(priority IN ('P0','P1','P2','P3','P4','P5')),
    estimated_hours REAL NOT NULL,
    dependencies TEXT,                    -- JSON array
    deadline DATE NOT NULL,
    acceptance_criteria TEXT NOT NULL,    -- JSON array
    rationale TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_allocations_sheet_date ON allocations(sheet_date);
CREATE INDEX idx_allocations_assignee ON allocations(assignee_agent);
CREATE INDEX idx_allocations_status ON allocations(status);

CREATE TABLE daily_sheets (
    sheet_date DATE PRIMARY KEY,
    hackathon_days_remaining INTEGER NOT NULL,
    decision_summary TEXT NOT NULL,
    ai_advice TEXT NOT NULL,              -- JSON
    load_snapshot TEXT NOT NULL,          -- JSON array
    signed_off INTEGER DEFAULT 0,
    markdown_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE work_records (
    task_id TEXT PRIMARY KEY REFERENCES allocations(task_id),
    summary TEXT NOT NULL,
    execution_steps TEXT NOT NULL,         -- JSON array
    commits TEXT,                          -- JSON array
    prs TEXT,                              -- JSON array
    test_results TEXT,                     -- JSON
    deliverables TEXT NOT NULL,            -- JSON array
    learnings TEXT,                        -- JSON array
    follow_up_actions TEXT,                -- JSON array
    markdown_path TEXT NOT NULL,
    closed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**持久化位置**：`data/director_allocation.sqlite`（加入 `.gitignore`）

---

## 4. AI 輔助派工演算法（規則式 v0.1）

### 4.1 輸入

```python
class TaskInput(BaseModel):
    title: str
    github_issue: int | None
    description: str
    labels: list[str]                     # bug / enhancement / epic / urgent ...
    dependencies: list[str]
    requested_priority: Priority | None   # 使用者指定（可選）
```

### 4.2 輸出

```python
class AllocationSuggestion(BaseModel):
    assignee_agent: str
    priority: Priority
    estimated_hours: float
    rationale: str
    risk_flags: list[str]
    alternatives: list[str] = Field(default_factory=list)  # 備選指派
```

### 4.3 演算法步驟

1. **任務分類**：依 labels + 關鍵字（regex）→ 決定 team namespace
   - `backend|api|service|fastapi` → `wEng`
   - `ml|model|training|forecast|diagnosis` → `wAI`
   - `data|etl|scada|cleaning|ingestion` → `wData`
   - `domain|iec|wake|power-curve` → `wDomain`
   - `research|docs|paper|rag` → `wRes`
   - 其他 → `wLab`
2. **負載查詢**：從 DB 查當前 assignee 的 `IN_PROGRESS` + `PENDING` 任務數
3. **優先序計分**：
   - Hackathon 倒數 < 7 天 且 label 含 `urgent|priority:high` → P1
   - 有下游依賴阻塞 → P1
   - Epic 子任務 → P2
   - 技術債 → P4
   - 其他 → P3
4. **工時估算**：
   - 設計文件：1-2 h
   - 小 PR（≤ 50 行）：2-4 h
   - 中 PR（50-150 行）：4-8 h
   - 大 PR（>150 行）→ 建議拆分（risk flag）
5. **替代方案**：若首選團隊負載 > 3 WIP，產出 alternatives（如交由 wRes 先做設計稿）

### 4.4 落地位置

`src/services/director_allocation/allocator.py`

```python
class AllocationEngine:
    def suggest(self, task: TaskInput, context: AllocationContext) -> AllocationSuggestion:
        ...
```

其中 `AllocationContext` 包含當日負載快照、Hackathon 倒數、近期決策。

---

## 5. REST API 設計

### 5.1 端點清單

| 方法 | 路徑 | 用途 | 授權 |
|------|------|------|------|
| `GET` | `/api/director/allocations` | 列出派工（分頁 + 篩選：日期 / 指派者 / 狀態） | 內部 |
| `POST` | `/api/director/allocations` | 建立派工（寫 DB + Markdown） | 總監 |
| `GET` | `/api/director/allocations/{task_id}` | 單一派工詳情 | 內部 |
| `PATCH` | `/api/director/allocations/{task_id}` | 更新派工狀態 | 總監 |
| `POST` | `/api/director/suggest` | 取得 AI 派工建議（不落地） | 總監 |
| `GET` | `/api/director/load-snapshot` | 當前團隊負載快照 | 內部 |
| `GET` | `/api/director/sheets/{date}` | 取得某日完整派工單（JSON） | 內部 |
| `POST` | `/api/director/sheets/{date}/signoff` | 簽核派工單 | 總監 |
| `GET` | `/api/director/work-records/{task_id}` | 讀取工作紀錄 | 內部 |
| `POST` | `/api/director/work-records` | 建立 / 更新工作紀錄 | 指派代理 |
| `POST` | `/api/director/import-markdown` | 從既有 Markdown 回填 DB（一次性遷移用） | 總監 |

### 5.2 回應格式範例

```jsonc
// GET /api/director/load-snapshot
{
  "timestamp": "2026-04-20T14:00:00Z",
  "hackathon_days_remaining": 28,
  "teams": [
    {"namespace": "wEng",   "wip_count": 1, "backlog_count": 5, "load_level": "high",   "suggestion": "先完成 #42 再排 #43"},
    {"namespace": "wAI",    "wip_count": 0, "backlog_count": 0, "load_level": "idle",   "suggestion": "可預先設計 #48"},
    {"namespace": "wData",  "wip_count": 0, "backlog_count": 1, "load_level": "low",    "suggestion": "週中啟動 #75"},
    {"namespace": "wDomain","wip_count": 0, "backlog_count": 0, "load_level": "idle",   "suggestion": "可協助 #50"},
    {"namespace": "wRes",   "wip_count": 1, "backlog_count": 1, "load_level": "low",    "suggestion": "持續紀錄"},
    {"namespace": "wLab",   "wip_count": 2, "backlog_count": 0, "load_level": "medium", "suggestion": "每日例行"}
  ]
}
```

---

## 6. Markdown ↔ DB 雙向同步

### 6.1 為何需要雙向同步

1. **Markdown 易讀**：直接由人類或 Claude Code 撰寫，Git 友善
2. **DB 易查**：支援統計、圖表、跨日期查詢
3. **漸進遷移**：既有 8 份 Markdown 可一次性匯入，新派工雙寫

### 6.2 轉換器（`src/services/director_allocation/converter.py`）

```python
class AllocationMarkdownConverter:
    @staticmethod
    def parse_sheet(path: Path) -> DailyAllocationSheet: ...

    @staticmethod
    def parse_record(path: Path) -> WorkRecord: ...

    @staticmethod
    def render_sheet(sheet: DailyAllocationSheet) -> str: ...

    @staticmethod
    def render_record(record: WorkRecord) -> str: ...
```

**解析策略**：以 Markdown 標題錨點（`## 1. 本日決策摘要` 等）切段，配合表格 token 化。

### 6.3 寫入順序

```
POST /api/director/allocations
    ↓
AllocationEngine.suggest() (可選)
    ↓
DB insert (transaction)
    ↓
Markdown render → write file
    ↓
git-aware 提醒（產出 commit 建議訊息，不自動 commit）
    ↓
回傳 201 + task_id
```

**設計原則**：服務不自動 git commit，避免副作用；由每日例行工作流或使用者執行。

---

## 7. 與既有系統整合點

| 整合點 | 現況 | 整合方式 |
|--------|------|----------|
| **#41 AlertRuleEngine** | 告警觸發可產生工單 | 工單可轉派工（`Alert → Allocation` mapping） |
| **OrchestrationEngine** | 既有工作流執行 | 執行結果寫回 `work_records` |
| **WorkOrderPanel（前端）** | 現有工單看板 | 階段三新增「派工」tab，共用 API |
| **daily_report.md** | 既有日報生成 | 每日掃描後從 DB 讀取派工統計，嵌入日報 |
| **docs/work-logs/** | 既有 Markdown 索引 | `POST /api/director/import-markdown` 一次性遷移 |
| **CLAUDE.md §4** | 「派工與紀錄文件化（#96）」章節 | 同步更新引用 API 端點 |

---

## 8. 測試策略

| 測試類型 | 範圍 | 目標覆蓋率 |
|----------|------|------------|
| 單元測試 | `models.py`, `allocator.py`, `converter.py` | ≥ 90% |
| 整合測試 | FastAPI endpoints（使用 `httpx.AsyncClient` + 測試資料庫） | ≥ 80% |
| 契約測試 | Markdown parser → roundtrip（parse → render → parse 相等性） | 100% 的 8 份既有檔案 |
| 資料遷移測試 | 讀入既有 `docs/work-logs/2026-04/*.md`，驗證無資料遺失 | 8/8 通過 |
| 手動驗收 | 總監視角：建立派工 → 查看負載 → 簽核 → 匯出 Markdown | 1 輪 |

**目標總覆蓋率**：≥ 85%

---

## 9. 安全與合規

| 項目 | 策略 |
|------|------|
| **授權** | 「總監」操作僅限內網 / 本地 FastAPI（同既有機制），不對外開放 |
| **輸入驗證** | 所有 API 採 Pydantic model 驗證 |
| **SQL Injection 防護** | 全用 parametrized queries（`sqlite3` `?` placeholder）或 SQLAlchemy |
| **Markdown Injection** | render 時跳脫 `|` / HTML tag；parse 時忽略未預期欄位（`extra="ignore"`） |
| **機密資訊** | `allocations.rationale` 禁止包含 API Key、密碼；透過 lint 檢查 regex |
| **稽核軌跡** | `allocations.updated_at` + 預留 `audit_log` 表於 v1.1 |
| **資料備份** | SQLite 檔案列入 `scripts/backup.sh`（v1.1） |

---

## 10. 實作時程與 PR 切分

### 10.1 PR 切分（每個 ≤ 300 行）

| PR | 範圍 | 預估工時 | 依賴 |
|----|------|----------|------|
| **PR 1** | `models.py` + DB schema + 遷移腳本 | 2 h | 設計 ✅ |
| **PR 2** | `AllocationEngine` 規則式演算法 + 單元測試 | 3 h | PR 1 |
| **PR 3** | `converter.py` Markdown ↔ DB + roundtrip 測試 | 3 h | PR 1 |
| **PR 4** | FastAPI 端點（allocations + suggest + load-snapshot） | 3 h | PR 2, 3 |
| **PR 5** | Work records API + 匯入既有 Markdown 腳本 | 2 h | PR 4 |
| **PR 6** | CLAUDE.md / README / 日報整合（docs 收斂） | 1 h | PR 5 |

**總計**：14 h（分 6 個 PR，預估跨 1-2 週）

### 10.2 建議時程

| 日期 | 里程碑 |
|------|--------|
| 2026-04-21 ~ 04-25 | Epic E 完成（#42 PR A/B + #43） |
| 2026-04-26 | 啟動 PR 1（模型 + schema） |
| 2026-04-27 | 啟動 PR 2（AllocationEngine） |
| 2026-04-28 | 啟動 PR 3（Converter） |
| 2026-04-29 | 啟動 PR 4（API） |
| 2026-04-30 | 啟動 PR 5（匯入既有 Markdown） |
| 2026-05-01 | PR 6（文件收斂）+ 整體驗收 |

---

## 11. 未來擴充（v1.1+）

| 擴充項目 | 版本 | 說明 |
|----------|------|------|
| LLM 驅動自然語言派工 | v1.1 | 輸入「請規劃本週 Epic D 啟動」，LLM 產出派工建議 |
| 審計軌跡 `audit_log` 表 | v1.1 | 紀錄誰在何時對派工做了什麼修改 |
| 前端派工面板（WorkOrderPanel tab） | v1.2（階段三） | 看板式拖拉、即時負載儀表板 |
| HTML / PDF 正式報告匯出 | v1.2（階段三） | 整合 `tmpl-formal-report.md`，WeasyPrint / Pandoc |
| Email / LINE 派工通知 | v1.3 | 與 #42 NotificationManager 整合 |
| 跨專案派工（多 workspace） | v2.0 | 支援多 Git repo / 多團隊 |

---

## 12. 設計決策摘要

| 決策 | 選項 | 採用 | 理由 |
|------|------|------|------|
| 資料庫 | SQLite / PostgreSQL | **SQLite** | 單機部署、零運維成本，符合研究平台定位 |
| ORM | SQLAlchemy / 純 sqlite3 | **sqlite3 + raw SQL** | 避免重型依賴，與既有 `alert_engine.py` 風格一致 |
| AI 輔助演算法 | 規則式 / LLM | **規則式（v0.1）** | 可預測、可測試；LLM 留待 v1.1 |
| Markdown 同步 | 單向（DB → MD） / 雙向 | **雙向** | 既有 8 份 Markdown 可漸進遷移 |
| 前端介面 | 本階段實作 / 延後 | **延後至階段三** | 本階段專注後端契約穩定 |
| 通知整合 | 本階段整合 / 延後 | **延後（依賴 #42 實作完成）** | 解耦發佈 |

---

## 13. 驗收標準（階段二完成定義）

- [ ] `src/services/director_allocation/` 模組建立
- [ ] DB schema 建立 + 遷移腳本可執行
- [ ] `AllocationEngine.suggest()` 可基於 3 個範例任務產出合理派工建議
- [ ] FastAPI 11 個端點全部實作並通過 integration 測試
- [ ] 既有 `docs/work-logs/2026-04/*.md`（8 份）可無損匯入 DB
- [ ] Markdown roundtrip 測試通過（parse → render → parse）
- [ ] 測試覆蓋率 ≥ 85%
- [ ] `ruff check .` All checks passed
- [ ] CLAUDE.md / README / 日報引用新 API 端點
- [ ] 至少一次實戰使用（本設計文件列為範例任務）

---

## 14. 連結與參考

- **階段一文件層**：`docs/templates/tmpl-work-assignment.md`, `tmpl-work-record.md`, `tmpl-formal-report.md`
- **相關 Issue**：[#96](https://github.com/dofliu/windai-lab/issues/96), [#44](https://github.com/dofliu/windai-lab/issues/44)（報告排程）, [#42](https://github.com/dofliu/windai-lab/issues/42)（通知渠道）
- **前置設計**：[docs/design/notification-channels.md](./notification-channels.md)
- **專案規範**：[CLAUDE.md §4 工作流程規範](../../CLAUDE.md)
- **日報整合**：[docs/daily_report.md](../daily_report.md)

---

*本設計文件由 wLab:director + wEng:backend-dev + wRes:rag-curator 於 2026-04-20 協作產出，作為 #96 階段二（服務層）的實作契約。*
