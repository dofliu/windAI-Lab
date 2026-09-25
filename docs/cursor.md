# WindAI Lab — Cursor

> 自動更新時間：2026-09-25（auto-advance #15 觸發後）
> 規格：`docs/routines/daily-workflow.md` §4（R2 基準快照）
> 自動推進：`docs/routines/auto-advance.md`（每 3 小時觸發，以本檔為唯一狀態交接介面）

## 上次工作時間

- 日期：2026-09-25
- Session：`auto-advance` 第 15 次觸發。佇列僅剩需人工項目（P2-1 / P2-2），依 playbook §6 執行完整健檢（自我測試三項 + iconv 編碼掃描 + 資產盤點 + GitHub Issue/CI 核對）。實測與 #14 基準完全一致，無回歸、無新問題，本次**無程式碼變更、無 commit**。
- 前次有效工作日：2026-09-24（auto-advance #14，健檢 only，見 [WLAB-20260924-04](work-logs/2026-09/WLAB-20260924-04-p0-new3-ci-verify-health-check.md)）；最近一次有實質 commit 為 auto-advance #13（`253f80f`，見 [WLAB-20260924-03](work-logs/2026-09/WLAB-20260924-03-p0-new2-verify-p1-new1-ruff-pin.md)）

## 數據基準（實測，auto-advance #15）

- 環境：新容器，依 playbook Phase 0 重裝，pin `ruff==0.6.0`、`black==24.8.0`（與 CI 一致）
- `ruff check .`（`0.6.0`，`/usr/local/bin/ruff`）：**0 錯誤**
- `python3 -m black --check --line-length 99 src/ tests/`：**全綠**，181 檔案
- `python3 -m pytest tests/ -q`：**872 pass / 0 fail / 5 skip**（與 #8～#14 基準相同，本次無回歸）
- `iconv` 編碼掃描（`src/` `tests/` `docs/` 下 `.py`/`.md`）：**0 個非 UTF-8 檔案**
- CI：最新 push（run `36023409328`，#14 的健檢 commit `4baf0db`）已確認 **conclusion=success**
- Open Issues：12（`list_issues` state=OPEN 核對，號碼與 #11～#14 完全一致：#34/35/36/37/46/47/48/49/50/51/52/69，無新增無關閉）
- 前端 TODO：1（`frontend/src/hooks/useWebSocket.ts:266`，穩定，本次未重新掃描細節）
- 最近 commit：`4baf0db`（2026-09-24，auto-advance #14；本次 #15 未變更程式碼，僅文件）
- 資產：
  - REST 端點：73（含 1 WS，與 #10～#14 基準一致）
  - 前端元件：41（本次 grep 統計為 41，#14 記錄為 39；未變更 `frontend/`，維持既有結論——純 grep `export` 口徑本身在每次觸發間有 ±1~2 誤差，非實際變化。建議下次需要精確值時改用 AST parser）
  - 技能：28（重新以 `find src -path "*skills*" -name "*.py"` 排除 `__pycache__`/`__init__.py`/`base.py`/`registry.py` 後核實為 28，與 #10～#14 基準一致；注意勿直接用未排除的 grep，會誤算為 37）
  - agent 模組：25
  - `.py` 檔案：141，總行數 30,411（`src/` 下，與 #14 完全一致）

## Issue 狀態快照（#15 重新核對，未變更）

剩餘 Open Issues：12 個（#34/#35/#36/#37/#46/#47/#48/#49/#50/#51/#52/#69）。詳見 #11 work-log。

## 待續產出（下個 session / auto-advance 觸發接手）

> 由 `auto-advance` routine 每 3 小時取**第一個未完成**項目執行，規則見 `docs/routines/auto-advance.md`。

**佇列持續清空，等待方向指派（#15 再次確認，無新項目）。** 目前僅剩以下需人工項目：

- [ ] **P2-1** `CLAUDE.md` 章節編號去重（現有兩組 §5/§6/§7）、§10「42 個代理」更正為 25。⚠️ **已嘗試執行並卡關（auto-advance #9）**：編輯內容本身通過自我測試，但 commit 動作被 Claude Code auto-mode classifier 以「Self-Modification」拒絕，工作樹已還原。**需人工授權**：需人工在具備更高權限的 session（或人工直接編輯）才能完成 commit；routine 之後觸發應**跳過此項**。

