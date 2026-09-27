# WindAI Lab — Cursor

> 自動更新時間：2026-09-27（auto-advance #28 觸發後）
> 規格：`docs/routines/daily-workflow.md` §4（R2 基準快照）
> 自動推進：`docs/routines/auto-advance.md`（每 3 小時觸發，以本檔為唯一狀態交接介面）

## 上次工作時間

- 日期：2026-09-27
- Session：`auto-advance` 第 28 次觸發。佇列僅剩需人工項目（P2-1 / P2-2），依 playbook §6 執行完整健檢（自我測試三項 + iconv 編碼掃描 + 資產盤點 + GitHub Issue/CI 核對）。實測與 #27 基準完全一致，無回歸、無新問題，本次**無程式碼變更**。
- 前次有效工作日：2026-09-27（auto-advance #27，健檢 only）；最近一次有實質程式碼 commit 仍為 auto-advance #13（`253f80f`，見 [WLAB-20260924-03](work-logs/2026-09/WLAB-20260924-03-p0-new2-verify-p1-new1-ruff-pin.md)）
- 🟡 **佇列已連續 15 次觸發（#14～#28）維持「等待方向指派」空轉**，僅剩需人工項目未解除。上次 push notification 補發提醒為 #22（2026-09-27T00:52 UTC）；本次（#28，2026-09-27T18:50 UTC）距上次提醒約 17 小時 58 分，**已達 15～18 小時補發門檻上緣**，且數據連續 15 次觸發無變化，故**本次已發送 push notification**，提醒使用者從 P2-2 候選方向中擇一指派，或協助處理 P2-1。下次補發時機重新起算（距本次起算滿 15～18 小時後，若仍無變化再發）。

## 數據基準（實測，auto-advance #28）

- 環境：新容器，依 playbook Phase 0 重裝，pin `ruff==0.6.0`、`black==24.8.0`（與 CI 一致）
- `ruff check .`（`0.6.0`，`/usr/local/bin/ruff`）：**0 錯誤**
- `python3 -m black --check --line-length 99 src/ tests/`：**全綠**，181 檔案
- `python3 -m pytest tests/ -q`：**872 pass / 0 fail / 5 skip**（與 #8～#27 基準相同，本次無回歸）
- `iconv` 編碼掃描（`src/` `tests/` `docs/` 下 `.py`/`.md`）：**0 個非 UTF-8 檔案**（238 檔掃描）
- CI：最新 push（run `36331101788`，#27 的健檢 commit `cdea32a`）已確認 **conclusion=success**
- Open Issues：12（`list_issues` state=OPEN 核對，號碼與 #11～#27 完全一致：#34/35/36/37/46/47/48/49/50/51/52/69，無新增無關閉）
- 前端 TODO：1（`frontend/src/hooks/useWebSocket.ts:266`，穩定，本次未重新掃描細節）
- 最近 commit：`cdea32a`（2026-09-27，auto-advance #27；本次 #28 未變更程式碼，僅文件）
- 資產：
  - REST 端點：73（`grep -rE "@router\.(get|post|put|delete|patch)\(|@app\.(get|post|put|delete|patch|websocket)\("` 精確比對裝飾器行，與 #10～#27 基準一致）
  - 前端元件：未重新掃描（`frontend/` 本次未變更；沿用 #14～#27 已知結論——純 grep `export` 口徑在 37～41 間波動，屬統計誤差非實際變化。維持建議：下次需要精確值時改用 AST parser）
  - 技能：28（重新以 `find src -path "*skills*" -name "*.py"` 排除 `__pycache__`/`__init__.py`/`base.py`/`registry.py` 後核實為 28，與 #10～#27 基準一致）
  - agent 模組：25（排除 7 個 `__init__.py` 及 8 個共用基礎設施檔後核實，與基準一致）
  - `.py` 檔案：141，總行數 30,411（`src/` 下，與 #27 完全一致）

## Issue 狀態快照（#28 重新核對，未變更）

剩餘 Open Issues：12 個（#34/#35/#36/#37/#46/#47/#48/#49/#50/#51/#52/#69）。詳見 #11 work-log。

## 待續產出（下個 session / auto-advance 觸發接手）

> 由 `auto-advance` routine 每 3 小時取**第一個未完成**項目執行，規則見 `docs/routines/auto-advance.md`。

**佇列持續清空，等待方向指派（#28 再次確認，無新項目）。** 目前僅剩以下需人工項目：

- [ ] **P2-1** `CLAUDE.md` 章節編號去重（現有兩組 §5/§6/§7）、§10「42 個代理」更正為 25。⚠️ **已嘗試執行並卡關（auto-advance #9）**：編輯內容本身通過自我測試，但 commit 動作被 Claude Code auto-mode classifier 以「Self-Modification」拒絕，工作樹已還原。**需人工授權**：需人工在具備更高權限的 session（或人工直接編輯）才能完成 commit；routine 之後觸發應**跳過此項**。

