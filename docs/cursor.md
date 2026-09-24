# WindAI Lab — Cursor

> 自動更新時間：2026-09-24（auto-advance #10 觸發後）
> 規格：`docs/routines/daily-workflow.md` §4（R2 基準快照）
> 自動推進：`docs/routines/auto-advance.md`（每 3 小時觸發，以本檔為唯一狀態交接介面）

## 上次工作時間

- 日期：2026-09-24
- Session：`auto-advance` 第 10 次觸發。待續產出佇列僅剩 P1-4 / P2-1 / P2-2，三項皆標註「需人工」，視為**佇列已清空**（依 `docs/routines/auto-advance.md` §6）。改跑一次完整健檢（Phase 4 三項 + 編碼掃描 + 資產盤點），數字已更新於下方。**本次無 commit**（§6 步驟 5：確實無事不 commit）。
- 前次有效工作日：2026-09-23（auto-advance #8，commit `e2a7fff`；#9 因 Self-Modification 被擋，無 commit）

## 數據基準（實測，auto-advance #10，未變更任何程式碼）

- `ruff check .`：**19 錯誤**（與 #8/#9 基準相同）
- `python3 -m black --check --line-length 99 src/ tests/`：**全綠**，181 檔案（⚠️ 本容器 PATH 上 `black` 預設為 `/root/.local/bin/black` 非 pin 版本，務必用 `python3 -m black` 呼叫避免誤判）
- `pytest tests/`：**877 收集 → 872 pass / 0 fail / 5 skip**（與 #8/#9 基準相同）
- 編碼掃描（`iconv -f UTF-8 -t UTF-8`，`src/ tests/ docs/` 內 `.py`/`.md`）：**0 個非 UTF-8 檔案**
- Python TODO/FIXME：0
- 前端 TODO：1（`frontend/src/hooks/useWebSocket.ts`，穩定）
- Open Issues：**18**（未變，本 routine 無 GitHub connector 無法核對）
- 最近 commit：`2712163`（2026-09-23，`docs: 更新 cursor.md，記錄 P2-1 因 Self-Modification 被系統層擋下`）——本次觸發無新 commit
- **CI：狀態未知**（本 routine 無 GitHub connector，無法查詢 Actions；沿用既有基準）
- 資產（本次重新實測）：
  - REST 端點：**72**（`src/api/main.py` + `src/api/director.py`，符合 P1-1 移除重複 `/api/reports` 後的預期值，73→72）+ 1 WS
  - 前端元件：**40**（`frontend/src/**/*.tsx`）
  - 技能（`src/skills/` 下扣除 `__init__.py`/`base.py`/`registry.py`）：**28**（data 7、features 4、leadership 1、ml 12、rag 3、reporting 1；舊基準寫 29，屬前次未精算的估計值，本次為實測數）
  - agent 模組：**25**（`src/agents/{leadership,data,ai,domain,engineering,research}/*.py`，與 `CLAUDE.md` §2 表格逐一核對一致）
  - DB 表：**沿用既有 9**（grep `__tablename__` 得 0 筆，本專案程式碼內無 SQLAlchemy ORM 表定義，「9 DB 表」應為架構文件中的規劃/邏輯表數而非可由程式碼驗證的實測值；建議下次有餘裕時對照 `docs/architecture-design.md` 澄清定義後再更新此數字）
  - `.py` 檔案：**141**，總行數 **30,411**（`src/` 下）

## Issue 狀態快照

| # | 標題 | 狀態 |
|---|------|------|
| #42 | [E2] 通知渠道 | 程式完成，待關閉 |
| #43 | [E3] 告警規則 YAML | 程式完成，待關閉 |
| #44 | [D1] 報告排程自動化 | 程式完成，待關閉 |
| #75 | 對接外部 API | 程式完成，待關閉 |
| #96 | 總監派工系統 | 程式完成，待關閉（P1-2 已修 converter 遺損問題，本項阻塞已解除） |
| #33 | [Epic E] 告警規則引擎 | 子任務齊，待關閉 |
| #34 | [Epic D] 報告與追蹤 | 進行中（#45/#46 未啟動） |
| #35/#36/#37 | Epic A / B / F | 未啟動 |
| #45–#52 | Epic 子任務 | 未啟動 |
| #69 | registry 雙軌技術債 | 保留 |

