# /diagnose - 風機故障診斷

當使用者呼叫此指令時，執行以下風力發電機故障診斷工作流程。

## 步驟

### 1. 確認風機 ID 和分析時間範圍
- 詢問使用者指定的風機 ID（turbine ID）
- 確認分析的時間範圍（start date / end date）
- 若使用者未提供，主動詢問以上資訊後再繼續

### 2. 擷取 SCADA + 感測器 + 氣象資料
- 從 SCADA 系統擷取運轉資料（power output, rotor speed, pitch angle, nacelle temperature 等）
- 收集振動感測器（vibration sensor）資料
- 取得對應時段的氣象資料（wind speed, wind direction, temperature, humidity）
- 確認所有資料來源的時間戳記對齊

### 3. 執行資料品質檢查
- 檢查 missing values 和 outliers
- 驗證感測器讀數是否在合理範圍內
- 標記資料異常區段並回報給使用者
- 必要時進行 data imputation 或建議排除異常區段

### 4. 建構診斷特徵
- 從原始資料中萃取統計特徵（mean, std, skewness, kurtosis）
- 計算 power curve deviation
- 建構時序特徵（rolling statistics, trend decomposition）
- 產生頻域特徵（FFT, spectral analysis）用於振動分析

### 5. 平行執行診斷分析
同時啟動以下三項分析任務：

- **異常偵測（Anomaly Detection）**：使用 wAI:anomaly-detector 識別運轉參數中的異常模式
- **故障分類（Fault Classification）**：使用 wAI:fault-diagnostician 判斷故障類型（gearbox, bearing, blade, generator, yaw system 等）
- **振動分析（Vibration Analysis）**：使用 wAI:signal-analyst 進行振動訊號的時頻域分析

### 6. 動態派遣領域專家驗證
- 根據步驟 5 的分類結果，動態選擇對應的 domain expert 進行驗證
- 例如：若判定為 gearbox 問題，派遣齒輪箱專家；若為 blade 問題，派遣葉片專家
- 專家對診斷結果進行交叉驗證，確認或修正故障判定

### 7. 生成故障分析報告
- 彙整所有分析結果，產出結構化的故障分析報告
- 報告內容包含：
  - 故障摘要（Fault Summary）
  - 異常時間軸（Anomaly Timeline）
  - 故障根因分析（Root Cause Analysis）
  - 嚴重程度評估（Severity Assessment）
  - 建議維護行動（Recommended Maintenance Actions）
- 附上關鍵圖表（power curve, vibration spectrum, time series plots）

## 呼叫的 Agents
- `wAI:fault-diagnostician` - 故障診斷專家
- `wAI:anomaly-detector` - 異常偵測模型
- `wAI:signal-analyst` - 訊號分析專家
- Domain experts（依故障類型動態派遣）
