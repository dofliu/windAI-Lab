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
|---|---|---|
| 索引 | `docs/work-logs/README.md` | 月度索引 |
| 派工單 | `docs/work-logs/YYYY-MM/YYYY-MM-DD-allocation.md` | 每日派工（一天最多 1 份）|
| 工作紀錄 | `docs/work-logs/YYYY-MM/WLAB-YYYYMMDD-NN-{slug}.md` | 任務結案才產一份 |

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
