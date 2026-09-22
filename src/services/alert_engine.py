"""告警規則引擎核心 — 分析結果自動觸發告警。

根據可配置的規則，在工作流程完成後自動檢查分析結果，
當指標超過閾值時建立告警並可選自動建立工單。
"""

import asyncio
import contextlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

OPERATORS: dict[str, Any] = {
    "<": lambda a, b: a < b,
    ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


@dataclass
class RuleCondition:
    """單一規則條件。"""

    metric: str
    operator: str
    threshold: float


@dataclass
class AlertRule:
    """告警規則定義。"""

    id: str
    name: str
    enabled: bool = True
    conditions: list[RuleCondition] = field(default_factory=list)
    severity: str = "warning"
    silence_minutes: int = 360
    auto_create_work_order: bool = False
    notify_channels: list[str] = field(default_factory=list)
    description_template: str = ""

    def to_dict(self) -> dict[str, Any]:
        """序列化為 dict。"""
        return {
            "id": self.id,
            "name": self.name,
            "enabled": self.enabled,
            "conditions": [
                {"metric": c.metric, "operator": c.operator, "threshold": c.threshold}
                for c in self.conditions
            ],
            "severity": self.severity,
            "silence_minutes": self.silence_minutes,
            "auto_create_work_order": self.auto_create_work_order,
            "notify_channels": self.notify_channels,
            "description_template": self.description_template,
        }


class AlertRuleEngine:
    """告警規則引擎。

    管理告警規則，在分析完成後自動檢查指標，
    觸發告警並透過 WebSocket 即時推播。
    """

    def __init__(self) -> None:
        self._rules: list[AlertRule] = []
        self._silence_tracker: dict[str, datetime] = {}
        self.load_rules()
        logger.info(f"告警規則引擎初始化完成，載入 {len(self._rules)} 條規則")

    def load_rules(self, file_path: Path | str | None = None) -> None:
        """從 YAML 設定檔載入告警規則。若檔案不存在則會自動建立預設檔。"""
        if file_path is None:
            file_path = _PROJECT_ROOT / "configs" / "alerts" / "rules.yaml"
        else:
            file_path = Path(file_path)

        if not file_path.exists():
            logger.warning(f"告警規則檔不存在：{file_path}，將嘗試建立預設檔")
            self._create_default_rules_yaml(file_path)

        try:
            with open(file_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            rules_data = data.get("rules", [])
            new_rules = []
            for rd in rules_data:
                conditions = []
                for cond_data in rd.get("conditions", []):
                    conditions.append(
                        RuleCondition(
                            metric=cond_data["metric"],
                            operator=cond_data["operator"],
                            threshold=float(cond_data["threshold"]),
                        )
                    )
                new_rules.append(
                    AlertRule(
                        id=rd["id"],
                        name=rd["name"],
                        enabled=rd.get("enabled", True),
                        conditions=conditions,
                        severity=rd.get("severity", "warning"),
                        silence_minutes=int(rd.get("silence_minutes", 360)),
                        auto_create_work_order=rd.get("auto_create_work_order", False),
                        notify_channels=rd.get("notify_channels", []),
                        description_template=rd.get("description_template", ""),
                    )
                )
            self._rules = new_rules
            logger.info(f"成功從 YAML 載入 {len(self._rules)} 條告警規則")
        except Exception as e:
            logger.error(f"從 YAML 載入告警規則失敗：{e}。將維持既有規則。")
            if not self._rules:
                self._load_default_rules()

    def _create_default_rules_yaml(self, file_path: Path) -> None:
        """生成預設的 rules.yaml 檔案。"""
        defaults = {
            "rules": [
                {
                    "id": "health_score_critical",
                    "name": "健康分數嚴重過低",
                    "enabled": True,
                    "severity": "critical",
                    "silence_minutes": 120,
                    "auto_create_work_order": True,
                    "notify_channels": ["email", "line"],
                    "conditions": [{"metric": "health_score", "operator": "<", "threshold": 0.5}],
                    "description_template": "風機健康分數 {health_score:.2f}，低於臨界值 0.5，需立即檢修",
                },
                {
                    "id": "health_score_warning",
                    "name": "健康分數過低",
                    "enabled": True,
                    "severity": "warning",
                    "silence_minutes": 360,
                    "auto_create_work_order": False,
                    "notify_channels": ["email"],
                    "conditions": [{"metric": "health_score", "operator": "<", "threshold": 0.7}],
                    "description_template": "風機健康分數 {health_score:.2f}，低於警戒值 0.7，建議排程檢查",
                },
                {
                    "id": "power_deviation_high",
                    "name": "功率偏差過大",
                    "enabled": True,
                    "severity": "critical",
                    "silence_minutes": 120,
                    "auto_create_work_order": True,
                    "notify_channels": ["email", "line", "webhook"],
                    "conditions": [
                        {"metric": "power_deviation_pct", "operator": ">", "threshold": 15.0},
                        {"metric": "wind_speed", "operator": ">", "threshold": 5.0},
                    ],
                    "description_template": "功率偏差 {power_deviation_pct:.1f}%（風速 {wind_speed:.1f} m/s），超過 15% 門檻",
                },
                {
                    "id": "anomaly_count_high",
                    "name": "異常數量過多",
                    "enabled": True,
                    "severity": "warning",
                    "silence_minutes": 240,
                    "auto_create_work_order": False,
                    "notify_channels": ["webhook"],
                    "conditions": [
                        {"metric": "temperature_anomaly_count", "operator": ">", "threshold": 10.0}
                    ],
                    "description_template": "偵測到 {temperature_anomaly_count:.0f} 個溫度異常點，超過 10 個門檻",
                },
                {
                    "id": "efficiency_loss_critical",
                    "name": "效率損失嚴重",
                    "enabled": True,
                    "severity": "critical",
                    "silence_minutes": 180,
                    "auto_create_work_order": True,
                    "notify_channels": ["email", "line"],
                    "conditions": [
                        {"metric": "efficiency_loss_pct", "operator": ">", "threshold": 20.0}
                    ],
                    "description_template": "效率損失 {efficiency_loss_pct:.1f}%，超過 20% 門檻，可能存在嚴重故障",
                },
            ]
        }
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(defaults, f, allow_unicode=True, sort_keys=False)
            logger.info(f"已生成預設 rules.yaml 於 {file_path}")
        except Exception as e:
            logger.error(f"生成預設 rules.yaml 失敗：{e}")

    @property
    def rules(self) -> list[AlertRule]:
        """取得所有規則的副本。"""
        return list(self._rules)

    def get_rule(self, rule_id: str) -> AlertRule | None:
        """依 ID 取得規則。"""
        for r in self._rules:
            if r.id == rule_id:
                return r
        return None

    def add_rule(self, rule: AlertRule) -> None:
        """新增或替換規則。"""
        self._rules = [r for r in self._rules if r.id != rule.id]
        self._rules.append(rule)
        logger.info(f"告警規則已新增/更新：{rule.id} — {rule.name}")

    def remove_rule(self, rule_id: str) -> bool:
        """移除規則，回傳是否成功。"""
        before = len(self._rules)
        self._rules = [r for r in self._rules if r.id != rule_id]
        return len(self._rules) < before

    def set_rule_enabled(self, rule_id: str, enabled: bool) -> bool:
        """啟用或停用規則，回傳是否成功。"""
        for r in self._rules:
            if r.id == rule_id:
                r.enabled = enabled
                logger.info(f"規則 {rule_id} 已{'啟用' if enabled else '停用'}")
                return True
        return False

    def _load_default_rules(self) -> None:
        """載入預設告警規則。"""
        defaults = [
            AlertRule(
                id="health_score_critical",
                name="健康分數嚴重過低",
                conditions=[RuleCondition("health_score", "<", 0.5)],
                severity="critical",
                silence_minutes=120,
                auto_create_work_order=True,
                description_template=(
                    "風機健康分數 {health_score:.2f}，低於臨界值 0.5，需立即檢修"
                ),
            ),
            AlertRule(
                id="health_score_warning",
                name="健康分數過低",
                conditions=[RuleCondition("health_score", "<", 0.7)],
                severity="warning",
                silence_minutes=360,
                auto_create_work_order=False,
                description_template=(
                    "風機健康分數 {health_score:.2f}，低於警戒值 0.7，建議排程檢查"
                ),
            ),
            AlertRule(
                id="power_deviation_high",
                name="功率偏差過大",
                conditions=[
                    RuleCondition("power_deviation_pct", ">", 15),
                    RuleCondition("wind_speed", ">", 5),
                ],
                severity="critical",
                silence_minutes=120,
                auto_create_work_order=True,
                description_template=(
                    "功率偏差 {power_deviation_pct:.1f}%（風速 {wind_speed:.1f} m/s），"
                    "超過 15% 門檻"
                ),
            ),
            AlertRule(
                id="anomaly_count_high",
                name="異常數量過多",
                conditions=[RuleCondition("temperature_anomaly_count", ">", 10)],
                severity="warning",
                silence_minutes=240,
                auto_create_work_order=False,
                description_template=(
                    "偵測到 {temperature_anomaly_count:.0f} 個溫度異常點，超過 10 個門檻"
                ),
            ),
            AlertRule(
                id="efficiency_loss_critical",
                name="效率損失嚴重",
                conditions=[RuleCondition("efficiency_loss_pct", ">", 20)],
                severity="critical",
                silence_minutes=180,
                auto_create_work_order=True,
                description_template=(
                    "效率損失 {efficiency_loss_pct:.1f}%，超過 20% 門檻，可能存在嚴重故障"
                ),
            ),
        ]
        self._rules.extend(defaults)

    def evaluate(
        self,
        analysis_results: dict[str, Any] | list[dict[str, Any]],
        turbine_id: str | None = None,
        task_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """評估所有啟用的規則，回傳觸發的告警清單。"""
        triggered: list[dict[str, Any]] = []

        for rule in self._rules:
            if not rule.enabled:
                continue

            metric_values: dict[str, float] = {}
            all_met = True

            for cond in rule.conditions:
                value = self._extract_metric(analysis_results, cond.metric)
                if value is None:
                    all_met = False
                    break
                metric_values[cond.metric] = value
                op_fn = OPERATORS.get(cond.operator)
                if op_fn is None or not op_fn(value, cond.threshold):
                    all_met = False
                    break

            if not all_met:
                continue

            silence_key = f"{rule.id}:{turbine_id or 'unknown'}"
            if self._is_silenced(silence_key, rule.silence_minutes):
                logger.debug(f"規則 {rule.id} 靜默中（{turbine_id}），跳過")
                continue

            self._silence_tracker[silence_key] = datetime.now()

            description = rule.description_template
            with contextlib.suppress(KeyError, ValueError):
                description = description.format(**metric_values)

            triggered.append(
                {
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "severity": rule.severity,
                    "turbine_id": turbine_id,
                    "task_id": task_id,
                    "metric_values": metric_values,
                    "description": description,
                    "auto_create_work_order": rule.auto_create_work_order,
                    "notify_channels": rule.notify_channels,
                }
            )
            logger.info(f"規則觸發：{rule.name}（{turbine_id}）— {description}")

        return triggered

    def _is_silenced(self, key: str, silence_minutes: int) -> bool:
        """檢查規則是否在靜默期內。"""
        last_triggered = self._silence_tracker.get(key)
        if last_triggered is None:
            return False
        return datetime.now() - last_triggered < timedelta(minutes=silence_minutes)

    def _extract_metric(self, data: Any, metric: str) -> float | None:
        """在巢狀結構中深度搜索指標值。"""
        if isinstance(data, dict):
            if metric in data:
                val = data[metric]
                if isinstance(val, int | float):
                    return float(val)
            for v in data.values():
                found = self._extract_metric(v, metric)
                if found is not None:
                    return found
        elif isinstance(data, list):
            for item in data:
                found = self._extract_metric(item, metric)
                if found is not None:
                    return found
        return None

    async def process_and_alert(
        self,
        analysis_results: dict[str, Any] | list[dict[str, Any]],
        turbine_id: str | None = None,
        task_id: str | None = None,
    ) -> list[str]:
        """評估規則並建立告警，回傳產生的 alert_id 清單。"""
        triggered = self.evaluate(analysis_results, turbine_id, task_id)
        if not triggered:
            return []

        from src.core.database import get_database

        db = get_database()
        alert_ids: list[str] = []

        for t in triggered:
            alert_id = db.create_alert(
                source="alert_rule_engine",
                severity=t["severity"],
                title=t["rule_name"],
                description=t["description"],
                turbine_id=t["turbine_id"],
                task_id=t["task_id"],
                agent_id="wLab:alert-engine",
                source_system="alert_rule_engine",
                source_alert_id=(
                    f"{t['rule_id']}:{t['turbine_id'] or 'unknown'}"
                    f":{datetime.now().strftime('%Y%m%d%H')}"
                ),
                tags=[t["rule_id"]],
                metrics=t["metric_values"],
            )
            alert_ids.append(alert_id)

            try:
                from src.api.websocket_manager import manager as ws_manager

                alert_data = db.get_alert(alert_id)
                if alert_data:
                    await ws_manager.broadcast_alert(alert_data, is_new=True)
            except Exception as exc:
                logger.warning(f"告警廣播失敗：{exc}")

            wo_id = None
            if t["auto_create_work_order"]:
                wo_id = await self._auto_create_work_order(db, t, alert_id)

            # ── 派發通知 ──
            notify_channels = t.get("notify_channels")
            if notify_channels:
                try:
                    from src.services.notification_manager import get_notification_manager
                    from src.services.notifiers.base import NotificationPayload

                    metric_values = t.get("metric_values", {})
                    metric_name = next(iter(metric_values.keys())) if metric_values else "unknown"
                    metric_val = next(iter(metric_values.values())) if metric_values else 0.0

                    threshold_val = 0.0
                    rule = self.get_rule(t["rule_id"])
                    if rule:
                        for cond in rule.conditions:
                            if cond.metric == metric_name:
                                threshold_val = cond.threshold
                                break

                    payload = NotificationPayload(
                        alert_id=alert_id,
                        turbine_id=t["turbine_id"] or "unknown",
                        rule_id=t["rule_id"],
                        rule_name=t["rule_name"],
                        severity=t["severity"],
                        metric=metric_name,
                        metric_value=metric_val,
                        threshold=threshold_val,
                        triggered_at=datetime.now(),
                        recommended_action=t["description"],
                        work_order_id=wo_id,
                    )

                    manager = get_notification_manager()
                    asyncio.create_task(manager.dispatch(payload, notify_channels))
                except Exception as n_exc:
                    logger.warning(f"通知分派背景任務建立失敗：{n_exc}")

        if alert_ids:
            logger.info(f"規則引擎產生 {len(alert_ids)} 個告警：{alert_ids}")

        return alert_ids

    async def _auto_create_work_order(
        self,
        db: Any,
        trigger: dict[str, Any],
        alert_id: str,
    ) -> str | None:
        """從觸發的規則自動建立工單。"""
        severity_to_priority = {
            "critical": "critical",
            "warning": "high",
            "info": "medium",
        }
        try:
            wo_id = db.create_work_order(
                title=f"[自動] {trigger['rule_name']}",
                description=trigger["description"],
                priority=severity_to_priority.get(trigger["severity"], "medium"),
                turbine_id=trigger["turbine_id"],
                alert_id=alert_id,
                assigned_agents=["wEng:backend-dev"],
            )
            try:
                from src.api.websocket_manager import manager as ws_manager

                wo_data = db.get_work_order(wo_id)
                if wo_data:
                    await ws_manager.broadcast_work_order_update(wo_data)
            except Exception:
                pass
            logger.info(f"自動建立工單：{wo_id}（告警 {alert_id}）")
            return wo_id
        except Exception as exc:
            logger.warning(f"自動建立工單失敗：{exc}")
            return None


_engine: AlertRuleEngine | None = None


def get_alert_rule_engine() -> AlertRuleEngine:
    """取得全域告警規則引擎單例。"""
    global _engine
    if _engine is None:
        _engine = AlertRuleEngine()
    return _engine
