# windAI-Lab Agent Configuration

> 此檔案為 **oh-my-claudecode (OMC)** 在 windAI-Lab 中的代理協作組態。
> 與 `CLAUDE.md`（系統行為規範）互補：CLAUDE.md 描述 6 層 namespace 代理階層；本檔指引 OMC 子代理（agent）與技能（skill）如何在風電運維情境下被組合使用。
>
> 文件版本：v0.1（2026-04-27 OMC 整合啟動）

---

## Project Context

- **Domain**：Wind turbine condition monitoring, fault diagnosis, SCADA analysis, predictive maintenance
- **Primary data**：Kelmarsh Wind Farm SCADA dataset（6 × Senvion MM92, 10-min averages, CC-BY-4.0），路徑 `data/external/`
- **Reference dataset**：Fuhrländer FL2500 SCADA dataset（4 turbines, 312 variables, 572 fault events，研究比對用）
- **Active experiments**：
  - WindGuard AI（LLM 推理 + 自動品質檢查）
  - Epic C ML 模型進化（LSTM v2 + PatchTST + ModelBenchmark）
  - Epic E 告警規則引擎（#41 ✅ / #42 設計 ✅）
  - 派工系統 #96（階段二 SQLite + AllocationEngine）
- **Target journals**：Applied Energy, Advanced Engineering Informatics, IEEE Access, Renewable Energy
- **Hackathon deadline**：2026-05-18（剩 21 天）

---

## Preferred Agent Workflow

OMC agent 與本專案 6 層命名空間的對應建議：

### 研究類任務（資料分析、實驗設計、論文）

```
explore → analyst → scientist → critic → executor → verifier
```

對應到 windAI-Lab：

| OMC agent | windAI namespace | 場景 |
|-----------|------------------|------|
| explore | wData:scada-processor | SCADA 變數初探、欄位分布 |
| analyst | wData:quality-checker | 缺失值 / 離群值 / 一致性 |
| scientist | wAI:fault-diagnostician / wAI:predictive-modeler | 故障分類、RUL、退化建模 |
| critic | wLab:research-lead | 假設驗證、論文邏輯檢視 |
| executor | wAI:experiment-tracker | MLflow 實驗執行 |
| verifier | wLab:director | 結果合規檢查（IEC、品質規則） |

### 程式碼／pipeline 類任務

```
explore → planner → architect → executor → verifier
```

| OMC agent | windAI namespace | 場景 |
|-----------|------------------|------|
| explore | wEng:backend-dev | 既有模組掃描 |
| planner | wLab:tech-lead | 任務拆解、PR 切片 |
| architect | wEng:tech-lead / wAI:rag-architect | 系統設計、API 介面 |
| executor | wEng:backend-dev / wEng:frontend-dev | 撰寫程式碼 + 測試 |
| verifier | wLab:director（Checkpoint） | ruff / mypy / pytest 全綠 |

### 論文寫作類任務

```
analyst → writer → critic → writer (revision loop)
```

| OMC agent | windAI namespace | 場景 |
|-----------|------------------|------|
| analyst | wRes:literature-reviewer | 文獻搜集 + 系統性整理 |
| writer | wRes:paper-writer | 章節初稿（IEEE / Elsevier 模板） |
| critic | wLab:research-lead | reviewer 視角檢視 |
| writer（revision） | wRes:paper-writer | 回應審查、潤稿 |

---

## Domain Knowledge Hints

### SCADA 變數慣例

- 風速類：`wind_speed`, `wind_speed_avg`, `Wind_speed`, `WSpeed`, `WS`
- 功率類：`power`, `active_power`, `power_output`, `Pwr`, `P_avg`
- 槳距類：`pitch_angle`, `blade_pitch`, `BladePitch`, `pitch_*_angle`
- 轉速類：`rotor_rpm`, `rotor_speed`, `generator_speed`, `RotorRPM`
- 溫度類：`gearbox_temp`, `bearing_temp`, `nacelle_temp`, `oil_temp`
- 環境類：`air_density`, `ambient_temp`, `humidity`, `nacelle_direction`

