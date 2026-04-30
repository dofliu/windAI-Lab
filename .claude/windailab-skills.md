# windAI-Lab × OMC 常用指令速查

> 對應 OMC v4.13.0+ | 最後更新：2026-04-27
> 搭配 [`AGENTS.md`](../AGENTS.md) 使用

---

## 研究資料分析

```
scientist: 分析 data/external/Kelmarsh/Turbine_1.parquet 的統計分布，輸出各欄位摘要與異常值報告
```

```
analyst: 比對 WT-01 與 WT-04 過去 30 天 pitch angle 分布，找出 stuck pitch 嫌疑時段
```

---

## 多台平行分析

```
sciomc: 同時分析 WT-01、WT-03、WT-05 三台 SCADA 的 pitch 角度異常模式，輸出對比表
```

```
sciomc: 對 Kelmarsh 6 台同時跑 NBM 訓練，產出 R² 排行榜
```

---

## 程式碼開發

```
autopilot: 在 src/skills/ml/ 新增 catboost_classification skill，並補測試
```

```
ralph: 修復 src/services/alert_engine.py 所有 test 錯誤，直到 pytest tests/services/test_alert_engine.py 全部通過
```

```
ralplan: 規劃 #96 階段二 AllocationEngine 的實作路線圖
```

---

## 論文寫作

```
writer: 根據 docs/reports/2026-W17-weekly-report.md 的 Epic C 結果，撰寫 IEEE 格式的 Results and Discussion 段落
```

```
critic: 審查 references/draft-pitch-fault-2026.md 的 methodology 章節，從 reviewer 角度找出邏輯漏洞
```

---

## 知識管理

```
wiki add: BGE-3 嵌入模型在 Kelmarsh 維護紀錄上的最佳 chunk size = 512，overlap = 64
```

```
wiki query: pitch system fault signatures
```

```
remember: WT-04 在 2024-08-15 ~ 2024-08-22 期間有未紀錄停機，須在所有訓練集中過濾
```

---

## 需求釐清

```
deep-interview: 我想設計一個能根據維護記錄自動推薦故障案例的功能
```

```
ralplan: 規劃 #44 報告排程自動化（Epic D）的實作路線圖
```

---

## 省 Token 模式

```
eco: scientist: 列出 src/skills/ 全部 skill 並各做一行說明
```

> `eco:` 開頭可降 30-50% token 用量，適合掃描型任務。

---

## windAI-Lab 內建 slash commands（系統原生，非 OMC）

| 指令 | 功能 |
|------|------|
| `/diagnose` | 執行故障診斷管線（ingestion → cleaning → features → classification → nbm） |
| `/onboard-student` | 新研究生入職引導 |
| `/build-rag` | 重建 RAG 知識庫 |
| `/lit-search` | 系統性文獻搜尋 |
| `/write-paper` | 啟動論文撰寫工作流 |

> 這些 slash command 仍由 windAI-Lab 自己的 `.claude/commands/` 提供；OMC 不會覆寫。

---

## 整合工作流範例

### Case A：新風場資料進來

```
1. wiki query: SCADA 變數命名慣例
2. scientist: 掃描 data/raw/{NEW_FARM}/，找出可用欄位
3. autopilot: 為新風場建立 turbine profile + 跑 NBM 基線
4. critic: 檢查結果合理性
5. wLab:director Checkpoint → 確認後寫入 docs/work-logs/
```

### Case B：故障診斷報告

```
1. /diagnose WT-XX
2. writer: 將 src/services/report_store.py 產出的 JSON 包裝成正式報告（v1.1 模板）
3. critic: 模板合規檢查
4. 派發 PDF / HTML 至 docs/reports/
```

### Case C：論文章節

```
1. lit-search: 主題關鍵字
2. analyst: 整理引用網路
3. writer: 撰寫章節
4. critic: reviewer 視角檢視
5. writer: 回應修訂
```

---

## Windows 環境注意

> ⚠️ 以下 OMC 功能在 **Windows 原生環境需要 WSL2**，本專案於 Linux/macOS 上不受影響：
>
> - `omc-teams`（需要 tmux）
> - `ccg` Claude-Codex-Gemini 三模型協作（需要 tmux）
> - `project-session-manager`（git worktree + tmux）
>
> **不受影響**（全平台可用）：所有 19 個 agent、autopilot、ralph、ultrawork、sciomc、deep-interview、wiki、remember、skillify、smart model routing。

---

## 參考資源

- OMC 官方文件：<https://omc.vibetip.help/docs>
- Agent 完整列表：<https://omc.vibetip.help/docs/agents>
- Skill 完整列表：<https://omc.vibetip.help/docs/skills>
- GitHub：<https://github.com/Yeachan-Heo/oh-my-claudecode>
- 本專案 OMC 整合 root：[`AGENTS.md`](../AGENTS.md)