## 待續產出（下個 session / auto-advance 觸發接手）

> 由 `auto-advance` routine 每 3 小時取**第一個未完成**項目執行，規則見 `docs/routines/auto-advance.md`。
> 每項皆已寫成可獨立執行的切片——全新 session 無需額外脈絡即可接手。

- [x] **P0-1**（完成於 auto-advance #1，commit `ab3b9c4`）`ruff check --fix .` 套用 158 項自動修復 + `black --line-length 99 src/ tests/`。詳見 [WLAB-20260922-02](work-logs/2026-09/WLAB-20260922-02-ruff-autofix.md)。
- [x] **P0-2**（完成於 auto-advance #2，commit `5084a8f`）修 `src/api/director.py` 缺少的 `import re`（L245 `re.sub`、L294 `re.match` NameError 已解）。詳見 [WLAB-20260922-03](work-logs/2026-09/WLAB-20260922-03-director-import-re.md)。
- [x] **P0-3**（完成於 auto-advance #3，commit `e9d459e`）修 4 個 `tests/unit/test_alert_engine.py` 失敗測試。詳見 [WLAB-20260922-04](work-logs/2026-09/WLAB-20260922-04-alert-engine-test-decouple.md)。
- [x] **P0-4**（完成於 auto-advance #4，commit `2e6fde5`）修 `src/services/report_scheduler.py:318` 報告通知內文遺失問題。詳見 [WLAB-20260922-05](work-logs/2026-09/WLAB-20260922-05-report-scheduler-notification-message.md)。
- [x] **P1-1**（完成於 auto-advance #5，commit `47ca81d`）修 `src/api/main.py` 的 `GET /api/reports` 重複註冊死碼。詳見 [WLAB-20260922-06](work-logs/2026-09/WLAB-20260922-06-main-duplicate-reports-route.md)。
- [x] **P1-2**（完成於 auto-advance #6，commit `b550570`）`converter.parse_record()` 補回遺失欄位：`WorkRecord` 新增 `title`/`github_issue`/`assignee`/`status`；`parse_record()` 寫入這些欄位不再丟棄；`render_record()` 三個中介資料參數改為可選並回退採用 record 自身欄位（既有呼叫端不受影響）；新增 render → parse → render 往返測試。詳見 [WLAB-20260922-07](work-logs/2026-09/WLAB-20260922-07-converter-record-metadata-roundtrip.md)。
- [x] **P1-3**（完成於 auto-advance #7，commit `1b5ba1f`）CI 防護：`.github/workflows/ci.yml` 的 `test` job 移除 `needs: lint`（兩者並行、各自回報）；ruff/black/mypy 改為 pin 版本 `ruff==0.6.0`/`black==24.8.0`/`mypy==1.11.0`，與 `requirements.txt` 一致；lint 範圍由 `src/` 擴到 `src/ tests/`（已本地驗證擴大範圍不會新增紅燈）。詳見 [WLAB-20260922-08](work-logs/2026-09/WLAB-20260922-08-ci-lint-test-decouple.md)。⚠️ 實際 CI Actions 執行結果需人工或下次有 GitHub connector 的 session 核對。
- [x] **P2-0**（完成於 auto-advance #8，commit `e2a7fff`）`converter.parse_record()` 補回 `created_at`/`closed_at` 雙向解析：`render_record()` 於 `record.closed_at` 存在時新增 `> **結束日期**：` metadata 行；`parse_record()` 解析「建立日期」「結束日期」回填 `WorkRecord`，修復多輪 round-trip 後 `status_str` 從 `completed` 退化為 `in_progress` 的問題。詳見 [WLAB-20260923-01](work-logs/2026-09/WLAB-20260923-01-converter-created-closed-at-roundtrip.md)。
- [ ] **P1-4** 關閉 6 個已完工 Issue（#33 / #42 / #43 / #44 / #75 / #96），每個附完工證據（commit sha + 對應程式位置）。✅ #96 的 converter 遺損阻塞（P1-2 / P2-0）已解除，可視為完工。⚠️ **需人工執行**：auto-advance Routine 無 GitHub connector（見 `docs/routines/auto-advance.md` §4.1），觸發時請直接跳過此項。
- [ ] **P2-1** `CLAUDE.md` 章節編號去重（現有兩組 §5/§6/§7）、§10「42 個代理」更正為 25。⚠️ **已嘗試執行並卡關（auto-advance #9）**：編輯內容本身通過自我測試（不影響 ruff/black/pytest），但 commit 動作被 **Claude Code auto-mode classifier 以「Self-Modification」拒絕**——CLAUDE.md 是治理 Claude 自身工作守則的檔案，系統層不允許 Claude 自動 commit 對它的修改，即使內容僅為編號/事實數字修正。工作樹已還原，**未留下未 commit 的改動**。⚠️ **需人工授權**：此項需要人工在具備更高權限的 session（或人工直接編輯）才能完成 commit；auto-advance routine 之後觸發應**跳過此項**（除非人工調整了 auto-mode 的分類規則），直接取下一項。
- [ ] **P2-2** 定向下一個功能方向（Phase 15 多風場管理 / Epic A 案例學習系統）— **屬方向性決策，需使用者指派，routine 不得自行啟動**。