> Smart loader 已內建 60+ 模糊匹配關鍵字（`src/data_pipeline/ingestion/smart_loader.py`）。

### 故障分類體系

| 類別 | IEC 61400 對照 | 主要訊號特徵 |
|------|----------------|---------------|
| pitch system | 槳距系統故障 | pitch angle 異常、roll moment 偏差 |
| drivetrain | 傳動系故障 | gearbox 振動、油溫上升 |
| generator | 發電機故障 | 繞組溫度、效率下降 |
| electrical | 電氣系統故障 | 諧波、功因異常 |

### 關鍵 Turbine ID 對照

| Kelmarsh ID | 系統別名 | 角色 |
|-------------|----------|------|
| Kelmarsh_1~6 | WT-01 ~ WT-06 | 預設 6 台 |

> 研究實驗常用比對組（Fuhrländer 資料集）：H07, H11, H16, H18, H19, H20

### 評估指標常規

- **故障診斷**：F1, Precision, Recall, AUC-ROC
- **回歸（NBM/RUL）**：RMSE, MAE, R², MAPE
- **RAG 檢索**：MRR, Recall@K, NDCG
- **業務 KPI**：MTTR, MTBF, false alarm rate

---

## Cost Optimization（Smart Model Routing）

OMC 內建依任務難度自動切換模型。本專案的建議分流：

| 模型 | 適用場景 | 範例任務 |
|------|----------|----------|
| **Haiku** | 檔案掃描、簡易整理、grep 結果摘要 | 列出資料夾結構、整理變數清單、檔名重整 |
| **Sonnet** | 資料分析、程式實作、debug、文件撰寫 | EDA、修 bug、寫 service、寫文件章節 |
| **Opus** | 架構決策、論文結構、critic 審查、計畫 | 設計新模組介面、論文 Results 統整、reviewer 視角 |

> 預設保險作法：**對外輸出（commit、PR、論文章節）走 Opus**；**內部探索（grep、ls、讀檔）走 Haiku**。

---

## Skill Routing 範例

OMC `skill` 與 windAI 內建 skill registry（`src/skills/`）的銜接示意：

| OMC skill | windAI pipeline | CLI 指令 |
|-----------|-----------------|----------|
| `scientist:` | `scada_ingestion → profiler → cleaning → features → fault_classification` | `/diagnose` |
| `sciomc:` | 平行多台分析 | `python -m src.cli batch-diagnose --turbines WT-01,WT-02,WT-03` |
| `autopilot:` | full feature workflow | 由 wLab:director 派工 |
| `ralph:` | 修 test 直到全綠 | `pytest tests/ -x` 反覆執行 |
| `writer:` | 章節撰寫 | `/write-paper` |
| `critic:` | reviewer 審查 | `/lab:report` |
| `wiki add:` | 知識點寫入 RAG | `/build-rag` |
| `lit-search:` | 文獻搜尋 | `/lit-search` |

---

## OMC × windAI 整合守則

1. **所有 OMC 子代理產出仍須通過 wLab:director Checkpoint**：未經總監確認的 commit/PR 不可推送。
2. **派工紀錄必填**：OMC 自動完成的任務也須回填 `docs/work-logs/YYYY-MM/WLAB-*.md`，避免「黑箱完成」。
3. **資料保護**：原始資料 (`data/raw/`, `data/external/`) 唯讀；OMC `executor` 禁止就地修改，必須輸出至 `data/processed/`。
4. **訊息格式**：跨代理通訊使用 `CLAUDE.md §9` 定義的 JSON 格式。
5. **繁體中文輸出**：對使用者的所有最終回覆均使用繁體中文，技術術語保留英文原文。

---

## 變更歷程

| 版本 | 日期 | 主要變更 |
|------|------|----------|
| v0.1 | 2026-04-27 | OMC 整合啟動：初版定義 agent workflow、domain hints、cost routing |

---

*由 wLab:director + wRes:rag-curator 協同產出 | OMC v4.13.0+ 適用*
