"""風場監控服務 — 定期拉資料、健康評估、告警觸發、自動派工。

核心運作循環：
1. 依各風場設定的 poll_interval_min 定期執行
2. 透過 DataConnector 取得最新 SCADA 資料
3. 呼叫 anomaly_detection 技能計算健康分數
4. 依門檻判斷告警等級
5. 紅色告警 → 建立工單 + 自動觸發 /diagnose workflow
6. 透過 WebSocket 推播告警至前端
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.services.wind_farm import (
    AlertSeverity,
    HealthLevel,
    MonitorRecord,
    ServiceTicket,
    TicketPriority,
    TicketStatus,
    TicketTrigger,
    WindFarm,
    WindFarmStatus,
)
from src.utils.logger import get_logger

logger = get_logger("wind_farm.monitor")


class DataConnector:
    """抽象資料連接器 — 統一不同來源的 SCADA 資料取得。

    目前支援：
    - local_file: 讀取本地 CSV/Parquet 檔案
    - rest_api: 預留（透過 httpx 取得 JSON → DataFrame）
    - opc_ua / sftp: 預留介面
    """

    @staticmethod
    async def fetch(farm: WindFarm) -> dict[str, pd.DataFrame]:
        """取得風場的 SCADA 資料。

        Returns:
            {turbine_id: DataFrame} 的映射。
            若風場只有一個資料檔，turbine_id 從檔名或 farm 設定推斷。
        """
        source = farm.data_source
        loop = asyncio.get_event_loop()

        if source.source_type == "local_file":
            return await loop.run_in_executor(None, lambda: _load_local(source.path, farm))
        elif source.source_type == "rest_api":
            return await _fetch_rest_api(source, farm)
        else:
            logger.warning(f"資料來源類型 {source.source_type} 尚未實作")
            return {}


def _load_local(path_str: str, farm: WindFarm) -> dict[str, pd.DataFrame]:
    """從本地檔案/資料夾載入資料。"""
    path = Path(path_str)
    result: dict[str, pd.DataFrame] = {}

    if not path.exists():
        logger.warning(f"路徑不存在：{path_str}")
        return result

    if path.is_file():
        df = _read_file(path)
        if df is not None:
            # 用檔名推斷 turbine_id
            tid = path.stem.split("_")[0] if "_" in path.stem else "WT-01"
            result[tid] = df
    elif path.is_dir():
        for f in sorted(path.glob("*.csv")) + sorted(path.glob("*.parquet")):
            df = _read_file(f)
            if df is not None:
                tid = f.stem.split("_")[0] if "_" in f.stem else f.stem
                result[tid] = df

    return result


def _read_file(path: Path) -> pd.DataFrame | None:
    """讀取單一 SCADA 檔案。"""
    try:
        if path.suffix.lower() == ".parquet":
            return pd.read_parquet(path)
        elif path.suffix.lower() == ".csv":
            return pd.read_csv(path, parse_dates=True, index_col=0)
        return None
    except Exception as e:
        logger.warning(f"讀取 {path.name} 失敗：{e}")
        return None


async def _fetch_rest_api(source: Any, farm: WindFarm) -> dict[str, pd.DataFrame]:
    """透過 REST API 取得 SCADA 資料（預留實作）。"""
    try:
        import httpx

        headers = {}
        if source.auth_token:
            headers["Authorization"] = f"Bearer {source.auth_token}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(source.path, headers=headers)
            resp.raise_for_status()
            data = resp.json()

            # 預期格式：{turbine_id: [{timestamp, wind_speed, power, ...}]}
            result: dict[str, pd.DataFrame] = {}
            if isinstance(data, dict):
                for tid, records in data.items():
                    if isinstance(records, list):
                        result[tid] = pd.DataFrame(records)
            return result
    except Exception as e:
        logger.error(f"REST API 取得資料失敗：{e}")
        return {}


# ════════════════════════════════════════════════════════════════
# 監控服務主體
# ════════════════════════════════════════════════════════════════


class MonitorService:
    """風場監控服務。

    管理所有風場的定期監控迴圈，包含：
    - 排程管理（每個風場獨立的輪詢週期）
    - 健康評估執行
    - 告警門檻判斷
    - 自動工單建立與派工
    """

    def __init__(self) -> None:
        self._running = False
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._records: list[MonitorRecord] = []
        self._tickets: list[ServiceTicket] = []
        self._max_records = 1000

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def records(self) -> list[MonitorRecord]:
        return self._records

    @property
    def tickets(self) -> list[ServiceTicket]:
        return self._tickets

    def get_ticket(self, ticket_id: str) -> ServiceTicket | None:
        """取得工單。"""
        for t in self._tickets:
            if t.id == ticket_id:
                return t
        return None

    def get_tickets_by_farm(self, farm_id: str) -> list[ServiceTicket]:
        """取得特定風場的所有工單。"""
        return [t for t in self._tickets if t.wind_farm_id == farm_id]

    def get_open_tickets(self) -> list[ServiceTicket]:
        """取得所有未關閉的工單。"""
        closed = {TicketStatus.RESOLVED, TicketStatus.CLOSED}
        return [t for t in self._tickets if t.status not in closed]

    # ── 手動建立工單 ────────────────────────────────────────

    def create_ticket(
        self,
        wind_farm_id: str,
        turbine_id: str = "",
        title: str = "",
        description: str = "",
        priority: str = "medium",
        trigger: str = "manual",
    ) -> ServiceTicket:
        """手動建立服務工單。"""
        from src.services.wind_farm.registry import wind_farm_registry

        farm = wind_farm_registry.get(wind_farm_id)
        ticket = ServiceTicket(
            wind_farm_id=wind_farm_id,
            wind_farm_name=farm.name if farm else "",
            turbine_id=turbine_id,
            title=title or f"{turbine_id or '風場'} 服務請求",
            description=description,
            priority=TicketPriority(priority),
            trigger=TicketTrigger(trigger),
        )
        self._tickets.append(ticket)
        logger.info(f"工單已建立：{ticket.id} — {ticket.title}")
        return ticket

    def update_ticket_status(
        self, ticket_id: str, status: str, resolution: str = ""
    ) -> ServiceTicket | None:
        """更新工單狀態。"""
        ticket = self.get_ticket(ticket_id)
        if ticket is None:
            return None

        ticket.status = TicketStatus(status)
        now = datetime.now(UTC).isoformat()

        if status == "assigned":
            ticket.assigned_at = now
        elif status == "in_progress":
            ticket.started_at = now
        elif status == "resolved":
            ticket.resolved_at = now
            if resolution:
                ticket.resolution = resolution
        elif status == "closed":
            ticket.closed_at = now

        return ticket

    # ── 監控迴圈 ────────────────────────────────────────────

    async def start(self) -> None:
        """啟動所有啟用中風場的監控迴圈。"""
        from src.services.wind_farm.registry import wind_farm_registry

        if self._running:
            return

        self._running = True
        logger.info("監控服務啟動")

        for farm in wind_farm_registry.list_active():
            self._start_farm_loop(farm)

    async def stop(self) -> None:
        """停止所有監控迴圈。"""
        self._running = False
        for task in self._tasks.values():
            task.cancel()
        self._tasks.clear()
        logger.info("監控服務已停止")

    def start_farm_monitor(self, farm_id: str) -> bool:
        """啟動單一風場的監控。"""
        from src.services.wind_farm.registry import wind_farm_registry

        farm = wind_farm_registry.get(farm_id)
        if farm is None:
            return False
        self._start_farm_loop(farm)
        return True

    def stop_farm_monitor(self, farm_id: str) -> bool:
        """停止單一風場的監控。"""
        task = self._tasks.pop(farm_id, None)
        if task:
            task.cancel()
            return True
        return False

    def _start_farm_loop(self, farm: WindFarm) -> None:
        """建立並啟動單一風場的監控非同步任務。"""
        if farm.id in self._tasks:
            return

        async def _loop() -> None:
            while self._running:
                try:
                    await self._check_farm(farm)
                except Exception as e:
                    logger.error(f"風場 {farm.name} 監控異常：{e}")
                    farm.consecutive_errors += 1
                    if farm.consecutive_errors >= 3:
                        farm.status = WindFarmStatus.ERROR
                        logger.warning(f"風場 {farm.name} 連續 3 次錯誤，標記為異常")
                await asyncio.sleep(farm.poll_interval_min * 60)

        self._tasks[farm.id] = asyncio.create_task(_loop())
        logger.info(f"風場 {farm.name} 監控已啟動（每 {farm.poll_interval_min} 分鐘）")

    async def _check_farm(self, farm: WindFarm) -> None:
        """執行單次風場健康檢查。"""
        from src.services.wind_farm.registry import wind_farm_registry

        logger.info(f"開始檢查風場：{farm.name}")
        farm.last_poll_at = datetime.now(UTC).isoformat()

        # 取得資料
        turbine_data = await DataConnector.fetch(farm)
        if not turbine_data:
            logger.warning(f"風場 {farm.name} 無法取得資料")
            farm.consecutive_errors += 1
            return

        farm.consecutive_errors = 0

        # 對每台風機進行健康評估
        for turbine_id, df in turbine_data.items():
            record = await self._evaluate_turbine(farm, turbine_id, df)
            if record:
                self._records.append(record)
                # 限制紀錄數量
                if len(self._records) > self._max_records:
                    self._records = self._records[-self._max_records :]

                # 更新 registry
                level = wind_farm_registry.update_turbine_health(
                    farm.id,
                    turbine_id,
                    record.health_score,
                    record.anomaly_count,
                    record.power_curve_deviation_pct,
                )

                # 告警判斷
                await self._handle_alert(farm, turbine_id, record, level)

    async def _evaluate_turbine(
        self, farm: WindFarm, turbine_id: str, df: pd.DataFrame
    ) -> MonitorRecord | None:
        """對單台風機執行健康評估。"""
        if df.empty:
            return None

        loop = asyncio.get_event_loop()

        try:
            from src.models.evaluation.anomaly_analysis import (
                compute_health_score,
                detect_power_curve_anomalies,
                detect_temperature_anomalies,
            )

            temp_result = await loop.run_in_executor(
                None, lambda: detect_temperature_anomalies(df)
            )
            pc_result = await loop.run_in_executor(None, lambda: detect_power_curve_anomalies(df))
            health_result = await loop.run_in_executor(None, lambda: compute_health_score(df))

            health_score = health_result.get("health_score", -1)
            anomaly_count = temp_result.get("anomaly_count", 0)
            pc_dev = pc_result.get("mean_deviation_pct", 0)
            eff_loss = pc_result.get("efficiency_loss_pct", 0)

            # 判斷告警等級
            severity = None
            if health_score < farm.alert_threshold_critical:
                severity = AlertSeverity.CRITICAL
            elif health_score < farm.alert_threshold_warning:
                severity = AlertSeverity.WARNING

            return MonitorRecord(
                wind_farm_id=farm.id,
                turbine_id=turbine_id,
                health_score=round(health_score, 1),
                anomaly_count=anomaly_count,
                power_curve_deviation_pct=round(pc_dev, 2),
                efficiency_loss_pct=round(eff_loss, 2),
                alert_severity=severity,
                details={
                    "health_details": health_result,
                    "temperature_components": temp_result.get("components_checked", []),
                },
            )
        except Exception as e:
            logger.error(f"風機 {turbine_id} 健康評估失敗：{e}")
            return None

    async def _handle_alert(
        self,
        farm: WindFarm,
        turbine_id: str,
        record: MonitorRecord,
        level: HealthLevel,
    ) -> None:
        """處理告警：WebSocket 推播 + 自動建立工單 + 觸發診斷。"""
        from src.api.websocket_manager import manager as ws_manager

        if record.alert_severity is None:
            return

        # WebSocket 推播告警
        alert_payload = {
            "type": "wind_farm_alert",
            "payload": {
                "wind_farm_id": farm.id,
                "wind_farm_name": farm.name,
                "turbine_id": turbine_id,
                "health_score": record.health_score,
                "severity": record.alert_severity,
                "anomaly_count": record.anomaly_count,
                "message": (
                    f"{'🔴' if level == HealthLevel.CRITICAL else '🟡'} "
                    f"{farm.name} {turbine_id} 健康分數 {record.health_score}/100"
                ),
                "timestamp": record.timestamp,
            },
        }
        await ws_manager.broadcast(alert_payload)

        # 紅色告警 → 自動建立工單
        if level == HealthLevel.CRITICAL:
            # 檢查是否已有該風機的進行中工單
            existing = [
                t
                for t in self._tickets
                if t.wind_farm_id == farm.id
                and t.turbine_id == turbine_id
                and t.status not in (TicketStatus.RESOLVED, TicketStatus.CLOSED)
            ]
            if existing:
                logger.info(f"{turbine_id} 已有進行中工單，跳過重複建立")
                return

            ticket = self.create_ticket(
                wind_farm_id=farm.id,
                turbine_id=turbine_id,
                title=f"{farm.name} {turbine_id} 健康異常（分數 {record.health_score}）",
                description=(
                    f"自動監控偵測到 {turbine_id} 健康分數降至 {record.health_score}/100，"
                    f"溫度異常 {record.anomaly_count} 筆，"
                    f"功率曲線偏差 {record.power_curve_deviation_pct}%"
                ),
                priority="critical",
                trigger="auto_monitor",
            )
            ticket.health_score_at_creation = record.health_score
            record.ticket_id = ticket.id

            # 自動觸發 /diagnose workflow
            if farm.auto_diagnose:
                await self._trigger_diagnosis(farm, turbine_id, ticket)

    async def _trigger_diagnosis(
        self, farm: WindFarm, turbine_id: str, ticket: ServiceTicket
    ) -> None:
        """自動觸發故障診斷工作流程。"""
        from src.agents.orchestrator.engine import engine
        from src.agents.orchestrator.workflows import create_diagnose_workflow
        from src.api.websocket_manager import manager as ws_manager

        ticket.status = TicketStatus.IN_PROGRESS
        ticket.started_at = datetime.now(UTC).isoformat()
        ticket.assigned_agents = [
            "project-director",
            "fault-diagnostician",
            "power-curve-expert",
            "predictive-modeler",
        ]

        workflow = create_diagnose_workflow(turbine_id)
        task_id = await engine.run_workflow_background(workflow)
        ticket.workflow_id = task_id

        # 廣播自動派工事件
        await ws_manager.broadcast(
            {
                "type": "auto_dispatch",
                "payload": {
                    "ticket_id": ticket.id,
                    "wind_farm_name": farm.name,
                    "turbine_id": turbine_id,
                    "workflow_id": task_id,
                    "message": (
                        f"🚨 已自動派工：{farm.name} {turbine_id} 故障診斷 " f"(工單 {ticket.id})"
                    ),
                },
            }
        )

        logger.info(
            f"自動診斷已觸發：{farm.name} {turbine_id} "
            f"(ticket={ticket.id}, workflow={task_id})"
        )

    # ── 手動觸發 ────────────────────────────────────────────

    async def check_farm_now(self, farm_id: str) -> list[MonitorRecord]:
        """手動觸發單次風場健康檢查。"""
        from src.services.wind_farm.registry import wind_farm_registry

        farm = wind_farm_registry.get(farm_id)
        if farm is None:
            return []

        records_before = len(self._records)
        await self._check_farm(farm)
        return self._records[records_before:]

    def get_farm_history(self, farm_id: str, limit: int = 50) -> list[MonitorRecord]:
        """取得風場的監控歷史紀錄。"""
        records = [r for r in self._records if r.wind_farm_id == farm_id]
        return records[-limit:]


# 全域單例
monitor_service = MonitorService()
