# WindAI Lab — Claude 工作守則

> 給 Claude 在這個 repo 工作時用的精簡指引。專案完整介紹見 `README.md`、現況見 `docs/PROJECT-STATUS.md`、近況見 `docs/daily_report.md`。

## 1. 專案一句話

風力發電 AI 研究協作平台：多代理 + 技能模組 + 虛擬辦公室 UI，協助風場資料清洗、模型訓練、診斷報告產出。Python 3.11 後端 (FastAPI) + React TS 前端。

## 2. 真實 agent / command 清單

**6 個團隊、25 個 Python agent**（檔案位於 `src/agents/{tier}/`）：

| Tier | 路徑 | Agent 檔名 (去 .py) |
|---|---|---|
| Leadership | `src/agents/leadership/` | director, project_manager, research_lead, tech_lead |
| Data | `src/agents/data/` | scada_processor, quality_checker, etl_engineer |
| AI/ML | `src/agents/ai/` | anomaly_detector, experiment_tracker, fault_diagnostician, feature_engineer, hyperparameter_tuner, predictive_modeler, rag_architect |
| Domain | `src/agents/domain/` | maintenance_planner, power_curve_expert, wake_analyst |
| Engineering | `src/agents/engineering/` | backend_dev, devops_engineer, frontend_dev, test_engineer |
| Research | `src/agents/research/` | literature_reviewer, paper_writer, rag_curator, report_generator |

註：`src/agents/` 下還有共用基礎設施 `base.py`、`registry.py`、`dynamic_registry.py`、`message_bus.py`、`skill_composing_agent.py`、`orchestrator/`，不算單一 agent。

**Claude Code sub-agent (8 個)**：`.claude/agents/{leadership,ai-ml,research-docs}/*.md`
**Slash commands (5 個)**：`/build-rag`, `/diagnose`, `/lit-search`, `/onboard-student`, `/write-paper`（定義於 `.claude/commands/`）

## 3. 開發環境與常用指令

```bash
# 安裝
pip install -r requirements.txt

# Lint / Format / Type check（pre-commit 會跑這順序）
ruff check --fix .
black .
mypy src/

# 測試
pytest                    # 全部
pytest tests/unit/ -x     # 單元測試，遇錯即停
pytest -k "scada"         # 篩名稱

# 啟動服務
uvicorn src.api.main:app --reload    # backend
cd frontend && npm run dev           # frontend
```

工具設定均在 `pyproject.toml`：ruff line-length=99、mypy strict、pytest asyncio。

## 4. Coding 規範（精簡）

- Python：所有 def/method 加 type hints；docstring 用 Google style，說明文字繁中
- 命名：變數/函式 `snake_case`、Class `PascalCase`、常數 `UPPER_SNAKE_CASE`
- 禁止 `Any` 型別（必要時加 `# type: ignore` 並註明原因）
- 對使用者輸出用繁體中文，技術術語保留英文
- 修改檔案前先 Read；遇到舊檔有 CRLF 行尾，照原樣保留別動

## 5. Git / PR 工作流

- 主分支：`master`（直接 push 前先 `git pull --rebase`）
- Feature 開發：`feat/*`；Claude Code 自動分支：`claude/*`
- Commit 訊息規範：`type(#issue): 描述`，type ∈ {feat, fix, docs, chore, refactor, test}
- 帶 `#issue` 編號可自動關聯 GitHub Issue
- CI 在 `.github/workflows/ci.yml`，PR 必須過 CI

## 6. 任務追蹤與派工紀錄

任務 ID 格式：`WLAB-{YYYYMMDD}-{NN}`。派工/紀錄文件：

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

模板：`docs/templates/tmpl-work-assignment.md`、`tmpl-work-record.md`、`tmpl-formal-report.md`

## 7. 資料規範要點

- SCADA 標準：`timestamp` (ISO 8601 UTC) + 必要欄位 `wind_speed`, `power_output`, `rotor_speed`, `blade_pitch_angle`, `nacelle_direction`，10 分鐘平均
- 檔案格式：Parquet 優先、CSV 備用
- `data/raw/` **唯讀**，處理結果落 `data/processed/` 或 `data/features/`
- 敏感資料（風場座標、發電量）**禁止** commit

## 8. 哪裡找更多資訊

- 完整功能與架構：`README.md`、`docs/architecture-design.md`
- 當前 Phase 與待辦：`docs/PROJECT-STATUS.md`（每週更新）
- 今日進度：`docs/daily_report.md`
- 願景與三步走演進路線：`docs/product-overview.md`
- 已歸檔（不再維護）：`docs/archived/`

---

> 工作前先看 `docs/daily_report.md` 知道現在在做什麼。修改 agent / 技能前先看對應的 `src/agents/` 與 `src/skills/` 模組註解。所有破壞性操作（刪檔、改 schema、跑 migration）執行前須先請使用者確認。
