# WindAI Lab — 自動推進 Routine（auto-advance）

> 版本：v1.1（2026-10-21 修訂：Phase 6 改為有條件寫檔、§4.1 能力說明更正）
> 觸發頻率：每 3 小時（cron `47 */3 * * *`，UTC — 伺服器依建立時間錨定分鐘數）
> Trigger ID：`trig_01DhdmQUUguMvZLjudiLEvB1`
> 執行模式：每次觸發開一個**全新 session**，以 `docs/cursor.md` 為唯一狀態交接介面
> 關聯規則：`CLAUDE.md` §5（Git/PR）、§6（任務追蹤）、`docs/routines/daily-workflow.md`（每日工作流）

---

## 1. 這個 Routine 要做什麼

在無人看管的情況下，**小步、可驗證地**推進 `docs/cursor.md` 的「待續產出」佇列，且每次推進都必須先通過自我測試才允許 commit。

設計原則：

| 原則 | 說明 |
|------|------|
| **一次只做一件事** | 每次觸發只完成佇列中**一個** P 項目。寧可做完一件並驗證，也不要半完成三件。 |
| **測試先於 commit** | 自我測試未全綠 → **不 commit 程式碼變更**，只更新 cursor.md 記錄阻塞原因。 |
| **狀態寫在檔案裡** | 下一次觸發是全新 session，沒有任何記憶。凡是後續需要知道的事，都必須寫進 `docs/cursor.md`。 |
| **不擴張範圍** | 佇列空了就提案，不自行發明功能。 |
| **主幹唯讀** | 只在 `claude/auto-advance` 分支工作，永不推 master。 |

---

## 2. 每次觸發的執行流程

### Phase 0 — 環境準備

```bash
cd /home/user/windAI-Lab
```

> ✅ **repo 一律到位**。2026-09-22 ～ 10-14 共 40 次觸發，無一次因取不到 repo 中止。建立本 Routine 時曾因 trigger 的 `sources` 為空而預期拿不到 checkout，該預期已被實績推翻。萬一真的沒有，再退回 clone 即可，不需為此預作任何準備：
> `cd /home/user/windAI-Lab 2>/dev/null || (git clone https://github.com/dofliu/windAI-Lab /home/user/windAI-Lab && cd /home/user/windAI-Lab)`

```bash
git fetch origin master claude/auto-advance claude/lucid-johnson-um3m2o

# 分支不存在就從帶有本 playbook 的分支開，最後才退回 master
git checkout -B claude/auto-advance origin/claude/auto-advance 2>/dev/null \
  || git checkout -B claude/auto-advance origin/claude/lucid-johnson-um3m2o 2>/dev/null \
  || git checkout -B claude/auto-advance origin/master
git merge --no-edit origin/master     # 衝突 → 見 §5

# 安裝依賴（新容器沒有任何套件）。刻意不裝 torch / chromadb / mlflow：
# 體積大且僅影響 5 個會自動 skip 的測試。
pip install --quiet fastapi==0.115.0 "uvicorn[standard]" "websockets>=13.0" \
  pydantic==2.9.0 pydantic-settings==2.5.0 pandas==2.2.0 "numpy>=1.26,<2" \
  scikit-learn xgboost scipy pytest==8.3.0 pytest-asyncio==0.24.0 \
  python-dotenv loguru "httpx>=0.28.1" pyyaml "python-multipart>=0.0.9"
pip install --quiet "ruff==0.6.0" "black==24.8.0"
```

> ⚠️ **ruff 版本必須 pin**，且須與 CI 實際版本一致。CI（`.github/workflows/ci.yml`）目前 pin `ruff==0.6.0`，本 routine 同步固定 `0.6.0`（2026-09-24 auto-advance #12 校正；舊版本 `0.15.8` 與 CI 規則集不同，曾造成本地 25 項誤判為新錯誤）。

### Phase 1 — 讀取狀態（**只讀 cursor.md，不要讀整篇 daily_report**）

1. `docs/cursor.md` — 唯一的狀態來源：數據基準、Issue 快照、待續產出、阻塞
2. 若 `docs/cursor.md` 不存在或明顯損壞 → 從 `docs/daily_report.md` 的「建議行動」反推佇列，並重建 cursor.md

### Phase 2 — 取一件工作

從「待續產出」由上而下取**第一個未完成**項目。優先序 **P0 → P1 → P2**。

判斷是否該跳過：

| 情況 | 動作 |
|------|------|
| 該項目在 §4 的禁止清單內 | 跳過，在 cursor.md 標註「需人工授權」 |
| 該項目上次觸發已標記為阻塞，且阻塞原因未解除 | 跳過，取下一項 |
| 該項目預估超出單次觸發能完成的範圍 | **拆小**，只做第一個可獨立驗證的切片 |
| 佇列全空 | 見 §6 |

### Phase 3 — 執行

實作變更。遵守 `CLAUDE.md` §4 coding 規範（type hints、Google style docstring 繁中、禁 `Any`、改檔前先讀）。

