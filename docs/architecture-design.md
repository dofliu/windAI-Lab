# WindAI Lab — 系統架構設計文件

> 版本：2.0 | 最後更新：2026-03-26
> 本文件描述 WindAI Lab 的完整系統架構，包含已完成與規劃中的設計。

---

## 1. 設計目標

建立一個**可擴展的風力發電 AI 研究平台**，能夠：
- 接受**任意格式**的風場資料（不限特定風機型號或資料來源）
- 透過**獨立技能模組**執行各類分析（資料清洗、特徵工程、ML 訓練等）
- 代理人**按需聘用/解聘**，不綁定固定團隊規模
- 新增分析能力只需**寫一個技能模組 + 一個 YAML 檔**

---

## 2. 系統總覽

```
┌─────────────────────────────────────────────────────────────────┐
│                      使用者介面 (React)                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │虛擬辦公室│ │SCADA 面板│ │ML Pipeline│ │人事管理  │          │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘          │
│       └────────────┴────────────┴─────────────┘                │
│                          │ WebSocket                            │
├──────────────────────────┼──────────────────────────────────────┤
│                     FastAPI 後端                                │
│  ┌──────────┐  ┌─────────────┐  ┌────────────────────┐        │
│  │REST API  │  │ WebSocket   │  │ FileWatcher        │        │
│  │端點      │  │ 即時推播    │  │ 檔案自動偵測       │        │
│  └────┬─────┘  └──────┬──────┘  └────────┬───────────┘        │
│       └───────────────┴─────────────────┘                      │
│                          │                                      │
│  ┌───────────────────────┼───────────────────────────────────┐ │
│  │              DynamicAgentRegistry                         │ │
│  │  ┌────────────┐  ┌──────────────┐  ┌────────────────┐    │ │
│  │  │ YAML 定義  │  │ Agent 實例   │  │ hire/fire/     │    │ │
│  │  │ (22 個)    │  │ (12 core)    │  │ upgrade API    │    │ │
│  │  └────────────┘  └──────┬───────┘  └────────────────┘    │ │
│  └─────────────────────────┼─────────────────────────────────┘ │
│                            │                                    │
│  ┌─────────────────────────┼─────────────────────────────────┐ │
│  │         SkillComposingAgent（通用代理）                    │ │
│  │                         │                                  │ │
│  │  task_routing:  "diagnose" → [skill1, skill2, skill3]     │ │
│  │                         │                                  │ │
│  │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐       │ │
│  │  │skill │→│skill │→│skill │→│skill │→│skill │       │ │
│  │  │  1   │  │  2   │  │  3   │  │  4   │  │  5   │       │ │
│  │  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘       │ │
│  │  (SkillRegistry: 6 個已實作，自動發現)                     │ │
│  └───────────────────────────────────────────────────────────┘ │
│                            │                                    │
│  ┌─────────────────────────┼─────────────────────────────────┐ │
│  │                   底層模組（不變）                          │ │
│  │  smart_loader │ scada_cleaner │ wind_features │ ML models │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 核心架構：技能 → 代理 → 管線

### 3.1 技能 (Skill) — 最小工作單元

```python
# 每個技能是獨立的、可重用的、有標準介面的模組
class BaseSkill(ABC):
    skill_id: str          # "scada_ingestion"
    display_name: str      # "SCADA 資料載入"

    async def execute(self, inp: SkillInput, progress_cb=None) -> SkillOutput
```

**關鍵設計**：技能之間透過 `SkillInput.dataframe` 傳遞 DataFrame，形成管線。

```
SkillInput(parameters, dataframe) → Skill.execute() → SkillOutput(data, dataframe, summary)
                                                              ↓
                                              下一個 Skill 的 SkillInput.dataframe
```

### 3.2 代理 (Agent) — 技能的組合者

```yaml
# configs/agents/registry/fault-diagnostician.yaml
id: "fault-diagnostician"
skills: ["scada_ingestion", "scada_cleaning", "domain_feature_extraction", "fault_classification"]
task_routing:
  - match: ["diagnose", "診斷"]
    pipeline: ["scada_ingestion", "scada_cleaning", "domain_feature_extraction", "fault_classification"]
