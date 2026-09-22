# 工作紀錄 — WLAB-20260922-04

> **任務名稱**：修復 test_alert_engine.py 4 個失敗測試（P0-3）
> **GitHub Issue**：無（auto-advance routine 自主發現）
> **指派代理**：auto-advance routine（第 3 次觸發）
> **建立日期**：2026-09-22
> **狀態**：✅ 完成

---

## 1. 任務概述

`tests/unit/test_alert_engine.py` 的 `TestAlertRuleEngine` 於 `setup_method` 中直接
`AlertRuleEngine()`，該建構子會讀取生產環境設定檔 `configs/alerts/rules.yaml`。
維運人員先前已在該檔案新增第 6 條規則（`connector_offline`），導致 4 個測試斷言
「預設 5 條規則」的測試全數失敗，形成測試綁死生產設定檔的技術債。

### 驗收標準

- [x] `pytest tests/unit/test_alert_engine.py` 全綠
- [x] 之後編輯 `configs/alerts/rules.yaml`（新增/刪除規則）不會再弄壞這組測試

---

## 2. 執行歷程

1. 確認 4 個失敗測試的根因：`AlertRuleEngine.__init__` 預設讀取
   `configs/alerts/rules.yaml`（現有 6 條規則），而非程式內建的
   `_load_default_rules()`（5 條）。
2. 確認 `load_rules(file_path)` 在傳入的路徑不存在時，會呼叫
   `_create_default_rules_yaml()` 自動生成與 `_load_default_rules()`
   完全一致的 5 條標準規則 YAML，再讀回。
3. 修改 `tests/unit/test_alert_engine.py`：將 `setup_method` 改為
   `@pytest.fixture(autouse=True)`，以 pytest 的 `tmp_path`（每個測試獨立、
   不存在的暫存路徑）呼叫 `engine.load_rules(tmp_path / "rules.yaml")`，
   使測試用的規則集與生產設定檔完全解耦。
4. 修正新增的 `from pathlib import Path` 觸發的 ruff `TC003`（該檔已有
   `from __future__ import annotations`，故移入 `TYPE_CHECKING` 區塊，
   與 `test_batch_loading.py` 等既有檔案的慣例一致）。
5. 驗證：即使 `configs/alerts/rules.yaml` 仍維持 6 條規則，測試依然全綠，
   證明解耦成功。

---

## 3. 變更記錄

| Commit | 訊息 | 變更檔案 |
|--------|------|----------|
| `e9d459e` | `fix(#alert-engine): 讓 test_alert_engine.py 與正式 configs/alerts/rules.yaml 解耦` | `tests/unit/test_alert_engine.py` |

---

## 4. 測試與驗證

| 測試類型 | 狀態 | 結果 |
|----------|------|------|
| `ruff check .` | ✅ | 25 錯誤（與變更前基準相同，未新增） |
| `black --check --line-length 99 src/ tests/` | ✅ | 全綠 |
| `pytest tests/ -q` | ✅ | 872 pass / 0 fail / 5 skip（原 868 pass / 4 fail） |

---

## 5. 學習與後續建議

### 學到什麼

- 單元測試不應直接依賴生產環境設定檔（`configs/`）的內容，否則維運人員的
  正常設定調整會意外弄壞 CI。應以獨立 fixture（暫存路徑 / 內嵌資料）建構
  待測物件。

### 後續行動

- 無（本項已完全解決，不留衍生 Issue）

---

*本工作紀錄依循 `docs/templates/tmpl-work-record.md` 模板精簡版，由 auto-advance routine 產出。*
