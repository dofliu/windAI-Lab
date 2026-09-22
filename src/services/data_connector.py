"""數據連接器服務 — 支援定時從 REST API 或本地模擬拉取 SCADA 資料並觸發主動分析。"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

logger = logging.getLogger("windailab.data_connector")

# 專案根目錄
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class BaseConnector(ABC):
    """資料連接器抽象基類。"""

    def __init__(self, connector_id: str, name: str, interval: int, config: dict[str, Any]):
        self.connector_id = connector_id
        self.name = name
        self.interval = interval
        self.config = config
        self.is_connected = False
        self.last_fetch_time: str | None = None
        self.fetch_count = 0

    @abstractmethod
    async def connect(self) -> bool:
        """建立連線。"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """斷開連線。"""
        pass

    @abstractmethod
    async def fetch_data(self) -> pd.DataFrame | None:
        """拉取 SCADA 資料並返回為 DataFrame。"""
        pass

    @property
    def status(self) -> dict[str, Any]:
        """取得連接器目前狀態。"""
        return {
            "id": self.connector_id,
            "name": self.name,
            "type": self.__class__.__name__.replace("Connector", "").lower(),
            "interval": self.interval,
            "is_connected": self.is_connected,
            "last_fetch_time": self.last_fetch_time,
            "fetch_count": self.fetch_count,
        }


class MockConnector(BaseConnector):
    """模擬連接器 — 定期從本地 Kelmarsh 歷史 SCADA 數據中截取一筆記錄以模擬實時流數據。"""

    def __init__(self, connector_id: str, name: str, interval: int, config: dict[str, Any]):
        super().__init__(connector_id, name, interval, config)
        self.turbine_id = config.get("turbine_id", "WT-01")
        self.data_cache: pd.DataFrame | None = None
        self.current_index = 0

    async def connect(self) -> bool:
        try:
            # 尋找本地 external 數據檔以載入模擬數據快取
            ext_dir = _PROJECT_ROOT / "data" / "external"
            data_file = None

            # Kelmarsh 數據檔名命名慣例中通常含有 Turbine_Data_Kelmarsh_
            # 我們尋找與 turbine_id（如 WT-01 -> Kelmarsh_1）匹配的檔案
            # 對照表：WT-01 ~ WT-06 = Kelmarsh_1 ~ Kelmarsh_6
            mapping_id = self.turbine_id
            if self.turbine_id.startswith("WT-"):
                try:
                    num = int(self.turbine_id.split("-")[1])
                    mapping_id = f"Kelmarsh_{num}"
                except Exception:
                    pass

            if ext_dir.exists():
                for f in ext_dir.iterdir():
                    if f.is_file() and "Turbine_Data_" in f.name and mapping_id in f.name:
                        data_file = f
                        break

            if not data_file:
                logger.warning(
                    f"MockConnector 找不到 {self.turbine_id} 的 external 數據檔，將使用隨機生成模式"
                )
                self.is_connected = True
                return True

            logger.info(f"MockConnector 載入數據源以進行模擬拉取：{data_file.name}")
            # 為加速啟動，僅載入前 500 行作為模擬迴圈庫
            loop = asyncio.get_event_loop()
            self.data_cache = await loop.run_in_executor(
                None, lambda: pd.read_csv(data_file, nrows=500, comment="#")
            )
            self.current_index = 0
            self.is_connected = True
            return True
        except Exception as e:
            logger.error(f"MockConnector 連線/初始化失敗：{e}")
            self.is_connected = False
            return False

    async def disconnect(self) -> None:
        self.is_connected = False
        self.data_cache = None

    async def fetch_data(self) -> pd.DataFrame | None:
        if not self.is_connected:
            await self.connect()

        self.fetch_count += 1
        self.last_fetch_time = datetime.now(UTC).isoformat()

        # 模式一：如果快取有載入數據，定時順序或隨機返回一筆
        if self.data_cache is not None and len(self.data_cache) > 0:
            row = self.data_cache.iloc[[self.current_index]].copy()
            # 更新時間戳記為當前時間以模擬實時性
            timestamp_col = next(
                (c for c in row.columns if "timestamp" in c.lower() or "time" in c.lower()), None
            )
            if timestamp_col:
                row[timestamp_col] = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")

            # 更新下一筆索引用於下次抓取，循環利用
            self.current_index = (self.current_index + 1) % len(self.data_cache)
            return row

        # 模式二：若無本地檔案，生成隨機合理的模擬行數據
        import random

        ws = random.uniform(3.0, 15.0)
        # 簡易正常風速/功率曲線對照 (12m/s 滿載 2050kW)
        if ws < 3.0:
            power = 0.0
        elif ws > 12.0:
            power = 2050.0
        else:
            power = 2050.0 * (((ws - 3) / 9) ** 3)

        mock_data = {
            "Timestamp": [datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")],
            "Wind_speed": [ws],
            "Active_power": [power],
            "Generator_temp": [random.uniform(65.0, 85.0)],
            "Gear_oil_temp": [random.uniform(55.0, 70.0)],
            "Nacelle_direction": [random.uniform(0.0, 360.0)],
        }
        return pd.DataFrame(mock_data)


class RESTConnector(BaseConnector):
    """REST API 連接器 — 從外部 HTTP/JSON 資料接口定時拉取最新數據。"""

    async def connect(self) -> bool:
        self.is_connected = True
        return True

    async def disconnect(self) -> None:
        self.is_connected = False

    async def fetch_data(self) -> pd.DataFrame | None:
        import httpx

        url = self.config.get("url")
        if not url:
            logger.error("RESTConnector 未配置 url")
            return None

        self.fetch_count += 1
        self.last_fetch_time = datetime.now(UTC).isoformat()

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=self.config.get("params"))
                if response.status_code == 200:
                    json_data = response.json()

                    # 嘗試包裝成 DataFrame
                    if isinstance(json_data, list):
                        df = pd.DataFrame(json_data)
                    elif isinstance(json_data, dict):
                        # 如果是單筆記錄 dict，將其放入 list 轉為 DataFrame
                        df = pd.DataFrame([json_data])
                    else:
                        logger.error(f"RESTConnector 收到不支援的 JSON 格式：{type(json_data)}")
                        return None

                    # 如果有欄位映射配置，進行映射
                    mapping = self.config.get("columns_mapping")
                    if mapping:
                        df = df.rename(columns=mapping)

                    return df
                else:
                    logger.error(f"RESTConnector 拉取失敗，HTTP 狀態碼：{response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"RESTConnector 拉取異常：{e}")
            return None


# paho.mqtt fallback 機制
try:
    import paho.mqtt.client as mqtt_lib

    HAS_PAHO = True
except ImportError:
    HAS_PAHO = False
    mqtt_lib = None


class MQTTConnector(BaseConnector):
    """MQTT 資料連接器 — 訂閱 MQTT Topic 以實時流式接收數據，定時批次封裝為 DataFrame 返回。"""

    def __init__(self, connector_id: str, name: str, interval: int, config: dict[str, Any]):
        super().__init__(connector_id, name, interval, config)
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 1883)
        self.topic = config.get("topic", "wind/scada")
        self.username = config.get("username")
        self.password = config.get("password")
        self.client_id = config.get("client_id", f"windai_connector_{connector_id}")
        self.turbine_id = config.get("turbine_id", "WT-01")

        self._buffer: list[dict[str, Any]] = []
        self._mqtt_client: Any = None
        self._simulate_task: asyncio.Task[None] | None = None

    async def connect(self) -> bool:
        if self.is_connected:
            return True

        if HAS_PAHO:
            try:
                self._mqtt_client = mqtt_lib.Client(client_id=self.client_id)
                if self.username and self.password:
                    self._mqtt_client.username_pw_set(self.username, self.password)

                def on_message(client: Any, userdata: Any, msg: Any) -> None:
                    import json

                    try:
                        payload = json.loads(msg.payload.decode("utf-8"))
                        if isinstance(payload, dict):
                            self._buffer.append(payload)
                        elif isinstance(payload, list):
                            self._buffer.extend(
                                [item for item in payload if isinstance(item, dict)]
                            )
                    except Exception as e:
                        logger.error(f"MQTTConnector 解析 Payload 失敗：{e}")

                self._mqtt_client.on_message = on_message

                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, lambda: self._mqtt_client.connect(self.host, self.port, keepalive=60)
                )
                self._mqtt_client.subscribe(self.topic)
                self._mqtt_client.loop_start()

                self.is_connected = True
                logger.info(f"MQTTConnector [{self.name}] 成功連線並訂閱 Topic: {self.topic}")
                return True
            except Exception as e:
                logger.error(
                    f"MQTTConnector [{self.name}] 真實連線失敗：{e}。將嘗試 Fallback 模擬流。"
                )
                self._start_simulator()
                self.is_connected = True
                return True
        else:
            logger.info(
                f"系統未安裝 paho-mqtt。MQTTConnector [{self.name}] 將自動啟動背景模擬流。"
            )
            self._start_simulator()
            self.is_connected = True
            return True

    def _start_simulator(self) -> None:
        """啟動 asyncio 數據流模擬器。"""
        if self._simulate_task is None or self._simulate_task.done():
            self._simulate_task = asyncio.create_task(self._simulate_stream())

    async def _simulate_stream(self) -> None:
        """背景定時向 Buffer 推送 SCADA 數據以模擬 MQTT 流。"""
        import random

        while True:
            try:
                await asyncio.sleep(random.uniform(5.0, 10.0))
                ws = random.uniform(3.0, 15.0)
                if ws < 3.0:
                    power = 0.0
                elif ws > 12.0:
                    power = 2050.0
                else:
                    power = 2050.0 * (((ws - 3) / 9) ** 3)

                data = {
                    "Timestamp": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
                    "Wind_speed": ws,
                    "Active_power": power,
                    "Generator_temp": random.uniform(65.0, 85.0),
                    "Gear_oil_temp": random.uniform(55.0, 70.0),
                    "Nacelle_direction": random.uniform(0.0, 360.0),
                }
                self._buffer.append(data)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"MQTT 模擬器出錯：{e}")
                await asyncio.sleep(5)

    async def disconnect(self) -> None:
        if not self.is_connected:
            return

        if self._mqtt_client:
            try:
                self._mqtt_client.loop_stop()
                self._mqtt_client.disconnect()
            except Exception as e:
                logger.error(f"斷開 MQTT 連線失敗：{e}")
            self._mqtt_client = None

        if self._simulate_task:
            self._simulate_task.cancel()
            self._simulate_task = None

        self.is_connected = False
        logger.info(f"MQTTConnector [{self.name}] 已斷開連線")

    async def fetch_data(self) -> pd.DataFrame | None:
        self.fetch_count += 1
        self.last_fetch_time = datetime.now(UTC).isoformat()

        if not self._buffer:
            import random

            mock_row = {
                "Timestamp": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
                "Wind_speed": random.uniform(6.0, 10.0),
                "Active_power": random.uniform(800.0, 1500.0),
                "Generator_temp": random.uniform(70.0, 80.0),
                "Gear_oil_temp": random.uniform(60.0, 68.0),
                "Nacelle_direction": random.uniform(180.0, 200.0),
            }
            return pd.DataFrame([mock_row])

        data_list = list(self._buffer)
        self._buffer.clear()

        df = pd.DataFrame(data_list)
        mapping = self.config.get("columns_mapping")
        if mapping:
            df = df.rename(columns=mapping)
        return df


class ConnectorManager:
    """資料對接管理器 — 控制多個連接器的背景定時拉取生命週期。"""

    def __init__(self, configs_dir: Path | None = None):
        self.configs_dir = configs_dir or (_PROJECT_ROOT / "configs" / "connectors")
        self.connectors: dict[str, BaseConnector] = {}
        self.active_tasks: dict[str, asyncio.Task[None]] = {}
        self.fail_counts: dict[str, int] = {}
        self.is_running = False

    def load_connectors(self) -> int:
        """載入設定檔並初始化連接器。"""
        if not self.configs_dir.exists():
            self.configs_dir.mkdir(parents=True, exist_ok=True)
            self._create_default_config()

        count = 0
        for f in self.configs_dir.iterdir():
            if f.is_file() and f.suffix in (".yaml", ".yml"):
                try:
                    with f.open("r", encoding="utf-8") as stream:
                        cfg = yaml.safe_load(stream)

                    if not cfg or not cfg.get("enabled", False):
                        continue

                    cid = cfg.get("id")
                    name = cfg.get("name", cid)
                    ctype = cfg.get("type", "mock").lower()
                    interval = cfg.get("interval_seconds", 60)
                    config_data = cfg.get("config", {})

                    if ctype == "mock":
                        conn = MockConnector(cid, name, interval, config_data)
                    elif ctype == "rest":
                        conn = RESTConnector(cid, name, interval, config_data)
                    elif ctype == "mqtt":
                        conn = MQTTConnector(cid, name, interval, config_data)
                    else:
                        logger.warning(f"不支援的連接器類型：{ctype}")
                        continue

                    self.connectors[cid] = conn
                    count += 1
                except Exception as e:
                    logger.error(f"載入連接器設定檔失敗 {f.name}：{e}")

        logger.info(f"資料對接管理器：已載入並初始化 {count} 個啟用中的連接器")
        return count

    def get_all_status(self) -> list[dict[str, Any]]:
        """取得所有連接器的狀態清單。"""
        return [c.status for c in self.connectors.values()]

    async def start(self) -> None:
        """啟動所有啟用中的連接器背景抓取任務。"""
        if self.is_running:
            return

        self.is_running = True
        self.load_connectors()

        for cid, conn in self.connectors.items():
            self.active_tasks[cid] = asyncio.create_task(self._fetch_loop(conn))

        logger.info("資料對接管理器背景任務已啟動")

    async def stop(self) -> None:
        """停止所有連接器的背景任務。"""
        self.is_running = False

        # 取消所有背景 Task
        for _cid, task in self.active_tasks.items():
            task.cancel()

        # 斷開連線
        for conn in self.connectors.values():
            await conn.disconnect()

        self.active_tasks.clear()
        self.connectors.clear()
        logger.info("資料對接管理器背景任務已停止")

    async def toggle_connector(self, cid: str, enable: bool) -> bool:
        """動態啟用或停用連接器。"""
        # 1. 如果已載入且需要停用
        if not enable and cid in self.connectors:
            if cid in self.active_tasks:
                self.active_tasks[cid].cancel()
                del self.active_tasks[cid]
            conn = self.connectors[cid]
            await conn.disconnect()
            del self.connectors[cid]
            logger.info(f"連接器已動態停用：{cid}")
            return True

        # 2. 如果未載入且需要啟用
        if enable and cid not in self.connectors:
            # 尋找對應的設定檔
            f = self.configs_dir / f"{cid}.yaml"
            if not f.exists():
                f = self.configs_dir / f"{cid}.yml"
            if not f.exists():
                logger.error(f"找不到連接器設定檔：{cid}")
                return False

            try:
                with f.open("r", encoding="utf-8") as stream:
                    cfg = yaml.safe_load(stream)

                name = cfg.get("name", cid)
                ctype = cfg.get("type", "mock").lower()
                interval = cfg.get("interval_seconds", 60)
                config_data = cfg.get("config", {})

                if ctype == "mock":
                    conn = MockConnector(cid, name, interval, config_data)
                elif ctype == "rest":
                    conn = RESTConnector(cid, name, interval, config_data)
                elif ctype == "mqtt":
                    conn = MQTTConnector(cid, name, interval, config_data)
                else:
                    return False

                await conn.connect()
                self.connectors[cid] = conn
                if self.is_running:
                    self.active_tasks[cid] = asyncio.create_task(self._fetch_loop(conn))
                logger.info(f"連接器已動態啟用：{cid}")
                return True
            except Exception as e:
                logger.error(f"動態啟用連接器失敗：{e}")
                return False

        return False

    def _handle_fetch_success(self, conn: BaseConnector) -> None:
        self.fail_counts[conn.connector_id] = 0

    def _handle_fetch_fail(self, conn: BaseConnector) -> None:
        self.fail_counts[conn.connector_id] = self.fail_counts.get(conn.connector_id, 0) + 1
        if self.fail_counts[conn.connector_id] >= 3:
            try:
                from src.services.alert_engine import get_alert_rule_engine

                engine = get_alert_rule_engine()
                engine.evaluate(
                    {
                        "connector_online_status": 0.0,
                        "connector_id": conn.connector_id,
                    },
                    turbine_id=conn.config.get("turbine_id", "SYSTEM"),
                )
                logger.warning(f"連接器 [{conn.name}] 連續 3 次拉取失敗，已觸發離線告警！")
            except Exception as e:
                logger.error(f"發送連接器離線告警失敗：{e}")

    async def _fetch_loop(self, conn: BaseConnector) -> None:
        """單一連接器的抓取迴圈。"""
        # 初始連線
        await conn.connect()

        while self.is_running:
            try:
                await asyncio.sleep(conn.interval)
                if not self.is_running:
                    break

                df = await conn.fetch_data()
                if df is not None and len(df) > 0:
                    self._handle_fetch_success(conn)
                    # 將資料存為 CSV 並寫入 data/raw 目錄以觸發 FileWatcher
                    target_dir = _PROJECT_ROOT / "data" / "raw"
                    target_dir.mkdir(parents=True, exist_ok=True)

                    turbine_id = conn.config.get("turbine_id", "WT-01")
                    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
                    filename = f"{turbine_id}_api_fetched_{timestamp}.csv"
                    file_path = target_dir / filename

                    # 異步寫入 CSV
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None, lambda data_df=df, fp=file_path: data_df.to_csv(fp, index=False)
                    )
                    logger.info(f"連接器 [{conn.name}] 拉取成功：數據已保存至 {filename}")
                else:
                    logger.warning(f"連接器 [{conn.name}] 拉取返回空數據或 None")
                    self._handle_fetch_fail(conn)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"連接器 [{conn.name}] 抓取迴圈發生錯誤：{e}")
                self._handle_fetch_fail(conn)
                await asyncio.sleep(10)  # 出錯後等待 10 秒再重試

    def _create_default_config(self) -> None:
        """建立預設的 MockConnector 設定檔以進行展示。"""
        default_cfg = {
            "id": "kelmarsh_mock",
            "name": "Kelmarsh WT-01 模擬拉取數據源",
            "type": "mock",
            "enabled": True,
            "interval_seconds": 60,
            "config": {
                "turbine_id": "WT-01",
            },
        }
        f = self.configs_dir / "kelmarsh_mock.yaml"
        try:
            with f.open("w", encoding="utf-8") as stream:
                yaml.safe_dump(default_cfg, stream, allow_unicode=True)
            logger.info(f"已建立預設模擬連接器設定檔：{f.name}")
        except Exception as e:
            logger.error(f"建立預設設定檔失敗：{e}")
