# WindAI Lab — TODO 路線圖與下一步工作規劃

> 最後更新：2026-04-02
> 目前���度：Phase 10 完成 — Checkpoint 機制 + 錯誤重試/降級（92%）

---

## 1. 當前狀態摘要

```
已完成 ██████████████████░░ 92%
                                      ↑ 我們在這裡
Phase:  1  2  3  4  5  5.5  6a  6b  6c  7  8  9  10    11  12
        ✅ ✅ ✅ ✅ ✅  ✅   ✅  ✅   ✅  ✅  ✅  ✅  ✅  ←→  ⬜   ⬜
```

| 類別 | 已完成 | 剩餘 |
|------|--------|------|
| 核心代理 | 12 | 0 |
| 可聘用代理 | 10 (YAML 定義) | 按需新增 |
| 技能模組 | 10 | 2-3 |
| ML 模型 | 3 | 3+ |
| API 端點 | 30+ | 5+ |
| 前端元件 | 28 | 3+ |
| Office Renderer | 3（pixel / modern / minimal） | 可擴充 |

### 架構狀態

| 系統 | 狀態 | 說明 |
|------|------|------|
| 舊系統（42 人固定） | ⚠️ 並行中 | 仍在運行，待切換 |
| 新系統（12 核心 + 聘用制） | ✅ 就緒 | DynamicRegistry + Skills + YAML |

---

## 2. 待辦事項

### ✅ 已完成 — Phase 9 成果

| 項目 | 說明 | 狀態 |
|------|------|------|
| ~~解除 Kelmarsh 硬編碼~~ | TurbineProfile 統一風機參數傳遞 | ✅ |
| ~~多檔案批次載入~~ | DataInspectorSkill + BatchLoadSkill | ✅ |
| ~~自動實驗技能~~ | AutoExperimentSkill（網格搜尋 + 排行榜） | ✅ |
| ~~警報事件處理~~ | AlarmProcessorSkill（事件→時間序列） | ✅ |

### ✅ 已完成 / 🔧 進行中 — Phase 10：UI 抽象層 + Workflow 統一架構

| 項目 | 說明 | 狀態 |
|------|------|------|
| ~~OfficeRenderer 介面~~ | 定義 OfficeViewProps / CompactViewProps / OfficeRendererDefinition | ✅ |
| ~~Renderer Registry~~ | registerRenderer / getRenderer / getAllRenderers | ✅ |
| ~~Pixel Renderer 封裝~~ | 現有 OfficeWorld + CompactOffice 封裝為可插拔 renderer | ✅ |
| ~~Modern Renderer~~ | Glassmorphism + 圓形 Avatar + 光暈動效 — 全新視覺風格 | ✅ |
| ~~Minimal Renderer~~ | 白板虛線框 + 便利貼 + 純文字大留白 — 全新視覺風格 | ✅ |
| ~~Theme visualStyle~~ | WindAITheme 擴展 visualStyle 欄位，主題綁定 renderer | ✅ |
| ~~ThemeSwitcher 升級~~ | 依 visualStyle 分組顯示，色塊 + 風格圖示預覽 | ✅ |
| ~~App.tsx 解耦~~ | 不再直接 import 特定 renderer，動態從 registry 取得 | ✅ |
| ~~Workflow 統一架構~~ | WorkflowStep 擴展 task_template/task_parameters/collaborator_ids | ✅ |
| ~~指令路由統一~~ | 刪除 main.py 硬寫分支，所有指令走 AVAILABLE_WORKFLOWS | ✅ |
| ~~diagnose 真實管線~~ | diagnose 指令自動偵測真實代理，走 skill pipeline | ✅ |
| ~~train-nbm / predict-rul~~ | 新增為獨立 Workflow，走統一路由 | ✅ |
| ~~real_workflows.py 棄用~~ | 標記 deprecated，不再被 import | ✅ |
| 更多 Renderer 風格 | 等距 3D / 賽博龐克 / 日系手繪 等（未來擴展） | ⬜ |
| ~~總監 Checkpoint 機制~~ | CheckpointConfig + 品質規則 + 自動調參重跑 | ✅ |
| ~~錯誤重試/降級~~ | RetryConfig + 指數退避 + SKIP/FALLBACK/ABORT 三策略 | ✅ |

