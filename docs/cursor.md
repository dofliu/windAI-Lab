# WindAI Lab — Cursor

> 自動更新時間：2026-10-27（Phase 15 第三切片：跨風機比較 API）
> 規格：`docs/routines/daily-workflow.md` §4（R2 基準快照）
> 自動推進：`docs/routines/auto-advance.md`（每 3 小時觸發，以本檔為唯一狀態交接介面）

## 上次工作時間

- **2026-10-27 auto-advance**：P1-5a 完成——新增 `tests/integration/test_new_case_flow.py`（TC-01 / TC-02 / TC-04，全程走 HTTP API、RAG 不可用走關鍵字降級），3 測試通過；未發現缺陷。ruff 0 / black 188 檔綠 / pytest 927 pass 5 skip。下一項 P1-5b。
- **2026-10-27 auto-advance**：P15-3 完成——`Database.compare_farm_turbines()` + `GET /api/farms/{farm_id}/compare`（同風場各風機的群組、使用中告警 / critical、開放工單並列，依嚴重度排序；風場不存在回 404）；補 1 個測試。健康分數 / 效能指標待 SCADA 資料來源確認，未納入。ruff 0 / black 187 檔綠 / pytest 924 pass 5 skip。
- **2026-10-27 auto-advance**：P15-2 完成——`Database.get_farms_overview()` + `GET /api/farms/overview`（各風場風機數 / 使用中告警 / critical 告警 / 開放工單，以 `farm_turbines` 對應 `turbine_id`；未歸屬風機不計）；補 1 個測試。發電量 / 可利用率待資料來源確認，未納入。ruff 0 / black 187 檔綠 / pytest 923 pass 5 skip。
- **2026-10-27（使用者指派 Phase 15）**：完成 Phase 15 第一切片——`wind_farms` / `turbine_groups` / `farm_turbines` 三張表、`Database` 風場 CRUD 與階層查詢、`/api/farms*` 6 個端點、`tests/unit/test_wind_farms.py` 8 測試。ruff 0 / black 187 檔綠 / pytest 922 pass 5 skip。
- **2026-10-21 auto-advance**：P2-3 完成——關閉 #47/#48/#49（附 commit sha 與程式位置），#35 子任務勾選。無程式變更。
- **#40（2026-10-14 auto-advance）**：P1-4 完成可做的部分——新增 `scripts/e2e_smoke.mjs`（手動、不進 CI、未改 package.json）：巡覽 5 分頁 / 11 子頁面檢查 API 4xx/5xx 與 JS 例外，並以 API 驗證工單結案 → `/api/cases` +1；實機（uvicorn + vite + Chromium）跑通。無 SCADA 資料時對 `/api/scada/*` 的 404 視為預期。ruff 0 / black 186 檔綠 / pytest 914 pass 5 skip。
- **#39（2026-10-14 auto-advance）**：P1-3 完成——`MockConnector.fetch_data` 每次拉取改產生 6 筆連續時間序列（10 分鐘間隔、跨次接續不重疊，`batch_size` 可由連接器 config 設定），快取模式與隨機模式皆適用；FileWatcher 觸發路徑不變。補 4 個測試。ruff 0 / black 186 檔綠 / pytest 914 pass 5 skip。
- **#38（2026-10-13 auto-advance）**：P1-2 完成——`MLDashboard.tsx` 改為讀 `/api/scada/turbines`（失敗保留 `Kelmarsh_1` fallback）；CommandBar / TaskLauncher / ScadaDashboard 原本已動態讀取，僅 API 失敗才用 fallback。ruff 0 / black 186 檔綠 / pytest 910 pass 5 skip / `npm run build` 通過。
- **2026-10-13（使用者 session）**：首次實機 E2E（uvicorn + vite + headless Chromium 巡覽全部分頁），排除 7 項缺陷，見 [WLAB-20261013-01](work-logs/2026-10/WLAB-20261013-01-ui-e2e-bugfix.md)。其中 **A1-2 已完成**（使用者授權把 `python-multipart` 加入 `requirements.txt`，阻塞解除）。Epic A 程式面全數完成。
- **#37（2026-10-13 auto-advance）**：佇列只剩阻塞 / 需人工項目，本次無變更。
- **#32～#36（2026-10-11～12）**：Epic A 的 A2-1、A2-2、A3-1、A3-2、A3-3 依序完成。

