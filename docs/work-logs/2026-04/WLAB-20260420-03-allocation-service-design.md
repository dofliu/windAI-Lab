# 工作紀錄 — WLAB-20260420-03

> **任務名稱**：#96 階段二 — `DirectorAllocationService` 服務層設計文件
> **GitHub Issue**：[#96](https://github.com/dofliu/windai-lab/issues/96)
> **指派代理**：wLab:director（主責）+ wEng:backend-dev（介面規劃）+ wRes:rag-curator（文件格式）
> **建立日期**：2026-04-20
> **狀態**：✅ 完成（設計文件階段，待實作）

---

## 1. 任務概述

延續 2026-04-19 完成的 #96 階段一（文件基礎建設）與 2026-04-20 第三輪的 #42 設計文件，本輪正式啟動 **#96 階段二（服務層）** 的設計規劃。

使用者於每日工作流中反覆強調：

> 確認各種工作，總監可以確實分配（AI 輔助），然後所有流程、工作細節、成果都可以如實詳細紀錄、存成文件，產生正式美觀報告。

階段一已解決「結構化文件」需求；階段二則聚焦於「AI 輔助派工」與「結構化資料層」，讓派工決策從人工 Markdown 進化為服務化、可查詢、可統計的系統。

### 驗收標準

- [x] 建立 `docs/design/director-allocation-service.md` v0.1
- [x] 涵蓋：架構圖 / Pydantic 模型 / DB schema / AI 輔助演算法 / 11 個 API 端點 / 雙向同步策略 / 測試 / 安全 / 時程
- [x] 明確 PR 切分策略（6 個 PR，每個 ≤ 300 行，共 14 h）
- [x] 實作時程定位於 2026-04-26 之後（Epic E 完工後啟動）
- [x] 與既有 `alert_engine.py`、`WorkOrderPanel`、`CLAUDE.md` 整合點明確化

---

## 2. 執行計畫

| 步驟 | 內容 | 預估工時 | 狀態 |
|------|------|----------|------|
| 1 | 盤點 #96 階段一產出與使用者核心需求 | 15 min | ✅ |
| 2 | 設計 Pydantic 模型與 SQLite schema | 20 min | ✅ |
| 3 | 規劃 AI 輔助派工演算法（規則式 v0.1） | 15 min | ✅ |
| 4 | 撰寫 11 個 REST API 端點契約 | 15 min | ✅ |
| 5 | 規劃 Markdown ↔ DB 雙向同步策略 | 10 min | ✅ |
| 6 | 切分 6 個實作 PR 與時程 | 10 min | ✅ |
| 7 | 更新派工單、月索引、日報 | 15 min | ✅ |

### 風險與假設

- **風險**：設計文件與後續實作脫節 → 透過 Pydantic model 與 DB schema 的明確契約降低
- **風險**：Markdown parser 容錯性不足 → 在 PR 3 中以既有 8 份檔案做 roundtrip 測試把關
- **假設**：本階段採規則式 AI 輔助，LLM 整合留待 v1.1
- **假設**：前端介面延後至階段三（v1.2），本階段專注後端契約穩定
- **緩解策略**：設計文件標註 v0.1，擴充點（LLM 派工 / 前端面板 / 通知整合）全數保留於第 11 節

---

## 3. 執行歷程

### 2026-04-20 UTC — 接案

- wLab:director 於本輪（第四輪）例行工作流中決策將 #96 階段二規劃提至本日處理
- 觸發原因：
  1. 使用者於本輪再次強調「AI 輔助派工 + 結構化紀錄 + 正式美觀報告」核心需求
  2. #42 設計文件已完工，wEng 負載可容納下一個設計任務
  3. 階段一經兩輪實戰驗證穩定，階段二規劃時機成熟

### 2026-04-20 UTC — 進度更新

- **完成項目**：
  - 整體架構圖（TaskAnalyzer → LoadEstimator → PriorityScorer → AllocationEngine → RecordWriter）
  - `Allocation`, `DailyAllocationSheet`, `WorkRecord`, `AiAdvice`, `TeamLoadSnapshot` 五個核心 Pydantic model
  - SQLite schema（3 張表：`allocations`, `daily_sheets`, `work_records` + 3 個 index）
  - AI 輔助派工演算法 4 步驟（分類 → 負載 → 計分 → 工時估算 + 替代方案）
  - 11 個 REST API 端點契約與 JSON 回應範例
  - Markdown ↔ DB 雙向同步設計（`AllocationMarkdownConverter`）
  - 測試策略（單元 / 整合 / 契約 / 遷移 / 手動，目標覆蓋率 ≥ 85%）
  - 安全與合規條款（SQL injection、Markdown injection、稽核軌跡 v1.1）
  - 6 個 PR 切分與 14 h 實作時程
- **遇到問題**：無
- **決策**：
  1. 資料庫採 **SQLite + raw sqlite3**，不引入 SQLAlchemy，與 `alert_engine.py` 風格一致
  2. AI 輔助演算法採 **規則式**，LLM 派工延後 v1.1，確保可預測與可測試
  3. Markdown 與 DB **雙向同步**，既有 8 份檔案可漸進匯入，兼顧人類可讀與機器查詢
  4. 服務 **不自動 git commit**，避免副作用；commit 由既有每日工作流執行
  5. 前端介面延後至 **階段三（v1.2）**，本階段專注後端契約穩定

### 2026-04-20 UTC — 結案

設計文件 v0.1 落地 ~530 行，完整覆蓋模型、演算法、API、同步、測試、安全、時程。後續實作可依 6 個 PR 契約執行，估需 14 h。本輪為派工系統 #96 的第三次實戰使用，成功驗證「設計先行、逐步 PR」方法論在跨階段任務中的適用性。

---

## 4. 變更記錄

| Commit / PR | 訊息 | 變更檔案 |
|-------------|------|----------|
| （本輪） | docs(#96): 階段二服務層設計文件 + 第四輪派工單 | 5 檔（1 新增 / 4 更新） |

### 本輪新增檔案

- `docs/design/director-allocation-service.md`（新增，~530 行）
- `docs/work-logs/2026-04/WLAB-20260420-03-allocation-service-design.md`（本紀錄）

### 本輪更新檔案

- `docs/work-logs/2026-04/2026-04-20-allocation.md`（新增任務 3）
- `docs/work-logs/README.md`（月索引附註第四輪）
- `docs/daily_report.md`（新輪更新）
- `README.md`（版本日期同步）

---

## 5. 測試與驗證

| 測試類型 | 狀態 | 結果 |
|----------|------|------|
| 單元測試 | N/A | 本輪純文件，無程式碼變更 |
| 整合測試 | N/A | 同上 |
| Lint (`ruff check .`) | ✅ | All checks passed! |
| 手動驗證 | ✅ | 設計文件交叉參照 `alert_engine.py` / CLAUDE.md §4 / 既有 8 份 Markdown 檔案結構 |
| 範例任務覆蓋 | ✅ | 以本設計文件的派工過程作為 AllocationEngine 的 smoke test 範例 |

---

## 6. 成果與交付物

### 交付清單

- [x] 設計文件（`docs/design/director-allocation-service.md` v0.1）
- [x] 派工單更新（任務 3 新增）
- [x] 工作紀錄（本檔）
- [x] 月索引更新
- [x] 日報更新
- [ ] 程式碼變更（不在本輪範圍，由後續 6 個 PR 執行）
- [ ] 測試（同上）

### 關鍵指標

| 指標 | 數值 |
|------|------|
| 設計文件行數 | ~530 行 |
| 文件變更總行數（預估） | ~700 行（純文件） |
| 程式碼變更行數 | 0 |
| 測試案例數變化 | 0（不變） |
| 規劃的 API 端點數 | 11 |
| 規劃的資料表數 | 3 |
| 規劃的 Pydantic model 數 | 5 |
| 規劃的 PR 數 | 6 |
| 規劃的實作工時 | 14 h |

---

## 7. 學習與後續建議

### 學到什麼

- **分階段推進驗證**：#96 採「階段一文件層 → 階段二服務層 → 階段三前端 / 報告」策略，兩次實戰後證實可行
- **設計先行避免實作反覆**：#42 / #96 兩次皆採設計文件先行，目前零返工
- **使用者需求反覆確認的價值**：本輪使用者再次強調核心需求，促成階段二規劃提前啟動
- **演算法選型優先級**：規則式 > LLM（初版），可預測、可測試、可向用戶說明

### 後續行動

- [ ] **2026-04-21 ~ 04-25**：先完成 Epic E（#42 PR A/B + #43），確保告警系統可運轉
- [ ] **2026-04-26**：啟動 PR 1（`models.py` + DB schema + 遷移腳本）
- [ ] **2026-04-27**：PR 2（`AllocationEngine` 規則式演算法 + 單元測試）
- [ ] **2026-04-28**：PR 3（`converter.py` Markdown ↔ DB + roundtrip 測試）
- [ ] **2026-04-29**：PR 4（FastAPI 端點：allocations + suggest + load-snapshot）
- [ ] **2026-04-30**：PR 5（work records API + 匯入既有 Markdown 腳本）
- [ ] **2026-05-01**：PR 6（CLAUDE.md / README / 日報整合）+ 整體驗收

### 衍生 Issue

- 暫無。保留擴充點於設計文件第 11 節（LLM 派工 / 審計軌跡 / 前端面板 / HTML-PDF 報告 / Email-LINE 通知整合 / 跨專案派工）。

---

*本工作紀錄由 wLab:director 主責於 2026-04-20 產出，wEng:backend-dev 提供介面規劃，wRes:rag-curator 協作文件格式，依循 `docs/templates/tmpl-work-record.md` 模板。*
