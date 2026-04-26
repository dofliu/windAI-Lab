# WindAI Lab — 風力發電 AI 研究協作系統

## 1. 專案概述

WindAI Lab 是一個風力發電領域的 AI 研究協作系統，整合 **42 個專業代理 (agents)** 與 **32 個 slash commands**，透過虛擬辦公室 (Virtual Office) 介面進行即時協作。系統目標為加速風力發電相關的資料分析、機器學習建模、論文撰寫及軟體工程開發流程。

核心能力：
- 風力發電 SCADA 資料清洗與分析
- 風機健康監測與預測性維護 (Predictive Maintenance)
- 功率曲線建模 (Power Curve Modeling)
- 尾流效應模擬 (Wake Effect Simulation)
- RAG 驅動的風能文獻搜尋與知識管理
- 多代理協作的研究論文撰寫

---

## 2. 系統架構

系統採用 **6 層代理階層 (6-Tier Agent Hierarchy)**：

| 層級 | 命名空間 | 職責 | 代理數量 |
|------|----------|------|----------|
| **Tier 1 — Leadership** | `wLab:` | 專案統籌、任務分派、進度追蹤 | 4 |
| **Tier 2 — Data Engineering** | `wData:` | 資料蒐集、清洗、ETL pipeline、資料驗證 | 8 |
| **Tier 3 — AI/ML** | `wAI:` | 模型訓練、實驗追蹤、超參數調整、推論部署 | 10 |
| **Tier 4 — Domain Knowledge** | `wDomain:` | 風力發電領域知識、IEC 標準、法規合規 | 6 |
| **Tier 5 — Software Engineering** | `wEng:` | 後端/前端開發、CI/CD、基礎設施管理 | 8 |
| **Tier 6 — Research & Docs** | `wRes:` | 論文撰寫、文獻管理、報告生成、RAG 知識庫 | 6 |

### 指揮鏈

```
wLab:director (總監)
├── wLab:project-manager (專案經理)
│   ├── wData:* (資料工程團隊)
│   ├── wAI:* (AI/ML 團隊)
│   └── wDomain:* (領域知識團隊)
├── wLab:tech-lead (技術主管)
│   └── wEng:* (軟體工程團隊)
└── wLab:research-lead (研究主管)
    └── wRes:* (研究文件團隊)
```

---

## 3. 代理命名規範

所有代理遵循統一的 namespace convention：

```
{namespace}:{role-name}
```

### Namespace 定義

| Namespace | 全稱 | 範例 |
|-----------|------|------|
| `wLab:` | WindAI Lab Leadership | `wLab:director`, `wLab:project-manager` |
| `wData:` | WindAI Data Engineering | `wData:scada-processor`, `wData:quality-checker` |
| `wAI:` | WindAI AI/ML | `wAI:model-trainer`, `wAI:experiment-tracker` |
| `wDomain:` | WindAI Domain Knowledge | `wDomain:iec-specialist`, `wDomain:wake-analyst` |
| `wEng:` | WindAI Software Engineering | `wEng:backend-dev`, `wEng:frontend-dev` |
| `wRes:` | WindAI Research & Docs | `wRes:paper-writer`, `wRes:rag-curator` |

### 命名規則

- 使用小寫英文，單字間以 hyphen (`-`) 連接
- 名稱須反映代理的主要職責
- 禁止使用底線 (`_`) 或大寫字母
- 每個代理須在 `configs/agents/` 目錄下有對應的 YAML 設定檔

---

## 4. 工作流程規範

### 核心原則

1. **確認後執行 (Confirm Before Execute)**：所有代理在執行任何修改性操作前，**必須**向使用者或上級代理請求確認。
2. **繁體中文輸出**：所有面向使用者的輸出均使用繁體中文，技術術語保留英文原文。
3. **任務追蹤**：每個任務須有明確的 task ID，格式為 `WLAB-{YYYYMMDD}-{seq}`。

### 標準工作流程