> ⚠️ **佇列狀態（auto-advance #10 起）**：以上三項皆為「需人工」，routine 可自主執行的佇列**目前為空**。下次觸發應直接依 §6 跑健檢並回報，除非使用者已新增可自主處理的項目、或人工已解除 P1-4／P2-1 的阻塞。**建議的下一個方向（供使用者挑選，非本 routine 自行啟動）**：
> 1. Phase 15：多風場管理（新增風場切換 / 跨場比較功能）
> 2. Epic A：案例學習系統（#35，尚未啟動的子任務）
> 3. 人工協助完成 P2-1（CLAUDE.md 編號去重）與 P1-4（關閉 6 個已完工 Issue）以清空技術債佇列

## 阻塞 / 風險

- 🟢 **CI 紅燈 73 天成因已修**（P1-3，commit `1b5ba1f`）：`needs: lint` 已移除，lint 與 test 並行回報；⚠️ 實際 Actions 執行結果尚未經人工核對，下次有 GitHub connector 的 session 應確認並行是否如預期運作
- 🟠 **大 commit 直推 master**：`bfca6a7` 5,315 行未過 CI 即進主幹，流程缺門檻
- 🟡 **文件與 tracker 脫鉤**：5 個 Issue 程式已完成但未關閉（需人工，見 P1-4）
- 🟡 **新發現（auto-advance #9）：CLAUDE.md 不可被此 routine 自動 commit**：任何觸及 `CLAUDE.md` 的佇列項目都會在 commit 階段被系統層擋下（Self-Modification），與 `docs/routines/auto-advance.md` §4 的「需人工授權」清單性質不同——這不是規則面的自我禁止，而是執行環境的硬性限制。建議：往後佇列不要再排入直接修改 `CLAUDE.md` 的項目，除非使用者確認可由人工協助完成 commit 步驟。
- 🟡 **新發現（auto-advance #10）：可自主執行的佇列已空**：P1-4（需 GitHub connector）、P2-1（CLAUDE.md 自我修改被擋）、P2-2（方向性決策）皆卡在「需人工」，routine 已連續 2 次觸發（#9、#10）無法產出新 commit。需使用者其中之一：(a) 指派新的技術方向（見上方建議清單）、(b) 協助完成 P2-1 的 commit、(c) 為 routine 掛上 GitHub connector 以解除 P1-4。
