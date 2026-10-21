# 工作紀錄 — WLAB-20261011-01

> **任務名稱**：Epic A 啟動 + A1-1 案例記錄核心（`cases` 表 + `CaseLearningService`）
> **GitHub Issue**：#47（父 Issue #35 [Epic A] 案例學習系統）
> **指派代理**：`auto-advance` routine（使用者於 session 內指派方向並要求立即跑一輪）
> **建立日期**：2026-10-11
> **狀態**：✅ 完成（A1-1 切片；#47 尚有 A1-2 結案 hook 未完成）

---

## 1. 任務概述

使用者於 2026-10-11 指派 P2-2 方向為 **Epic A 案例學習系統**，並授權完成 P2-1（`CLAUDE.md` 章節重編，另 commit）。
依 playbook「一次一件、可驗證」原則，將 Epic A 拆為 A1-1 ~ A3-3 共 7 個切片寫入 `docs/cursor.md`，本次完成 A1-1。

## 2. 執行內容

| 檔案 | 變更 |
|------|------|
| `src/core/database.py` | 新增 `cases` 表（`work_order_id` UNIQUE）+ `create_case`（冪等）/ `get_case` / `get_case_by_work_order` / `list_cases`（依故障類型、風機篩選）/ `mark_case_indexed` |
| `src/services/case_learning.py`（新） | `extract_case()` 純函式提取故障類型 / 症狀 / 解法 / 處理時間；`CaseRecord.to_summary()` 摘要模板；`CaseLearningService.record_case()` 寫 SQLite + 選用寫入 ChromaDB `maintenance_cases` |
| `tests/unit/test_case_learning.py`（新） | 11 個測試：提取規則、故障類型優先序、冪等、未結案略過、向量庫失敗降級 |

設計決策：

- **故障類型優先序**：工單 `metadata.fault_type` → 告警 `metadata.fault_type_zh/fault_type`（WindGuard 診斷）→ 告警首個 tag（規則 ID）→ 告警 `source` → 「未分類」
- **解法來源**：工單 `metadata.resolution` 優先，否則串接工單備註
- **向量庫為選用依賴**：以 Protocol 注入；未注入或寫入失敗時案例仍存 SQLite、`indexed=False`，日後可補寫（測試環境未裝 chromadb 亦可跑）
- 僅 `status=completed` 觸發；`cancelled` 不建案例

## 3. 自我測試

- `ruff check .`（0.6.0）：**0 錯誤**
- `black --check --line-length 99 src/ tests/`：全綠，183 檔
- `pytest tests/ -q`：**883 pass / 0 fail / 5 skip**（+11）
- `mypy`（新模組）：僅 loguru `logger?` 型別假警報，與既有 `rag_service.py` 相同基準，非新缺陷

## 4. 後續

下一切片 **A1-2**：在 `PATCH /api/work-orders/{id}` 結案時呼叫 `CaseLearningService.record_case()`（失敗不影響工單更新）+ 整合測試。完成後 #47 驗收標準即全數滿足。

## 5. A2-1 切片（auto-advance #32）

A1-2 因 `python-multipart` 缺失無法在 CI 測試 API 層而阻塞（詳見 cursor.md）。改做 A2-1：新增 `src/skills/rag/case_recommender.py`（`CaseRecommender`，同風機 +0.1 加權、Top-5、向量庫失敗回傳空列表）與 `tests/unit/test_case_recommender.py`（6 測試）。自我測試：ruff 0 / black 通過 / pytest 889 pass、5 skip。