- [ ] **P2-2** 定向下一個功能方向 — **屬方向性決策，需使用者指派，routine 不得自行啟動**。建議候選（供使用者挑選）：
  1. **Phase 15 多風場管理**
  2. **Epic A 案例學習系統**（Issue #35，含子項 #47 案例自動記錄 / #48 相似案例推薦 / #49 案例推薦 API+前端）
  3. **Epic B 故障知識體系**（Issue #36，含子項 #50 故障知識圖譜 / #51 維護效果追蹤）
  4. **Epic D 報告與追蹤**（Issue #34，含子項 #46 追蹤儀表板）
  5. **Epic F 學術論文規劃**（Issue #37，含子項 #52 投稿策略與時程）
  6. 人工協助完成 P2-1（`CLAUDE.md` 章節整理）

> **下次觸發**：佇列現只有需人工項目，應依 playbook §6 執行完整健檢（三項自我測試 + iconv 掃描 + 資產盤點 + Issue 核對），確認無新問題後維持「等待方向指派」狀態，**不做 commit**（除非使用者已於期間指派新方向或發現新的實質缺陷）。

## 阻塞 / 風險

- 🟢 **P1-3 lint/test 解耦確認有效**（沿用 #11 實測，CI run `35953337501`）：Lint 失敗不阻塞 Tests，兩者獨立回報
- ✅ **ruff 版本 pin 一致性已解除**（#12/#13 雙重確認）：CI 實際 ruff 版本（0.6.0）下的 lint 問題已修正並驗證；routine playbook 本身的 pin 版本亦已同步校正
- 🆕 **容器內 ruff 版本陷阱**（#13 發現，#14/#15 再次確認）：`/root/.local/bin/ruff`（舊版 `0.15.8`）在 PATH 中優先於 `pip install` 裝到 `/usr/local/bin/ruff` 的目標版本，`which ruff` 可能誤導。驗證 ruff 版本時，改用 `/usr/local/bin/ruff` 絕對路徑執行 lint 步驟。同理 `pytest` 執行也應優先用 `python3 -m pytest`，而非直接呼叫可能指向舊版環境的 `pytest` binary（#14 發現 `/root/.local/bin/pytest` 缺少 pandas，改用 `python3 -m pytest` 解決）。
- 🟠 **大 commit 直推 master**：`bfca6a7` 5,315 行未過 CI 即進主幹，流程缺門檻（沿用既有記錄，本次未新增證據）
- 🟡 **CLAUDE.md 不可被此 routine 自動 commit**（auto-advance #9 發現）：任何觸及 `CLAUDE.md` 的佇列項目都會在 commit 階段被系統層擋下（Self-Modification）。往後佇列不要再排入直接修改 `CLAUDE.md` 的項目，除非使用者確認可由人工協助完成 commit 步驟。`docs/routines/` 下的規則類文件不在此限（#13 已驗證可正常 commit）。
- 🟢 GitHub connector 持續可用（#11～#15 皆驗證成功），`docs/routines/auto-advance.md` §4.1「無 connector」描述已過時，下次觸發請直接嘗試查詢而非假設不可用。
- 🟡 **前端元件計數口徑不穩**（#14 發現，#15 再次確認）：純 grep `export` 統計對同一份未變更程式碼在不同觸發間得到 39 / 40 / 41，屬統計方法誤差而非實際差異，且誤差幅度比原先記錄的 ±1 更大。非阻塞，但下次若需精確值應改用更嚴謹的計數方式（如 AST parser）而非持續沿用不穩定的 grep 口徑。
- ℹ️ **技能數量計數需排除基礎設施檔**（#15 校準）：`src/skills/` 下若用 `find ... -name "*.py"` 未排除 `base.py`、`registry.py`（皆為共用基礎設施，非單一技能），會把 28 誤算為 37。下次沿用 #10～#15 的排除方式核實。
