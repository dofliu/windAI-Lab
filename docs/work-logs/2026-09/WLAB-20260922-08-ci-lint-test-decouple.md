# 工作紀錄 — WLAB-20260922-08

> **任務名稱**：CI lint 與 test job 解耦、pin ruff/black/mypy 版本、lint 範圍擴至 tests/（P1-3）
> **GitHub Issue**：無明確對應 Issue（CI 流程健檢缺陷，源自 `docs/cursor.md` 待續產出）
> **指派代理**：auto-advance routine（第 7 次觸發）
> **建立日期**：2026-09-22
> **狀態**：✅ 完成

---

## 1. 任務概述

`.github/workflows/ci.yml` 的 `test` job 設有 `needs: lint`，導致 lint job
任何一個空白字元等級的錯誤都會封鎖整個測試層回饋（依 cursor.md 記錄，此問題已
持續 73 天）。此外 lint job 的 `pip install ruff black mypy` 未 pin 版本，與
`requirements.txt` 宣告的 `ruff==0.6.0` / `black==24.8.0` / `mypy==1.11.0`
不一致，可能導致 CI 上的 lint 結果與本地開發環境不同；且 lint 範圍只涵蓋
`src/`，未涵蓋 `tests/`。

### 驗收標準

- [x] `test` job 移除 `needs: lint`，兩者並行執行、各自回報
- [x] lint job 的 ruff/black/mypy 安裝改為 pin 版本，與 `requirements.txt` 一致
- [x] `ruff check` 與 `black --check` 範圍由 `src/` 擴大到 `src/ tests/`

---

## 2. 執行歷程

1. 讀取 `.github/workflows/ci.yml`，確認 `test` job 的 `needs: lint` 依賴、
   未 pin 版本的安裝指令、以及只掃 `src/` 的 lint 範圍。
2. 移除 `test` job 的 `needs: lint`，改為與 `lint` job 並行執行。
3. 將 `pip install ruff black mypy` 改為
   `pip install ruff==0.6.0 black==24.8.0 mypy==1.11.0`，對齊
   `requirements.txt` 現有宣告版本。
4. 將 `ruff check src/` 與 `black --check --line-length 99 src/` 分別擴大為
   `ruff check src/ tests/` 與 `black --check --line-length 99 src/ tests/`。
5. 本地以 pin 版本（`ruff==0.15.8`／`black==24.8.0`，依
   `docs/routines/auto-advance.md` Phase 0 的自我測試環境慣例）驗證
   `ruff check .` 與 `ruff check src/ tests/` 錯誤數相同（19 個，皆為既有
   基準、非本次變更引入），確認擴大 lint 範圍不會讓 CI 新增紅燈。

---

## 3. 變更記錄

| Commit | 訊息 | 變更檔案 |
|--------|------|----------|
| `1b5ba1f` | `chore: CI lint 與 test job 解耦、pin ruff/black/mypy 版本、lint 範圍擴至 tests/` | `.github/workflows/ci.yml` |

---

## 4. 測試與驗證

| 測試類型 | 狀態 | 結果 |
|----------|------|------|
| `ruff check .` | ✅ | 19 錯誤（既有基準，未變；本次僅改 workflow YAML，不影響 Python 程式） |
| `black --check --line-length 99 src/ tests/` | ✅ | 全綠 |
| `pytest tests/ -q` | ✅ | 872 pass / 0 fail / 5 skip（與變更前相同） |

> 本次變更僅涉及 `.github/workflows/ci.yml`（GitHub Actions 設定），實際
> CI 執行結果需等下次 push 觸發 Actions 後由人工或有 GitHub connector 的
> session 核對（本 routine 無 `mcp__github__*` 工具，無法查詢 Actions 狀態）。

---

## 5. 學習與後續建議

### 學到什麼

- CI 的 `needs: lint` 依賴會把「格式問題」與「邏輯正確性回饋」綁在一起，
  一旦 lint 有既有debt（如本次基準的 19 個 ruff 警告），會讓開發者長期看
  不到測試層的真實回饋。兩者解耦後，即使 lint 仍有既有 debt，測試層依然
  能獨立回報。
- CI 與本地開發環境的 lint 版本不一致（CI 未 pin、`requirements.txt` 有
  pin）是常見但容易被忽略的一致性缺口；此次一併修正。

### 後續行動

- 待下次 push 後，若有 GitHub connector 的 session 可核對 CI Actions 是否
  依預期並行執行、以及 lint job 在新 pin 版本下是否仍回報 19 個既有錯誤
  （若 pin 版本改變導致錯誤數增減，需另外評估是否為版本行為差異）。
- cursor.md 的「待續產出」P1-3 項目已完成，可移除或標記完成。

---

*本工作紀錄依循 `docs/templates/tmpl-work-record.md` 模板精簡版，由 auto-advance routine 產出。*
