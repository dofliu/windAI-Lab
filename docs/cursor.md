# WindAI Lab — Cursor

> 自動更新時間：2026-10-11（auto-advance #34）
> 規格：`docs/routines/daily-workflow.md` §4（R2 基準快照）
> 自動推進：`docs/routines/auto-advance.md`（每 3 小時觸發，以本檔為唯一狀態交接介面）

## 上次工作時間

- **#34（2026-10-11）**：完成 **A3-1**：`GET /api/cases`（分頁 + `fault_type`/`turbine_id` 篩選，回傳 total）、`GET /api/cases/{case_id}`，新增 `Database.count_cases` + 2 測試。端點本身因 python-multipart 阻塞無法以 TestClient 測（僅 DB 層有測試），解除後補。

- **#33（2026-10-11）**：完成 **A2-2**：`CaseRecommender` 新增 `store`（SQLite `list_cases`）降級——searcher 缺席 / 失敗 / 無結果時以 bigram 關鍵字 + 故障類型比對，+5 測試。A1-2 仍阻塞。

- **#32（2026-10-11）**：A1-2 因缺 `python-multipart` 阻塞（見阻塞清單）→ 改做 **A2-1**：`src/skills/rag/case_recommender.py` + 6 個測試。

- **#31（2026-10-11）**：使用者指派方向 **Epic A 案例學習系統**（P2-2 解除），並授權完成 P2-1。本輪完成 **A1-1**（`cases` 表 + `CaseLearningService`），見 [WLAB-20261011-01](work-logs/2026-10/WLAB-20261011-01-epic-a-case-recording.md)。
- **#30（2026-10-11）**：P2-1 `CLAUDE.md` 章節重編 §1–§14、代理數更正為 25（使用者授權，已 commit）。
- 空轉期（#14～#29）已結束，佇列重新有可自主推進的工作。

## 數據基準（實測，#34，2026-10-11）

- 環境：新容器，`python3 -m pip install`（`pip` 指向 Python 3.13，pandas 2.2.0 會編譯失敗，務必用 `python3 -m pip`），pin `ruff==0.6.0`、`black==24.8.0`
- `python3 -m ruff check .`：**0 錯誤**
- `python3 -m black --check --line-length 99 src/ tests/`：**全綠**，185 檔
- `python3 -m pytest tests/ -q`：**896 pass / 0 fail / 5 skip**（+2，來自 count_cases 測試）
- `src/` `.py` 檔：142，總行數 30,807
- REST 端點：75（+2：/api/cases、/api/cases/{case_id}）
- 技能 28、agent 模組 25（未變動）
- Open Issues：12（#34/35/36/37/46/47/48/49/50/51/52/69）
- mypy 注意：loguru `logger?` 的 attr-defined 為既有基準假警報（`rag_service.py` 同樣 14 筆），非新缺陷

## 待續產出（下個 session / auto-advance 觸發接手）

> 每次觸發取**第一個未完成**項目。Epic A 依 Issue #35 拆成可獨立驗證的切片，**一次一個**。

### P1 — Epic A 案例學習系統（Issue #35，使用者 2026-10-11 指派）

- [x] **A1-1**（#47）`cases` 表 + `Database` 案例 CRUD + `src/services/case_learning.py`（`extract_case` / `CaseRecord.to_summary` / `CaseLearningService.record_case`，選用寫入 ChromaDB `maintenance_cases`）— commit 見 git log
- [ ] **A1-2（⛔ 阻塞，需人工）**（#47）結案 hook：`src/api/main.py` 的 `PATCH /api/work-orders/{order_id}` 在 `status` 變為 `completed` 時呼叫 `CaseLearningService(get_database(), indexer).record_case(order_id)`；indexer 取得 `RAGService` 失敗時傳 None；**案例記錄失敗不得讓工單更新失敗**。補 API 層測試（`TestClient` + tmp DB）。完成後 #47 驗收全滿足（關 Issue 需人工 / GitHub connector）
- [x] **A2-1**（#48，#32 完成）`src/skills/rag/case_recommender.py` `CaseRecommender`：輸入告警描述 → 在 `maintenance_cases` 語意搜尋 Top-5（同 `turbine_id` 加權優先），回傳 case_id / 相似度 / 故障類型 / 解法摘要。測試以假 RAG 注入（不依賴 chromadb）
- [x] **A2-2**（#48，#33 完成；`CaseRecommender(searcher, store=db)`，A3-2 API 組裝時傳入 `get_database()`）向量庫不可用時的降級：以 SQLite `cases` 做關鍵字 / 同故障類型比對，確保無 chromadb 環境仍回傳結果
- [x] **A3-1**（#49，#34 完成；端點 TestClient 測試待 python-multipart 解除後補）API：`GET /api/cases`（分頁 + `fault_type` / `turbine_id` 篩選）、`GET /api/cases/{id}`
- [ ] **A3-2**（#49）API：`GET /api/cases/similar?alert_id=xxx` → Top-5（接 A2）
- [ ] **A3-3**（#49）前端 `frontend/src/components/CaseRecommendation.tsx` + 整合進 WorkOrderPanel（可展開完整解法）；需 `npm run build` / 前端 lint 通過

### P2 — 需人工

- [ ] **P2-3** Issue #47 / #48 / #49 / #35 的勾選與關閉（需 GitHub connector 或人工）

## 阻塞 / 風險

- ⛔ **A1-2 阻塞（需人工授權）**：`import src.api.main` 在無 `python-multipart` 時直接 RuntimeError（`File`/`UploadFile` 路由），而 `requirements.txt` 與 CI 都沒有該套件，且 playbook 禁止自行新增依賴。任何 `TestClient` 測試在 CI 會失敗。解法擇一：(a) 人工把 `python-multipart` 加進 `requirements.txt`（建議，FastAPI 上傳本就需要）；(b) 授權使用 `pytest.importorskip`。解除後 A1-2 實作已設計好：`update_work_order` 於 `fields.get("status")=="completed"` 時呼叫 `_record_case_on_close(db, order_id)`（try/except 包住 `CaseLearningService(db, indexer).record_case`，`_get_rag_service()` 失敗時 indexer=None）。

- ℹ️ **Epic A 前置條件**：Issue #35 建議累積 50+ 已結案工單後再啟用推薦。A2/A3 可先完成程式與測試，但推薦品質須等真實資料累積，不阻塞開發
- ℹ️ **chromadb 未安裝於 routine 環境**（刻意不裝，見 playbook Phase 0）：案例相關測試一律以 Protocol 注入假 indexer，勿在測試中直接依賴 chromadb
- 🟡 **容器內 ruff 版本陷阱**：`/root/.local/bin/ruff`（0.15.8）在 PATH 優先；一律用 `python3 -m ruff`，pytest 用 `python3 -m pytest`
- 🟡 **CLAUDE.md 自動 commit 會被 Self-Modification 擋下**：P2-1 這次是使用者在 session 內明確授權才完成；之後佇列不要排入修改 `CLAUDE.md` 的項目
- 🟠 **大 commit 直推 master**：`bfca6a7` 5,315 行未過 CI 即進主幹，流程缺門檻（沿用既有記錄）
- 🟢 GitHub connector：本 session 可用；定時觸發的 session 是否帶 connector 不保證，需 API 的項目仍歸 P2「需人工」
- ℹ️ 前端元件計數 grep 口徑不穩（37～41），需精確值時改用 AST parser；技能計數須排除 `base.py` / `registry.py`
