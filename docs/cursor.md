# WindAI Lab — Cursor

> 自動更新時間：2026-09-24（auto-advance #12 觸發後）
> 規格：`docs/routines/daily-workflow.md` §4（R2 基準快照）
> 自動推進：`docs/routines/auto-advance.md`（每 3 小時觸發，以本檔為唯一狀態交接介面）

## 上次工作時間

- 日期：2026-09-24
- Session：`auto-advance` 第 12 次觸發。完成 P0-新1：以 CI 實際 pin 的 `ruff==0.6.0` 修正全部 25 項 lint 錯誤（9× UP038、4× E741、3× B904、6× N815、1× TCH003、1× SIM108、1× E402），三項自我測試全綠，commit `0d5d025` 已 push。詳見 [WLAB-20260924-02](work-logs/2026-09/WLAB-20260924-02-ci-actual-ruff-lint-fix.md)。
- 前次有效工作日：2026-09-24（auto-advance #11，無 commit；關閉 6 個 Issue + 定位 CI 根因，見 [WLAB-20260924-01](work-logs/2026-09/WLAB-20260924-01-close-completed-issues.md)）

## ⚠️ 待下次觸發優先確認：CI 是否真正轉綠

本次 push（`0d5d025`）觸發 CI run **`35983653111`**（https://github.com/dofliu/windAI-Lab/actions/runs/35983653111），觸發結束時該 run 狀態仍為 `in_progress`，**尚未取得最終結論**。下次觸發第一步：

1. 用 `mcp__github__actions_get`（`get_workflow_run`，resource_id `35983653111`）或改查 `claude/auto-advance` 分支最新一次 run 確認結論
2. 若 Lint job 轉綠 → 本次 P0-新1 視為完全驗證成功，記錄確認即可，無需重做
3. 若 Lint job 仍紅 → 讀取 `get_job_logs` 找出新錯誤（可能是本次修正遺漏、或 ruff 對 tests/ 目錄有本次未涵蓋的規則差異），視規模拆成新 P0 項目處理
4. GitHub connector 本次觸發已確認可用（`mcp__github__get_me` 成功），`docs/routines/auto-advance.md` §4.1「無 connector」描述持續視為過時，下次觸發請直接嘗試查詢

## 數據基準（實測，auto-advance #12）

- `pip install ruff==0.6.0`（**改用 CI 實際 pin 版本，取代 routine playbook 舊 pin `0.15.8`**；下次觸發 Phase 0 的 `pip install "ruff==0.15.8"` 應同步改為 `"ruff==0.6.0"`，playbook 尚未修正，見下方阻塞）
- `ruff check src/ tests/`（`0.6.0`）：**0 錯誤**（25 → 0，本次修正全部完成）
- `python3 -m black --check --line-length 99 src/ tests/`：**全綠**，181 檔案
- `pytest tests/`：**877 收集 → 872 pass / 0 fail / 5 skip**（與 #8～#11 基準相同，本次修正無回歸）
- CI：push 後觸發 run `35983653111`，觸發結束時仍 `in_progress`，**結論待下次觸發確認**（見上方待辦）
- Open Issues：12（與 #11 相同，本次未變更 Issue）
- 前端 TODO：1（`frontend/src/hooks/useWebSocket.ts`，穩定）
- 最近 commit：`0d5d025`（2026-09-24，auto-advance #12，修正 CI 實際 ruff 版本下的 25 項 lint 錯誤，8 檔變更）
- 資產（沿用 #10/#11 實測，本次未變更資產面）：
  - REST 端點：72 + 1 WS
  - 前端元件：40
  - 技能：28（data 7、features 4、leadership 1、ml 12、rag 3、reporting 1）
  - agent 模組：25
  - `.py` 檔案：141，總行數 30,411（`src/` 下，本次僅修改既有行，行數變動極小）

## Issue 狀態快照（沿用 #11 實測，本次未變更）