### Phase 4 — 自我測試（**這是本 routine 的核心門檻**）

依序執行，全部必須通過：

```bash
ruff check .                              # 期望：All checks passed!
black --check --line-length 99 src/ tests/   # 期望：無 would reformat
python -m pytest tests/ -q                # 期望：0 failed
```

**判定規則**：

| 結果 | 動作 |
|------|------|
| 三項全綠 | → Phase 5 commit |
| 任一項紅，且**由本次變更造成** | 修好再測。修不好 → `git checkout -- .` 全數還原，到 Phase 6 記錄阻塞 |
| 任一項紅，但**變更前就紅**（基準紅） | 若本次工作目標正是修它，繼續修；否則記錄為既有基準、不阻擋本次 commit，但必須在 cursor.md 數據基準更新該數字 |

**絕對禁止**用以下手段換綠燈：

- 跳過、停用、刪除、標記 xfail 任何測試
- 放寬 ruff / black 設定（`pyproject.toml` 的 `select` / `ignore` 不得為了過關而改）
- 用 `# noqa` / `# type: ignore` 掩蓋真實缺陷（僅在 CLAUDE.md §4 允許的情況並註明原因）

### Phase 5 — Commit 與 push

> ⛔ **先過 Phase 6 的閘門**：若本次唯一的變更是 `docs/cursor.md`，而且只是序號、日期或「與 #N 一致」這類措辭，那就**不要走這一節**——不 commit、不 push。判斷標準見 Phase 6。

```bash
git add -A
git commit   # 訊息格式見下
git push -u origin claude/auto-advance
```

Commit 訊息依 `CLAUDE.md` §5：`type(#issue): 描述`，type ∈ {feat, fix, docs, chore, refactor, test}，並附上自我測試結果：

```
fix(#96): converter.parse_record 補回遺失的 4 個中介資料欄位

自我測試：ruff 0 錯誤 / black 通過 / pytest 877 全綠

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

推送失敗（網路）→ 重試最多 4 次，間隔 2s / 4s / 8s / 16s。

### Phase 6 — 收尾：cursor.md **只在有實質變化時**才寫

**先判斷，再決定寫不寫。** 把本次結果與現有 `docs/cursor.md` 比對，只看這四類**實質**內容：

| 類別 | 算實質變化 |
|------|-----------|
| 待續產出 | 有項目完成、新增、改寫或重新排序 |
| 數據基準 | lint / test / 資產計數的**數字本身**改變 |
| 阻塞 / 風險 | 新增、解除，或嚴重度改變 |
| Issue 狀態 | 開關狀態或指派改變 |

**不算**實質變化：觸發序號（`#18` → `#19`）、「自動更新時間」的日期、「與 #N 一致」這類指涉上一輪的措辭，以及任何僅因本次執行而遞增的計數器。

#### 無實質變化 → 什麼都不做

**不寫檔、不 commit、不 push、不發通知。** 依 §9 格式回報「本次無變更」即可。

這條**優先於本節其餘要求，也優先於 Phase 5**。寧可連續多次觸發零 commit，也不要產出只改計數器的 commit——那會污染 git 歷史、觸發無意義的 CI，並稀釋真正有價值的變更。

> 📌 **為什麼要寫在這裡**：2026-09-25 ～ 10-09 曾連續產出 15 個這類 commit（佔當期 40 個 commit 的 38%），每個只改 `cursor.md` 的 12 ～ 21 行計數器，並各自觸發一次完整 CI。當時 §6 已寫明「不做 commit」，但本節舊版無條件要求「覆寫 cursor.md」——**流程指令壓過了例外條款**。判斷因此移進流程本身，而不是依賴記得另一個章節的例外。

#### 有實質變化 → 覆寫 cursor.md

**覆寫**（不累積歷史，避免膨脹）：

- 「上次工作時間」→ 本次觸發時間
- 「數據基準」→ Phase 4 實測的**真實數字**（不可沿用上次的）
- 「待續產出」→ 完成的打勾或移除；新發現的追加到對應優先序
- 「阻塞 / 風險」→ 新增本次遇到的阻塞；解除的移除

並在 `docs/work-logs/YYYY-MM/` 補一行紀錄（任務 ID `WLAB-YYYYMMDD-NN`）。
**若本次僅有文件層產出**（無程式變更），只更新 cursor.md，**不要**開新的 work-log 檔案 — 依 `docs/work-logs/README.md` §4.2 的寫作量管控。

---

## 3. 允許自主執行的工作

- 修 lint / format / 型別錯誤
- 修失敗測試（修測試或修程式，取正確的那一邊）
- 補測試覆蓋
- 修 `docs/cursor.md` 佇列中明確描述的缺陷
- 更新文件、校準文件中的指標（以實測數字）
- CI workflow 設定調整（`.github/workflows/ci.yml`）
- 查詢 GitHub CI 執行結果，以及關閉**已完工**的 Issue（須附完工證據：commit sha + 對應程式位置）

---

## 4. 禁止自主執行 — 必須留給人工授權

