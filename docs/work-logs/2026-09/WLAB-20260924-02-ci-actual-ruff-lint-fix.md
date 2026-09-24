# 工作紀錄 — WLAB-20260924-02

> **任務名稱**：修正 CI 實際 pin 的 ruff==0.6.0 下的 25 項 lint 錯誤（P0-新1）
> **GitHub Issue**：#96（沿用既有派工系統相關 Issue，供 commit 關聯）
> **指派代理**：`auto-advance` routine（第 12 次觸發）
> **建立日期**：2026-09-24
> **狀態**：✅ 完成

---

## 1. 任務概述

auto-advance #11 定位出 CI 持續紅燈的真正根因：routine 本地自我測試 pin 的 `ruff==0.15.8` 與 CI 實際 pin 的 `ruff==0.6.0` 規則集不同，導致「本地全綠」從未真正代表「CI 會綠」。以 `ruff==0.6.0` 實測共 25 項錯誤，寫入 `docs/cursor.md` P0-新1 待下次觸發處理。本次觸發直接處理該項目。

### 驗收標準

- [x] `pip install ruff==0.6.0` 並以此版本驗證
- [x] 修正 25 項錯誤（9× UP038、4× E741、3× B904、6× N815、1× TCH003、1× SIM108、1× E402）
- [x] `ruff==0.6.0` + `black` + `pytest` 三項自我測試全綠
- [x] commit 訊息說明改用 CI 實際 pin 版本驗證

---

## 2. 執行歷程

實測 `ruff check src/ tests/`（0.6.0）與 cursor.md 記錄的 25 項錯誤明細完全吻合，逐項修正：

| 類別 | 檔案 | 處理方式 |
|---|---|---|
| UP038 ×9 | `director_review.py`、`report_generator.py` | `isinstance(x, (int, float))` → `isinstance(x, int \| float)` |
| E741 ×4 | `director.py`、`allocator.py`、`converter.py` | 變數 `l` 改為語意化名稱（`load_entry`/`label`/`learning`） |
| B904 ×3 | `main.py` | `except Exception as e: raise HTTPException(...)` 補 `from e` |
| N815 ×6 | `director_allocation/models.py` | `TeamNamespace` enum 成員（`wLab`/`wData`/...）為刻意保留的命名空間前綴（CLAUDE.md §9），逐行加 `# noqa: N815` 並加註說明，不改名 |
| TCH003 ×1 | `notifiers/base.py` | `datetime` 僅用於型別註記（dataclass + `from __future__ import annotations`），移入 `TYPE_CHECKING` 區塊 |
| SIM108 ×1 | `converter.py` | if/else 改三元運算子 |
| E402 ×1 | `main.py` | `from src.api.director import router` 原置於 `app = FastAPI(...)` 之後以便 `app.include_router()`；核查 `director.py` 無循環 import 疑慮，改為將 import 搬至檔案頂部，`include_router()` 呼叫保留原位置 |

## 3. 自我測試

- `ruff check src/ tests/`（0.6.0）：**0 錯誤**（25 → 0）
- `black --check --line-length 99 src/ tests/`：全綠，181 檔案
- `pytest tests/`：872 pass / 0 fail / 5 skip（與基準相同，無回歸）

Commit `0d5d025`，已 push 至 `claude/auto-advance`。push 後觸發 CI run `35983653111`，觸發時仍在執行中（in_progress），實際結論待下次觸發或人工於 GitHub Actions 頁面確認。

## 4. 結論

- P0-新1 完工，佇列移除
- 8 檔變更，35 行增/35 行刪，符合單次觸發規模上限（≤10 檔、1 commit）
- 待確認：下次觸發應先查證 CI run `35983653111`（或之後最新一次）的 Lint job 是否真正轉綠，作為本次修正是否徹底解決根因的最終驗證