```
使用者下達指令
    ↓
wLab:director 接收並分析
    ↓
分派至對應團隊負責代理
    ↓
執行代理擬定執行計畫
    ↓
【等待確認】→ 使用者/上級確認
    ↓
執行任務並回報進度
    ↓
結果回傳至 wLab:director 整合
    ↓
輸出最終結果予使用者
```

### 派工與紀錄文件化（#96）

所有總監派工決策與代理工作執行歷程，**必須**透過下列文件結構保存：

| 文件 | 路徑 | 用途 |
|------|------|------|
| 總索引 | `docs/work-logs/README.md` | 月度派工檔案索引 |
| 派工單 | `docs/work-logs/YYYY-MM/YYYY-MM-DD-allocation.md` | 每日總監派工決策 |
| 工作紀錄 | `docs/work-logs/YYYY-MM/WLAB-YYYYMMDD-NN-{slug}.md` | 單一任務從接案到結案 |
| 派工單模板 | `docs/templates/tmpl-work-assignment.md` | 派工單格式 |
| 工作紀錄模板 | `docs/templates/tmpl-work-record.md` | 任務紀錄格式 |
| 正式報告模板 | `docs/templates/tmpl-formal-report.md` | 對外交付格式（HTML/PDF） |
| **每日工作流 routines** | `docs/routines/daily-workflow.md` | **每日工作流改善機制（拆 session、cursor 快照、續行守則）** |

### 每日工作流 routines（v1.0，2026-04-26 起生效）

執行每日工作流時，**必須**遵循 `docs/routines/daily-workflow.md` 的改善機制：

1. **拆 session（A/B/C）**：避免單回合過載觸發 API Stream idle timeout
   - Session A：Phase 1-3（讀取 + 掃描 + Issue）
   - Session B：Phase 4（主動工作 + 文件產出）
   - Session C：Phase 5-7（更新主要文件 + commit/push + email）
2. **以 `docs/cursor.md` 為段間交接介面**：後段 session 不重讀整篇 daily_report
3. **單回合限制**：≤ 20 個工具呼叫、≤ 250 行 markdown 新增、≤ 2 份新檔案
4. **長文件 ≥ 200 行**：交 subagent 並行產出（如週報、啟動備忘錄）
5. **例行維運日**：採 `tmpl-work-assignment-lite.md`（精簡版，待 4/28 抽出）
6. **失敗續行守則**：若中斷，依 routines 第 8 節步驟恢復；不重做、不 reset

### Slash Commands 分類

系統提供 32 個 slash commands，依功能分類如下：

| 類別 | 指令範例 | 說明 |
|------|----------|------|
| 資料操作 | `/data:load`, `/data:clean`, `/data:validate` | SCADA 資料處理 |
| 模型操作 | `/ai:train`, `/ai:evaluate`, `/ai:deploy` | ML 模型生命週期 |
| 研究工具 | `/res:search`, `/res:summarize`, `/res:cite` | 文獻與論文工具 |
| 系統管理 | `/lab:status`, `/lab:assign`, `/lab:report` | 專案管理 |
| 工程工具 | `/eng:test`, `/eng:build`, `/eng:deploy` | 軟體工程 CI/CD |
| 領域工具 | `/domain:standard`, `/domain:simulate` | 領域知識查詢 |

---

## 5. 技術棧

### Backend

- **語言**：Python 3.11+
- **Web Framework**：FastAPI
- **即時通訊**：WebSocket（代理間通訊與虛擬辦公室即時更新）
- **任務佇列**：Celery + Redis
- **資料庫**：PostgreSQL（結構化資料）、MongoDB（非結構化資料/文件）
- **向量資料庫**：ChromaDB / Qdrant（RAG 知識庫）

### Frontend

- **框架**：React 18 + TypeScript
- **狀態管理**：Zustand
- **UI 元件庫**：Tailwind CSS + shadcn/ui
- **即時更新**：WebSocket client
- **圖表**：Recharts / D3.js（風力資料視覺化）

### MLOps

