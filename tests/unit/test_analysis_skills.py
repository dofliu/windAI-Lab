"""新增分析技能測試 — yaw_misalignment、curtailment_detection、alarm_correlation、power_curve_binning。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from tests.unit._ws_mock import mock_ws_manager  # noqa: F401

from src.skills.base import SkillInput, SkillStatus


# ── 共用測試資料 ──


def _make_scada_df(n: int = 200) -> pd.DataFrame:
    """建立模擬 SCADA 資料。"""
    rng = np.random.default_rng(42)
    index = pd.date_range("2024-01-01", periods=n, freq="10min")

    wind_speed = rng.uniform(2, 25, n)
    nacelle_dir = rng.uniform(0, 360, n)
    # wind_direction = nacelle_dir + 偏差（模擬偏航偏移）
    wind_dir = (nacelle_dir + rng.normal(5, 3, n)) % 360

    # 功率：三次方模型 + 截斷
    rated = 2050.0
    cut_in = 3.0
    rated_ws = 12.0
    ratio = np.clip((wind_speed - cut_in) / (rated_ws - cut_in), 0, None)
    power = np.clip(rated * ratio**3, 0, rated)
    # 加入噪音
    power += rng.normal(0, 20, n)
    power = np.clip(power, 0, rated)

    return pd.DataFrame(
        {
            "Wind Speed_Mean": wind_speed,
            "Active Power_Mean": power,
            "Nacelle Position_Mean": nacelle_dir,
            "Wind Direction_Mean": wind_dir,
        },
        index=index,
    )


def _make_alarm_df(n: int = 100) -> pd.DataFrame:
    """建立模擬警報資料。"""
    rng = np.random.default_rng(42)
    index = pd.date_range("2024-01-01", periods=n, freq="30min")
    codes = rng.choice(["A001", "A002", "A003", "B001", "B002"], n, p=[0.3, 0.25, 0.2, 0.15, 0.1])
    return pd.DataFrame({"alarm_code": codes}, index=index)


# ═══════════════════════════════════════════════════════════════
# YawMisalignmentSkill
# ═══════════════════════════════════════════════════════════════


class TestYawMisalignment:
    @pytest.fixture()
    def skill(self):
        from src.skills.features.yaw_misalignment import YawMisalignmentSkill

        return YawMisalignmentSkill()

    def test_skill_id(self, skill) -> None:
        assert skill.skill_id == "yaw_misalignment"

    @pytest.mark.asyncio
    async def test_basic_analysis(self, skill) -> None:
        df = _make_scada_df()
        inp = SkillInput(parameters={}, dataframe=df)
        output = await skill.execute(inp)

        assert output.status == SkillStatus.SUCCESS
        data = output.data
        assert "mean_offset" in data
        assert "std_offset" in data
        assert "estimated_power_loss_pct" in data
        assert "severity" in data
        # 我們模擬了 ~5° 的偏差（方向可能為正或負，取決於 circular diff）
        assert abs(abs(data["mean_offset"]) - 5) < 3

    @pytest.mark.asyncio
    async def test_wind_speed_bins(self, skill) -> None:
        df = _make_scada_df()
        inp = SkillInput(parameters={}, dataframe=df)
        output = await skill.execute(inp)

        assert "wind_speed_bins" in output.data
        bins = output.data["wind_speed_bins"]
        assert len(bins) > 0

    @pytest.mark.asyncio
    async def test_no_dataframe_error(self, skill) -> None:
        inp = SkillInput(parameters={})
        output = await skill.execute(inp)
        assert output.status == SkillStatus.ERROR

    @pytest.mark.asyncio
    async def test_missing_cols_error(self, skill) -> None:
        df = pd.DataFrame({"col_a": [1, 2, 3]})
        inp = SkillInput(parameters={}, dataframe=df)
        output = await skill.execute(inp)
        assert output.status == SkillStatus.ERROR

    @pytest.mark.asyncio
    async def test_severity_levels(self, skill) -> None:
        """不同偏差程度對應不同嚴重度。"""
        # 大偏差
        rng = np.random.default_rng(0)
        n = 100
        index = pd.date_range("2024-01-01", periods=n, freq="10min")
        nacelle = rng.uniform(0, 360, n)
        wind = (nacelle + 20) % 360  # 20° 偏差 → Critical

        df = pd.DataFrame(
            {
                "Nacelle Position_Mean": nacelle,
                "Wind Direction_Mean": wind,
                "Wind Speed_Mean": rng.uniform(5, 15, n),
            },
            index=index,
        )
        inp = SkillInput(parameters={}, dataframe=df)
        output = await skill.execute(inp)
        assert output.data["severity"] == "Critical"

    @pytest.mark.asyncio
    async def test_preserves_dataframe(self, skill) -> None:
        """輸出應保留原始 DataFrame。"""
        df = _make_scada_df(50)
        inp = SkillInput(parameters={}, dataframe=df)
        output = await skill.execute(inp)
        assert output.dataframe is df


# ═══════════════════════════════════════════════════════════════
# CurtailmentDetectionSkill
# ═══════════════════════════════════════════════════════════════


class TestCurtailmentDetection:
    @pytest.fixture()
    def skill(self):
        from src.skills.features.curtailment_detection import CurtailmentDetectionSkill

        return CurtailmentDetectionSkill()

    def test_skill_id(self, skill) -> None:
        assert skill.skill_id == "curtailment_detection"

    @pytest.mark.asyncio
    async def test_basic_detection(self, skill) -> None:
        df = _make_scada_df(300)
        inp = SkillInput(parameters={"rated_power_kw": 2050}, dataframe=df)
        output = await skill.execute(inp)

        assert output.status == SkillStatus.SUCCESS
        data = output.data
        assert "curtailment_events" in data
        assert "curtailment_ratio_pct" in data
        assert "estimated_energy_loss_kwh" in data
        assert data["rated_power_kw"] == 2050

    @pytest.mark.asyncio
    async def test_curtailment_with_cap(self, skill) -> None:
        """模擬明確的功率截斷（降載至 1500 kW）。"""
        n = 200
        rng = np.random.default_rng(42)
        index = pd.date_range("2024-01-01", periods=n, freq="10min")
        ws = rng.uniform(8, 20, n)
        power = np.clip(2050 * ((ws - 3) / 9) ** 3, 0, 1500)  # 截斷在 1500

        df = pd.DataFrame(
            {"Wind Speed_Mean": ws, "Active Power_Mean": power},
            index=index,
        )
        inp = SkillInput(parameters={"rated_power_kw": 2050}, dataframe=df)
        output = await skill.execute(inp)

        assert output.status == SkillStatus.SUCCESS
        # 應偵測到降載事件
        assert output.data["curtailment_events"] > 0

    @pytest.mark.asyncio
    async def test_no_dataframe_error(self, skill) -> None:
        inp = SkillInput(parameters={})
        output = await skill.execute(inp)
        assert output.status == SkillStatus.ERROR

    @pytest.mark.asyncio
    async def test_missing_cols_error(self, skill) -> None:
        df = pd.DataFrame({"x": [1]})
        inp = SkillInput(parameters={}, dataframe=df)
        output = await skill.execute(inp)
        assert output.status == SkillStatus.ERROR

    def test_theoretical_power(self, skill) -> None:
        ws = pd.Series([0, 3, 6, 9, 12, 15, 20])
        result = skill._theoretical_power(ws, 2050, 3.0, 12.0)
        # 0 m/s → 0, 3 m/s → 0, 12 m/s → 2050, >12 → 2050
        assert result.iloc[0] == 0
        assert result.iloc[1] == 0
        assert abs(result.iloc[4] - 2050) < 1
        assert abs(result.iloc[5] - 2050) < 1

    def test_infer_interval(self, skill) -> None:
        idx = pd.date_range("2024-01-01", periods=10, freq="10min")
        df = pd.DataFrame({"a": range(10)}, index=idx)
        hours = skill._infer_interval_hours(df)
        assert abs(hours - 10 / 60) < 0.01


# ═══════════════════════════════════════════════════════════════
# AlarmCorrelationSkill
# ═══════════════════════════════════════════════════════════════


class TestAlarmCorrelation:
    @pytest.fixture()
    def skill(self):
        from src.skills.ml.alarm_correlation import AlarmCorrelationSkill

        return AlarmCorrelationSkill()

    def test_skill_id(self, skill) -> None:
        assert skill.skill_id == "alarm_correlation"

    @pytest.mark.asyncio
    async def test_basic_analysis(self, skill) -> None:
        df = _make_alarm_df()
        inp = SkillInput(parameters={}, dataframe=df)
        output = await skill.execute(inp)

        assert output.status == SkillStatus.SUCCESS
        data = output.data
        assert data["unique_alarms"] == 5
        assert data["total_events"] == 100
        assert len(data["top_alarms"]) > 0

    @pytest.mark.asyncio
    async def test_frequent_pairs(self, skill) -> None:
        df = _make_alarm_df(200)
        inp = SkillInput(parameters={"window_minutes": 120, "min_support": 2}, dataframe=df)
        output = await skill.execute(inp)

        assert output.status == SkillStatus.SUCCESS
        # 應找到一些共現對
        assert "frequent_pairs" in output.data

    @pytest.mark.asyncio
    async def test_custom_alarm_col(self, skill) -> None:
        df = pd.DataFrame(
            {"my_fault_code": ["F1", "F2", "F1", "F3"]},
            index=pd.date_range("2024-01-01", periods=4, freq="1h"),
        )
        inp = SkillInput(parameters={"alarm_code_col": "my_fault_code"}, dataframe=df)
        output = await skill.execute(inp)
        assert output.status == SkillStatus.SUCCESS
        assert output.data["unique_alarms"] == 3

    @pytest.mark.asyncio
    async def test_no_alarm_col_error(self, skill) -> None:
        df = pd.DataFrame({"wind_speed": [1, 2, 3]})
        inp = SkillInput(parameters={}, dataframe=df)
        output = await skill.execute(inp)
        assert output.status == SkillStatus.ERROR

    @pytest.mark.asyncio
    async def test_no_dataframe_error(self, skill) -> None:
        inp = SkillInput(parameters={})
        output = await skill.execute(inp)
        assert output.status == SkillStatus.ERROR

    def test_auto_detect_alarm_col(self, skill) -> None:
        df = pd.DataFrame({"error_code": [1, 2], "value": [10, 20]})
        assert skill._find_alarm_col(df) == "error_code"


# ═══════════════════════════════════════════════════════════════
# PowerCurveBinningSkill
# ═══════════════════════════════════════════════════════════════


class TestPowerCurveBinning:
    @pytest.fixture()
    def skill(self):
        from src.skills.features.power_curve_binning import PowerCurveBinningSkill

        return PowerCurveBinningSkill()

    def test_skill_id(self, skill) -> None:
        assert skill.skill_id == "power_curve_binning"

    @pytest.mark.asyncio
    async def test_basic_binning(self, skill) -> None:
        df = _make_scada_df(500)
        inp = SkillInput(
            parameters={"rated_power_kw": 2050, "bin_width": 0.5},
            dataframe=df,
        )
        output = await skill.execute(inp)

        assert output.status == SkillStatus.SUCCESS
        data = output.data
        assert data["valid_bins"] > 0
        assert data["estimated_aep_mwh"] > 0
        assert data["capacity_factor_pct"] > 0
        assert len(data["bin_table"]) > 0

    @pytest.mark.asyncio
    async def test_bin_table_structure(self, skill) -> None:
        df = _make_scada_df(500)
        inp = SkillInput(parameters={"bin_width": 1.0}, dataframe=df)
        output = await skill.execute(inp)

        bin_table = output.data["bin_table"]
        for b in bin_table:
            assert "wind_speed" in b
            assert "mean_power_kw" in b
            assert "std_power_kw" in b
            assert "count" in b
            assert b["count"] >= 3  # IEC 最低要求

    @pytest.mark.asyncio
    async def test_custom_bin_width(self, skill) -> None:
        df = _make_scada_df(500)
        inp = SkillInput(parameters={"bin_width": 1.0}, dataframe=df)
        output = await skill.execute(inp)
        assert output.data["bin_width_ms"] == 1.0

    @pytest.mark.asyncio
    async def test_no_dataframe_error(self, skill) -> None:
        inp = SkillInput(parameters={})
        output = await skill.execute(inp)
        assert output.status == SkillStatus.ERROR

    @pytest.mark.asyncio
    async def test_missing_cols_error(self, skill) -> None:
        df = pd.DataFrame({"x": [1]})
        inp = SkillInput(parameters={}, dataframe=df)
        output = await skill.execute(inp)
        assert output.status == SkillStatus.ERROR

    def test_aep_rayleigh_estimation(self, skill) -> None:
        """AEP 估算應產出合理數值。"""
        bin_table = [
            {"wind_speed": 5, "mean_power_kw": 200},
            {"wind_speed": 8, "mean_power_kw": 800},
            {"wind_speed": 10, "mean_power_kw": 1400},
            {"wind_speed": 12, "mean_power_kw": 2000},
            {"wind_speed": 14, "mean_power_kw": 2050},
        ]
        aep = skill._estimate_aep_rayleigh(bin_table, 0.5, 7.0)
        # 2MW 風機 AEP 通常在 3000-7000 MWh
        assert 100 < aep < 10000

    def test_aep_empty(self, skill) -> None:
        assert skill._estimate_aep_rayleigh([], 0.5, 7.0) == 0.0
