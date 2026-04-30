# WindAI Lab — 每日工作流程 Routines（v1.0）

> **建立日期**：2026-04-26
> **觸發原因**：4/26 上一回合遭遇 API Stream idle timeout 中斷
> **目標**：在保留使用者「派工 + 結構化紀錄 + 正式報告」三軸核心需求前提下，把每日工作流改造為可分段續行、不易單回合過載的結構

---

## 1. 既有流程的痛點（觀察）

| 痛點 | 觀察證據 |
|------|----------|
| **單回合產出過載** | 4/26 一個回合要讀 6+ 個長文件、產出 3 個 100~250 行的繁中 Markdown、再更新 3 個既有文件 |
| **歷史脈絡逐日膨脹** | CLAUDE.md (357 行) + daily_report.md 每日重寫 + 累積 11 份 work-logs，每次都重讀 |
| **大段繁中表格生成偏慢** | 派工單 / 工作紀錄 / 週報依賴密集表格，串流速度比純文字慢 |
| **無斷點續行機制** | 一旦 timeout，已產出檔案散落，下回合難以快速接續 |

---

## 2. 改善要點概覽

| 編號 | 改善點 | 工夫 | 預期效果 |
|------|--------|------|----------|
| **R1** | 拆 session（A/B/C 三段觸發） | 低 | 單回合負擔 ↓ 60% |
| **R2** | `docs/cursor.md` 基準快照 | 低 | 每日讀取 token ↓ 70% |
| **R3** | 派工單模板 v1.2 精簡版（例行維運日專用） | 低 | 例行日文件量 ↓ 50% |
| **R4** | 長文件用 subagent 並行 | 中 | 主串流壓力 ↓ 40% |
| **R5** | Stop hook 自動 commit untracked | 已啟用 | 已強制提醒，避免遺失 |
| **R6** | 失敗續行守則 | 低 | 中斷可定位、不重做 |

---

## 3. R1 — 拆 session（A / B / C 三段觸發）

### 流程圖

```
排程觸發點 1（早上 09:00）
  └─ Session A — 掃描與 Issue 管理
       Phase 1（讀文件）
       Phase 2（git log / ruff / TODO）
       Phase 3（Issue 新建 / 關閉）
       產出：cursor.md（快照）+ work-logs/YYYY-MM-DD-allocation.md（派工單草稿）

排程觸發點 2（早上 10:00）
  └─ Session B — 主動工作 + 文件產出
       Phase 4（依 cursor 決定產出範圍）
       產出：WLAB-YYYYMMDD-NN-*.md 各份工作紀錄

排程觸發點 3（傍晚 17:00）
  └─ Session C — 收束
       Phase 5（更新 daily_report / README / work-logs README）
       Phase 6（commit + push）
       Phase 7（email 通知）
```

### 觸發方式

- 推薦透過 cron / `claude /loop` / GitHub Actions 排定 3 個觸發點
- 每段以 `cursor.md` 為交接介面，後段 session 不需重讀整篇 daily_report

### Slash command 對照（建議）

| Session | 建議 slash command |
|---------|--------------------|
| A | `/daily-scan` |
| B | `/daily-produce` |
| C | `/daily-close` |

### 執行原則

- **每段最多 30 個工具呼叫**：超過則拆出下一段
- **每段 markdown 產出 ≤ 2 份新檔案**：第三份起延後或交 subagent
- **單檔產出 ≤ 200 行**：超過拆段或交 subagent

---

## 4. R2 — `docs/cursor.md` 基準快照

### 用途

替代「每日重讀 daily_report 全文」當作上次基準。Session A 結束時寫入，Session B/C 只需讀此檔。

### 內容結構

```markdown
# WindAI Lab — Cursor

> 自動更新時間：2026-04-26 10:00

## 上次工作時間
- 日期：2026-04-26
- Session 結束：A 完成

## 數據基準
- Lint 錯誤：0
- Python TODO/FIXME：0
- 前端 TODO：1（穩定）
- Open Issues：19
- 最近 commit：dd99ec0

## Issue 狀態快照
| # | 標題 | 狀態 |
|---|------|------|
| #42 | [E2] 通知渠道 | 4/27 啟動 |

## 待續產出（Session B 接手）
- [ ] WLAB-20260426-02 W18 啟動備忘錄
- [ ] daily_report.md 更新

## 阻塞 / 風險
- API timeout（已透過 R1 改善）
```

### 維護規則

- Session A 結束時 **覆寫**（不累積歷史，避免膨脹）
- Session B 結束時更新「待續產出」狀態
- Session C 結束時清空「待續產出」並標記日結

---

## 5. R3 — 派工單模板 v1.2 精簡版

### 適用情境

- 本日為「例行維運日」（無新實作 PR、無大文件產出）
- 任務數 ≤ 2、合計工時 ≤ 2h

### 不適用

- 啟動日（如 4/27 W18 多軌啟動）
- 週報日（4/30）
- 設計稿日（5/01）

