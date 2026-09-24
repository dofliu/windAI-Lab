# WindAI Lab — Cursor

> 自動更新時間：2026-09-24（auto-advance #13 觸發後）
> 規格：`docs/routines/daily-workflow.md` §4（R2 基準快照）
> 自動推進：`docs/routines/auto-advance.md`（每 3 小時觸發，以本檔為唯一狀態交接介面）

## 上次工作時間

- 日期：2026-09-24
- Session：`auto-advance` 第 13 次觸發。完成 P0-新2（確認 CI run `35983653111` conclusion=success，#12 的 lint 修正已驗證通過）與 P1-新1（校正 `docs/routines/auto-advance.md` Phase 0 的 ruff pin 版本，`0.15.8` → `0.6.0`，與 CI 實際 pin 一致）。三項自我測試全綠，commit `253f80f` 已 push。詳見 [WLAB-20260924-03](work-logs/2026-09/WLAB-20260924-03-p0-new2-verify-p1-new1-ruff-pin.md)。
- 前次有效工作日：2026-09-24（auto-advance #12，完成 P0-新1，commit `0d5d025`，見 [WLAB-20260924-02](work-logs/2026-09/WLAB-20260924-02-ci-actual-ruff-lint-fix.md)）

## ⚠️ 待下次觸發優先確認：CI 是否真正轉綠

本次 push（`253f80f`，僅變更 `docs/routines/auto-advance.md` 一份文件）觸發 CI run **`36001740425`**（https://github.com/dofliu/windAI-Lab/actions/runs/36001740425），觸發結束時該 run 狀態仍為 `in_progress`。下次觸發第一步：

1. 用 `mcp__github__actions_get`（`get_workflow_run`，resource_id `36001740425`）確認結論
2. 因本次僅變更 routine 文件、未動 `src/`/`tests/`，預期會綠；若真的紅，需查明是否與本次變更無關（既有基準紅），而非本次修正造成
3. GitHub connector 本次觸發持續可用（`actions_get`、`list_issues` 皆成功），`docs/routines/auto-advance.md` §4.1「無 connector」描述持續視為過時

## 數據基準（實測，auto-advance #13）

- `ruff` 安裝陷阱：容器內 `/root/.local/bin/ruff` 為舊版殘留（`0.15.8`），優先於 PATH 中 `pip install` 安裝到 `/usr/local/bin/ruff` 的版本。下次觸發若 `ruff --version` 顯示非預期版本，改用絕對路徑 `/usr/local/bin/ruff` 驗證。
- `pip install ruff==0.6.0`（已與 CI 實際 pin 版本一致，playbook 本次已同步校正）
- `ruff check .`（`0.6.0`，`/usr/local/bin/ruff`）：**0 錯誤**
- `python -m black --check --line-length 99 src/ tests/`：**全綠**，181 檔案
- `pytest tests/ -q`：**877 收集 → 872 pass / 0 fail / 5 skip**（與 #8～#12 基準相同，本次無回歸）
- CI：push 後觸發 run `36001740425`，觸發結束時仍 `in_progress`，**結論待下次觸發確認**（見上方待辦）；上一個 run `35983653111`（#12 的修正 commit）已確認 `conclusion=success`
- Open Issues：12（與 #11/#12 相同，本次未變更 Issue，已用 `list_issues` 重新核對）
- 前端 TODO：1（`frontend/src/hooks/useWebSocket.ts:266`，穩定）
- 最近 commit：`253f80f`（2026-09-24，auto-advance #13，校正 routine playbook 的 ruff pin 版本，1 檔變更）
- 資產（沿用 #10～#12 實測，本次未變更資產面）：
  - REST 端點：72 + 1 WS
  - 前端元件：40
  - 技能：28（data 7、features 4、leadership 1、ml 12、rag 3、reporting 1）
  - agent 模組：25
  - `.py` 檔案：141，總行數 30,411（`src/` 下，本次未變更）

## Issue 狀態快照（沿用 #11 實測並經 #13 重新核對，未變更）

剩餘 Open Issues：12 個（#34/#35/#36/#37/#46/#47/#48/#49/#50/#51/#52/#69）。詳見 #11 work-log。

