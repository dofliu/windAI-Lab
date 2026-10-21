# 工作紀錄 — WLAB-20261013-01

> **任務名稱**：實機 UI 端對端測試 + 缺陷排除（含 Epic A1-2 結案 hook）
> **GitHub Issue**：#47（A1-2）、#49（案例推薦顯示）
> **指派代理**：Claude Code（使用者於 session 內要求「完整測試、更新工作規劃、把 bug 排除」）
> **建立日期**：2026-10-13
> **狀態**：✅ 完成

---

## 1. 任務概述

第一次以實機方式驗證整個系統：啟動 FastAPI 後端（:5800）+ Vite 前端（:5173），用 headless Chromium（Playwright）
走過 5 個分頁、13 個子頁面並截圖，再以 API 建立告警 → 工單 → 結案的真實流程驗證 Epic A 案例推薦。
另以程式掃描全部 76 條 API 路由（路由遮蔽檢查 + 44 條無參數 GET 逐一呼叫）。

## 2. 發現與修復

| # | 缺陷 | 影響 | 修復 |
|---|------|------|------|
| B1 | `GET /api/agents/available` 宣告在 `/api/agents/{agent_id}` 之後被遮蔽，永遠 404 | 人事管理頁退回「模擬模式（內建資料）」 | 路由移到 `{agent_id}` 之前 |
| B2 | `requirements.txt` 缺 `python-multipart`，`File`/`UploadFile` 路由使 app 啟動即失敗 | 依 README 安裝後後端無法啟動；A1-2 因此阻塞 | 加入 `python-multipart>=0.0.9`（使用者授權排除 bug） |
| B3 | A1-2 結案 hook 未接：工單標記 completed 不會建立案例 | 案例推薦在正常使用下永遠無資料 | `update_work_order` 於 `status=completed` 呼叫 `_record_case_on_close`（失敗只記 log，不影響工單更新；RAG 不可用時只寫 SQLite） |
| B4 | 手動告警的故障類型被推為來源值 `manual` | 推薦卡片顯示「manual」，無參考價值 | 系統內建通用來源略過，改用告警標題（外部系統名如 `windguard` 仍保留） |
| B5 | `/api/scada/turbines` 無條件列出 Kelmarsh_1~6（ZIP 不存在也列）；連接器拉取檔每分鐘一份全部列出 | 下拉選單充滿載不到 / 重複的項目 | 抽出 `_scan_turbines(data_root)`：Kelmarsh 只在 ZIP 存在時列出；`*_api_fetched_*` 同風機只列最新 |
| B6 | MockConnector 每 60 秒在 `data/raw/` 新增一個 CSV，永不清理 | 磁碟無限增長 | `_prune_fetched_files`：每風機只保留最新 10 份（只動連接器自己產生的檔名） |
| B7 | SCADA 頁先以寫死的 `Kelmarsh_1` 發請求，晚到的 404 覆蓋目前風機狀態 | 正常資料上方殘留「找不到風機 Kelmarsh_1」紅框 | 取得風機清單前不發請求 + 請求序號丟棄過期回應 |

## 3. 測試

- 新增 `tests/unit/test_api_regressions.py`（9 個，TestClient + 暫存 DB，不啟動 lifespan）、`test_data_connector.py` +2、`test_case_learning.py` +1
- 修復前跑新測試：**7 failed**；修復後全綠（確認測試真能抓到缺陷）
- `ruff check .`：0 錯誤｜`black --check`：186 檔全綠｜`pytest`：**910 pass / 0 fail / 5 skip**（+12）
- `npm run build`（tsc + vite）：通過
- 實機 UI 複測：全部分頁巡覽 **0 個 API 4xx/5xx、0 個 JS 例外**；UI 上點「開始處理 → 標記完成」後 `/api/cases` 自動 +1
- mypy：420 → 423，新增 3 筆皆為既有基準的 loguru `logger?` 假警報（CI 未跑 mypy）

## 4. 未修 / 後續（已寫入 `docs/cursor.md`）

- MockConnector 每個拉取檔只有 1 筆紀錄，SCADA 圖只畫得出 1 個點（展示資料設計問題）
- `MLDashboard` / `CommandBar` / `TaskLauncher` 仍寫死 Kelmarsh 清單
- 實機 E2E 尚無自動化（本次 Playwright 腳本為一次性）