- **實驗追蹤**：MLflow
- **模型版本管理**：MLflow Model Registry
- **資料版本管理**：DVC (Data Version Control)
- **超參數調整**：Optuna

### 基礎設施

- **容器化**：Docker + Docker Compose
- **CI/CD**：GitHub Actions
- **監控**：Prometheus + Grafana

---

## 6. 目錄結構說明

```
windAILab/
├── configs/          # 設定檔（代理設定、系統參數、環境變數範本）
├── data/             # 資料目錄（原始資料、處理後資料、特徵工程輸出）
├── deployments/      # 部署設定（Docker、K8s manifests、環境設定）
├── docs/             # 專案文件（API 文件、架構設計、使用手冊）
├── frontend/         # React + TypeScript 前端（虛擬辦公室 UI）
├── models/           # 訓練完成的模型檔案與 model artifacts
├── notebooks/        # Jupyter notebooks（探索性分析、實驗記錄）
├── references/       # 參考文獻（論文 PDF、IEC 標準文件）
├── scripts/          # 工具腳本（資料下載、環境初始化、批次處理）
├── src/              # 主要原始碼（後端 API、代理邏輯、ML pipeline）
└── tests/            # 測試程式碼（unit tests、integration tests、e2e tests）
```

### `src/` 內部結構慣例

```
src/
├── agents/           # 代理定義與邏輯
│   ├── leadership/   # wLab: 代理
│   ├── data/         # wData: 代理
│   ├── ai/           # wAI: 代理
│   ├── domain/       # wDomain: 代理
│   ├── engineering/  # wEng: 代理
│   └── research/     # wRes: 代理
├── api/              # FastAPI routes 與 endpoints
├── core/             # 核心模組（設定、日誌、例外處理）
├── models/           # ML 模型定義與訓練邏輯
├── services/         # 業務邏輯層
└── utils/            # 通用工具函式
```

---

## 7. 程式碼規範

### Python 規範

- **Linter**：ruff（取代 flake8 + isort）
- **Formatter**：black（行寬上限 99 字元）
- **型別檢查**：mypy（strict mode）
- **所有函式與方法必須加上 type hints**

```python
# 正確範例
def calculate_power_curve(
    wind_speed: np.ndarray,
    air_density: float = 1.225,
    rotor_diameter: float = 126.0,
) -> pd.DataFrame:
    """計算風機功率曲線。

    Args:
        wind_speed: 風速陣列 (m/s)。
        air_density: 空氣密度 (kg/m³)，預設為海平面標準值。
        rotor_diameter: 轉子直徑 (m)。

    Returns:
        包含風速與對應功率的 DataFrame。
    """
    ...
```

### 程式碼風格要求

- Docstring 使用 Google style，說明文字以繁體中文撰寫
- 變數與函式名稱使用英文 `snake_case`
- Class 名稱使用英文 `PascalCase`
- 常數使用 `UPPER_SNAKE_CASE`
- import 排序：標準庫 → 第三方套件 → 本地模組（由 ruff 自動處理）
- 禁止使用 `Any` 型別，除非有明確理由並加上 `# type: ignore` 註解說明

### 預提交檢查 (Pre-commit)

```yaml
# 執行順序
1. ruff check --fix     # lint 與自動修正
2. black .              # 格式化
3. mypy src/            # 型別檢查
4. pytest tests/ -x     # 測試（失敗即中止）
```

---

## 8. 資料規範

### SCADA 資料格式

- 標準時間欄位：`timestamp`（ISO 8601 格式，UTC 時區）
- 取樣頻率：預設 10 分鐘平均值
- 必要欄位：`wind_speed`, `power_output`, `rotor_speed`, `blade_pitch_angle`, `nacelle_direction`
- 檔案格式：Parquet（首選）、CSV（相容性備用）

### 感測器資料 (Sensor Data)

- 振動資料取樣率：至少 1 kHz
- SCADA 警報碼須對照 IEC 61400 標準分類
- 所有感測器資料須包含品質標記 (quality flag)：`0=正常`, `1=可疑`, `2=無效`

### 資料處理規則

