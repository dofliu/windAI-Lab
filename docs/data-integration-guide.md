# WindAI Lab — 多來源資料整合指南

> 本文件說明如何將非 Kelmarsh 的風場資料匯入 WindAI Lab 系統進行分析。

---

## 1. 目前的資料流程

```
目前只支援 Kelmarsh 風場：

data/external/Kelmarsh_SCADA_2016.zip
    ↓ kelmarsh_loader.py (ZIP → CSV → DataFrame)
    ↓ 自動辨識 Kelmarsh_1 ~ Kelmarsh_6
    ↓
API /api/scada/{turbine_id}/overview
    ↓ 自動偵測 wind_speed / power 欄位（模糊匹配）
    ↓
前端 ScadaDashboard → 散佈圖 / 趨勢圖
```

**問題**：kelmarsh_loader.py 是硬編碼（hardcoded）的，只認得 Kelmarsh 格式。

---

## 2. 不同資料來源的格式差異

實際上風場 SCADA 資料的欄位名稱和格式差異很大：

| 來源 | 風速欄位 | 功率欄位 | 時間格式 | 檔案格式 |
|------|---------|---------|---------|---------|
| **Kelmarsh** | `Wind Speed_Mean` | `Power_Mean` | `Timestamp`, ISO 8601 | CSV in ZIP |
| **ENGIE (La Haute Borne)** | `Va_avg` | `P_avg` | `Date_time`, `DD/MM/YYYY HH:MM` | CSV |
| **Penmanshiel** | `Wind_Speed_Mean` | `Active_Power_Mean` | `PCTimeStamp` | CSV in ZIP |
| **EDP Open Data** | `Amb_WindSpeed_Avg` | `Grd_Prod_Pwr_Avg` | 10-min timestamps | CSV |
| **自有風場** | 完全自定義 | 完全自定義 | 各式各樣 | CSV/Parquet/Excel/DB |

---

## 3. 解決方案：通用資料適配器 (Universal Data Adapter)

### 架構設計

```
使用者的 CSV/Parquet/Excel
    ↓
UniversalDataAdapter
    ├── 自動偵測欄位映射 (Column Mapping)
    ├── 時間戳記解析 (Timestamp Parsing)
    ├── 單位轉換 (Unit Conversion)
    └── 品質驗證 (Quality Validation)
    ↓
標準化 DataFrame（統一欄位名稱）
    ↓
現有 ML Pipeline / SCADA Dashboard 可直接使用
```

### 標準化欄位名稱（內部格式）

| 標準欄位 | 說明 | 單位 | 必要 |
|---------|------|------|------|
| `timestamp` | 時間戳記 | ISO 8601 UTC | ✅ |
| `wind_speed` | 風速 | m/s | ✅ |
| `power` | 發電功率 | kW | ✅ |
| `rotor_speed` | 轉子轉速 | rpm | 建議 |
| `blade_pitch` | 葉片角度 | degrees | 建議 |
| `nacelle_direction` | 機艙方位 | degrees | 選填 |
| `ambient_temp` | 環境溫度 | °C | 選填 |
| `generator_temp` | 發電機溫度 | °C | 選填 |

---

## 4. 使用方式

### 方式 A：直接放 CSV（最簡單）

只要你的 CSV 至少有「風速」和「功率」兩個欄位，系統就能運作。

**步驟**：

```bash
# 1. 把你的 CSV 放到 data/raw/ 目錄
cp my_wind_farm.csv data/raw/

# 2. 系統自動偵測風速/功率欄位（模糊匹配）
#    會嘗試匹配以下關鍵字：
#    - 風速: wind_speed, windspeed, ws, Va_avg, Wind Speed
#    - 功率: power, active_power, P_avg, Power_Mean
```

### 方式 B：提供欄位映射（格式差異大時）

```python
# 在 API 呼叫時指定欄位映射
POST /api/scada/upload
{
  "file_path": "data/raw/my_farm.csv",
  "column_mapping": {
    "timestamp": "Date_time",
    "wind_speed": "Va_avg",
    "power": "P_avg",
    "rotor_speed": "Rt_avg"
  },
  "timestamp_format": "%d/%m/%Y %H:%M",
  "turbine_id": "MyFarm_T1"
}
```

### 方式 C：撰寫自訂 Loader（完全控制）