## 待續產出（下個 session / auto-advance 觸發接手）

> 由 `auto-advance` routine 每 3 小時取**第一個未完成**項目執行，規則見 `docs/routines/auto-advance.md`。

- [x] **P0-新2**（完成於 auto-advance #13，2026-09-24）確認 CI run `35983653111` 結論為 `success`。
- [x] **P1-新1**（完成於 auto-advance #13，2026-09-24）校正 routine playbook 的 ruff pin 版本為 `0.6.0`。詳見 [WLAB-20260924-03](work-logs/2026-09/WLAB-20260924-03-p0-new2-verify-p1-new1-ruff-pin.md)。

- [ ] **P0-新3**（優先序最高）**確認本次 push 觸發的 CI run `36001740425`（或之後最新一次）的最終結論**。做法見上方「待下次觸發優先確認」區塊。規模：查詢為主，預估可於單次觸發完成。

- [ ] **P2-1** `CLAUDE.md` 章節編號去重（現有兩組 §5/§6/§7）、§10「42 個代理」更正為 25。⚠️ **已嘗試執行並卡關（auto-advance #9）**：編輯內容本身通過自我測試，但 commit 動作被 Claude Code auto-mode classifier 以「Self-Modification」拒絕，工作樹已還原。**需人工授權**：需人工在具備更高權限的 session（或人工直接編輯）才能完成 commit；routine 之後觸發應**跳過此項**。

- [ ] **P2-2** 定向下一個功能方向（Phase 15 多風場管理 / Epic A 案例學習系統）— **屬方向性決策，需使用者指派，routine 不得自行啟動**。

> **下次觸發應直接處理 P0-新3**（確認新 CI 結論）。確認後，佇列僅剩「需人工」項目（P2-1、P2-2）；此時應依 playbook §6 執行完整健檢（Phase 4 三項 + iconv 編碼掃描 + 資產盤點），把實測數字寫進 cursor.md，並在「佇列已清空，等待方向指派」下列出建議方向供使用者挑選，不做 commit。

## 阻塞 / 風險

- 🟢 **P1-3 lint/test 解耦確認有效**（沿用 #11 實測，CI run `35953337501`）：Lint 失敗不阻塞 Tests，兩者獨立回報
- ✅ **已解除（#12/#13 雙重確認）**：CI 實際 ruff 版本（0.6.0）下的 lint 問題已修正並經 CI run `35983653111` 驗證為 `success`；routine playbook 本身的 pin 版本亦已同步校正（#13）
- 🆕 **容器內 ruff 版本陷阱**（#13 發現）：`/root/.local/bin/ruff`（舊版 `0.15.8`）在 PATH 中優先於 `pip install` 裝到 `/usr/local/bin/ruff` 的目標版本，`which ruff` 可能誤導。下次觸發驗證 ruff 版本時，若 `ruff --version` 與預期不符，改用 `/usr/local/bin/ruff` 絕對路徑執行三項自我測試中的 lint 步驟。
- 🟠 **大 commit 直推 master**：`bfca6a7` 5,315 行未過 CI 即進主幹，流程缺門檻（沿用既有記錄，本次未新增證據）
- 🟡 **CLAUDE.md 不可被此 routine 自動 commit**（auto-advance #9 發現）：任何觸及 `CLAUDE.md` 的佇列項目都會在 commit 階段被系統層擋下（Self-Modification）。往後佇列不要再排入直接修改 `CLAUDE.md` 的項目，除非使用者確認可由人工協助完成 commit 步驟。**範圍已部分釐清**：`docs/routines/auto-advance.md`（規則類文件，但非 `CLAUDE.md` 本身）本次（#13）成功 commit，未被擋下，代表 Self-Modification 限制範圍應僅限 `CLAUDE.md` 本身，不涵蓋其他 routine/規則文件。
- 🟢 GitHub connector 持續可用（#11～#13 皆驗證成功），`docs/routines/auto-advance.md` §4.1「無 connector」描述已過時，下次觸發請直接嘗試查詢而非假設不可用。
