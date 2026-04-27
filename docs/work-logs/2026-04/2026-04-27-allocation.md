# 總監派工單 — 2026-04-27

> **派工日期**：2026-04-27（週一，W18 啟動日）
> **派工總監**：wLab:director
> **本日任務數**：2
> **Hackathon 倒數**：剩餘 21 天（截止 2026-05-18）

---

## 1. 本日決策摘要

W18 啟動日（週一），但使用者於今晨追加新需求：**整合 oh-my-claudecode (OMC)** 到 windAI-Lab。總監決策：

1. **新需求優先級判定**：OMC 整合屬於「研發工具升級」類，可降低後續多代理協作的 token 成本（預估 30-50%）、加速論文 / 報告產出。雖非 Hackathon 關鍵路徑，但因屬於工具基礎建設，越早整合效益越大，故核定為 **W18 第一線啟動任務**（與 #42 PR A / #75 / #48 / #50 並列 P1）。
2. **與既有計畫平行不衝突**：OMC 整合本身屬於文件 + 設定檔變更，wEng / wAI / wDomain / wData 仍可依既有規劃啟動 #42 PR A / #48 / #50 / #75。本日的 OMC 工作由 **wLab:director + wRes:rag-curator** 主責，不佔用前述四線資源。
3. **可控風險**：因 OMC plugin 安裝為「互動式 Claude Code session 指令」，無法在自動化環境執行，故本日交付為「文件 + AGENTS.md + 速查表 + 整合指南」三件套，安裝 / 驗證步驟由使用者於下次互動 session 人工執行。
4. **空窗恢復**：4/26 為週日輕量維運日，今日（4/27 週一）進入 W18 正式啟動，wAI / wDomain 連續閒置 8 天的紀錄須在本週內透過 #48 / #50 啟動打破。

---

## 2. 團隊負載快照

| 團隊 | WIP | 待辦 | 負載 | 建議 |
|------|-----|------|------|------|
| wLab: Leadership | **WLAB-20260427-01 OMC 整合（主責）** + #96 階段二 | #96 階段二 PR 1（4/28） | 🟡 中 | 本日整合 OMC，4/28 起轉 #96 |
| wData: Data Engineering | #75 規格收集（同步啟動） | #75 規格 v0.1 | 🟢 中 | 4/27 早上強制啟動 |
| wAI: AI/ML | #48 設計稿（同步啟動） | #48 設計稿 | 🟡 中 | **4/27 強制啟動（已等 8 天）** |
| wDomain: Domain Knowledge | #50 故障知識圖譜建模（同步啟動） | #50 設計稿 | 🟡 中 | **4/27 強制啟動（已等 8 天）** |
| wEng: Software Engineering | #42 PR A（同步啟動） | #42 PR A / #43 / #44 / #69 / #96 階段二 | 🔴 高（W18 ~20h） | 4/27-5/03 多 PR 並進 |
| wRes: Research & Docs | **WLAB-20260427-01 紀錄（協作）** + W18 週報籌備 | #52 / W18 週報（4/30） | 🟡 中 | 持續紀錄 + 啟動週報初稿 |

> **wAI / wDomain 連續閒置已達 8 天**：今日強制啟動為終止連敗的關鍵點。

---

## 3. 派工明細

### 任務 1：WLAB-20260427-01 — oh-my-claudecode (OMC) 整合啟動

| 欄位 | 內容 |
|------|------|
| **Task ID** | WLAB-20260427-01 |
| **GitHub Issue** | （新需求，尚未建立 issue） |
| **指派代理** | wLab:director（主責） + wRes:rag-curator（紀錄與文件） |
| **協作代理** | — |
| **優先序** | P1 |
| **預估工時** | 1.5 h |
| **依賴** | 無 |
| **截止日** | 2026-04-27 |
| **驗收標準** | ① AGENTS.md 已建立於 repo 根目錄 ② `.claude/windailab-skills.md` 速查表已建立 ③ `docs/omc-integration-guide.md` 整合指南已建立 ④ README / CLAUDE.md / TODO-roadmap / daily_report 已更新 ⑤ 派工單 + 工作紀錄已歸檔 ⑥ commit + push 至 `claude/practical-knuth-Sf0UT` ⑦ Email 通知已寄送 |
| **工作紀錄連結** | [WLAB-20260427-01-omc-integration.md](./WLAB-20260427-01-omc-integration.md) |

