"""WindAI Lab 測試共用 fixtures。

提供跨測試模組共用的 pytest fixtures，包含合成 SCADA 資料框架
與應用程式設定實例，以避免重複建立測試資料的樣板程式碼。
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.core.config import Settings


@pytest.fixture()
def sample_scada_df() -> pd.DataFrame:
    """建立小型合成 SCADA 資料框架。

    Returns:
        含有 wind_speed_Mean、power_Mean、ambient_temp_Mean、
        gear_oil_temp_Mean 欄位與 DatetimeIndex 的 DataFrame。
    """
    index = pd.date_range(start="2024-01-01 00:00", periods=20, freq="10min")
    data = {
        "Wind Speed_Mean": [
            2.0, 3.5, 5.0, 7.5, 10.0,
            12.0, 14.0, 8.0, 6.0, 4.5,
            3.0, 9.5, 11.0, 13.5, 5.5,
            7.0, 15.0, 20.0, 22.0, 1.0,
        ],
        "Active Power_Mean": [
            0.0, 50.0, 250.0, 700.0, 1400.0,
            2000.0, 2050.0, 900.0, 400.0, 100.0,
            0.0, 1200.0, 1800.0, 2050.0, 300.0,
            600.0, 2050.0, 2050.0, 2050.0, 0.0,
        ],
        "Nacelle Ambient Temp_Mean": [
            10.0, 10.5, 11.0, 11.5, 12.0,
            12.5, 13.0, 12.0, 11.0, 10.5,
            10.0, 11.5, 12.0, 13.0, 11.0,
            11.5, 13.5, 14.0, 14.5, 10.0,
        ],
        "Gear Oil Temp_Mean": [
            45.0, 46.0, 48.0, 52.0, 58.0,
            62.0, 65.0, 55.0, 50.0, 47.0,
            44.0, 57.0, 61.0, 64.0, 49.0,
            53.0, 66.0, 70.0, 72.0, 43.0,
        ],
    }
    return pd.DataFrame(data, index=index)


@pytest.fixture()
def app_settings() -> Settings:
    """建立應用程式設定實例。

    Returns:
        使用預設值的 Settings 實例（不從 .env 檔案載入）。
    """
    return Settings()