- [ ] **P2-2** 定向下一個功能方向 — **屬方向性決策，需使用者指派，routine 不得自行啟動**。建議候選（供使用者挑選）：
  1. **Phase 15 多風場管理**
  2. **Epic A 案例學習系統**（Issue #35，含子項 #47 案例自動記錄 / #48 相似案例推薦 / #49 案例推薦 API+前端）
  3. **Epic B 故障知識體系**（Issue #36，含子項 #50 故障知識圖譜 / #51 維護效果追蹤）
  4. **Epic D 報告與追蹤**（Issue #34，含子項 #46 追蹤儀表板）
  5. **Epic F 學術論文規劃**（Issue #37，含子項 #52 投稿策略與時程）
  6. 人工協助完成 P2-1（`CLAUDE.md` 章節整理）

> **下次觸發**：佇列現只有需人工項目，應依 playbook §6 執行完整健檢（三項自我測試 + iconv 掃描 + 資產盤點 + Issue 核對），確認無新問題後維持「等待方向指派」狀態。**#28（本次）已補發 push notification 提醒**（距 #22 約 17 小時 58 分，達 15～18 小時門檻）。之後若數據持續無變化，**不需要每次都發**——僅在數據出現變化（新 Issue、CI 失敗、資產計數變動等）或距 #28 本次提醒已滿 15～18 小時以上時才再發送，避免重複打擾。

## 阻塞 / 風險

- 🟢 **P1-3 lint/test 解耦確認有效**（沿用 #11 實測，CI run `35953337501`）：Lint 失敗不阻塞 Tests，兩者獨立回報
- ✅ **ruff 版本 pin 一致性已解除**（#12/#13 雙重確認）：CI 實際 ruff 版本（0.6.0）下的 lint 問題已修正並驗證；routine playbook 本身的 pin 版本亦已同步校正
- 🆕 **容器內 ruff 版本陷阱**（#13 發現，#14～#19 再次確認）：`/root/.local/bin/ruff`（舊版 `0.15.8`）在 PATH 中優先於 `pip install` 裝到 `/usr/local/bin/ruff` 的目標版本，`which ruff` 可能誤導。驗證 ruff 版本時，改用 `/usr/local/bin/ruff` 絕對路徑執行 lint 步驟。同理 `pytest` 執行也應優先用 `python3 -m pytest`，而非直接呼叫可能指向舊版環境的 `pytest` binary。
- 🟠 **大 commit 直推 master**：`bfca6a7` 5,315 行未過 CI 即進主幹，流程缺門檻（沿用既有記錄，本次未新增證據）
- 🟡 **CLAUDE.md 不可被此 routine 自動 commit**（auto-advance #9 發現）：任何觸及 `CLAUDE.md` 的佇列項目都會在 commit 階段被系統層擋下（Self-Modification）。往後佇列不要再排入直接修改 `CLAUDE.md` 的項目，除非使用者確認可由人工協助完成 commit 步驟。`docs/routines/` 下的規則類文件不在此限（#13 已驗證可正常 commit）。
- 🟢 GitHub connector 持續可用（#11～#25 皆驗證成功），`docs/routines/auto-advance.md` §4.1「無 connector」描述已過時，下次觸發請直接嘗試查詢而非假設不可用。
- 🟡 **前端元件計數口徑不穩**（#14 發現，#15/#16 再次確認、誤差擴大）：純 grep `export` 統計對同一份未變更程式碼在不同觸發間得到 37 / 39 / 40 / 41，屬統計方法誤差而非實際差異。非阻塞，但下次若需精確值應改用更嚴謹的計數方式（如 AST parser）而非持續沿用不穩定的 grep 口徑。#17～#28 因 `frontend/` 未變更而略過重新掃描。
- ℹ️ **技能數量計數需排除基礎設施檔**（#15 校準，#16～#27 沿用）：`src/skills/` 下若用 `find ... -name "*.py"` 未排除 `base.py`、`registry.py`（皆為共用基礎設施，非單一技能），會把 28 誤算為 37。下次沿用 #10～#27 的排除方式核實。
- 🟡 **佇列連續 15 次觸發（#14～#28）空轉**：自 #14 起僅剩 P2-1（`CLAUDE.md` 自我修改被系統擋下）與 P2-2（方向性決策）兩個需人工項目，routine 已無自主可推進工作。#18、#22、#28（本次）各發過一次 push notification 提醒；其餘觸發數據皆無變化，未重複發送。**下次補發門檻：距 #28 本次提醒滿 15～18 小時後（約 2026-09-28 09:50～12:50 UTC），若數據仍無變化才補發。**
