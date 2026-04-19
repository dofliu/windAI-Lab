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

## 4. 月度索引

### 2026 年 4 月

| 日期 | 派工單 | 主要任務 | 完成度 |
|------|--------|----------|--------|
| 04-19 | [allocation](2026-04/2026-04-19-allocation.md) | #41 告警規則引擎 + 派工系統文件基礎建設 | ✅ |

---

## 5. 整合點

- **日報整合**：每日 `docs/daily_report.md` 會引用當日派工單
- **Issue 連結**：每份工作紀錄須引用對應 GitHub Issue 編號
- **Commit 連結**：以 commit hash 反查實際變更
- **PR 連結**：附上 PR 連結以利審核追蹤

---

*由 Claude Code 自動建立並維護，最後更新：2026-04-19*
