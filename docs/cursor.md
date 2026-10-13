# WindAI Lab — Cursor

> 自動更新時間：2026-10-13（使用者 session：實機 UI 測試 + 缺陷排除）
> 規格：`docs/routines/daily-workflow.md` §4（R2 基準快照）
> 自動推進：`docs/routines/auto-advance.md`（每 3 小時觸發，以本檔為唯一狀態交接介面）

## 上次工作時間

- **2026-10-13（使用者 session）**：首次實機 E2E（uvicorn + vite + headless Chromium 巡覽全部分頁），排除 7 項缺陷，見 [WLAB-20261013-01](work-logs/2026-10/WLAB-20261013-01-ui-e2e-bugfix.md)。其中 **A1-2 已完成**（使用者授權把 `python-multipart` 加入 `requirements.txt`，阻塞解除）。Epic A 程式面全數完成。
- **#37（2026-10-13 auto-advance）**：佇列只剩阻塞 / 需人工項目，本次無變更。
- **#32～#36（2026-10-11～12）**：Epic A 的 A2-1、A2-2、A3-1、A3-2、A3-3 依序完成。

## 數據基準（實測，2026-10-13）

- 環境：`python3 -m pip install`（`pip` 指向 Python 3.13，pandas 2.2.0 會編譯失敗，務必用 `python3 -m pip`），pin `ruff==0.6.0`、`black==24.8.0`；**需 `python-multipart`**（已在 requirements.txt 與 Phase 0 安裝清單）
- `python3 -m ruff check .`：**0 錯誤**
- `python3 -m black --check --line-length 99 src/ tests/`：**全綠**，186 檔
- `python3 -m pytest tests/ -q`：**910 pass / 0 fail / 5 skip**
- `npm run build`（frontend）：通過
- `mypy src/`：423 errors（基準；CI 只安裝不執行 mypy，多數為 loguru `logger?` 假警報）
- 實機 UI 巡覽：0 個 API 4xx/5xx、0 個 JS 例外
- `src/` `.py` 檔：143，總行數 31,182
- REST/WS 端點：76（`/api` + `/ws`，以 app.routes 實算）
- 技能 28、agent 模組 25（未變動）
- Open Issues：12（#34/35/36/37/46/47/48/49/50/51/52/69）——本 session 未核對

## 待續產出（下個 session / auto-advance 觸發接手）

> 每次觸發取**第一個未完成**項目，一次一個。

### P1 — 實機測試後續（2026-10-13 發現）

- [x] **P1-1** `docs/routines/auto-advance.md` Phase 0 安裝清單補 `python-multipart`（2026-10-13 同 commit 完成）
- [ ] **P1-2** 前端寫死 Kelmarsh 清單統一改為讀 `/api/scada/turbines`：`MLDashboard.tsx`（L30-32）、`CommandBar.tsx` / `TaskLauncher.tsx` 的 `FALLBACK_TURBINES` 僅在 API 失敗時使用；`npm run build` 驗證
- [ ] **P1-3** MockConnector 每次拉取只產 1 筆紀錄、一檔一筆 → SCADA 圖只有 1 個點。改為同風機追加寫入單一滾動檔（或拉取時產生一段時間序列），保留 FileWatcher 觸發；補測試
- [ ] **P1-4** 實機 E2E 自動化：把本次 Playwright 巡覽腳本（全部分頁 + 工單結案 → 案例推薦）收成 `scripts/e2e_smoke.mjs` 或 run skill，CI 前端 job 可選擇性執行。**新增 Playwright 依賴屬供應鏈決策 → 需人工授權**，授權前只能寫成不進 CI 的手動腳本

### P2 — 需人工

- [ ] **P2-3** Issue #47 / #48 / #49 / #35 勾選與關閉（Epic A 程式面已全數完成；需 GitHub connector 或人工）
- [ ] **P2-4** 推薦品質驗證：Issue #35 建議累積 50+ 已結案工單後評估 Top-5 命中率（需真實資料）
- [ ] **P2-5** 下一個方向（Epic A 完成後）：Phase 15 多風場管理 / 其他 Epic，待使用者指派

## 阻塞 / 風險

- ✅ **A1-2 阻塞已解除**（2026-10-13）：`python-multipart` 已加入 `requirements.txt`，結案 hook 與 API 層 TestClient 測試已完成
- ℹ️ **TestClient 測試寫法**：參考 `tests/unit/test_api_regressions.py`——`TestClient(app)` 不用 `with`（不啟動 lifespan 的背景連接器 / 排程），以 monkeypatch 取代 `src.core.database._db_instance` 與 `_get_rag_service`
- ℹ️ **路由宣告順序**：FastAPI 依宣告順序比對，固定路徑（`/available`、`/similar`）必須寫在 `/{id}` 之前；已有兩次前例
- ℹ️ **chromadb 未安裝於 routine 環境**（刻意不裝）：案例相關測試一律注入假 indexer / 讓 `_get_rag_service` 拋錯
- ℹ️ **本機 DB 殘留**：本次手動測試建立的 3 筆舊案例 fault_type 為 `manual`（修復前寫入），僅存在容器內 `windai.db`（gitignored），不影響 repo
- 🟡 **容器內 ruff 版本陷阱**：`/root/.local/bin/ruff`（0.15.8）在 PATH 優先；一律用 `python3 -m ruff`、`python3 -m pytest`
- 🟡 **CLAUDE.md 自動 commit 會被 Self-Modification 擋下**：佇列不要排入修改 `CLAUDE.md` 的項目
- 🟠 **大 commit 直推 master**：`bfca6a7` 5,315 行未過 CI 即進主幹，流程缺門檻（沿用既有記錄）
- 🟢 GitHub connector：定時觸發的 session 不保證帶 connector，需 API 的項目歸 P2「需人工」
- ℹ️ 前端元件計數 grep 口徑不穩（37～41），需精確值時改用 AST parser；技能計數須排除 `base.py` / `registry.py`