```python
# src/data_pipeline/ingestion/custom_loader.py
from src.data_pipeline.ingestion.base_loader import BaseDataLoader

class MyFarmLoader(BaseDataLoader):
    """我的風場資料載入器。"""

    def load(self, turbine_id: str) -> pd.DataFrame:
        # 讀取你的資料
        df = pd.read_csv(f"data/raw/{turbine_id}.csv")

        # 映射到標準欄位
        df = df.rename(columns={
            "Va_avg": "wind_speed",
            "P_avg": "power",
            "Date_time": "timestamp",
        })

        # 轉換時間格式
        df["timestamp"] = pd.to_datetime(df["timestamp"],
                                          format="%d/%m/%Y %H:%M")
        return df
```

---

## 5. 現階段的替代方案（不需要改程式碼）

如果你現在就想用其他資料來源分析，可以這樣做：

### 步驟 1：準備你的 CSV

確保 CSV 至少有這樣的欄位：

```csv
timestamp,wind_speed,power
2024-01-01 00:00:00,5.2,120.5
2024-01-01 00:10:00,6.1,250.3
...
```

### 步驟 2：放入 data/raw/ 目錄

```bash
cp my_data.csv data/raw/MyFarm_T1.csv
```

### 步驟 3：修改 API 讓它也能讀 raw CSV

目前 API 的 `scada_overview` 端點會呼叫 `kelmarsh_loader.load_turbine_data()`。
可以加一個 fallback：如果不是 Kelmarsh 開頭的 turbine_id，就直接讀 CSV：

```python
# 在 main.py 的 scada_overview 中加入：
if turbine_id.startswith("Kelmarsh"):
    df = load_turbine_data(turbine_id)  # 原有 Kelmarsh loader
else:
    # 通用 CSV 載入
    csv_path = Path("data/raw") / f"{turbine_id}.csv"
    df = pd.read_csv(csv_path)
```

### 步驟 4：前端加入你的風機 ID

```typescript
// ScadaDashboard.tsx 或透過 API 動態取得
const turbines = ['Kelmarsh_1', ..., 'MyFarm_T1', 'MyFarm_T2']
```

---

## 6. 未來規劃：完整的 BaseDataLoader 抽象層

```python
# src/data_pipeline/ingestion/base_loader.py（規劃中）

class BaseDataLoader(ABC):
    """所有資料載入器的抽象基底。"""

    @abstractmethod
    def load(self, turbine_id: str, **kwargs) -> pd.DataFrame:
        """載入指定風機的資料。"""
        ...

    @abstractmethod
    def list_turbines(self) -> list[str]:
        """列出可用的風機 ID。"""
        ...

    def validate(self, df: pd.DataFrame) -> pd.DataFrame:
        """驗證必要欄位是否存在。"""
        required = ["wind_speed", "power"]
        missing = [c for c in required if not any(
            c.lower() in col.lower() for col in df.columns
        )]
        if missing:
            raise ValueError(f"缺少必要欄位：{missing}")
        return df
```

```python
# 註冊 loader
LOADERS: dict[str, BaseDataLoader] = {
    "kelmarsh": KelmashLoader(),
    "engie": ENGIELoader(),
    "custom": GenericCSVLoader(),
}
```

---

## 7. 支援的檔案格式

| 格式 | 支援狀態 | 說明 |
|------|---------|------|
| CSV | ✅ 已支援 | 預設分隔符 `,`，支援自訂 |
| Parquet | ✅ 已支援 | pandas 原生支援 |
| Excel (.xlsx) | 🔜 規劃中 | 需 `openpyxl` |
| JSON | 🔜 規劃中 | 巢狀結構需展平 |
| 資料庫 (SQL) | 🔜 規劃中 | SQLAlchemy 連線 |
| OPC UA (即時) | 📋 長期計畫 | PLC 資料串接 |

---

## 8. 常見問題

**Q：欄位名稱完全不同怎麼辦？**
A：系統使用模糊匹配（fuzzy matching），會嘗試比對 `wind_speed`, `windspeed`, `ws`, `Va_avg` 等常見名稱。如果都匹配不到，你可以提供明確的 `column_mapping`。

**Q：取樣頻率不同（1 分鐘 vs 10 分鐘 vs 1 小時）？**
A：系統對取樣頻率沒有硬性要求。資料會原樣載入，趨勢圖會自動 resample 為每日平均。ML 模型也不依賴固定頻率。

**Q：多個風場的資料可以混在一起嗎？**
A：建議每個風機一個 CSV 檔案，以 `{farm}_{turbine_id}.csv` 命名。API 用 turbine_id 區分不同風機。

**Q：資料量很大（超過 100 萬筆）怎麼辦？**
A：建議用 Parquet 格式（壓縮率高、讀取快）。API 端的取樣限制（limit=2000）會控制傳給前端的資料量，不影響 ML 訓練使用全量資料。
