"""統計異常偵測技能與報告生成技能測試。"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.skills.base import SkillInput, SkillStatus


# ════════════════════════════════════════════════════════════════
# AnomalyDetectionSkill
# ════════════════════════════════════════════════════════════════


class TestAnomalyDetectionSkill:
    def test_import(self) -> None:
        from src.skills.ml.anomaly_detection import AnomalyDetectionSkill

        skill = AnomalyDetectionSkill()
        assert skill.skill_id == "anomaly_detection"
        assert skill.display_name == "統計異常偵測"
        assert skill.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_no_input_returns_error(self) -> None:
        from src.skills.ml.anomaly_detection import AnomalyDetectionSkill

        skill = AnomalyDetectionSkill()
        inp = SkillInput(parameters={})
        result = await skill.execute(inp)
        assert result.status == SkillStatus.ERROR
        assert any("未收到" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_empty_dataframe_returns_error(self) -> None:
        import pandas as pd

        from src.skills.ml.anomaly_detection import AnomalyDetectionSkill

        skill = AnomalyDetectionSkill()
        inp = SkillInput(parameters={}, dataframe=pd.DataFrame())
        result = await skill.execute(inp)
        assert result.status == SkillStatus.ERROR

    @pytest.mark.asyncio
    async def test_with_valid_data(self) -> None:
        """以簡單的模擬 SCADA 資料測試完整流程。"""
        import numpy as np
        import pandas as pd

        from src.skills.ml.anomaly_detection import AnomalyDetectionSkill

        np.random.seed(42)
        n = 500
        wind_speed = np.random.uniform(3, 25, n)
        power = np.where(
            wind_speed < 3, 0,
            np.where(wind_speed > 25, 0, wind_speed ** 3 * 0.13 + np.random.normal(0, 10, n))
        )
        gear_temp = 40 + power / 100 + np.random.normal(0, 2, n)

        df = pd.DataFrame({
            "Wind speed (m/s)_Mean": wind_speed,
            "Active power (kW)_Mean": power,
            "Gear oil temp (°C)_Mean": gear_temp,
        })
        df.index = pd.date_range("2024-01-01", periods=n, freq="10min")

        skill = AnomalyDetectionSkill()
        inp = SkillInput(
            parameters={"turbine_id": "TEST-01", "threshold_std": 3.0},
            dataframe=df,
        )

        progress_calls: list[tuple[float, str]] = []

        async def track_progress(p: float, msg: str) -> None:
            progress_calls.append((p, msg))

        result = await skill.execute(inp, progress_cb=track_progress)

        assert result.status == SkillStatus.SUCCESS
        assert "health_score" in result.data
        assert isinstance(result.data["health_score"], float)
        assert 0 <= result.data["health_score"] <= 100
        assert "temperature_anomaly_count" in result.data
        assert "power_curve_deviation_pct" in result.data
        assert "efficiency_loss_pct" in result.data
        assert result.summary  # 非空摘要
        assert result.dataframe is not None
        assert len(progress_calls) >= 3  # 至少 3 次進度回報


# ════════════════════════════════════════════════════════════════
# ReportGeneratorSkill
# ════════════════════════════════════════════════════════════════


class TestReportGeneratorSkill:
    def test_import(self) -> None:
        from src.skills.reporting.report_generator import ReportGeneratorSkill

        skill = ReportGeneratorSkill()
        assert skill.skill_id == "report_generator"
        assert skill.display_name == "報告生成"

    @pytest.mark.asyncio
    async def test_diagnosis_report_empty_context(self) -> None:
        from src.skills.reporting.report_generator import ReportGeneratorSkill

        skill = ReportGeneratorSkill()
        inp = SkillInput(
            parameters={"turbine_id": "WT-01", "report_type": "diagnosis"},
            context={},
        )
        result = await skill.execute(inp)
        assert result.status == SkillStatus.SUCCESS
        assert "report_markdown" in result.data
        md = result.data["report_markdown"]
        assert "# 風機故障診斷報告" in md
        assert "WT-01" in md

    @pytest.mark.asyncio
    async def test_diagnosis_report_with_context(self) -> None:
        from src.skills.reporting.report_generator import ReportGeneratorSkill

        skill = ReportGeneratorSkill()
        inp = SkillInput(
            parameters={"turbine_id": "WT-02", "report_type": "diagnosis"},
            context={
                "anomaly_detection": {
                    "status": "success",
                    "data": {
                        "health_score": 72.5,
                        "health_details": {
                            "data_completeness_score": 95.0,
                            "power_curve_score": 68.0,
                            "temperature_score": 65.0,
                            "availability_score": 88.0,
                        },
                        "temperature_anomaly_count": 5,
                        "temperature_anomalies": [
                            {
                                "component": "齒輪箱油溫",
                                "actual_temp": 85.2,
                                "expected_temp": 72.1,
                                "deviation": 3.5,
                            }
                        ],
                        "components_checked": ["齒輪箱油溫", "發電機前軸承"],
                        "power_curve_deviation_pct": -8.3,
                        "worst_wind_speed_bin": "10.0-10.5 m/s",
                        "efficiency_loss_pct": 6.2,
                    },
                },
                "fault_classification": {
                    "status": "success",
                    "data": {
                        "f1_macro": 0.78,
                        "f1_per_class": {"normal": 0.95, "gearbox": 0.65, "generator": 0.72},
                    },
                },
            },
        )
        result = await skill.execute(inp)
        assert result.status == SkillStatus.SUCCESS
        md = result.data["report_markdown"]
        assert "72.5/100" in md
        assert "齒輪箱油溫" in md
        assert "0.78" in md  # f1_macro
        assert result.data["section_count"] >= 3

    @pytest.mark.asyncio
    async def test_monthly_report(self) -> None:
        from src.skills.reporting.report_generator import ReportGeneratorSkill

        skill = ReportGeneratorSkill()
        inp = SkillInput(
            parameters={"turbine_id": "WT-03", "report_type": "monthly"},
            context={
                "anomaly_detection": {
                    "data": {
                        "health_score": 85.0,
                        "temperature_anomaly_count": 2,
                        "power_curve_deviation_pct": -3.0,
                        "efficiency_loss_pct": 1.5,
                    },
                },
            },
        )
        result = await skill.execute(inp)
        assert result.status == SkillStatus.SUCCESS
        md = result.data["report_markdown"]
        assert "月度健康評估報告" in md
        assert "WT-03" in md

    @pytest.mark.asyncio
    async def test_model_eval_report(self) -> None:
        from src.skills.reporting.report_generator import ReportGeneratorSkill

        skill = ReportGeneratorSkill()
        inp = SkillInput(
            parameters={"turbine_id": "WT-04", "report_type": "model_eval"},
            context={
                "nbm_training": {
                    "data": {
                        "r2_score": 0.92,
                        "mae": 45.3,
                        "rmse": 62.1,
                        "train_samples": 8000,
                        "test_samples": 2000,
                    },
                },
            },
        )
        result = await skill.execute(inp)
        assert result.status == SkillStatus.SUCCESS
        md = result.data["report_markdown"]
        assert "模型效能評估報告" in md
        assert "0.92" in md

    @pytest.mark.asyncio
    async def test_progress_callback(self) -> None:
        from src.skills.reporting.report_generator import ReportGeneratorSkill

        skill = ReportGeneratorSkill()
        inp = SkillInput(
            parameters={"turbine_id": "WT-05"},
            context={},
        )
        progress_calls: list[tuple[float, str]] = []

        async def track(p: float, msg: str) -> None:
            progress_calls.append((p, msg))

        await skill.execute(inp, progress_cb=track)
        assert len(progress_calls) >= 2
        assert progress_calls[-1][0] == 1.0  # 最後必為 100%

    @pytest.mark.asyncio
    async def test_recommendations_generation(self) -> None:
        from src.skills.reporting.report_generator import _generate_recommendations

        # 低健康分數
        recs = _generate_recommendations(
            {"health_score": 50, "temperature_anomaly_count": 15, "efficiency_loss_pct": 12},
            None, None, None,
        )
        assert any("立即" in r for r in recs)
        assert any("軸承" in r or "溫度" in r for r in recs)

        # 正常狀況
        recs = _generate_recommendations(
            {"health_score": 90, "temperature_anomaly_count": 0, "efficiency_loss_pct": 1},
            None, None, None,
        )
        assert any("正常" in r for r in recs)


# ════════════════════════════════════════════════════════════════
# Workflow 整合
# ════════════════════════════════════════════════════════════════


class TestHealthCheckWorkflow:
    def test_workflow_creation(self) -> None:
        from src.agents.orchestrator.workflows import create_health_check_workflow

        wf = create_health_check_workflow("WT-01")
        assert wf.id == "health-check"
        assert "WT-01" in wf.name
        assert len(wf.steps) == 5  # dispatch + load + anomaly + report + review

    def test_anomaly_step_has_retry(self) -> None:
        from src.agents.orchestrator.workflows import create_health_check_workflow

        wf = create_health_check_workflow("WT-01")
        anomaly_step = wf.steps[2]  # 異常偵測分析
        assert anomaly_step.retry.max_retries == 1

    def test_registered_in_available_workflows(self) -> None:
        from src.agents.orchestrator.workflows import AVAILABLE_WORKFLOWS

        assert "health-check" in AVAILABLE_WORKFLOWS


# ════════════════════════════════════════════════════════════════
# Skill Registry 自動發現
# ════════════════════════════════════════════════════════════════


class TestSkillAutoDiscovery:
    def test_new_skills_discoverable(self) -> None:
        from src.skills.registry import SkillRegistry

        registry = SkillRegistry()
        count = registry.auto_discover()
        assert count > 0
        assert registry.has("anomaly_detection")
        assert registry.has("report_generator")

    def test_skill_metadata(self) -> None:
        from src.skills.registry import SkillRegistry

        registry = SkillRegistry()
        registry.auto_discover()

        anomaly = registry.get("anomaly_detection")
        assert anomaly is not None
        assert anomaly.display_name == "統計異常偵測"

        report = registry.get("report_generator")
        assert report is not None
        assert report.display_name == "報告生成"
