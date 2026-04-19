"""告警規則引擎單元測試。"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.alert_engine import (
    AlertRule,
    AlertRuleEngine,
    RuleCondition,
    get_alert_rule_engine,
)


class TestRuleCondition:
    """RuleCondition 資料類別測試。"""

    def test_create_condition(self) -> None:
        cond = RuleCondition(metric="health_score", operator="<", threshold=0.7)
        assert cond.metric == "health_score"
        assert cond.operator == "<"
        assert cond.threshold == 0.7


class TestAlertRule:
    """AlertRule 資料類別測試。"""

    def test_create_rule(self) -> None:
        rule = AlertRule(
            id="test_rule",
            name="測試規則",
            conditions=[RuleCondition("health_score", "<", 0.7)],
            severity="warning",
        )
        assert rule.id == "test_rule"
        assert rule.enabled is True
        assert rule.silence_minutes == 360

    def test_to_dict(self) -> None:
        rule = AlertRule(
            id="test_rule",
            name="測試規則",
            conditions=[
                RuleCondition("health_score", "<", 0.7),
                RuleCondition("wind_speed", ">", 3),
            ],
            severity="critical",
            auto_create_work_order=True,
        )
        d = rule.to_dict()
        assert d["id"] == "test_rule"
        assert len(d["conditions"]) == 2
        assert d["conditions"][0]["metric"] == "health_score"
        assert d["auto_create_work_order"] is True


class TestAlertRuleEngine:
    """AlertRuleEngine 核心邏輯測試。"""

    def setup_method(self) -> None:
        self.engine = AlertRuleEngine()

    def test_default_rules_loaded(self) -> None:
        assert len(self.engine.rules) == 5
        rule_ids = {r.id for r in self.engine.rules}
        assert "health_score_critical" in rule_ids
        assert "health_score_warning" in rule_ids
        assert "power_deviation_high" in rule_ids
        assert "anomaly_count_high" in rule_ids
        assert "efficiency_loss_critical" in rule_ids

    def test_add_rule(self) -> None:
        custom = AlertRule(id="custom_1", name="自訂規則")
        self.engine.add_rule(custom)
        assert len(self.engine.rules) == 6
        assert self.engine.get_rule("custom_1") is not None

    def test_add_rule_replaces_existing(self) -> None:
        custom = AlertRule(id="health_score_warning", name="替換的規則")
        self.engine.add_rule(custom)
        assert len(self.engine.rules) == 5
        assert self.engine.get_rule("health_score_warning").name == "替換的規則"

    def test_remove_rule(self) -> None:
        assert self.engine.remove_rule("health_score_critical") is True
        assert len(self.engine.rules) == 4
        assert self.engine.get_rule("health_score_critical") is None

    def test_remove_nonexistent_rule(self) -> None:
        assert self.engine.remove_rule("nonexistent") is False

    def test_enable_disable_rule(self) -> None:
        assert self.engine.set_rule_enabled("health_score_critical", False) is True
        rule = self.engine.get_rule("health_score_critical")
        assert rule.enabled is False

        assert self.engine.set_rule_enabled("health_score_critical", True) is True
        rule = self.engine.get_rule("health_score_critical")
        assert rule.enabled is True

    def test_enable_nonexistent_rule(self) -> None:
        assert self.engine.set_rule_enabled("nonexistent", True) is False

    # ── evaluate 測試 ──

    def test_evaluate_no_trigger(self) -> None:
        results = {"health_score": 0.95, "efficiency_loss_pct": 5}
        triggered = self.engine.evaluate(results, turbine_id="WT-01")
        assert len(triggered) == 0

    def test_evaluate_health_score_warning(self) -> None:
        results = {"health_score": 0.65}
        triggered = self.engine.evaluate(results, turbine_id="WT-01")
        rule_ids = {t["rule_id"] for t in triggered}
        assert "health_score_warning" in rule_ids

    def test_evaluate_health_score_critical(self) -> None:
        results = {"health_score": 0.4}
        triggered = self.engine.evaluate(results, turbine_id="WT-01")
        rule_ids = {t["rule_id"] for t in triggered}
        assert "health_score_critical" in rule_ids
        assert "health_score_warning" in rule_ids

    def test_evaluate_compound_condition(self) -> None:
        results = {"power_deviation_pct": 20, "wind_speed": 8}
        triggered = self.engine.evaluate(results, turbine_id="WT-01")
        rule_ids = {t["rule_id"] for t in triggered}
        assert "power_deviation_high" in rule_ids

    def test_evaluate_compound_condition_partial_fail(self) -> None:
        results = {"power_deviation_pct": 20, "wind_speed": 3}
        triggered = self.engine.evaluate(results, turbine_id="WT-01")
        rule_ids = {t["rule_id"] for t in triggered}
        assert "power_deviation_high" not in rule_ids

    def test_evaluate_nested_results(self) -> None:
        results = {
            "anomaly_detection": {
                "status": "success",
                "data": {"health_score": 0.3, "temperature_anomaly_count": 15},
            }
        }
        triggered = self.engine.evaluate(results, turbine_id="WT-01")
        rule_ids = {t["rule_id"] for t in triggered}
        assert "health_score_critical" in rule_ids
        assert "anomaly_count_high" in rule_ids

    def test_evaluate_list_results(self) -> None:
        results = [
            {"chart_type": "scatter", "data": {"health_score": 0.4}},
            {"chart_type": "bar", "data": {"efficiency_loss_pct": 25}},
        ]
        triggered = self.engine.evaluate(results, turbine_id="WT-01")
        rule_ids = {t["rule_id"] for t in triggered}
        assert "health_score_critical" in rule_ids
        assert "efficiency_loss_critical" in rule_ids

    def test_evaluate_disabled_rule_skipped(self) -> None:
        self.engine.set_rule_enabled("health_score_warning", False)
        results = {"health_score": 0.65}
        triggered = self.engine.evaluate(results, turbine_id="WT-01")
        rule_ids = {t["rule_id"] for t in triggered}
        assert "health_score_warning" not in rule_ids

    def test_evaluate_description_template(self) -> None:
        results = {"health_score": 0.45}
        triggered = self.engine.evaluate(results, turbine_id="WT-01")
        critical = [t for t in triggered if t["rule_id"] == "health_score_critical"][0]
        assert "0.45" in critical["description"]

    def test_evaluate_includes_metric_values(self) -> None:
        results = {"health_score": 0.45}
        triggered = self.engine.evaluate(results, turbine_id="WT-01")
        critical = [t for t in triggered if t["rule_id"] == "health_score_critical"][0]
        assert critical["metric_values"]["health_score"] == 0.45
        assert critical["turbine_id"] == "WT-01"
        assert critical["auto_create_work_order"] is True

    # ── 靜默期測試 ──

    def test_silence_period(self) -> None:
        results = {"health_score": 0.65}
        t1 = self.engine.evaluate(results, turbine_id="WT-01")
        assert len([t for t in t1 if t["rule_id"] == "health_score_warning"]) == 1

        t2 = self.engine.evaluate(results, turbine_id="WT-01")
        assert len([t for t in t2 if t["rule_id"] == "health_score_warning"]) == 0

    def test_silence_different_turbines(self) -> None:
        results = {"health_score": 0.65}
        t1 = self.engine.evaluate(results, turbine_id="WT-01")
        t2 = self.engine.evaluate(results, turbine_id="WT-02")
        assert len([t for t in t1 if t["rule_id"] == "health_score_warning"]) == 1
        assert len([t for t in t2 if t["rule_id"] == "health_score_warning"]) == 1

    def test_silence_period_expires(self) -> None:
        results = {"health_score": 0.65}
        self.engine.evaluate(results, turbine_id="WT-01")

        key = "health_score_warning:WT-01"
        self.engine._silence_tracker[key] = datetime.now() - timedelta(minutes=400)

        t2 = self.engine.evaluate(results, turbine_id="WT-01")
        assert len([t for t in t2 if t["rule_id"] == "health_score_warning"]) == 1

    # ── _extract_metric 測試 ──

    def test_extract_metric_flat(self) -> None:
        assert self.engine._extract_metric({"health_score": 0.8}, "health_score") == 0.8

    def test_extract_metric_nested(self) -> None:
        data = {"a": {"b": {"health_score": 0.5}}}
        assert self.engine._extract_metric(data, "health_score") == 0.5

    def test_extract_metric_in_list(self) -> None:
        data = [{"x": 1}, {"health_score": 0.3}]
        assert self.engine._extract_metric(data, "health_score") == 0.3

    def test_extract_metric_missing(self) -> None:
        assert self.engine._extract_metric({"other": 1}, "health_score") is None

    def test_extract_metric_non_numeric(self) -> None:
        assert self.engine._extract_metric({"health_score": "good"}, "health_score") is None

    # ── process_and_alert 整合測試 ──

    @pytest.mark.asyncio
    async def test_process_and_alert_no_triggers(self) -> None:
        results = {"health_score": 0.95}
        alert_ids = await self.engine.process_and_alert(results, turbine_id="WT-01")
        assert alert_ids == []

    @pytest.mark.asyncio
    async def test_process_and_alert_creates_alerts(self) -> None:
        mock_db = MagicMock()
        mock_db.create_alert.return_value = "ALT-20260418-test1234"
        mock_db.get_alert.return_value = {"id": "ALT-20260418-test1234", "severity": "warning"}

        mock_ws = AsyncMock()

        with (
            patch("src.services.alert_engine.get_database", return_value=mock_db),
            patch("src.services.alert_engine.ws_manager", mock_ws, create=True),
            patch.dict(
                "sys.modules",
                {"src.api.websocket_manager": MagicMock(manager=mock_ws)},
            ),
        ):
            results = {"health_score": 0.65}
            engine = AlertRuleEngine()
            alert_ids = await engine.process_and_alert(results, turbine_id="WT-01")

        assert len(alert_ids) >= 1
        mock_db.create_alert.assert_called()

    @pytest.mark.asyncio
    async def test_process_and_alert_auto_work_order(self) -> None:
        mock_db = MagicMock()
        mock_db.create_alert.return_value = "ALT-20260418-test5678"
        mock_db.get_alert.return_value = {"id": "ALT-20260418-test5678", "severity": "critical"}
        mock_db.create_work_order.return_value = "WO-20260418-test9999"
        mock_db.get_work_order.return_value = {"id": "WO-20260418-test9999"}

        mock_ws = AsyncMock()

        with (
            patch("src.services.alert_engine.get_database", return_value=mock_db),
            patch.dict(
                "sys.modules",
                {"src.api.websocket_manager": MagicMock(manager=mock_ws)},
            ),
        ):
            results = {"health_score": 0.4}
            engine = AlertRuleEngine()
            alert_ids = await engine.process_and_alert(results, turbine_id="WT-01")

        assert len(alert_ids) >= 1
        mock_db.create_work_order.assert_called()


class TestAlertRuleOperators:
    """運算子測試。"""

    def setup_method(self) -> None:
        self.engine = AlertRuleEngine()
        for r in list(self.engine.rules):
            self.engine.remove_rule(r.id)

    def _add_and_test(self, operator: str, threshold: float, value: float) -> bool:
        self.engine._silence_tracker.clear()
        rule = AlertRule(
            id="op_test",
            name="運算子測試",
            conditions=[RuleCondition("val", operator, threshold)],
        )
        self.engine.add_rule(rule)
        return len(self.engine.evaluate({"val": value})) > 0

    def test_less_than(self) -> None:
        assert self._add_and_test("<", 10, 5) is True
        assert self._add_and_test("<", 10, 15) is False

    def test_greater_than(self) -> None:
        assert self._add_and_test(">", 10, 15) is True
        assert self._add_and_test(">", 10, 5) is False

    def test_less_equal(self) -> None:
        assert self._add_and_test("<=", 10, 10) is True
        assert self._add_and_test("<=", 10, 11) is False

    def test_greater_equal(self) -> None:
        assert self._add_and_test(">=", 10, 10) is True
        assert self._add_and_test(">=", 10, 9) is False

    def test_equal(self) -> None:
        assert self._add_and_test("==", 10, 10) is True
        assert self._add_and_test("==", 10, 11) is False

    def test_not_equal(self) -> None:
        assert self._add_and_test("!=", 10, 11) is True
        assert self._add_and_test("!=", 10, 10) is False

    def test_invalid_operator(self) -> None:
        assert self._add_and_test("~", 10, 5) is False


class TestGetAlertRuleEngine:
    """全域單例測試。"""

    def test_singleton(self) -> None:
        import src.services.alert_engine as mod

        mod._engine = None
        e1 = get_alert_rule_engine()
        e2 = get_alert_rule_engine()
        assert e1 is e2
        mod._engine = None