### 🔴 高優先 — RAG 知識庫

| 項目 | 說明 | 預估 |
|------|------|------|
| **RAG 文件向量嵌入** | BGE-3 本地嵌入模型 + ChromaDB | 3-4h |
| **文件 chunking 策略** | PDF → 段落分割 → 嵌入 → 存儲 | 2h |
| **檢索 API 端點** | 查詢介面 + 結果格式化 | 2h |

### 🔴 高優先 — 前端戰情中心

| 項目 | 說明 | 預估 |
|------|------|------|
| **MissionView 戰情中心** | 任務進行時自動切換，只顯示參與代理 | 4h |
| **AnalysisDashboard 分析面板** | 右側即時圖表 + 報告清單（可點擊展開） | 4-6h |
| **ViewSwitcher 自動切換** | 偵測任務狀態 office ↔ mission 切換 | 1-2h |
| ~~主題系統 Theme Pack~~ | ~~頭像/圖標/配色/底圖獨立可替換~~ → **已由 Renderer 架構取代** | ✅ |

### 🟡 中優先 — 技能深化

| 項目 | 說明 | 預估 |
|------|------|------|
| **統計異常偵測技能** | Z-score/IQR/IsolationForest 包裝為 skill | 1h |
| **報告生成技能** | Markdown 報告自動產出 skill | 1h |
| Weibull 風速分佈擬合 | 風資源評估基礎 | 2h |
| LSTM 時序預測 | 風速/功率短期預測 | 4-6h |

### 🟢 低優先 — 工程基礎

| 項目 | 說明 | 預估 |
|------|------|------|
| SQLite/PostgreSQL 持久化 | 任務記錄 + 工作日誌 | 4-6h |
| Slash Commands 實作 | /data:load, /ai:train 等前端指令 | 3-4h |

---

## 3. 新增代理方式（新制）

不再需要改程式碼，只需：

```yaml
# 1. 建立 configs/agents/registry/my-new-agent.yaml
id: "my-new-agent"
name: "wAI:my-new-agent"
display_name: "我的新代理"
tier: "ai-ml"
color: "#8b5cf6"
icon: "🤖"
core: false
skills: ["scada_ingestion", "scada_cleaning"]
task_routing:
  - match: ["分析"]
    pipeline: ["scada_ingestion", "scada_cleaning"]
```

```bash
# 2. 重啟後端 or 呼叫 API
curl -X POST "http://localhost:8000/api/agents/hire?agent_id=my-new-agent"
```

### 新增技能方式

```python
# 1. 建立 src/skills/ml/my_skill.py
class MySkill(BaseSkill):
    skill_id = "my_skill"
    display_name = "我的技能"

    async def execute(self, inp, progress_cb=None):
        # 你的邏輯
        return SkillOutput(status=SkillStatus.SUCCESS, data={...})
```

技能會被 `SkillRegistry.auto_discover()` 自動發現並註冊。

---

## 4. 建議的下一步順序

1. ~~**主題系統**~~ → ✅ 已完成（Phase 10 Renderer 架構）
2. ~~**Workflow 統一架構**~~ → ✅ 已完成（Phase 10 指令路由統一）
3. ~~**總監 Checkpoint 機制**~~ → ✅ 已完成（CheckpointConfig + 品質規則 + 自動調參重跑）
4. ~~**錯誤重試/降級**~~ → ✅ 已完成（RetryConfig + 指數退避 + 三種降級策略 + 前端即時顯示）
5. **RAG 知識庫**（BGE-3 嵌入 + ChromaDB + 風機手冊）
6. **戰情中心介面**（MissionView + AnalysisDashboard + ViewSwitcher）
7. **擴展更多 Renderer**（等距 3D / 賽博龐克 / 自定義風格）
8. **補齊剩餘技能**（異常偵測、報告生成）
9. **新 ML 模型**（Weibull + LSTM）
