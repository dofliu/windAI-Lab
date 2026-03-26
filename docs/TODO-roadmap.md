# WindAI Lab — TODO 路線圖與下一步工作規劃

> 最後更新：2026-03-25
> 目前進度：Phase 7 完成 — 架構重構完成，進入功能深化階段（75%）

---

## 1. 當前狀態摘要

```
已完成 ███████████████░░░░░ 75%
                                  ↑ 我們在這裡
Phase:  1  2  3  4  5  5.5  6a  6b  6c  7 ←→ 8  9
        ✅ ✅ ✅ ✅ ✅  ✅   ✅  ✅   ✅  ✅     ⬜  ⬜
```

| 類別 | 已完成 | 剩餘 |
|------|--------|------|
| 核心代理 | 12 | 0 |
| 可聘用代理 | 10 (YAML 定義) | 按需新增 |
| 技能模組 | 6 | 4-6 |
| ML 模型 | 3 | 3+ |
| API 端點 | 30+ | 5+ |
| 前端元件 | 23 | 3+ |

### 架構狀態

| 系統 | 狀態 | 說明 |
|------|------|------|
| 舊系統（42 人固定） | ⚠️ 並行中 | 仍在運行，待切換 |
| 新系統（12 核心 + 聘用制） | ✅ 就緒 | DynamicRegistry + Skills + YAML |

---

## 2. 待辦事項

### 🔴 高優先 — 架構切換

| 項目 | 說明 | 預估 |
|------|------|------|
| **切換至新架構** | 舊 agent_registry → DynamicAgentRegistry 為主 | 2-3h |
| **前端動態載入** | mockData 42 人 → 後端 API 動態取得 | 2h |
| **模擬模式整合** | 模擬模式讀取 YAML 定義的代理清單 | 1-2h |

### 🔴 高優先 — 技能深化

| 項目 | 說明 | 預估 |
|------|------|------|
| **自動特徵分析技能** | 接入 auto_feature_analysis 為獨立 skill | 1h |
| **資料品質評估技能** | 獨立的品質報告生成 skill | 1h |
| **統計異常偵測技能** | Z-score/IQR/IsolationForest 包裝為 skill | 1h |
| **報告生成技能** | Markdown 報告自動產出 skill | 1h |

### 🟡 中優先 — 前端增強

| 項目 | 說明 | 預估 |
|------|------|------|
| **SCADA 散佈圖 NaN 修復** | 前端功率曲線圖「無散佈圖資料」問題 | 1h |
| **風機健康總覽 Dashboard** | 多風機狀態卡片式總覽 | 4h |
| **代理工作進度即時追蹤** | 真實技能管線進度條 | 2h |
| **人事管理面板強化** | 解聘按鈕、技能更新 UI、代理詳情 | 2h |

### 🟡 中優先 — 新增技能/模型

| 項目 | 說明 | 預估 |
|------|------|------|
| Weibull 風速分佈擬合 | 風資源評估基礎 | 2h |
| LSTM 時序預測 | 風速/功率短期預測 | 4-6h |
| Autoencoder 異常偵測 | 無監督異常偵測 | 3-4h |

### 🟢 低優先 — 工程基礎

| 項目 | 說明 | 預估 |
|------|------|------|
| CI/CD Pipeline | GitHub Actions（lint + test + build） | 3h |
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

1. **切換至新架構**（讓人事管理面板真正生效）
2. **補齊 4 個技能**（特徵分析、品質評估、異常偵測、報告）
3. **SCADA 前端修復**（散佈圖 + 趨勢圖 NaN 問題）
4. **風機健康總覽 Dashboard**（多風機狀態卡片）
5. **Weibull + LSTM 新模型**
