# WindAI Lab — 工作紀錄總索引

> 本目錄歸檔總監（`wLab:director`）每日派工決策、各代理工作紀錄與最終成果交付。
> 對應 Issue：[#96 總監工作分配與紀錄系統](https://github.com/dofliu/windai-lab/issues/96)

---

## 1. 目錄結構

```
docs/work-logs/
├── README.md                              ← 本檔（總索引）
└── YYYY-MM/                               ← 按月分流
    ├── YYYY-MM-DD-allocation.md           ← 當日總監派工單
    └── WLAB-YYYYMMDD-NN-{slug}.md         ← 個別任務工作紀錄
```

### 命名規範

| 類別 | 檔名格式 | 範例 |
|------|----------|------|
| 派工總覽 | `YYYY-MM-DD-allocation.md` | `2026-04-19-allocation.md` |
| 任務紀錄 | `WLAB-{YYYYMMDD}-{seq}-{slug}.md` | `WLAB-20260419-01-alert-engine.md` |

---

## 2. 文件用途

| 文件類型 | 模板 | 用途 |
|----------|------|------|
| **派工單** | `docs/templates/tmpl-work-assignment.md` | 總監每日派工決策、團隊負載、優先序 |
| **工作紀錄** | `docs/templates/tmpl-work-record.md` | 單一任務從接案到結案的完整紀錄 |
| **正式報告** | `docs/templates/tmpl-formal-report.md` | 對外交付的美觀報告（HTML/PDF） |

---

## 3. 派工流程

```
使用者需求 / 系統偵測 / Issue 建立
            │
            ▼
   wLab:director 評估
   ├─ 任務性質分析（domain / engineering / research / data / ai）
   ├─ 團隊負載查詢（wData/wAI/wDomain/wEng/wRes 當前 WIP）
   ├─ 優先序判定（P1-P5：依據 Hackathon 倒數、依賴鏈、使用者期待）
   └─ 指派代理 + 預估工時 + 截止日
            │
            ▼
   產生派工單（YYYY-MM-DD-allocation.md）
            │
            ▼
   執行代理建立工作紀錄（WLAB-*.md）
   ├─ 接案 timestamp / 計畫 / 風險
   ├─ 執行過程（commits、PR、測試結果）
   └─ 結案紀錄（成果、學習、後續建議）
            │
            ▼
   wLab:director 整合進日報（docs/daily_report.md）
            │
            ▼
   每週彙整為正式報告（formal-report.html / .pdf）
```

---

## 4. 寫作量管控規則 ⚠️

為避免文件爆量、降低 Claude 每次工作時的 context 載入成本，**所有產出必須遵守以下上限**：

### 4.1 開新檔的時機（白名單）

僅在以下情況才產生新檔：

| 情境 | 動作 |
|------|------|
| 新的一天有派工 | 產生 **1 份** `YYYY-MM-DD-allocation.md`（一天最多一份）|
| 任務正式結案（PR 合併或交付完成） | 產生 **1 份** `WLAB-YYYYMMDD-NN-{slug}.md` |
| 週報截止日（每週四） | 產生 **1 份** `docs/reports/YYYY-WNN-weekly-report.md` |

### 4.2 禁止情況（黑名單）

- ❌ 任務「進度更新」不另開檔，直接附在當日 `daily_report.md` 或在 PR 描述中
- ❌ 同一天有第二輪派工，**追加在原 allocation 末尾**，不開 `-round2.md`
- ❌ 不要為每個 commit 開檔；commit message 已是工作紀錄
- ❌ 不要在工作紀錄中重貼 PR diff、測試輸出全文 —— 用 commit hash 與 PR 連結代替
- ❌ 不要把模板（templates）內容複製到工作紀錄；用 reference 連結

### 4.3 大小上限

| 文件類型 | 建議上限 | 超過怎辦 |
|----------|----------|----------|
| `*-allocation.md` | 200 行 | 拆分當日多輪派工，但仍合併在同一份檔案 |
| `WLAB-*.md` | 200 行 | 拆出附錄到 `docs/design/` 或在 PR 描述中 |
| 週報 | 300 行 | 引用該週紀錄連結，不複製內容 |

### 4.4 內容引用優先序

當紀錄中需要引用既有資料時，依此優先序使用「連結」而非「複製」：

1. GitHub Issue / PR (`#NN`)
2. Commit hash (`abc1234`)
3. 既有 design / template 文件路徑
4. 上一輪 work-log 連結
5. 確實有需要時，才放完整內容（且須是當下決策的「決定性訊息」）

### 4.5 月度封存規則

- 上一個月結束後，**不再修改**該月的 `YYYY-MM/` 目錄內容（凍結）
- 月度索引（本檔 §5）會持續更新，但不擴增該月舊檔案

---

## 5. 月度索引

### 2026 年 9 月

| 日期 | 派工單 | 主要任務 | 完成度 |
|------|--------|----------|--------|
| 05-01 ~ 09-21 | — | 停擺期（僅 07-03 / 07-10 兩次 commit，皆未留派工紀錄） | ⚠ |
| 09-22 | [allocation](2026-09/2026-09-22-allocation.md) | **復工健檢** — CI 紅燈 73 天定位 + 5 項缺陷記錄 + `TODO-roadmap.md` 損壞修復 + 文件全面校準；[auto-advance P0-1](2026-09/WLAB-20260922-02-ruff-autofix.md) ruff --fix 158 項 + black 格式化；[auto-advance P0-2](2026-09/WLAB-20260922-03-director-import-re.md) director.py 補 import re；[auto-advance P0-3](2026-09/WLAB-20260922-04-alert-engine-test-decouple.md) test_alert_engine.py 與生產 rules.yaml 解耦；[auto-advance P0-4](2026-09/WLAB-20260922-05-report-scheduler-notification-message.md) report_scheduler 補回遺失的報告通知內文 | ✅ |

### 2026 年 4 月

| 日期 | 派工單 | 主要任務 | 完成度 |
|------|--------|----------|--------|
| 04-19 | [allocation](2026-04/2026-04-19-allocation.md) | #41 告警規則引擎 + 派工系統文件基礎建設 | ✅ |
| 04-20 | [allocation](2026-04/2026-04-20-allocation.md) | #42 通知渠道設計文件 + #96 階段二服務層設計（Epic E 推進 + 派工系統進階） | ✅ |
| 04-21 | — | 空窗（無 commit） | ⚠ |
| 04-22 | — | 空窗（無 commit） | ⚠ |
| 04-23 | [allocation](2026-04/2026-04-23-allocation.md) | 空窗恢復 + **首份正式週報產出（2026-W17）** + Epic E 排程重整 | ✅ |
| 04-24 | [allocation](2026-04/2026-04-24-allocation.md) | W17 收尾 · 輕量維運 + **`tmpl-formal-report.md` v1.0 → v1.1 升版**（4 項回饋落地） | ✅ |
| 04-26 | [allocation](2026-04/2026-04-26-allocation.md) | W17→W18 過渡日 · 輕量維運 + W18 啟動就緒備忘錄 | ✅ |
| 04-27 | [allocation](2026-04/2026-04-27-allocation.md) | **W18 Day 1 · OMC 整合啟動**（AGENTS.md + 速查表 + 整合指南） + daily_report 瘦身 | ✅ |

### 2026-W17 正式週報

- [docs/reports/2026-W17-weekly-report.md](../reports/2026-W17-weekly-report.md) — 首份正式週報實例（對應 `tmpl-formal-report.md` 驗證）
- 驗證回饋 → 2026-04-24 已將 4 項改進建議落地為 **`tmpl-formal-report.md` v1.1**（詳見 [WLAB-20260424-02](2026-04/WLAB-20260424-02-formal-report-template-v1-1.md)）

---

## 6. 整合點

- **日報整合**：每日 `docs/daily_report.md` 會引用當日派工單
- **週報整合**：每週四產出 `docs/reports/YYYY-WNN-weekly-report.md`，彙整該週派工單與工作紀錄
- **Issue 連結**：每份工作紀錄須引用對應 GitHub Issue 編號
- **Commit 連結**：以 commit hash 反查實際變更
- **PR 連結**：附上 PR 連結以利審核追蹤

---

*由 Claude Code 自動建立並維護，最後更新：2026-09-22（復工健檢日）*