```

代理本身**沒有邏輯**，只是宣告「我有哪些技能」和「什麼任務用哪些技能」。
`SkillComposingAgent` 通用 class 根據 YAML 自動執行技能管線。

### 3.3 管線 (Pipeline) — 技能的執行序列

```
使用者: "diagnose Kelmarsh_1"
    ↓ SkillComposingAgent._match_route("diagnose")
    ↓ pipeline: ["scada_ingestion", "scada_cleaning", "domain_feature_extraction", "fault_classification"]
    ↓
[scada_ingestion] → 52,416 筆 SCADA → DataFrame
    ↓ DataFrame 傳遞
[scada_cleaning] → 去重 + 插值 + 異常過濾 → cleaned DataFrame
    ↓ DataFrame 傳遞
[domain_feature_extraction] → +5 個特徵欄位 → enriched DataFrame
    ↓ DataFrame 傳遞
[fault_classification] → F1 Macro: 1.0000 → TaskResult
```

---

## 4. 資料流程與已知限制

### 4.1 當前資料流程

```
任意 CSV/Parquet/ZIP
    ↓ smart_loader（自動偵測格式與欄位）
    ↓ _normalize(): 去除前綴 H05|、單位 (kW) 等
    ↓
DataFrame（原始欄位名保留）
    ↓ scada_cleaner（去重、插值、異常過濾）
    ↓ _find_column(): 模糊匹配 wind_speed、power 等
    ↓
DataFrame（清洗後）
    ↓ wind_features（領域特徵工程）
    ↓ 新增: power_curve_deviation, capacity_factor, temp_delta 等
    ↓
DataFrame（含特徵）
    ↓ 分支至不同 ML 技能
    ├─→ fault_classification → F1 Macro
    ├─→ nbm_training → R², MAE
    └─→ rul_prediction → 退化趨勢, RUL 預估
```

### 4.2 已知的 Kelmarsh 綁定問題

以下參數**硬編碼為 Senvion MM92 風機**，需要參數化：

| 參數 | 硬編碼值 | 出現位置 | 影響 |
|------|---------|---------|------|
| 額定功率 | 2050 kW | scada_cleaner, wind_features, power_curve_nbm | 異常閾值、正規化、過濾 |
| 轉子直徑 | 92 m | wind_features | 葉尖速度比計算 |
| 額定風速 | 12.5 m/s | wind_features | 理論功率曲線公式 |
| 切入風速 | 3.0 m/s | 全部 | 正常運轉過濾 |
| 切出風速 | 25.0 m/s | 全部 | 正常運轉過濾 |
| 取樣頻率 | 10 分鐘 | wind_features (rolling=144) | 滾動視窗大小 |

### 4.3 不支援的資料類型

| 資料類型 | 目前狀態 | 需要什麼 |
|---------|---------|---------|
| 警報事件清單（非時間序列） | ❌ 不支援 | 事件 → 時間序列轉換技能 |
| 不同取樣頻率（1 秒 / 1 小時） | ⚠️ 部分 | 自適應滾動視窗 |
| 無風速/功率的資料 | ⚠️ 部分 | 通用特徵分析（不依賴特定欄位） |
| 故障標籤資料（已標記） | ❌ 不支援 | 有監督訓練技能 |
| 多風機比較分析 | ❌ 不支援 | 跨風機分析技能 |

---

## 5. 規劃中的改進

### 5.1 風機參數自動推斷

```python
# 新增技能: turbine_profiler
class TurbineProfilerSkill(BaseSkill):
    """從資料自動推斷風機參數，不需手動輸入。"""

    async def execute(self, inp):
        df = inp.dataframe
        return SkillOutput(data={
            "rated_power": df[power_col].quantile(0.98),      # 從資料推斷
            "cut_in_speed": estimate_cut_in(df),               # 從功率曲線拐點推斷
            "cut_out_speed": df[ws_col].quantile(0.995),       # 從資料推斷
            "sampling_interval": infer_sampling_rate(df.index), # 從索引推斷
        })
```

### 5.2 通用特徵分析技能（不依賴特定欄位）

```python
# 新增技能: auto_feature_analysis
class AutoFeatureAnalysisSkill(BaseSkill):
    """對任意 DataFrame 執行特徵分析，不預設欄位名稱。"""

    async def execute(self, inp):
        df = inp.dataframe
        # 1. 所有數值欄位的基本統計
        # 2. 欄位間相關性矩陣
        # 3. 缺失值分佈
        # 4. 異常值偵測（Z-score / IQR）
        # 5. 時間趨勢分析（如果有時間索引）
        # 6. 特徵重要度（如果有目標欄位）
