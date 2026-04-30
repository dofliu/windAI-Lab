# windAI-Lab × oh-my-claudecode (OMC) 整合指南

> **文件版本**：v0.1
> **建立日期**：2026-04-27
> **適用版本**：OMC v4.13.0+, Claude Code v2.1.119+
> **整合任務**：[WLAB-20260427-01](work-logs/2026-04/WLAB-20260427-01-omc-integration.md)

---

## 1. 整合目的

windAI-Lab 已具備自有的 6 層 namespace 代理階層（`wLab:` / `wData:` / `wAI:` / `wDomain:` / `wEng:` / `wRes:`，總計 22 個 YAML 代理 + 28 個技能模組）。引入 **oh-my-claudecode (OMC)** 的目的：

1. **互補而非取代**：OMC 提供通用型 agent（explore / planner / scientist / writer / critic ...），與 windAI 的領域代理並行工作。
2. **省 Token / Smart Routing**：OMC 內建 haiku/sonnet/opus 自動切換，預估可降 30-50% token 用量。
3. **多模型協作**：在支援的環境（WSL2 / Linux）可啟動 ccg（Claude-Codex-Gemini）三模型平行討論。
4. **持久化記憶**：`wiki add` / `remember` / `skillify` 提供跨 session 知識保留，銜接專案 RAG 知識庫。

> ⚠️ OMC plugin 安裝為 **互動式 Claude Code 指令**，無法在 SDK / CI 環境直接執行。本指南提供「人工於 Claude Code session 中安裝」的操作步驟。

---

## 2. 環境需求

| 項目 | 最低版本 | 本機驗證版本（2026-04-27） |
|------|----------|----------------------------|
| Claude Code CLI | ≥ 1.0 | **2.1.119** ✅ |
| Node.js | ≥ 18 | **v22.22.2** ✅ |
| npm | ≥ 9 | **10.9.7** ✅ |
| Python | ≥ 3.11 | **3.11.15** ✅ |

驗證指令：

```bash
claude --version
node --version
npm --version
python3 --version
```

---

## 3. 安裝步驟（人工於 Claude Code session 執行）

### Step 1：確認當前位置

```bash
pwd                # 應顯示 /path/to/windAI-Lab
ls -la             # 確認看得到 README.md / CLAUDE.md / AGENTS.md
```

### Step 2：安裝 OMC plugin

於 Claude Code session 內輸入：

```
/plugin marketplace add https://github.com/Yeachan-Heo/oh-my-claudecode
/plugin install oh-my-claudecode
```

安裝完成後執行初始化：

```
/oh-my-claudecode:omc-setup
```

> 過程中如有提示，選擇「預設值」即可。安裝完成後 `.claude/` 目錄會新增 OMC 相關設定檔（不會覆寫既有 `.claude/agents/` 或 `.claude/commands/`）。

### Step 3：驗證安裝

```
/oh-my-claudecode:omc-doctor
```

預期輸出：所有檢查項目（Node / npm / Claude Code 版本 / 設定檔）皆綠燈。

### Step 4：第一個任務（Smoke Test）

```
scientist: 請掃描這個 repo 的 Python 檔案結構，給我一份 windAI-Lab 的模組地圖，包含：
1. 各資料夾的功能說明
2. 主要 Python 模組列表
3. 目前有哪些 TODO 或未完成的功能
```

**預期結果**：OMC 會自動切換到適合的模型（多半是 sonnet），產出與 [`docs/work-logs/2026-04/WLAB-20260427-01-omc-integration.md`](work-logs/2026-04/WLAB-20260427-01-omc-integration.md) 內附的「初版模組地圖」對齊的結果。

---

## 4. 與 windAI-Lab 既有系統整合

### 4.1 命名空間衝突檢查

OMC 的 agent 名稱（`scientist`, `analyst`, `writer`, `critic`, `executor`, `verifier` 等）與 windAI 的 `wLab:` / `wData:` 等命名空間 **不衝突**。OMC agent 無前綴，windAI agent 一律 `w*:` 前綴。

### 4.2 .claude/ 目錄分工

```
.claude/
├── agents/                    ← windAI 原有（手寫 .md 代理）
│   ├── ai-ml/
│   ├── leadership/
│   └── research-docs/
├── commands/                  ← windAI 原有 slash commands
│   ├── build-rag.md
│   ├── diagnose.md
│   ├── lit-search.md
│   ├── onboard-student.md
│   └── write-paper.md
├── windailab-skills.md        ← 本次新增：OMC 常用指令速查
└── (omc 安裝後新增的目錄)     ← OMC 安裝後產生
```

