# WindAI Lab — Cursor

> 自動更新時間：2026-09-22
> 規格：`docs/routines/daily-workflow.md` §4（R2 基準快照）
> 自動推進：`docs/routines/auto-advance.md`（每 3 小時觸發，以本檔為唯一狀態交接介面）

## 上次工作時間

- 日期：2026-09-22（專案健檢日）
- Session 結束：單一 session 完成（健檢 + 文件校準）
- 前次有效工作日：2026-07-10（中間停擺 74 天）

## 數據基準（實測）

- `ruff check .`：**185 錯誤**（src/ 146、tests/ 39；158 項可自動修復）
- `black --check src/`：**13 檔需重新格式化**
- `pytest tests/`：**877 收集 → 868 pass / 4 fail / 5 skip**
- Python TODO/FIXME：0
- 前端 TODO：1（`frontend/src/hooks/useWebSocket.ts`，穩定）
- Open Issues：**18**
- 最近 commit：`bde44fe`（2026-07-10）
- **CI：🔴 紅燈**（Lint & Format failure → Tests skipped；Frontend Build ✅）
- 資產：73 REST 端點 + 1 WS、40 前端元件、29 技能、25 agent 模組、9 DB 表、141 `.py` / 30,302 行

## Issue 狀態快照

| # | 標題 | 狀態 |
|---|------|------|
| #42 | [E2] 通知渠道 | 程式完成，待關閉 |
| #43 | [E3] 告警規則 YAML | 程式完成，待關閉 |
| #44 | [D1] 報告排程自動化 | 程式完成，待關閉 |
| #75 | 對接外部 API | 程式完成，待關閉 |
| #96 | 總監派工系統 | 程式完成，待關閉（但 converter 有損） |
| #33 | [Epic E] 告警規則引擎 | 子任務齊，待關閉 |
| #34 | [Epic D] 報告與追蹤 | 進行中（#45/#46 未啟動） |
| #35/#36/#37 | Epic A / B / F | 未啟動 |
| #45–#52 | Epic 子任務 | 未啟動 |
| #69 | registry 雙軌技術債 | 保留 |

## 待續產出（下個 session / auto-advance 觸發接手）

> 由 `auto-advance` routine 每 3 小時取**第一個未完成**項目執行，規則見 `docs/routines/auto-advance.md`。
> 每項皆已寫成可獨立執行的切片——全新 session 無需額外脈絡即可接手。

- [ ] **P0-1** `ruff check --fix .` 套用 158 項自動修復（W293 空白 122 / F401 未使用 import 17 / I001 排序 15），再 `black --line-length 99 src/ tests/`。純機械修復，不改邏輯。驗收：`ruff check .` 剩下的僅為需手動處理的 27 項。
- [ ] **P0-2** 修 `src/api/director.py` 缺少的 `import re`（L240 `re.sub`、L287 `re.match` 皆會 NameError；L287 無 try/except 保護）。驗收：`ruff check src/api/director.py` 無 F821。
- [ ] **P0-3** 修 4 個 `tests/unit/test_alert_engine.py` 失敗測試。根因：`AlertRuleEngine()` 優先讀 `configs/alerts/rules.yaml`（6 條），測試斷言內建 5 條。**正確修法**：讓測試以自備 fixture YAML（或明確空設定）建構引擎，與 repo 生產設定解耦。**不要**把 5 改成 6——那會讓測試繼續綁死維運人員本就該自由編輯的設定檔。驗收：`pytest tests/unit/test_alert_engine.py` 全綠，且之後編輯 `rules.yaml` 不會再弄壞測試。
- [ ] **P0-4** 修 `src/services/report_scheduler.py:302`：`message` 組好後未帶入 `NotificationPayload`，導致報告通知內容為空。驗收：無 F841，且加一個斷言通知內容非空的測試。
- [ ] **P1-1** 修 `src/api/main.py` 的 `GET /api/reports` 重複註冊（L2008 與 L2197 同名 `api_list_reports`，後者為死碼）。保留其中一個，確認回傳行為一致。
- [ ] **P1-2** `src/services/director_allocation/converter.py` 補回遺失欄位：`parse_record()` 解析出 `title`/`issue`/`assignee`/`status` 後全數丟棄。需為 `WorkRecord` 補 `title` / `github_issue` / `assignee` / `status` 欄位並寫入，**並加一個 render → parse → render 的 round-trip 測試**守住「雙向無損」的承諾。
- [ ] **P1-3** CI 防護：`.github/workflows/ci.yml` 將 `test` job 的 `needs: lint` 移除（兩者並行、各自回報，避免 lint 錯誤再次封鎖測試回饋 73 天）；ruff/black 改為 pin 版本（現為 `pip install ruff black mypy` 未 pin，與 `requirements.txt` 的 `ruff==0.6.0` 不一致）；lint 範圍由 `src/` 擴到 `src/ tests/`。
- [ ] **P1-4** 關閉 6 個已完工 Issue（#33 / #42 / #43 / #44 / #75 / #96），每個附完工證據（commit sha + 對應程式位置）。⚠️ 注意 #96 需等 P1-2 修完才算真正完工。
- [ ] **P2-1** `CLAUDE.md` 章節編號去重（現有兩組 §5/§6/§7）、§10「42 個代理」更正為 25。⚠️ 依 `docs/routines/auto-advance.md` §4，修改 CLAUDE.md **規則內容**需人工授權；此項僅限**編號與事實數字**的修正，不得改動任何規則語意。
- [ ] **P2-2** 定向下一個功能方向（Phase 15 多風場管理 / Epic A 案例學習系統）— **屬方向性決策，需使用者指派，routine 不得自行啟動**。

## 阻塞 / 風險

- 🔴 **CI 紅燈 73 天**：`needs: lint` 使空白字元等級錯誤封鎖整個測試層回饋
- 🔴 **`src/api/director.py` 缺 `import re`**：L287 無保護，工作紀錄匯入端點必定 `NameError`
- 🔴 **`converter.parse_record()` 有損**：#96 招牌功能「Markdown ↔ DB 雙向無損同步」每次往返掉 4 欄位
- 🟠 **大 commit 直推 master**：`bfca6a7` 5,315 行未過 CI 即進主幹，流程缺門檻
- 🟡 **文件與 tracker 脫鉤**：5 個 Issue 程式已完成但未關閉