```

### 5.3 警報事件處理技能

```python
# 新增技能: alarm_processor
class AlarmProcessorSkill(BaseSkill):
    """將警報事件清單轉換為時間序列特徵。"""

    async def execute(self, inp):
        # 輸入: 事件清單 (timestamp, alarm_code, duration)
        # 輸出: 時間序列 DataFrame
        #   - alarm_count_per_day: 每日警報次數
        #   - alarm_duration_per_day: 每日警報持續時間
        #   - alarm_type_encoded: 警報類型 one-hot 編碼
        #   - mtbf: 平均故障間隔時間
```

### 5.4 自適應取樣頻率

```python
# 改進: scada_cleaning 和 wind_features 的滾動視窗
def _adaptive_rolling_window(df, target_hours=24):
    """根據實際取樣頻率計算滾動視窗大小。"""
    if isinstance(df.index, pd.DatetimeIndex):
        median_interval = df.index.to_series().diff().median()
        records_per_hour = pd.Timedelta(hours=1) / median_interval
        return int(records_per_hour * target_hours)
    return 144  # 預設: 10 分鐘取樣
```

---

## 6. 聘用制度

### 6.1 代理生命週期

```
YAML 定義（configs/agents/registry/xxx.yaml）
    ↓ DynamicAgentRegistry.load_specs()
    ↓
AgentSpec（定義）→ 狀態: offline
    ↓ bootstrap_core() or hire()
    ↓
SkillComposingAgent（實例）→ 狀態: idle
    ↓ execute_command()
    ↓
Working → Completed → idle
    ↓ fire()
    ↓
AgentSpec（保留）→ 狀態: offline（可重新聘用）
```

### 6.2 新增代理步驟

```bash
# 1. 寫 YAML
cat > configs/agents/registry/my-agent.yaml << 'EOF'
id: "my-agent"
name: "wAI:my-agent"
display_name: "我的代理"
tier: "ai-ml"
color: "#8b5cf6"
icon: "🤖"
core: false
skills: ["scada_ingestion", "scada_cleaning", "my_custom_skill"]
task_routing:
  - match: ["分析", "analyze"]
    pipeline: ["scada_ingestion", "scada_cleaning", "my_custom_skill"]
EOF

# 2. 重啟後端 → 出現在「可聘用人員」清單
# 3. 點「聘用」或 POST /api/agents/hire?agent_id=my-agent
```

### 6.3 新增技能步驟

```python
# 1. 在 src/skills/ 下建立檔案
# src/skills/ml/my_custom_skill.py
class MyCustomSkill(BaseSkill):
    skill_id = "my_custom_skill"
    display_name = "我的技能"

    async def execute(self, inp, progress_cb=None):
        df = inp.dataframe
        # ... 你的邏輯
        return SkillOutput(status=SkillStatus.SUCCESS, data={...}, dataframe=df)