1. 原始資料 (`data/raw/`) **唯讀**，禁止就地修改
2. 處理後資料存放於 `data/processed/`，須記錄處理步驟的 metadata
3. 特徵工程輸出存放於 `data/features/`
4. 所有資料處理步驟須可重現 (reproducible)，透過 DVC 追蹤 pipeline
5. 敏感資料（風場位置、發電量等商業資訊）**禁止**提交至版本控制

### 資料命名慣例

```
{wind_farm_id}_{data_type}_{start_date}_{end_date}.parquet
# 範例：WF001_scada_20240101_20240331.parquet
```

---

## 9. 整合規則

### 與 iWrite 代理系統整合

WindAI 代理與既有的 iWrite 代理系統共存，整合規則如下：

- **命名空間隔離**：WindAI 代理使用 `w` 開頭的 namespace（`wLab:`, `wData:` 等），與 iWrite 系統的命名空間互不衝突
- **共用基礎設施**：共用 message bus 與 task queue，透過 namespace prefix 路由訊息
- **跨系統呼叫**：WindAI 代理可透過標準化 API 呼叫 iWrite 代理的寫作功能（如論文潤稿、翻譯）
- **權限管理**：跨系統呼叫須經由各自的 Leadership 層級代理授權

### 與 PLC 代理整合

- WindAI 的 `wData:` 代理可透過 OPC UA protocol 接收 PLC 代理轉發的即時資料
- PLC 資料流入 WindAI 系統前須經過 `wData:quality-checker` 驗證
- 即時控制指令（如降載、停機）**禁止**由 WindAI 代理直接發送，必須透過 PLC 代理執行

### 訊息格式

代理間通訊使用統一的 JSON 格式：

```json
{
  "message_id": "msg-uuid",
  "from": "wAI:model-trainer",
  "to": "wLab:project-manager",
  "type": "task_complete",
  "payload": { ... },
  "timestamp": "2026-03-24T10:30:00Z"
}
```

---

## 10. 虛擬辦公室

### 概念說明

虛擬辦公室 (Virtual Office) 是 WindAI Lab 的即時協作介面，以視覺化方式呈現所有 42 個代理的狀態與互動。使用者可透過 React 前端即時監控代理活動、下達指令、檢視任務進度。

### 代理狀態 (Agent Status)

| 狀態 | 英文 | 圖示顏色 | 說明 |
|------|------|----------|------|
| **待命** | Idle | 灰色 | 代理閒置，等待任務指派 |
| **工作中** | Working | 綠色 | 代理正在執行任務 |
| **等待確認** | Awaiting Confirmation | 黃色 | 代理已完成計畫擬定，等待使用者或上級確認 |
| **完成** | Completed | 藍色 | 任務已完成，等待結果被提取 |
| **錯誤** | Error | 紅色 | 執行過程發生錯誤，需人工介入 |

### 辦公室佈局

虛擬辦公室依團隊劃分區域：

```
┌─────────────────────────────────────────────┐
│              Leadership 指揮中心              │
│  wLab:director  wLab:project-manager  ...   │
├──────────────┬──────────────┬───────────────┤
│  Data Eng.   │   AI/ML      │  Domain       │
│  資料工程室   │  模型實驗室   │  領域知識庫    │
│  wData:*     │  wAI:*       │  wDomain:*    │
├──────────────┴──────────────┴───────────────┤
│  Software Eng. 軟體工程室  │  Research 研究室 │
│  wEng:*                   │  wRes:*         │
└───────────────────────────┴─────────────────┘
```

### 即時功能

- **WebSocket 推播**：代理狀態變更、任務進度即時更新至前端
- **訊息流 (Message Feed)**：顯示代理間的通訊記錄，可依 namespace 篩選
- **任務看板 (Task Board)**：Kanban 風格的任務追蹤面板
- **代理對話 (Agent Chat)**：使用者可直接與特定代理對話互動
- **儀表板 (Dashboard)**：系統資源使用狀況、模型訓練進度、資料處理統計
