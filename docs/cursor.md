# WindAI Lab — Cursor

> 自動更新時間：2026-09-24（auto-advance #11 觸發後）
> 規格：`docs/routines/daily-workflow.md` §4（R2 基準快照）
> 自動推進：`docs/routines/auto-advance.md`（每 3 小時觸發，以本檔為唯一狀態交接介面）

## 上次工作時間

- 日期：2026-09-24
- Session：`auto-advance` 第 11 次觸發。**本次觸發首次確認掛載 GitHub connector**（`mcp__github__get_me` 驗證身份為 repo owner `dofliu`），過去 §4.1 標註「本 Routine 無 GitHub connector」的技術限制已解除。完成 P1-4：逐檔核實並關閉 6 個已完工 Issue。過程中意外定位出 CI 持續紅燈的真正根因（ruff 版本落差，見下方新增 P0）。本次無程式碼變更，故無 commit；GitHub 端動作（留言 + 關閉 Issue）已完成。
- 前次有效工作日：2026-09-23（auto-advance #9，commit `2712163`；P2-1 因 Self-Modification 被擋）

## ⚠️ 重要修正：本 Routine 現在有 GitHub connector

`docs/routines/auto-advance.md` §4.1 描述的「本 Routine 未攜帶 GitHub connector」已**不再準確**——本次觸發的 session 實測 `mcp__github__*` 工具可用且已驗證身份。下次觸發應：
1. 直接嘗試呼叫 `mcp__github__get_me` 確認 connector 是否存在，不要一律假設不存在
2. 若可用，§4.1 表格中標「❌ 不可用」的能力（查 CI 狀態、開關 Issue）視為**可用**
3. 若不可用（例如 connector 被移除），才回退到 §4.1 的舊行為

## 數據基準（實測，auto-advance #11）

- `ruff check .`（本地舊 pin `ruff==0.15.8`）：**19 錯誤**（與 #8/#9/#10 基準相同，但**此版本與 CI 實際使用版本不同，此數字具誤導性，見下方 P0**）
- `ruff check src/ tests/`（**CI 實際 pin 的 `ruff==0.6.0`**，經 `get_job_logs` 讀取 Actions 記錄證實）：**25 錯誤**（9× UP038、4× E741、3× B904、6× N815、1× TCH003、1× SIM108、1× E402，明細見下方 P0）
- `python3 -m black --check --line-length 99 src/ tests/`：**全綠**，181 檔案（兩個 ruff 版本下 black 結果一致；⚠️ 呼叫務必用 `python3 -m black` 避免 PATH 上非 pin 版本誤判）
- `pytest tests/`：**877 收集 → 872 pass / 0 fail / 5 skip**（與 #8/#9/#10 基準相同）
- **CI 實測（透過 GitHub Actions API 直接核對，非沿用假設）**：
  - 最新 `claude/auto-advance` push（`4d58651`，run `35953337501`）：Lint & Format **failure**（Ruff check 25 錯誤）、Tests **success**、Frontend Build **success**
  - ✅ 確認 P1-3（`needs: lint` 解耦）確實生效：Lint 失敗不再阻塞 Tests，兩者獨立回報
  - `master` 分支最後一次 CI 觸發是 2026-04-06（PR #65 合併），此後無新 push/PR 觸發 master CI（auto-advance 只在自己的分支工作，符合規則）
- Open Issues：**12**（18 → 12，因本次關閉 6 個已完工 Issue：#33/#42/#43/#44/#75/#96）
- 前端 TODO：1（`frontend/src/hooks/useWebSocket.ts`，穩定）
- 最近 commit：`4d58651`（2026-09-24，auto-advance #10 的健檢更新）——本次觸發無新 commit（純 GitHub API 操作，無程式碼變更）
- 資產（沿用 #10 實測，本次未變更程式碼）：
  - REST 端點：72 + 1 WS
  - 前端元件：40
  - 技能：28（data 7、features 4、leadership 1、ml 12、rag 3、reporting 1）
  - agent 模組：25
  - `.py` 檔案：141，總行數 30,411（`src/` 下）

## Issue 狀態快照（實測，非沿用假設）

| # | 標題 | 狀態 |
|---|------|------|
| #42 | [E2] 通知渠道 | ✅ 已於 2026-09-24 關閉（completed） |
| #43 | [E3] 告警規則 YAML | ✅ 已於 2026-09-24 關閉（completed） |
| #44 | [D1] 報告排程自動化 | ✅ 已於 2026-09-24 關閉（completed） |
| #75 | 對接外部 API | ✅ 已於 2026-09-24 關閉（completed） |
| #96 | 總監派工系統（階段一範圍） | ✅ 已於 2026-09-24 關閉（completed） |
| #33 | [Epic E] 告警規則引擎 | ✅ 已於 2026-09-24 關閉（completed，子項 E1/E2/E3 均齊） |
| #34 | [Epic D] 報告與追蹤 | 進行中（#45/#46 未啟動） |
| #35/#36/#37 | Epic A / B / F | 未啟動 |
| #46–#52 | Epic 子任務 | 未啟動 |
| #69 | registry 雙軌技術債 | 保留 |

剩餘 Open Issues：12 個（#34/#35/#36/#37/#46/#47/#48/#49/#50/#51/#52/#69）。

## 待續產出（下個 session / auto-advance 觸發接手）

> 由 `auto-advance` routine 每 3 小時取**第一個未完成**項目執行，規則見 `docs/routines/auto-advance.md`。