## 數據基準（實測，2026-10-14）

- 環境：`python3 -m pip install`（`pip` 指向 Python 3.13，pandas 2.2.0 會編譯失敗，務必用 `python3 -m pip`），pin `ruff==0.6.0`、`black==24.8.0`；**需 `python-multipart`**（已在 requirements.txt 與 Phase 0 安裝清單）
- `python3 -m ruff check .`：**0 錯誤**
- `python3 -m black --check --line-length 99 src/ tests/`：**全綠**，188 檔
- `python3 -m pytest tests/ -q`：**927 pass / 0 fail / 5 skip**
- `npm run build`（frontend）：通過
- `mypy src/`：本次未跑（環境未裝 mypy；上次基準 423 errors；CI 只安裝不執行 mypy，多數為 loguru `logger?` 假警報）
- 實機 UI 巡覽：0 個 API 4xx/5xx、0 個 JS 例外
- `src/` `.py` 檔：143，總行數 31,182
- REST/WS 端點：83（`/api` + `/ws`，以 app.routes 實算）
- 技能 28、agent 模組 25（未變動）
- Open Issues：9（#34/35/36/37/46/50/51/52/69）——#47/#48/#49 已於 2026-10-21 關閉；其餘未重新核對

## 待續產出（下個 session / auto-advance 觸發接手）

> 每次觸發取**第一個未完成**項目，一次一個。

### P1 — 實機測試後續（2026-10-13 發現）

- [x] **P1-1** `docs/routines/auto-advance.md` Phase 0 安裝清單補 `python-multipart`（2026-10-13 同 commit 完成）
- [x] **P1-2** 前端寫死 Kelmarsh 清單統一改為讀 `/api/scada/turbines`：`MLDashboard.tsx`（L30-32）、`CommandBar.tsx` / `TaskLauncher.tsx` 的 `FALLBACK_TURBINES` 僅在 API 失敗時使用；`npm run build` 驗證
- [x] **P1-3**（#39 完成）MockConnector 每次拉取只產 1 筆紀錄、一檔一筆 → SCADA 圖只有 1 個點。改為同風機追加寫入單一滾動檔（或拉取時產生一段時間序列），保留 FileWatcher 觸發；補測試
- [x] **P1-4**（#40：手動腳本已完成；CI 整合仍待授權，見阻塞）實機 E2E 自動化：把本次 Playwright 巡覽腳本（全部分頁 + 工單結案 → 案例推薦）收成 `scripts/e2e_smoke.mjs` 或 run skill，CI 前端 job 可選擇性執行。**新增 Playwright 依賴屬供應鏈決策 → 需人工授權**，授權前只能寫成不進 CI 的手動腳本

### P1 — 新案例處理能力驗證（使用者 2026-10-27 指派）

> 規劃見 `docs/routines/case-e2e-test-plan.md`；每次觸發取一個切片，追加到 `tests/integration/test_new_case_flow.py`

- [x] **P1-5a**（2026-10-27 完成）切片 1：TC-01 / TC-02 / TC-04（告警 → 工單 → 結案 → 案例 → 相似推薦、重複結案冪等）
- [ ] **P1-5b** 切片 2：TC-05 / TC-06 / TC-07（容錯）
- [ ] **P1-5c** 切片 3：TC-03（推薦 Top-3 命中率 ≥ 80%）
- [ ] **P1-5d** 切片 4：TC-08 / TC-09 / TC-10（多風場連動 + 耗時記錄）

