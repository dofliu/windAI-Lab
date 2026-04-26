# WindAI Lab — 風力發電 AI 研究協作系統

> **版本**：0.1.0 | **最後更新**：2026-04-26 | **進度**：Phase 14 進行中（Step 1 完成 + Epic C ✅ + #64 ✅ + #41 ✅ + #96 派工系統文件層 ✅ + #42 通知渠道設計文件 ✅ + #96 階段二服務層設計 ✅ + 首份正式週報 2026-W17 ✅ + `tmpl-formal-report.md` v1.1 ✅ + **W18 啟動就緒備忘錄 ✅** + **每日工作流 routines 改善 ✅**）

多代理協作平台，結合虛擬辦公室介面與真實 SCADA 資料分析，專為風力發電研究設計。

---

## 系統亮點

- **12 位核心 AI 代理** + 10 位可按需聘用的專家，YAML 驅動、零程式碼新增
- **28 個獨立技能模組**，自動發現、自由組合成分析管線
- **虛擬辦公室 UI**，3 種視覺風格（像素風 / 現代企業 / 極簡白板），即時監控代理狀態
- **真實 SCADA 資料分析**：故障診斷（F1=1.0）、功率曲線建模（R²=0.997）、RUL 預測
- **通用資料載入**：丟入任意 CSV/Parquet，自動偵測欄位、清洗、特徵工程
- **RAG 知識庫**：BGE-3 嵌入 + ChromaDB，風能文獻語意搜尋
- **總監 Checkpoint 機制**：品質規則 + 自動調參重跑 + 錯誤重試/降級

---

## 快速啟動

### 後端

```bash
# 安裝依賴
pip install -r requirements.txt

# 啟動 API 伺服器
uvicorn src.api.main:app --reload
uvicorn src.api.main:app --host 0.0.0.0 --port 5800 --reload

```

### 前端

```bash
cd frontend
npm install
npm run dev
```

### Docker（一鍵啟動）

```bash
docker compose up -d
```

| 服務 | 網址 |
|------|------|
| 前端虛擬辦公室 | <http://localhost:5173> |
| 後端 REST API | <http://localhost:8000> |
| API 互動文件 | <http://localhost:8000/docs> |

---

## 核心架構

```
使用者指令 → 統一 Workflow 路由 → OrchestrationEngine
                                        │
                            DynamicAgentRegistry
                            (12 core + 10 hirable)
                                        │
                          SkillComposingAgent（通用代理）
                            task_routing → 技能管線
                                        │
                    ┌───────┬───────┬───────┬───────┐
                    skill₁  skill₂  skill₃  skill₄  skill₅
                    (SkillRegistry: 12 個技能，自動發現)
                                        │
                              底層模組（不變）
                smart_loader │ scada_cleaner │ ML models
```

### 技能 → 代理 → 管線

| 層級 | 說明 |
|------|------|
| **技能 (Skill)** | 最小工作單元，獨立可重用（如 `scada_ingestion`、`fault_classification`） |
| **代理 (Agent)** | 技能的組合者，由 YAML 定義 skills + task_routing |
| **管線 (Pipeline)** | 技能的執行序列，DataFrame 自動在技能間傳遞 |

### 代理階層

| 層級 | 命名空間 | 職責 |
|------|----------|------|
| Leadership | `wLab:` | 專案統籌、任務分派、Checkpoint 品質控管 |
| Data Engineering | `wData:` | 資料載入、清洗、批次處理、品質驗證 |
| AI/ML | `wAI:` | 模型訓練、故障診斷、異常偵測、超參數調整 |
| Domain Knowledge | `wDomain:` | IEC 標準、尾流模擬、功率曲線分析 |
| Software Engineering | `wEng:` | 後端/前端開發、CI/CD |
| Research & Docs | `wRes:` | 論文撰寫、文獻管理、RAG 知識庫、報告生成 |

---

## 可用指令

在前端 CommandBar 或透過 WebSocket 執行：