- [x] **P1-4**（完成於 auto-advance #11，2026-09-24）關閉 6 個已完工 Issue（#33/#42/#43/#44/#75/#96），每個附完工證據（commit sha + 對應程式位置，逐檔核實而非沿用舊標註）。詳見 [WLAB-20260924-01](work-logs/2026-09/WLAB-20260924-01-close-completed-issues.md)。

- [ ] **P0-新1**（優先序最高——這才是 CI 持續紅燈的真正根因）**修正 CI 實際 ruff 版本（0.6.0）下的 25 項錯誤，並校正 routine 本地自我測試的 pin 版本**。
  背景：`docs/routines/auto-advance.md` Phase 0 指示本地 pin `ruff==0.15.8`，但 `.github/workflows/ci.yml` 實際 pin 的是 `ruff==0.6.0`（與 `requirements.txt` 一致）。兩版本規則集不同，導致本地「19 錯誤基準不變」的自我測試結果**從未真正代表 CI 會綠燈**。
  執行步驟：
  1. `pip install ruff==0.6.0`（**改用此版本做本次自我測試**，之後 routine playbook 的 Phase 0 也應同步修正 pin 版本為 `0.6.0`）
  2. 修正以下 25 項（可安全修正，均為小範圍語意不變的修正）：
     - `src/services/director_allocation/models.py:21-26`：6 個 `wLab/wData/wAI/wDomain/wEng/wRes` class 屬性觸發 N815（mixedCase）——這些是刻意設計的 namespace 常數（見 CLAUDE.md §9 命名空間隔離），**不應改名**，應在對應行加 `# noqa: N815` 並註明原因（CLAUDE.md §4 允許的例外情況）
     - `src/services/notifiers/base.py:7`：TCH003，將 `from datetime import datetime` 移入 `if TYPE_CHECKING:` 區塊（若 `datetime` 僅用於型別註記）或確認是否為 runtime 使用，非 runtime 才移動
     - 9 處 UP038（`src/skills/leadership/director_review.py:183,308`、`src/skills/reporting/report_generator.py:115,248,393,406,408,413,415`）：`isinstance(x, (int, float))` → `isinstance(x, int | float)`
     - 4 處 E741（`src/api/director.py:393`、`src/services/director_allocation/allocator.py:107,173`、`src/services/director_allocation/converter.py:495`）：變數名 `l` 改為不易混淆的名稱（如 `line`/`log_entry`，依上下文判斷）
     - 3 處 B904（`src/api/main.py:2201,2217,2274`）：`except` 區塊內 `raise` 補上 `from err` 或 `from None`
     - 1 處 SIM108（`src/services/director_allocation/converter.py:41`）：改為三元運算子
     - 1 處 E402（`src/api/main.py:183`）：模組層級 import 不在檔案頂部，需確認是否有意為之（如避免循環 import），若無特殊原因則搬移到頂部
  3. 全部修完後以 `ruff==0.6.0` + `black` + `pytest` 三項自我測試全綠才 commit
  4. commit 訊息需說明「改用 CI 實際 pin 的 ruff==0.6.0 驗證，非沿用過時的 0.15.8 基準」
  規模預估：單次觸發可完成（7 個檔案，25 處小修正，符合 §7 上限）。

- [ ] **P2-1** `CLAUDE.md` 章節編號去重（現有兩組 §5/§6/§7）、§10「42 個代理」更正為 25。⚠️ **已嘗試執行並卡關（auto-advance #9）**：編輯內容本身通過自我測試，但 commit 動作被 Claude Code auto-mode classifier 以「Self-Modification」拒絕，工作樹已還原。**需人工授權**：需人工在具備更高權限的 session（或人工直接編輯）才能完成 commit；routine 之後觸發應**跳過此項**。

- [ ] **P2-2** 定向下一個功能方向（Phase 15 多風場管理 / Epic A 案例學習系統）— **屬方向性決策，需使用者指派，routine 不得自行啟動**。

> **下次觸發應直接處理 P0-新1**（已解除「佇列已清空」狀態——這是本次觸發新發現的真實可自主執行項目，優先序高於 P2-1/P2-2）。

## 阻塞 / 風險

- 🟢 **P1-3 lint/test 解耦確認有效**（實測 CI run `35953337501`）：Lint 失敗不再阻塞 Tests，兩者獨立回報，符合設計預期
- 🔴 **CI 持續紅燈的真正根因已定位（新發現）**：routine 本地自我測試的 ruff pin 版本（0.15.8）與 CI 實際使用版本（0.6.0）不一致，導致「本地全綠」長期無法代表「CI 會綠」。這解釋了為何 P1-3（lint/test 解耦，已於 #7 完成）之後 CI 的 Lint job 依然持續 failure。修正方式見上方 P0-新1。
- 🟠 **大 commit 直推 master**：`bfca6a7` 5,315 行未過 CI 即進主幹，流程缺門檻（沿用既有記錄，本次未新增證據）
- 🟡 **新發現（auto-advance #9）：CLAUDE.md 不可被此 routine 自動 commit**：任何觸及 `CLAUDE.md` 的佇列項目都會在 commit 階段被系統層擋下（Self-Modification）。往後佇列不要再排入直接修改 `CLAUDE.md` 的項目，除非使用者確認可由人工協助完成 commit 步驟。
- ✅ **已解除（auto-advance #10 記錄的阻塞，本次已解除）**：P1-4 因無 GitHub connector 卡住——本次觸發確認 connector 已可用，P1-4 完工。`docs/routines/auto-advance.md` §4.1 的「無 connector」描述已過時，下次觸發請先驗證而非假設。
