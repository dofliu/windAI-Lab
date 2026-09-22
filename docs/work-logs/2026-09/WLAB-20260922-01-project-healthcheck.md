# 工作紀錄 — WLAB-20260922-01

> **任務名稱**：專案全面健檢與文件校準
> **GitHub Issue**：無（使用者直接指派）
> **指派代理**：`wLab:director` + `wEng:test-engineer`
> **建立日期**：2026-09-22
> **狀態**：✅ 完成（文件層）／⛔ 程式修復待核定

---

## 1. 任務概述

使用者要求「檢視目前專案 → 更新專案文件 → 討論下一步推進方向與做法」。專案自 2026-07-10 起停擺 74 天，需先確認真實狀態，再校準文件，最後提出推進方案。

### 驗收標準

- [x] 以指令實測取代人工估計，盤點專案真實狀態
- [x] 核對 GitHub CI / Issue 與本地文件的落差
- [x] 修復文件層問題（損壞檔、缺檔、日期矛盾、指標過期）
- [x] 產出具優先序的推進方案
- [x] **不擅自修改程式碼**（缺陷僅記錄，待總監核定）

---

## 2. 執行歷程

### 2026-09-22 — 接案與環境實測

- 讀取 `CLAUDE.md` / `STATUS.yaml` / `PROJECT-STATUS.md` / `daily_report.md` / `TODO-roadmap.md`
- 安裝核心依賴（fastapi / pandas / sklearn / xgboost / scipy / pytest 等；未裝 torch / chromadb / mlflow，對應 5 個測試 skip）
- 執行 `ruff check .`、`black --check src/`、`pytest tests/`
- 以 `find` / `grep` / `pytest --collect-only` 盤點資產

### 2026-09-22 — GitHub 核對

- `list_workflow_runs(ci.yml, branch=master)` → run #303（2026-07-10）conclusion = **failure**，最後綠燈為 #302（2026-04-30）
- `list_workflow_jobs(29087577821)` → Lint & Format **failure**（Ruff check 步驟）、Black check **skipped**、Tests **skipped**、Frontend Build **success**
- `list_issues(state=OPEN)` → **18 個**，其中 5 個文件已標 ✅ 完成

### 2026-09-22 — 缺陷根因定位

以 `git show --stat bfca6a7` 鎖定 2026-07-03 的 5,315 行 commit 為問題來源，逐項讀碼驗證 ruff 報出的非裝飾性錯誤。

### 2026-09-22 — 文件修復

修復 `docs/TODO-roadmap.md` 位元組損壞、補建 `docs/cursor.md`、校準三份狀態文件。

---

## 3. 變更記錄

- `docs/TODO-roadmap.md` — 修復非法 UTF-8 + 還原遺失章節 + 移除重複區段 + 指標校準
- `docs/PROJECT-STATUS.md` — 新增「專案健康度（2026-09-22 實測）」章節 + 完成度表校準 + Issue 狀態註記
- `STATUS.yaml` — 日期 / 里程碑 / 指標更新 + 新增 `health` 欄位
- `docs/daily_report.md` — 依「每日重寫」格式重寫為健檢日報
- `docs/cursor.md` — 新建（CLAUDE.md §6 指定但從未存在）
- `docs/work-logs/2026-09/2026-09-22-allocation.md` — 新建派工單
- `docs/work-logs/2026-09/WLAB-20260922-01-project-healthcheck.md` — 本檔
- `docs/work-logs/README.md` — 新增 2026-09 月度索引

---

## 4. 測試與驗證

| 測試類型 | 指令 | 結果 |
|----------|------|------|
| Lint | `ruff check .` | 185 錯誤（src/ 146、tests/ 39） |
| Format | `black --check --line-length 99 src/` | 13 檔需重新格式化 |
| 單元測試 | `pytest tests/ -q` | 877 收集：868 pass / 4 fail / 5 skip |
| 編碼完整性 | `iconv -f UTF-8 -t UTF-8` 掃全 repo | 修復前：`TODO-roadmap.md` 非法；修復後：全數 VALID |
| CI 核對 | GitHub Actions run #303 | Lint ❌ / Tests ⏭️ / Frontend ✅ |

---

## 5. 成果與交付物

### 5.1 CI 紅燈根因鏈

```
bfca6a7 (07-03, 5315 行直推 master，未跑 ruff/black)
   → bde44fe (07-10, 只熱修 BaseModel NameError，未修 lint)
   → run #303: Lint ❌ → Black ⏭️ → Tests ⏭️ (needs: lint)
   → 紅燈 73 天；測試自 2026-04-30 起未在 CI 執行過
```

