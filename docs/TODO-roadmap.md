# WindAI Lab — TODO 路線圖與下一步工作規劃

> 最後更新：2026-03-25
> 目前進度：Phase 6a 完成 — 25/42 代理（60%）

本文件整理尚未完成的工作項目、優先級排序與需討論的決策要點，作為團隊討論下一步工作的基礎。

---

## 1. 當前狀態摘要

```
已完成 ████████████░░░░░░░░ 60%
                              ↑ 我們在這裡
Phase:  1  2  3  4  5  5.5  6a ←→ 6b  6c  7
        ✅ ✅ ✅ ✅ ✅  ✅   ✅      ⬜  ⬜  ⬜
```

| 類別 | 已完成 | 剩餘 |
|------|--------|------|
| 代理 (Agents) | 25 | 17 |
| ML 模型 | 3 | 3+ |
| API 端點 | 22+ | 8+ |
| 前端元件 | 16 | 4+ |

---

## 2. 未完成代理清單（17/42 待實作）

### 🔴 高優先 — 直接影響核心功能

| 代理 | Tier | 預估工時 | 說明 | 前置需求 |
|------|------|---------|------|---------|
| `wAI:model-trainer` | AI/ML | 3h | 統一模型訓練管理（排程、佇列、資源分配） | 無 |
| `wAI:model-evaluator` | AI/ML | 3h | 跨模型效能比較、混淆矩陣、學習曲線 | model-trainer |
| `wAI:inference-deployer` | AI/ML | 4h | 模型部署至推論端點、批次推論 | model-evaluator |
| `wData:data-validator` | Data | 2h | 資料格式驗證（IEC 61400 標準） | 無 |

### 🟡 中優先 — 擴展功能覆蓋

| 代理 | Tier | 預估工時 | 說明 | 前置需求 |
|------|------|---------|------|---------|
| `wDomain:wind-resource-analyst` | Domain | 4h | Weibull 分佈擬合、年均發電量估算 | 無 |
| `wDomain:iec-specialist` | Domain | 3h | IEC 61400 標準合規檢查 | data-validator |
| `wRes:teaching-assistant` | Research | 3h | 互動式教學、程式碼範例生成 | 無 |
| `wRes:data-storyteller` | Research | 3h | 資料敘事報告、視覺化解讀 | report-generator |
| `wData:stream-processor` | Data | 5h | 即時串流資料處理（Kafka/Redis Stream） | 無 |
| `wData:metadata-curator` | Data | 2h | 資料後設資料管理、資料目錄 | 無 |

### 🟢 低優先 — 完善度提升

| 代理 | Tier | 預估工時 | 說明 | 前置需求 |
|------|------|---------|------|---------|
| `wData:storage-manager` | Data | 3h | 儲存策略（冷/熱分層、壓縮） | 無 |
| `wData:pipeline-monitor` | Data | 3h | Pipeline 健康監控、告警 | stream-processor |
| `wDomain:regulatory-advisor` | Domain | 3h | 風電法規諮詢、合規建議 | iec-specialist |
| `wEng:api-designer` | Eng | 3h | API 規格設計、OpenAPI 文件 | 無 |
| `wEng:database-admin` | Eng | 4h | PostgreSQL/MongoDB 管理 | 無 |
| `wEng:security-analyst` | Eng | 3h | 安全掃描、漏洞分析 | 無 |
| `wEng:infra-manager` | Eng | 3h | 基礎設施監控、擴展建議 | 無 |

---

## 3. Phase 6b — 工程基礎設施（下一步建議）

### 3.1 GitHub Actions CI Pipeline

**狀態**：⬜ 未開始
**預估工時**：3-4 小時

```yaml
# 預計 pipeline 結構
name: CI
on: [push, pull_request]
jobs:
  lint:    ruff check src/
  format:  black --check src/
  typecheck: mypy src/
  test:    pytest tests/ -x --cov
```

**待討論**：
- 是否需要在 CI 中執行 ML 模型訓練測試？（耗時可能超過 5 分鐘）
- 測試資料是否提交至 Git 或用 DVC 管理？

### 3.2 PostgreSQL 持久化

**狀態**：⬜ 未開始
**預估工時**：6-8 小時

**範圍**：
- [ ] 任務記錄持久化（task_id, agent_id, status, timestamps）
- [ ] 工作日誌持久化（WorkLogEntry）
- [ ] 代理狀態歷史記錄
- [ ] SQLAlchemy ORM 模型定義
- [ ] Alembic migration 設定
- [ ] Docker Compose 新增 PostgreSQL service

**待討論**：
- 是否先用 SQLite 做 MVP，再遷移至 PostgreSQL？
- 歷史資料保留策略（保留 90 天 vs 全部保留）？

### 3.3 MongoDB 非結構化資料

**狀態**：⬜ 未開始
**預估工時**：4-5 小時

**範圍**：
- [ ] ML 實驗記錄（hyperparameters, metrics, artifacts）
- [ ] RAG 文件原始內容與 metadata
- [ ] SCADA 資料快照與分析報告存檔

**待討論**：
- ChromaDB 已在使用中，是否另外需要 MongoDB？
- 或者用 PostgreSQL JSONB 欄位取代 MongoDB？

---