### 模板結構（精簡版）

```markdown
# 派工單（精簡） — YYYY-MM-DD

> 派工總監：wLab:director｜任務數：N｜倒數：N 天｜模式：輕量維運

## 決策摘要（≤ 2 句）
{...}

## 任務（一格一條）
| Task ID | 名稱 | 指派 | 工時 | 截止 | 紀錄 |
|---------|------|------|------|------|------|
| WLAB-... | ... | wLab+wRes | 0.8h | YYYY-MM-DD | [link] |

## 風險（僅必要時）
- {...}

## 簽核
- [x] 總監已審閱
```

> 路徑：`docs/templates/tmpl-work-assignment-lite.md`（待 4/28 抽出）

---

## 6. R4 — 長文件用 subagent 並行

### 適用文件

- 週報（≥ 250 行）
- 啟動就緒備忘錄（≥ 150 行）
- 設計文件（≥ 200 行）

### 操作模式

```
主回合
  ├─ Agent({type: general-purpose, prompt: "撰寫 W18 啟動備忘錄..."})
  └─ 主回合並行寫派工單 + 工作紀錄

主回合等候 agent 回傳
  └─ 對 agent 產出做最終審稿（10-20% 修改），寫入檔案
```

### 注意事項

- subagent 產出後，**主回合仍需親自寫入檔案**（agent 看不到使用者的最終語境）
- subagent 拿到的 prompt 必須自包含（路徑、章節結構、字數上限）
- 適合「結構固定、可獨立判斷」的內容；不適合「需引用本回合多個工具結果」的整合性產出

---

## 7. R5 — Stop hook 自動提醒未提交檔案

### 現況

`~/.claude/stop-hook-git-check.sh` 已啟用，會在 Stop 時偵測 untracked / staged / modified 檔案並提醒。

### 4/26 實證

```
[~/.claude/stop-hook-git-check.sh]: There are untracked files in the repository.
Please commit and push these changes to the remote branch.
```

→ 主回合接手後立即 commit dd99ec0，避免遺失工作。

### 後續強化建議（可選）

- 在 hook 中加入 `--dry-run` 提示 commit message 建議
- 偵測 `WLAB-*.md` 類型自動帶入 `docs:` 前綴

---

## 8. R6 — 失敗續行守則

### 中斷時的恢復步驟

1. **檢查 untracked / 已提交檔案**
   ```bash
   git status --short
   git log --oneline -5
   ```

2. **比對 cursor.md「待續產出」清單**
   - 若 cursor.md 已被 Session A 寫入，依其待續清單續行
   - 若 cursor.md 未存在，從 daily_report.md「本日增量」反推

3. **commit 已完成檔案**（避免長期 untracked）
   ```bash
   git add <已完成檔案>
   git commit -m "docs: YYYY-MM-DD 部分產出（中斷續行）"
   git push -u origin <branch>
   ```

4. **續行剩餘工作**
   - 優先補完當日「使用者核心需求」相關產出（派工 / 紀錄 / 報告）
   - 流程改善類產出（如本檔）優先級次於核心交付

5. **回填 daily_report.md「中斷紀錄」段落**

### 不要做的事

- ❌ 重做已完成的檔案
- ❌ 為了「乾淨重來」而 reset 未推送的 commit
- ❌ 在續行回合啟動新實作工作（保留至下一個正規工作日）

---

## 9. 實施計畫

| 編號 | 改善 | 何時生效 | 負責 |
|------|------|----------|------|
| R1 | 拆 session A/B/C | 2026-04-27 起試行（W18 第一週） | wLab + 排程設定 |
| R2 | cursor.md | 2026-04-27 Session A 首次寫入 | wLab |
| R3 | tmpl-work-assignment-lite.md | 2026-04-28 抽出 | wRes |
| R4 | subagent 用於週報 | 2026-04-30 W18 週報首次採用 | wRes |
| R5 | Stop hook | 已啟用 | — |
| R6 | 失敗續行守則 | 即日生效（本檔） | 全員 |

---

## 10. 驗證指標

| 指標 | 4/26 基線 | W18 目標 |
|------|-----------|----------|
| 單日 timeout 發生次數 | 1 | 0 |
| 單回合工具呼叫數 | 30+ | ≤ 20（拆段後） |
| 單回合 markdown 新增行數 | 800+ | ≤ 250（單段） |
| 例行維運日文件量 | ~250 行 | ≤ 120 行（採 lite 模板） |
| 中斷後續行成功率 | 100%（4/26 已驗證） | 維持 100% |

---

## 11. 變更記錄

| 版本 | 日期 | 變更 |
|------|------|------|
| v1.0 | 2026-04-26 | 首次建立（觸發原因：API Stream idle timeout） |

---

*本 routines 文件由 wLab:director + wRes:rag-curator 共同建立，遵循專案 CLAUDE.md 規範。*