剩餘 Open Issues：12 個（#34/#35/#36/#37/#46/#47/#48/#49/#50/#51/#52/#69）。詳見 #11 work-log。

## 待續產出（下個 session / auto-advance 觸發接手）

> 由 `auto-advance` routine 每 3 小時取**第一個未完成**項目執行，規則見 `docs/routines/auto-advance.md`。

- [x] **P0-新1**（完成於 auto-advance #12，2026-09-24）修正 CI 實際 ruff 版本（0.6.0）下的 25 項錯誤。詳見 [WLAB-20260924-02](work-logs/2026-09/WLAB-20260924-02-ci-actual-ruff-lint-fix.md)。

- [ ] **P0-新2**（優先序最高）**確認 CI run `35983653111`（或之後最新一次）的最終結論**，若仍紅則續修。做法見上方「待下次觸發優先確認」區塊。規模：查詢 + 視情況修正，預估可於單次觸發完成。

- [ ] **P1-新1** 修正 `docs/routines/auto-advance.md` Phase 0 的 ruff pin 版本：目前寫的是 `pip install --quiet "ruff==0.15.8"`，應改為 `"ruff==0.6.0"` 以與 CI 實際版本一致（P0-新1 已證實兩版本規則集不同）。**注意**：修改 `docs/routines/auto-advance.md` 本身不在 CLAUDE.md 保護範圍內（非 CLAUDE.md 本身），理論上可自主執行；但因 P2-1 曾證實「改到規則文件」有被 Self-Modification classifier 擋下的先例，**執行前應先小範圍嘗試，若被擋則記錄阻塞、跳過，不重試**。

- [ ] **P2-1** `CLAUDE.md` 章節編號去重（現有兩組 §5/§6/§7）、§10「42 個代理」更正為 25。⚠️ **已嘗試執行並卡關（auto-advance #9）**：編輯內容本身通過自我測試，但 commit 動作被 Claude Code auto-mode classifier 以「Self-Modification」拒絕，工作樹已還原。**需人工授權**：需人工在具備更高權限的 session（或人工直接編輯）才能完成 commit；routine 之後觸發應**跳過此項**。

- [ ] **P2-2** 定向下一個功能方向（Phase 15 多風場管理 / Epic A 案例學習系統）— **屬方向性決策，需使用者指派，routine 不得自行啟動**。

> **下次觸發應直接處理 P0-新2**（確認 CI 結論），若 CI 已確認全綠，接著可嘗試 P1-新1（playbook pin 版本校正），P2-1/P2-2 仍維持「需人工」不動。

## 阻塞 / 風險

- 🟢 **P1-3 lint/test 解耦確認有效**（沿用 #11 實測，CI run `35953337501`）：Lint 失敗不阻塞 Tests，兩者獨立回報
- ✅ **已解除（本次 #12 完成）**：CI 實際 ruff 版本（0.6.0）下的 25 項錯誤已全數修正並 push，等待 CI 最終結論確認（見上方 P0-新2）
- 🟠 **大 commit 直推 master**：`bfca6a7` 5,315 行未過 CI 即進主幹，流程缺門檻（沿用既有記錄，本次未新增證據）
- 🟡 **CLAUDE.md 不可被此 routine 自動 commit**（auto-advance #9 發現）：任何觸及 `CLAUDE.md` 的佇列項目都會在 commit 階段被系統層擋下（Self-Modification）。往後佇列不要再排入直接修改 `CLAUDE.md` 的項目，除非使用者確認可由人工協助完成 commit 步驟。**尚不確定此限制是否也涵蓋 `docs/routines/*.md` 等規則類文件**——P1-新1 將是驗證此範圍的第一個案例，若被擋請記錄清楚是哪個檔案觸發。
- 🟢 GitHub connector 持續可用（#11、#12 皆驗證成功），`docs/routines/auto-advance.md` §4.1「無 connector」描述已過時，下次觸發請直接嘗試查詢而非假設不可用。