### 4.3 與 CLAUDE.md / AGENTS.md 的關係

| 文件 | 角色 | 主要讀者 |
|------|------|----------|
| `CLAUDE.md` | 系統行為規範（強制） | Claude Code 主體 + 所有代理 |
| `AGENTS.md` | OMC 子代理協作指引 | OMC agent + 開發者 |
| `.claude/windailab-skills.md` | OMC 常用指令速查 | 開發者（速查卡） |
| `docs/omc-integration-guide.md` | 本檔（整合說明文件） | 新加入專案的工程師 |

---

## 5. 推薦工作流（windAI 情境）

### Case A：新風場資料進來

```
1. wiki query: SCADA 變數命名慣例
2. scientist: 掃描 data/raw/{NEW_FARM}/，找出可用欄位
3. autopilot: 為新風場建立 turbine profile + 跑 NBM 基線
4. critic: 檢查結果合理性
5. wLab:director Checkpoint → 確認後寫入 docs/work-logs/
```

### Case B：故障診斷報告產出

```
1. /diagnose WT-XX           （windAI 原生 slash command）
2. writer: 將 src/services/report_store.py 產出的 JSON 包裝成正式報告（v1.1 模板）
3. critic: 模板合規檢查
4. 派發 PDF / HTML 至 docs/reports/
```

### Case C：論文章節寫作

```
1. lit-search: 主題關鍵字       （windAI 原生）
2. analyst: 整理引用網路        （OMC）
3. writer: 撰寫章節             （OMC）
4. critic: reviewer 視角檢視    （OMC）
5. writer: 回應修訂             （OMC）
```

---

## 6. Windows 環境限制

OMC 部分功能 **僅支援 WSL2 / Linux / macOS**：

| 功能 | Windows 原生 | WSL2 / Linux / macOS |
|------|--------------|----------------------|
| 19 個 agent | ✅ | ✅ |
| `autopilot` / `ralph` / `sciomc` / `deep-interview` | ✅ | ✅ |
| `wiki` / `remember` / `skillify` | ✅ | ✅ |
| Smart model routing | ✅ | ✅ |
| `omc-teams`（tmux 多窗格） | ❌ | ✅ |
| `ccg` 三模型協作 | ❌ | ✅ |
| `project-session-manager`（git worktree + tmux） | ❌ | ✅ |

> windAI-Lab 主開發環境為 Linux，上述限制無影響。

---

## 7. 進階：自訂 Skill

若某個工作流值得保留為可重複使用的 skill：

```
skillify: 把剛才的 SCADA 模組地圖分析流程，存成可重複使用的 skill
```

OMC 會產出 `SKILL.md` 草稿。本專案 skill 統一存放於：

```
.claude/skills/{skill-name}/SKILL.md
```

---

## 8. 整合驗收清單

- [x] AGENTS.md 已建立於 repo 根目錄
- [x] `.claude/windailab-skills.md` 速查表已建立
- [x] 本整合指南已建立
- [x] CLAUDE.md / README.md / TODO 已更新（指向 OMC 整合）
- [ ] OMC plugin 已於 Claude Code session 安裝（**需人工執行**）
- [ ] `omc-doctor` 全綠（**需人工執行**）
- [ ] Smoke test 完成（**需人工執行**）

---

## 9. 後續工作

| 工作項目 | 負責 | 預計時程 |
|----------|------|----------|
| 人工跑完 Step 2 / Step 3 安裝 + 驗證 | 使用者 | 4/27 ~ 4/28 |
| 將模組地圖結果回寫 `docs/omc-integration-guide.md` | wRes:rag-curator | 4/28 |
| 評估是否將 `wLab:director` 改寫為 OMC critic + verifier 鏈 | wLab:director | W18-19 評估 |
| 對接 OMC `wiki` 與 windAI RAG（ChromaDB） | wAI:rag-architect | W19+ |
| 建立首個自訂 skill（建議：故障報告自動化） | wEng:backend-dev | W19+ |

---

## 10. 參考資源

- OMC 官方文件：<https://omc.vibetip.help/docs>
- Agent 完整列表：<https://omc.vibetip.help/docs/agents>
- Skill 完整列表：<https://omc.vibetip.help/docs/skills>
- GitHub：<https://github.com/Yeachan-Heo/oh-my-claudecode>

---

*文件擁有者：wLab:director + wRes:rag-curator | 對應 task：WLAB-20260427-01*