## 4. Phase 6c — 前端增強

### 4.1 風機健康狀態總覽 Dashboard

**狀態**：⬜ 未開始
**預估工時**：4-5 小時

```
┌──────────────────────────────────────────┐
│           風場健康狀態總覽                  │
├────────┬────────┬────────┬────────┬──────┤
│  KM-1  │  KM-2  │  KM-3  │  KM-4  │ ... │
│  ✅ 正常 │  ✅ 正常 │  ⚠️ 注意 │  ✅ 正常 │     │
│ R²=.996│ R²=.994│ R²=.981│ R²=.995│     │
│ 功率正常 │ 功率正常 │ 偏低8% │ 功率正常 │     │
└────────┴────────┴────────┴────────┴──────┘
```

### 4.2 模型訓練進度即時追蹤

**狀態**：⬜ 未開始
**預估工時**：3-4 小時

- WebSocket 推播訓練進度（epoch, loss, metrics）
- 前端即時折線圖顯示 loss 曲線
- 訓練完成通知

---

## 5. Phase 7 — 產品化（長期規劃）

| 項目 | 預估工時 | 優先級 | 備註 |
|------|---------|--------|------|
| 認證授權系統 (JWT + OAuth) | 8h | 高 | 多使用者支援 |
| 生產環境安全強化 | 6h | 高 | HTTPS, CSP, rate limiting |
| Prometheus + Grafana 監控 | 5h | 中 | 系統效能監控 |
| OPC UA PLC 資料整合 | 8h | 中 | 即時 SCADA 資料串接 |
| 深度學習模型 (LSTM, Transformer) | 10h | 中 | 需 GPU 支援 |
| 多語言 i18n 支援 | 4h | 低 | 英文/日文/簡體中文 |
| 完整 42 代理實作 | 20h+ | 持續進行 | 每個 2-5 小時 |

---

## 6. 需討論的決策要點

以下是需要在團隊中討論的開放問題，影響後續開發方向：

### 決策 1：下一步優先順序

**選項 A — 深度優先（強化 AI/ML 能力）**
- 實作 model-trainer → model-evaluator → inference-deployer
- 新增 2-3 個 ML 模型（LSTM 時序預測、Autoencoder 異常偵測）
- 加入 MLflow 實驗追蹤整合
- 優點：核心研究能力最大化
- 缺點：工程基礎設施持續薄弱

**選項 B — 廣度優先（強化工程基礎）**
- CI/CD pipeline + 資料庫持久化 + 健康總覽 Dashboard
- 實作 data-validator + iec-specialist（標準合規）
- 優點：系統穩定性與可維護性提升
- 缺點：新功能推出速度放緩

**選項 C — 混合策略（建議）**
- 先花 1 天完成 CI pipeline + SQLite 持久化（最小可行工程基礎）
- 再花 2 天實作 model-trainer + model-evaluator + 健康總覽 Dashboard
- 最後補齊 Domain 代理（wind-resource-analyst, iec-specialist）

### 決策 2：資料庫策略

| 方案 | 複雜度 | 適合場景 |
|------|--------|---------|
| SQLite（單檔） | 低 | 單機研究用 |
| PostgreSQL | 中 | 多人協作 / 生產環境 |
| PostgreSQL + MongoDB | 高 | 完整企業架構 |
| PostgreSQL + JSONB | 中 | 結構 + 半結構混合 |

**建議**：先用 SQLite 做 MVP，確認 schema 後再遷移至 PostgreSQL。

### 決策 3：前端功能擴展

| 功能 | 使用者價值 | 開發成本 |
|------|----------|---------|
| 風機健康總覽 Dashboard | ⭐⭐⭐⭐⭐ | 中（4-5h） |
| 尾流視覺化（風場 2D 地圖） | ⭐⭐⭐⭐ | 高（6-8h，需 D3.js） |
| 模型訓練進度即時圖表 | ⭐⭐⭐ | 中（3-4h） |
| 代理間通訊視覺化 | ⭐⭐ | 高（5-6h） |

### 決策 4：新增 ML 模型

| 模型 | 用途 | 依賴 | 複雜度 |
|------|------|------|--------|
| LSTM 時序預測 | 風速/功率短期預測 | PyTorch/TensorFlow | 高 |
| Autoencoder 異常偵測 | 無監督異常偵測 | PyTorch | 中高 |
| Gaussian Process | 功率曲線不確定性估計 | scikit-learn | 中 |
| Weibull 擬合 | 風資源評估 | scipy | 低 |

---

## 7. 工時估算總覽

| 階段 | 預估工時 | 狀態 |
|------|---------|------|
| Phase 6b 工程基礎 | 13-17h | ⬜ |
| Phase 6c 前端增強 | 7-9h | ⬜ |
| 剩餘 17 代理 | 50-60h | ⬜ |
| Phase 7 產品化 | 40-50h | ⬜ |
| **總計** | **~110-136h** | — |

**若以每天 4-6 小時計算**：約 20-30 個工作天可完成至 Phase 7。

---

## 8. 下次會議建議議程

1. 確認下一步優先順序（選項 A/B/C）
2. 資料庫策略決策
3. 前端功能排序
4. 是否引入深度學習模型？（GPU 需求評估）
5. 代理實作分工安排