**派工理由**：

使用者於今晨提出 OMC 整合需求，屬於「研發工具基礎建設」。考量：

1. **Token 節省效益**：OMC smart routing 預估降 30-50% 用量，在 Hackathon 倒數 21 天的高頻使用情境下，效益可觀
2. **不影響其他 P1 任務**：OMC 整合屬文件 + 設定變更，可與 #42 / #48 / #50 / #75 並行
3. **可量化交付**：3 份文件（AGENTS / skills / guide）為明確產物，當日可結案
4. **可重複利用模式**：建立 OMC × 領域代理協作模式，可作為後續 windAI 系列專案的範本

---

### 任務 2：WLAB-20260427-02 — 每日例行工作流（W18 啟動日）

| 欄位 | 內容 |
|------|------|
| **Task ID** | WLAB-20260427-02 |
| **GitHub Issue** | 例行（無對應 issue） |
| **指派代理** | wLab:director（主責） |
| **協作代理** | wRes:rag-curator（紀錄） |
| **優先序** | P2 |
| **預估工時** | 0.3 h |
| **依賴** | 無 |
| **截止日** | 2026-04-27 |
| **驗收標準** | ① git log（48h）盤點 ② ruff / TODO 掃描 ③ Issue 狀態確認 ④ daily_report.md 更新 |
| **工作紀錄連結** | 併入 WLAB-20260427-01 之 §7 紀錄段落 |

**派工理由**：W18 啟動日仍維持每日節奏不中斷，但因 OMC 整合本身已涵蓋多數例行步驟，故併入主任務以節省冗餘文件。

---

## 4. W18 同步啟動的其他線（僅備忘，本派工單不主責）

| 線別 | 任務 | 主責代理 | 備註 |
|------|------|----------|------|
| Epic E | #42 PR A — Base + Email Notifier | wEng:backend-dev | 4h，今日啟動 |
| 外部 API | #75 規格收集 | wData:scada-processor | 2h，今日啟動 |
| Epic A | #48 設計稿 — 案例推薦 | wAI:model-trainer | 2h，**強制啟動** |
| Epic B | #50 設計稿 — 故障知識圖譜 | wDomain:wake-analyst | 2h，**強制啟動** |

> 上述四線的派工細節以各自的工作紀錄文件追蹤；本派工單只記錄「本日 OMC 整合」與「例行工作流」兩件主軸。

---

## 5. 風險與對策

| 風險 | 影響 | 對策 |
|------|------|------|
| OMC plugin 互動式安裝無法自動化 | 安裝步驟須使用者人工執行 | 文件已標明「Step 2 / Step 3 需人工」，並提供 smoke test 預期結果 |
| OMC 與既有 `.claude/agents/` 名稱衝突 | 行為不可預期 | 已在 AGENTS.md §4.1 確認命名空間隔離（OMC 無前綴 vs windAI `w*:` 前綴） |
| W18 第一日多線啟動可能拖延 | 進度延後至 4/28 | OMC 整合本身為文件類，不阻塞其他線；若其他線當日未啟動，4/28 仍可追上 |
| Windows 使用者無法享受 ccg / omc-teams | 部分功能受限 | 文件已標明 WSL2 需求，主開發環境為 Linux 不影響 |

---

## 6. 預期成果

完成後 windAI-Lab 將具備：

- ✅ OMC × windAI 協作的官方文件指引（AGENTS.md）
- ✅ 開發者快速速查表（.claude/windailab-skills.md）
- ✅ 完整安裝 / 驗證 / 工作流範例（docs/omc-integration-guide.md）
- ✅ 派工系統第 6 次實戰紀錄（持續驗證 #96 模板）
- ⬜ 待人工執行：plugin 安裝 + omc-doctor 驗證 + smoke test

---

*由 wLab:director 簽核 | 2026-04-27 上午*