# 2. SkillRegistry.auto_discover() 自動發現（重啟即可）
```

---

## 7. 目錄結構

```
windAILab/
├── configs/agents/registry/     # YAML 代理定義（一人一檔）
│   ├── scada-processor.yaml     # core: true
│   ├── fault-diagnostician.yaml # core: true
│   ├── wake-analyst.yaml        # core: false (可聘用)
│   └── ...
│
├── src/
│   ├── skills/                  # 技能模組（獨立、可重用）
│   │   ├── base.py              # BaseSkill, SkillInput, SkillOutput
│   │   ├── registry.py          # SkillRegistry（自動發現）
│   │   ├── data/                # 資料處理技能
│   │   ├── ml/                  # ML 模型技能
│   │   ├── features/            # 特徵工程技能
│   │   └── reporting/           # 報告生成技能
│   │
│   ├── agents/                  # 代理框架
│   │   ├── base.py              # BaseAgent（不變）
│   │   ├── skill_composing_agent.py  # 通用技能組合代理
│   │   ├── dynamic_registry.py  # 統一註冊表（hire/fire）
│   │   └── orchestrator/        # 工作流程引擎
│   │
│   ├── data_pipeline/           # 底層資料處理
│   │   ├── ingestion/smart_loader.py  # 通用資料載入
│   │   └── cleaning/scada_cleaner.py  # SCADA 清洗
│   │
│   ├── models/                  # ML 模型
│   │   ├── nbm/power_curve_nbm.py
│   │   ├── classification/fault_classifier.py
│   │   └── degradation/rul_model.py
│   │
│   ├── features/                # 特徵工程
│   │   └── domain_features/wind_features.py
│   │
│   ├── services/                # 服務
│   │   └── file_watcher.py      # 檔案自動監控
│   │
│   └── api/                     # FastAPI
│       ├── main.py
│       └── websocket_manager.py
│
└── frontend/src/
    ├── renderers/               # ★ 可插拔辦公室 Renderer 架構
    │   ├── types.ts             # OfficeRendererDefinition 介面
    │   ├── registry.ts          # registerRenderer / getRenderer
    │   ├── pixel/               # 🎮 像素風格（原 OfficeWorld 封裝）
    │   ├── modern/              # ◉ 現代企業風（Glassmorphism + 光暈）
    │   └── minimal/             # ◻ 極簡白板風（手繪虛線 + 便利貼）
    ├── themes/
    │   ├── theme.ts             # WindAITheme（含 visualStyle 欄位）
    │   └── ThemeProvider.tsx     # React Context + localStorage
    ├── components/
    │   ├── OfficeWorld.tsx       # 虛擬辦公室（像素風 renderer 用）
    │   ├── AgentManagement.tsx   # 人事管理面板
    │   ├── ThemeSwitcher.tsx     # 依風格分組的主題切換器
    │   ├── FileWatcherStatus.tsx # 檔案監控狀態
    │   └── ...
    └── hooks/
        ├── useAgentSimulation.ts # 模擬模式
        └── useWebSocket.ts       # 後端連線
```

---

## 8. API 端點一覽

### 代理管理
| 方法 | 端點 | 說明 |
|------|------|------|
| GET | `/api/agents` | 所有代理狀態 |
| GET | `/api/agents/available` | 可聘用清單 |
| POST | `/api/agents/hire?agent_id=xxx` | 聘用代理 |
| POST | `/api/agents/fire?agent_id=xxx` | 解聘代理 |
| GET | `/api/skills` | 所有技能清單 |

### 指令執行（統一 Workflow 路由）

所有指令走同一條路徑：`AVAILABLE_WORKFLOWS[command] → Workflow → OrchestrationEngine`
引擎自動偵測代理是否有真實實例，有則走 skill pipeline，無則播放模擬動畫。

| 指令 | 說明 | 真實執行時的技能管線 |
|------|------|---------|
| `diagnose` | 故障診斷 | ingestion → profiler → cleaning → features → classification → nbm |
| `train-nbm` | NBM 訓練 | ingestion → profiler → cleaning → features → nbm |
| `predict-rul` | RUL 預測 | ingestion → profiler → cleaning → features → rul |
| `data:load` | 資料載入 | scada_ingestion |
| `data:clean` | 資料清洗 | scada_cleaning |
| `ai:train` | 模型訓練 | 平行：fault + NBM + RUL |
| `ai:evaluate` | 模型評估 | 平行：fault + RUL |
| `lit-search` | 文獻搜索 | 模擬（無真實 skill） |

### 檔案監控
| 方法 | 端點 | 說明 |
|------|------|------|
| POST | `/api/file-watcher/start` | 啟動監控 |
| POST | `/api/file-watcher/stop` | 停止監控 |
| POST | `/api/file-watcher/scan` | 強制掃描 |
| GET | `/api/file-watcher/status` | 監控狀態 |

---

## 9. 下一步規劃

### 第一優先：解除 Kelmarsh 綁定

| 工作項目 | 內容 |
|---------|------|
| `TurbineProfiler` 技能 | 自動從資料推斷風機參數 |
| 參數化所有閾值 | rated_power 等改為 SkillInput 參數 |
| 自適應滾動視窗 | 根據取樣頻率自動調整 |

### 第二優先：新增資料類型支援

| 工作項目 | 內容 |
|---------|------|
| `AlarmProcessor` 技能 | 警報事件 → 時間序列轉換 |
| `AutoFeatureAnalysis` 技能 | 通用特徵分析（不預設欄位） |
| `SupervisedTrainer` 技能 | 有標籤資料的監督式訓練 |

### 第三優先：前端強化

| 工作項目 | 內容 |
|---------|------|
| 技能管線進度即時顯示 | 每個步驟的進度條 |
| 風機健康總覽 Dashboard | 多風機狀態卡片 |
| 分析結果視覺化 | 互動式圖表 |
