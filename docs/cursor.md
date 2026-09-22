# WindAI Lab — Cursor

> 自動更新時間：2026-09-22
> 規格：`docs/routines/daily-workflow.md` §4（R2 基準快照）

## 上次工作時間

- 日期：2026-09-22（專案健檢日）
- Session 結束：單一 session 完成（健檢 + 文件校準）
- 前次有效工作日：2026-07-10（中間停擺 74 天）

## 數據基準（實測）

- `ruff check .`：**185 錯誤**（src/ 146、tests/ 39；158 項可自動修復）
- `black --check src/`：**13 檔需重新格式化**
- `pytest tests/`：**877 收集 → 868 pass / 4 fail / 5 skip**
- Python TODO/FIXME：0
- 前端 TODO：1（`frontend/src/hooks/useWebSocket.ts`，穩定）
- Open Issues：**18**
- 最近 commit：`bde44fe`（2026-07-10）
- **CI：🔴 紅燈**（Lint & Format failure → Tests skipped；Frontend Build ✅）
- 資產：73 REST 端點 + 1 WS、40 前端元件、29 技能、25 agent 模組、9 DB 表、141 `.py` / 30,302 行

## Issue 狀態快照

| # | 標題 | 狀態 |
|---|------|------|
| #42 | [E2] 通知渠道 | 程式完成，待關閉 |
| #43 | [E3] 告警規則 YAML | 程式完成，待關閉 |
| #44 | [D1] 報告排程自動化 | 程式完成，待關閉 |
| #75 | 對接外部 API | 程式完成，待關閉 |
| #96 | 總監派工系統 | 程式完成，待關閉（但 converter 有損） |
| #33 | [Epic E] 告警規則引擎 | 子任務齊，待關閉 |
| #34 | [Epic D] 報告與追蹤 | 進行中（#45/#46 未啟動） |
| #35/#36/#37 | Epic A / B / F | 未啟動 |
| #45–#52 | Epic 子任務 | 未啟動 |
| #69 | registry 雙軌技術債 | 保留 |

## 待續產出（下個 session 接手）

- [ ] **P0** 恢復 CI 綠燈：`ruff check --fix` + `black src/` + 手動修 5 項實際缺陷
- [ ] **P0** 修 4 個 `test_alert_engine.py` 失敗測試（以 fixture 解耦，不是把 5 改成 6）
- [ ] **P1** CI 防護：lint / test job 解除 `needs` 相依 + pre-commit gate + master 分支保護
- [ ] **P1** 關閉 6 個已完工 Issue
- [ ] **P2** CLAUDE.md 章節編號去重、§10「42 個代理」→ 25
- [ ] **P2** 定向下一個功能 Epic（Phase 15 多風場 / Epic A 案例學習）

## 阻塞 / 風險

- 🔴 **CI 紅燈 73 天**：`needs: lint` 使空白字元等級錯誤封鎖整個測試層回饋
- 🔴 **`src/api/director.py` 缺 `import re`**：L287 無保護，工作紀錄匯入端點必定 `NameError`
- 🔴 **`converter.parse_record()` 有損**：#96 招牌功能「Markdown ↔ DB 雙向無損同步」每次往返掉 4 欄位
- 🟠 **大 commit 直推 master**：`bfca6a7` 5,315 行未過 CI 即進主幹，流程缺門檻
- 🟡 **文件與 tracker 脫鉤**：5 個 Issue 程式已完成但未關閉