### 5.2 遺留缺陷（皆來自 `bfca6a7`，已驗證非誤報）

| # | 位置 | 問題 | 影響 |
|---|------|------|------|
| 1 | `src/api/director.py:240,287` | 未 `import re` 卻用 `re.sub`/`re.match`（F821） | L240 被 `except Exception` 吞掉（檔名 slug 功能靜默失效）；**L287 無保護 → 工作紀錄匯入端點必定 `NameError`** |
| 2 | `converter.py:288-297` | `parse_record()` 解析出 `title`/`issue`/`assignee`/`status` 後全數丟棄，`WorkRecord` 無對應欄位（4× F841）。`render_record()` 卻會寫出這 4 欄 | #96 招牌功能「Markdown ↔ DB **雙向無損**同步」實為有損，每次往返掉 4 欄位 |
| 3 | `report_scheduler.py:302` | 組好 `message` 後未帶入 `NotificationPayload`（F841） | 報告自動生成的 Email / LINE 通知內容為空 |
| 4 | `main.py:2008 & 2197` | `GET /api/reports` 註冊兩次、函式同名（F811） | 後者為死碼 |
| 5 | `main.py:177` | 模組層 import 置於 app 設定後（E402） | 與 07-10 熱修的 NameError 同類風險 |

### 5.3 4 個失敗測試根因

`AlertRuleEngine()` 現優先讀 `configs/alerts/rules.yaml`（6 條，含 `connector_offline`），僅在讀取失敗才回退程式內建 5 條。`test_alert_engine.py` 4 個測試仍斷言 5 條。

**這是測試過期而非程式錯誤**。

### 5.4 文件損壞修復細節

`docs/TODO-roadmap.md` 為全 repo 唯一非法 UTF-8 檔案，`bfca6a7` 的錯誤就地編輯造成兩處斷裂：

| 斷點 | 症狀 | 修法 |
|------|------|------|
| 原 L39 | 「新系統」列被截斷成 `\| 新系` + 半個 UTF-8 位元組（`E7 B5`），並吞掉 `## 2. 三步走演進路線` / Step 1 / Phase 11 / Phase 12 / Phase 13 表頭 | 自 `ca7053d` 還原章節，補回 Phase 13 表頭與首列 |
| 原 L110 | `\| Connector YAML 設定 ... \| ✅ \|flow 實驗記錄 \| ✅ \|` — Epic C 的 C1 列在 "MLflow" 中間被切開後沾到此列尾，C2/C3 成為孤兒列 | 截掉沾附碎片、刪除 2 列孤兒 |
| 原 L116-160 | 整段舊版「待辦 Epics + Step 2 + Phase 14」重複貼上，且 ✅ 狀態為過期版本 | 刪除重複段，保留新版 |

結果：296 行 → 275 行，`iconv` 驗證通過，章節結構與損壞前完全一致。

---

## 6. 學習與後續建議

* 學到什麼：
  - `needs: lint` 的 CI 相依讓一個**空白字元等級**的錯誤封鎖了整個測試層回饋達 73 天。品質門檻的串接順序本身就是風險。
  - 大 commit 直推 master 會同時繞過 CI 與 code review。本次 5,315 行帶進 5 個缺陷 + 1 份損壞文件。
  - **ruff 的 F841/F821 不是裝飾性警告**。本次 5 項缺陷中有 3 項（含招牌功能的資料遺失）純粹由 F841/F821 指出。
  - 文件裡人工填寫的指標會無聲腐化（端點 56→73、元件 32→40）。改為指令實測可從根本避免。

* 後續行動：
  - **P0** `ruff check --fix`（158 項自動）+ 手動修 5 項缺陷 + `black src/`
  - **P0** 修 4 個失敗測試：以自備 fixture YAML 建構引擎，與 repo 生產設定解耦（不是把 5 改成 6——那會讓測試繼續綁死維運人員本就該自由編輯的設定檔）
  - **P1** CI 防護：lint / test 解除 `needs` 相依（兩者並行，各自回報）+ pre-commit gate + master 分支保護 + CI 的 ruff/black 改為 pin 版本（現為 unpinned，與 `requirements.txt` 的 `ruff==0.6.0` 不一致）
  - **P1** 關閉 6 個已完工 Issue（#33 / #42 / #43 / #44 / #75 / #96）
  - **P2** CLAUDE.md 章節編號去重（現有兩組 §5/§6/§7）、§10「42 個代理」更正為 25
  - **P2** `converter.py` 的有損問題應連帶為 `WorkRecord` 補上 `title` / `github_issue` / `assignee` / `status` 欄位，並加一個 round-trip 測試守住