| 禁止事項 | 原因 |
|----------|------|
| push 到 `master` | 主幹變更需人工把關 |
| 開 Pull Request | 使用者未授權自動開 PR |
| merge / 核准任何 PR | 同上 |
| force-push、rewrite history | 破壞性且不可逆 |
| 刪除或改名既有檔案（非本次新建者） | 範圍外的破壞 |
| 新增第三方依賴到 `requirements.txt` | 供應鏈決策 |
| 動 `data/raw/`（唯讀）或 commit 敏感資料（風場座標、發電量） | `CLAUDE.md` §10 |
| 修改 `CLAUDE.md` 的規則內容 | 那是本 routine 的上位規範 |
| 啟動一個全新 Epic / Phase | 方向性決策屬總監與使用者 |

遇到禁止事項 → 寫進 cursor.md「阻塞 / 風險」，標註 **需人工授權**，取下一項工作。

### 4.1 本 Routine 的實際能力（2026-10-15 依 23 天實績修訂）

| 能力 | 可用性 |
|------|--------|
| `git` 讀寫、fetch / merge / commit / push | ✅ 可用 |
| lint / format / pytest / 檔案操作 | ✅ 可用 |
| 查 GitHub Actions CI 執行結果 | ✅ 可用 |
| 關閉 / 查詢 GitHub Issue | ✅ 可用 |
| 開 PR、merge、核准 PR | ⛔ **能力上可行，但規則禁止**——見上表 |

> ⚠️ **本節先前的內容是錯的，已更正。** 建立時依 trigger 的 `mcp_connections: []` 判定此 Routine 沒有任何 GitHub 能力，並據此要求把關閉 Issue 一律標為「需人工執行」。實績推翻了該判定：2026-09-24 的觸發實際關閉了 6 個已完工 Issue（#33 / #42 / #43 / #44 / #75 / #96），並讀取了 CI run 結果。錯誤的限制說明會讓 Routine 跳過它本來做得到的事，因此整節重寫。

**開 PR、merge、核准仍然禁止**——那是規則上的界線（見 §4 表格），不是能力上的限制。兩者不要混為一談。

---

## 5. Merge 衝突處理

1. 以 `git merge origin/master` 併入（**不用 rebase**，避免改寫已推送的歷史）
2. lockfile / 產生檔 → 用專案工具重新產生，不手改
3. 兩邊改同一段邏輯、任選一邊都會遺失行為 → **不猜**，還原 merge、記錄到 cursor.md 待人工裁決

---

## 6. 佇列空了怎麼辦

**不要自行發明功能**。依序：

1. 跑一次完整健檢（Phase 4 三項 + `iconv` 編碼掃描 + 資產盤點），把實測數字寫進 cursor.md
2. 核對 GitHub：CI 狀態、Open Issue 與文件是否仍一致
3. 若發現新的實質問題 → 追加到待續產出，下次觸發處理
4. 若確實無事：在 cursor.md 標明「佇列已清空，等待方向指派」，並列出**建議的下一個方向**（例如 Phase 15 多風場管理 / Epic A 案例學習系統）供使用者挑選
5. 結束本次觸發。**不做任何 commit** — 依 Phase 6：無實質變化就不寫檔、不 commit、不通知

---

## 7. 單次觸發的規模上限

沿用 `docs/routines/daily-workflow.md` §3 的精神，避免單次觸發過載：

| 項目 | 上限 |
|------|------|
| 完成的 P 項目 | 1 |
| 變更檔案數 | ≤ 10（純 lint 自動修復不計） |
| 新增 markdown 行數 | ≤ 250 |
| 新建檔案數 | ≤ 2 |
| commit 數 | 1（一次觸發一個原子 commit） |

超出上限 → 拆小，把剩下的寫回 cursor.md 待續產出。

---

## 8. 失敗續行

若某次觸發中斷（timeout、容器回收）：

1. **不要 reset、不要重做**已完成並推送的部分
2. 下次觸發時 `git log origin/claude/auto-advance` 看實際推到哪
3. 對照 cursor.md「待續產出」續行
4. 若 cursor.md 與 git 歷史不一致（例如 commit 有推但 cursor 未更新）→ **以 git 歷史為準**，修正 cursor.md 後繼續

---

## 9. 每次觸發的回報格式

觸發結束時，用以下格式簡短回報（供使用者在通知中快速掃視）：

```
【auto-advance #N】2026-09-22 15:00 UTC

做了什麼：<一句話>
自我測試：ruff <n> / black <pass|fail> / pytest <p> pass, <f> fail
Commit：<sha 或「無（原因）」>
下一步：<cursor.md 佇列的下一項>
阻塞：<有則列出，無則「無」>
```

無實質進展時（佇列空、全數阻塞、或 cursor.md 無實質變化）回報同樣格式，`Commit` 一欄寫「無（本次無實質變化）」，**並且不發通知**。不要為了看起來有產出而硬做事——連續多次「本次無變更」是正常且正確的狀態。