| 指令 | 說明 | 技能管線 |
|------|------|----------|
| `diagnose WT-01` | 故障診斷（真實 SCADA） | ingestion → profiler → cleaning → features → classification → nbm |
| `train-nbm WT-01` | NBM 功率曲線訓練 | ingestion → profiler → cleaning → features → nbm |
| `predict-rul WT-01` | RUL 退化預測 | ingestion → profiler → cleaning → features → rul |
| `data:load` | 資料載入 | scada_ingestion |
| `data:clean` | 資料清洗 | scada_cleaning |
| `ai:train` | 全模型訓練 | 平行：fault + NBM + RUL |
| `ai:evaluate` | 模型評估 | 平行：fault + RUL |
| `lit-search 主題` | 文獻搜索 | 模擬動畫 |
| `lab:status` | 系統狀態 | — |

風機 ID 對應：WT-01 ~ WT-06 = Kelmarsh_1 ~ Kelmarsh_6

---

## 技術棧

| 類別 | 技術 |
|------|------|
| **後端** | Python 3.11+, FastAPI, WebSocket, Pydantic v2 |
| **前端** | React 18, TypeScript, Vite, Tailwind CSS |
| **ML/AI** | scikit-learn, XGBoost, PyTorch (LSTM), Optuna |
| **RAG** | ChromaDB, sentence-transformers (BGE-3), LangChain |
| **資料處理** | pandas, NumPy, SciPy (Weibull) |
| **實驗追蹤** | MLflow, JSONL 排行榜 |
| **部署** | Docker Compose |
| **程式碼品質** | ruff, black, mypy (strict), pytest |

---

## 專案結構

```
windAILab/
├── .claude/                        # Claude Code 設定
│   ├── agents/                     # 8 個 AI 代理定義（Claude Code 用）
│   └── commands/                   # 5 個 slash 指令
├── configs/agents/registry/        # YAML 代理定義（一人一檔，22 個）
├── data/
│   ├── external/                   # Kelmarsh SCADA 資料集
│   └── raw/                        # 使用者上傳資料（FileWatcher 監控）
├── docs/                           # 專案文件
│   ├── architecture-design.md      # 系統架構設計
│   ├── progress-report.md          # 開發歷程（Phase 1-10）
│   ├── TODO-roadmap.md             # 路線圖與待辦事項
│   ├── use-cases.md                # 使用場景與範例
│   ├── data-integration-guide.md   # 多來源資料整合指南
│   └── templates/                  # 文件模板（實驗計畫、模型卡等）
├── frontend/src/
│   ├── renderers/                  # 可插拔辦公室 Renderer（pixel/modern/minimal）
│   ├── themes/                     # 主題系統（含 visualStyle 綁定）
│   ├── components/                 # UI 元件（32 個）
│   └── hooks/                      # React hooks
├── src/
│   ├── skills/                     # 技能模組（28 個，自動發現）
│   │   ├── base.py                 # BaseSkill 抽象介面
│   │   ├── registry.py             # SkillRegistry
│   │   ├── data/                   # 資料處理技能
│   │   ├── ml/                     # ML 模型技能
│   │   ├── features/               # 特徵工程技能
│   │   └── reporting/              # 報告生成技能
│   ├── agents/                     # 代理框架
│   │   ├── skill_composing_agent.py  # 通用技能組合代理
│   │   ├── dynamic_registry.py     # 統一註冊表（hire/fire）
│   │   └── orchestrator/           # 工作流程引擎
│   ├── data_pipeline/              # 底層資料處理
│   │   ├── ingestion/smart_loader.py  # 通用資料載入
│   │   └── cleaning/scada_cleaner.py  # SCADA 清洗
│   ├── models/                     # ML 模型
│   │   ├── nbm/power_curve_nbm.py  # 正常行為模型
│   │   ├── classification/         # 故障分類
│   │   └── degradation/            # RUL 退化模型
│   ├── features/                   # 特徵工程
│   ├── services/                   # 業務服務（FileWatcher 等）
│   └── api/                        # FastAPI 後端
│       ├── main.py                 # API 路由 + WebSocket
│       └── websocket_manager.py    # 即時推播管理
├── tests/                          # 測試（32 檔案 / 812 測試）
├── requirements.txt                # Python 依賴
├── pyproject.toml                  # 專案設定（ruff/black/mypy/pytest）
├── Dockerfile                      # 容器化部署
└── CLAUDE.md                       # Claude Code 系統行為規範
```