### P1 — Phase 15 多風場管理（使用者 2026-10-27 指派）

- [x] **P15-1** WindFarm 階層式資料模型（風場 → 群組 → 單機）：DB + API + 測試
- [x] **P15-2** 風場總覽 API（`/api/farms/overview`）：告警數、開放工單數已完成；發電量 / 可利用率待資料來源確認，另列追蹤
- [x] **P15-3** 跨風機比較 API（`/api/farms/{id}/compare`）：告警 / 工單並列已完成；健康 / 效能指標待資料來源確認，另列追蹤
- [ ] **P15-4** 前端：風場總覽儀表板（多風場卡片）+ 風場管理頁
- [ ] **P15-5** 客戶管理 + OAuth2/JWT 認證——**需人工授權**（可能新增依賴、屬安全設計決策）

### P2 — 需人工

- [x] **P2-3**（2026-10-21 auto-advance）#47 / #48 / #49 已附 commit 證據並關閉；#35 子任務已勾選，保持開啟待 P2-4 驗證
- [ ] **P2-4** 推薦品質驗證：Issue #35 建議累積 50+ 已結案工單後評估 Top-5 命中率（需真實資料）
- [ ] **P2-5** 下一個方向（Epic A 完成後）：Phase 15 多風場管理 / 其他 Epic，待使用者指派

## 阻塞 / 風險

- 🔴 **需人工授權**：把 `scripts/e2e_smoke.mjs` 接入 CI 需新增 Playwright 依賴（供應鏈決策）。執行方式：`NODE_PATH=<含 playwright 的 node_modules> [CHROMIUM_PATH=…] node scripts/e2e_smoke.mjs`（需後端 :5800、前端 :5173 已啟動）
- ✅ **A1-2 阻塞已解除**（2026-10-13）：`python-multipart` 已加入 `requirements.txt`，結案 hook 與 API 層 TestClient 測試已完成
- ℹ️ **TestClient 測試寫法**：參考 `tests/unit/test_api_regressions.py`——`TestClient(app)` 不用 `with`（不啟動 lifespan 的背景連接器 / 排程），以 monkeypatch 取代 `src.core.database._db_instance` 與 `_get_rag_service`
- ℹ️ **路由宣告順序**：FastAPI 依宣告順序比對，固定路徑（`/available`、`/similar`）必須寫在 `/{id}` 之前；已有兩次前例
- ℹ️ **chromadb 未安裝於 routine 環境**（刻意不裝）：案例相關測試一律注入假 indexer / 讓 `_get_rag_service` 拋錯
- ℹ️ **本機 DB 殘留**：本次手動測試建立的 3 筆舊案例 fault_type 為 `manual`（修復前寫入），僅存在容器內 `windai.db`（gitignored），不影響 repo
- 🟡 **容器內 ruff 版本陷阱**：`/root/.local/bin/ruff`（0.15.8）在 PATH 優先；一律用 `python3 -m ruff`、`python3 -m pytest`
- 🟡 **CLAUDE.md 自動 commit 會被 Self-Modification 擋下**：佇列不要排入修改 `CLAUDE.md` 的項目
- 🟠 **大 commit 直推 master**：`bfca6a7` 5,315 行未過 CI 即進主幹，流程缺門檻（沿用既有記錄）
- ✅ **GitHub 能力誤判已更正**（2026-10-21）：先前記載「不保證帶 connector、需 API 的項目歸人工」是錯的。實績顯示查 CI 結果與開關 Issue 皆可執行（2026-09-24 曾關閉 6 個 Issue）。僅「開 PR / merge / 核准」仍禁止——那是規則界線，不是能力限制。詳見 `docs/routines/auto-advance.md` §4.1
- ℹ️ 前端元件計數 grep 口徑不穩（37～41），需精確值時改用 AST parser；技能計數須排除 `base.py` / `registry.py`
