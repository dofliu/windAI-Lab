# WLAB-20261014-01 MockConnector 拉取改為時間序列

- 來源：auto-advance #39，cursor.md P1-3
- 問題：MockConnector 每次拉取只產 1 筆紀錄，SCADA 圖只有 1 個點
- 變更：`src/services/data_connector.py` — 每次拉取產生 `batch_size`（預設 6）筆、10 分鐘間隔、跨次接續不重疊的時間序列；快取 / 隨機兩種模式皆適用；FileWatcher 觸發路徑不變
- 測試：`tests/unit/test_data_connector.py` 新增 `TestMockConnectorTimeSeries`（4 案）
- 自我測試：ruff 0 錯誤 / black 通過 / pytest 914 pass, 5 skip