---

## 新增代理 / 技能（零程式碼）

### 新增代理

```yaml
# configs/agents/registry/my-agent.yaml
id: "my-agent"
name: "wAI:my-agent"
display_name: "我的代理"
tier: "ai-ml"
core: false
skills: ["scada_ingestion", "scada_cleaning", "my_skill"]
task_routing:
  - match: ["分析", "analyze"]
    pipeline: ["scada_ingestion", "scada_cleaning", "my_skill"]
```

```bash
# 聘用
curl -X POST "http://localhost:8000/api/agents/hire?agent_id=my-agent"
```

### 新增技能

```python
# src/skills/ml/my_skill.py
class MySkill(BaseSkill):
    skill_id = "my_skill"
    display_name = "我的技能"

    async def execute(self, inp, progress_cb=None):
        df = inp.dataframe
        # 你的邏輯
        return SkillOutput(status=SkillStatus.SUCCESS, data={...}, dataframe=df)
```

技能會被 `SkillRegistry.auto_discover()` 自動發現並註冊。

---

## 資料來源

### 內建資料集

**Kelmarsh Wind Farm SCADA Dataset** (CC-BY-4.0)

- 6 x Senvion MM92 (2050 kW, 92m rotor)
- 10 分鐘平均值，2016 年全年
- 來源：<https://zenodo.org/records/5841834>

### 使用自己的資料

將 CSV/Parquet 放入 `data/raw/`，系統會自動偵測風速/功率欄位（模糊匹配 60+ 關鍵字）。詳見 [docs/data-integration-guide.md](docs/data-integration-guide.md)。

---

## API 快速測試

```bash
# 查看所有代理狀態
curl http://localhost:8000/api/agents

# 查看可聘用代理
curl http://localhost:8000/api/agents/available

# 查看技能模組
curl http://localhost:8000/api/skills

# 語意搜尋知識庫
curl -X POST http://localhost:8000/api/knowledge-base/search \
  -H "Content-Type: application/json" \
  -d '{"query": "wind turbine fault detection"}'
```

---

## 文件索引

| 文件 | 說明 |
|------|------|
| [CLAUDE.md](CLAUDE.md) | Claude Code 系統行為規範（代理命名、工作流程、程式碼規範） |
| [docs/architecture-design.md](docs/architecture-design.md) | 系統架構設計（技能→代理→管線、聘用制度、API 一覽） |
| [docs/progress-report.md](docs/progress-report.md) | 開發歷程 Phase 1-10 詳細記錄 |
| [docs/TODO-roadmap.md](docs/TODO-roadmap.md) | 路線圖與待辦事項（Phase 11-19 三步走） |
| [docs/FUTURE-ROADMAP.md](docs/FUTURE-ROADMAP.md) | 願景定位：從研究平台到風場運維服務公司 |
| [docs/EVOLUTION-PLAN.md](docs/EVOLUTION-PLAN.md) | 詳細執行計畫（70+ 工作項目，含檔案位置與驗收標準） |
| [docs/PROJECT-STATUS.md](docs/PROJECT-STATUS.md) | 專案現況總覽（一頁式摘要） |
| [docs/use-cases.md](docs/use-cases.md) | 6 大使用場景與操作範例 |
| [docs/data-integration-guide.md](docs/data-integration-guide.md) | 多來源資料整合指南 |
| [docs/work-logs/README.md](docs/work-logs/README.md) | 總監派工與工作紀錄總索引（#96） |
| [docs/templates/](docs/templates/) | 文件模板（派工單 / 工作紀錄 / 正式報告 / 論文 / 實驗計畫） |

---

## 授權

本專案為研究用途。Kelmarsh 資料集授權為 CC-BY-4.0。
