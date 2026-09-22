# 工作紀錄 — WLAB-20260922-06

> **任務名稱**：移除 `main.py` 重複註冊的 `GET /api/reports` 死碼（P1-1）
> **GitHub Issue**：#96（總監派工系統相關端點）
> **指派代理**：auto-advance routine（第 5 次觸發）
> **建立日期**：2026-09-22
> **狀態**：✅ 完成

---

## 1. 任務概述

`src/api/main.py` 有兩處 `@app.get("/api/reports")` 註冊，函式同名 `api_list_reports`：

- L2016：`from src.services.report_store import list_reports` → `return list_reports()`
- L2204：`from src.services import report_store` → `return report_store.list_reports()`

FastAPI 依註冊順序比對路由，第一個相符的路由勝出，因此 L2204 的第二份定義
永遠不會被實際呼叫到，是純死碼。

### 驗收標準

- [x] 保留其中一份定義，回傳行為與之前一致（皆呼叫同一個 `report_store.list_reports()`）
- [x] 移除後 `ruff` 不再警告函式重複定義，且無新增錯誤

---

## 2. 執行歷程

1. 確認兩份定義邏輯完全等價（皆是 `report_store.list_reports()` 的透傳），無業務邏輯差異，也未見任何測試直接引用函式名稱 `api_list_reports`。
2. 保留 L2016 原定義，刪除 L2204–2210 的重複區塊（`@app.get` 裝飾器 + 函式本體，共 8 行）。
3. 以 `git stash` 對照變更前後的 `pytest --collect-only` 數字，確認 877 collected 為既有基準（並非本次變更造成的差異），避免誤判自我測試結果。

---

## 3. 變更記錄

| Commit | 訊息 | 變更檔案 |
|--------|------|----------|
| `47ca81d` | `fix(#96): 移除 main.py 重複註冊的 GET /api/reports 死碼` | `src/api/main.py` |

---

## 4. 測試與驗證

| 測試類型 | 狀態 | 結果 |
|----------|------|------|
| `ruff check .` | ✅ | 23 錯誤（較前次基準 24 減少 1，`main.py` 未新增錯誤） |
| `black --check --line-length 99 src/ tests/` | ✅ | 全綠 |
| `pytest tests/ -q` | ✅ | 872 pass / 0 fail / 5 skip（877 collected，與變更前相同） |

---

## 5. 學習與後續建議

### 學到什麼

- cursor.md 記錄的「878 collected」與本次實測的「877 collected」不一致；經
  `git stash` 比對確認 877 才是變更前後皆一致的真實基準，878 應為前次紀錄的
  環境雜訊（非本次變更造成），已在 cursor.md 更正。

### 後續行動

- 下一項待續產出為 **P1-2**：`converter.parse_record()` 遺失欄位（`title` /
  `github_issue` / `assignee` / `status`），需補欄位並加 round-trip 測試。

---

*本工作紀錄依循 `docs/templates/tmpl-work-record.md` 模板精簡版，由 auto-advance routine 產出。*
