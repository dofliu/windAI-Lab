"""WindGuard AI 診斷推理整合測試。

驗證 WindGuard LLM 診斷推理模組、風場批次掃描器，
以及 FaultDiagnostician agent 的 LLM 整合功能。
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ── WindGuardDiagnosis 測試 ──────────────────────────────────


class TestWindGuardDiagnosis:
    """windguard_diagnosis.WindGuardDiagnosis 的測試。"""

    def _make_sample_report(self) -> dict[str, Any]:
        """建立測試用的診斷報告。"""
        return {
            "turbine_id": "WT-01",
            "health_score": 62.5,
            "total_records": 54986,
            "analysis_period": {"start": "2023-01-01", "end": "2023-12-31"},
            "health_details": {
                "data_completeness_score": 95.0,
                "power_curve_score": 55.0,
                "temperature_score": 42.0,
                "availability_score": 78.0,
            },
            "temperature_anomalies": [
                {
                    "timestamp": "2023-10-17 14:30:00",
                    "component": "發電機前軸承",
                    "actual_temp": 105.3,
                    "expected_temp": 68.2,
                    "deviation": 5.4,
                },
                {
                    "timestamp": "2023-10-17 14:40:00",
                    "component": "齒輪箱油溫",
                    "actual_temp": 92.1,
                    "expected_temp": 72.0,
                    "deviation": 4.1,
                },
            ],
            "temperature_anomaly_count": 48,
            "temperature_components_checked": ["齒輪箱油溫", "發電機前軸承", "發電機後軸承"],
            "power_curve_analysis": {
                "mean_deviation_pct": -12.3,
                "worst_wind_speed_bin": "8.0-8.5 m/s",
                "efficiency_loss_pct": 8.5,
            },
            "operational_summary": {
                "operating_hours": 7200,
                "availability": 82.1,
                "capacity_factor": 28.5,
            },
            "warnings": [
                "健康分數偏低 (62.5/100)，建議優先排檢",
                "偵測到 48 個溫度異常事件，可能有過熱風險",
            ],
            "recommendations": [
                "建議對發電機前軸承進行詳細檢查與油液分析",
                "建議檢查葉片狀態（結冰、髒汙、損傷）與 pitch 系統校正",
            ],
        }

    def test_build_diagnosis_prompt_contains_key_info(self) -> None:
        """確認 prompt 包含報告中的關鍵資訊。"""
        from src.services.windguard_diagnosis import WindGuardDiagnosis

        wg = WindGuardDiagnosis.__new__(WindGuardDiagnosis)
        report = self._make_sample_report()
        prompt = wg._build_diagnosis_prompt(report)

        assert "WT-01" in prompt
        assert "62.5" in prompt
        assert "54,986" in prompt or "54986" in prompt
        assert "發電機前軸承" in prompt
        assert "105.3" in prompt
        assert "-12.3" in prompt
        assert "82.1" in prompt

    def test_build_diagnosis_prompt_with_rag_contexts(self) -> None:
        """確認 RAG 上下文被正確嵌入 prompt。"""
        from src.services.windguard_diagnosis import WindGuardDiagnosis

        wg = WindGuardDiagnosis.__new__(WindGuardDiagnosis)
        report = self._make_sample_report()
        rag = [
            {
                "content": "Generator bearing replacement case study...",
                "source": "maintenance_log_2023.pdf",
                "relevance": 0.85,
            }
        ]
        prompt = wg._build_diagnosis_prompt(report, rag)
        assert "maintenance_log_2023.pdf" in prompt
        assert "Generator bearing" in prompt

    def test_parse_llm_response_valid_json(self) -> None:
        """確認能正確解析 LLM 的 JSON 回覆。"""
        from src.services.windguard_diagnosis import WindGuardDiagnosis

        wg = WindGuardDiagnosis.__new__(WindGuardDiagnosis)
        raw = '```json\n{"fault_type": "generator_bearing_failure", "severity": "High"}\n```'
        result = wg._parse_llm_response(raw)
        assert result["fault_type"] == "generator_bearing_failure"
        assert result["severity"] == "High"

    def test_parse_llm_response_invalid_json(self) -> None:
        """確認解析失敗時回傳 fallback 結構。"""
        from src.services.windguard_diagnosis import WindGuardDiagnosis

        wg = WindGuardDiagnosis.__new__(WindGuardDiagnosis)
        result = wg._parse_llm_response("This is not JSON at all")
        assert result["fault_type"] == "parse_error"
        assert "This is not JSON" in result["reasoning_chain"][0]

    def test_extract_tool_calls(self) -> None:
        """確認能從 LLM 回覆中提取工具呼叫。"""
        from src.services.windguard_diagnosis import WindGuardDiagnosis

        wg = WindGuardDiagnosis.__new__(WindGuardDiagnosis)
        response = (
            'Let me investigate both turbines.\n'
            'TOOL_CALL: detect_anomalies(turbine_id="WT-01")\n'
            'TOOL_CALL: detect_anomalies(turbine_id="WT-02")\n'
        )
        calls = wg._extract_tool_calls(response)
        assert len(calls) == 2
        assert calls[0]["tool_name"] == "detect_anomalies"
        assert calls[0]["params"]["turbine_id"] == "WT-01"
        assert calls[1]["params"]["turbine_id"] == "WT-02"

    def test_extract_tool_calls_no_calls(self) -> None:
        """確認無工具呼叫時回傳空列表。"""
        from src.services.windguard_diagnosis import WindGuardDiagnosis

        wg = WindGuardDiagnosis.__new__(WindGuardDiagnosis)
        calls = wg._extract_tool_calls("Based on the data, WT-01 is more critical.")
        assert calls == []

    def test_reason_about_diagnosis_calls_llm(self) -> None:
        """確認 reason_about_diagnosis 正確呼叫 LLM 並回傳結果。"""
        from src.services.windguard_diagnosis import WindGuardDiagnosis

        mock_llm = MagicMock()
        mock_llm.generate.return_value = json.dumps({
            "fault_type": "generator_bearing_failure",
            "fault_type_zh": "發電機軸承故障",
            "severity": "High",
            "confidence": 0.85,
            "reasoning_chain": ["溫度異常集中在發電機軸承"],
            "physical_mechanism": "軸承磨損導致摩擦熱增加",
            "maintenance_actions": [{"action": "更換軸承", "priority": "immediate"}],
            "risk_if_ignored": "可能導致發電機永久損壞",
        })

        wg = WindGuardDiagnosis()
        wg._llm = mock_llm

        report = self._make_sample_report()
        result = wg.reason_about_diagnosis(report)

        assert result["fault_type"] == "generator_bearing_failure"
        assert result["severity"] == "High"
        assert result["turbine_id"] == "WT-01"
        assert result["health_score"] == 62.5
        mock_llm.generate.assert_called_once()


# ── FleetScanner 測試 ────────────────────────────────────────


class TestFleetScanner:
    """fleet_scanner.FleetScanner 的測試。"""

    def _mock_loader(self, turbine_id: str) -> Any:
        """建立 mock 資料載入器。"""
        import numpy as np
        import pandas as pd

        n = 500
        rng = np.random.default_rng(42)
        dates = pd.date_range("2023-01-01", periods=n, freq="10min")
        df = pd.DataFrame(
            {
                "Wind Speed (m/s)_Mean": rng.uniform(3, 25, n),
                "Active Power (kW)_Mean": rng.uniform(0, 2050, n),
                "Gear Oil Temperature (°C)_Mean": rng.uniform(40, 85, n),
                "Generator Bearing Front Temperature (°C)_Mean": rng.uniform(50, 90, n),
                "Generator Bearing Rear Temperature (°C)_Mean": rng.uniform(50, 90, n),
                "Ambient Temperature (°C)_Mean": rng.uniform(-5, 35, n),
                "Blade Pitch Angle (°)_Mean": rng.uniform(0, 25, n),
                "Rotor Speed (rpm)_Mean": rng.uniform(5, 18, n),
            },
            index=dates,
        )
        return df

    def test_scan_fleet_returns_ranking(self) -> None:
        """確認風場掃描回傳風險排序。"""
        from src.services.fleet_scanner import FleetScanner

        scanner = FleetScanner(max_workers=2)
        result = scanner.scan_fleet(
            ["WT-01", "WT-02", "WT-03"],
            loader=self._mock_loader,
        )

        assert "fleet_summary" in result
        assert "risk_ranking" in result
        summary = result["fleet_summary"]
        assert summary["total_turbines"] == 3
        assert summary["scanned_ok"] == 3

    def test_scan_fleet_assigns_risk_levels(self) -> None:
        """確認每台風機都被分配了風險等級。"""
        from src.services.fleet_scanner import FleetScanner

        scanner = FleetScanner(max_workers=2)
        result = scanner.scan_fleet(["WT-01", "WT-02"], loader=self._mock_loader)

        for r in result["risk_ranking"]:
            assert r["risk_level"] in ("Critical", "High", "Medium", "Low")
            assert "health_score" in r
            assert "anomaly_rate_pct" in r

    def test_scan_fleet_sorted_by_health(self) -> None:
        """確認風險排序是依健康分數由低到高。"""
        from src.services.fleet_scanner import FleetScanner

        scanner = FleetScanner(max_workers=2)
        result = scanner.scan_fleet(
            ["WT-01", "WT-02", "WT-03"],
            loader=self._mock_loader,
        )
        scores = [r["health_score"] for r in result["risk_ranking"]]
        assert scores == sorted(scores)

    def test_scan_fleet_handles_loader_error(self) -> None:
        """確認載入失敗時不會中斷整個掃描。"""
        from src.services.fleet_scanner import FleetScanner

        def failing_loader(tid: str) -> Any:
            if tid == "WT-BAD":
                raise ValueError("Data not found")
            return self._mock_loader(tid)

        scanner = FleetScanner(max_workers=2)
        result = scanner.scan_fleet(
            ["WT-01", "WT-BAD", "WT-02"],
            loader=failing_loader,
        )
        assert result["fleet_summary"]["scanned_ok"] == 2
        assert result["fleet_summary"]["scan_failed"] == 1


# ── diagnosis_service 整合測試 ───────────────────────────────


class TestDiagnosisServiceWindGuard:
    """diagnosis_service 的 WindGuard 相關函式測試。"""

    def test_run_windguard_diagnosis_with_mock_llm(self) -> None:
        """確認 run_windguard_diagnosis 在 LLM mock 下正常運作。"""
        import numpy as np
        import pandas as pd

        n = 500
        rng = np.random.default_rng(42)
        dates = pd.date_range("2023-01-01", periods=n, freq="10min")
        df = pd.DataFrame(
            {
                "Wind Speed (m/s)_Mean": rng.uniform(3, 25, n),
                "Active Power (kW)_Mean": rng.uniform(0, 2050, n),
                "Gear Oil Temperature (°C)_Mean": rng.uniform(40, 85, n),
                "Generator Bearing Front Temperature (°C)_Mean": rng.uniform(50, 90, n),
                "Generator Bearing Rear Temperature (°C)_Mean": rng.uniform(50, 90, n),
                "Ambient Temperature (°C)_Mean": rng.uniform(-5, 35, n),
                "Blade Pitch Angle (°)_Mean": rng.uniform(0, 25, n),
                "Rotor Speed (rpm)_Mean": rng.uniform(5, 18, n),
            },
            index=dates,
        )

        mock_llm_response = json.dumps({
            "fault_type": "gearbox_oil_degradation",
            "fault_type_zh": "齒輪箱油品劣化",
            "severity": "Medium",
            "confidence": 0.72,
            "reasoning_chain": ["油溫偏高"],
            "physical_mechanism": "潤滑油劣化導致散熱效率下降",
            "maintenance_actions": [{"action": "油品更換", "priority": "scheduled"}],
            "risk_if_ignored": "齒輪箱加速磨損",
        })

        with patch("src.services.windguard_diagnosis.WindGuardDiagnosis.llm", new_callable=lambda: property(lambda self: MagicMock())) as _:
            from src.services.windguard_diagnosis import WindGuardDiagnosis

            mock_llm = MagicMock()
            mock_llm.generate.return_value = mock_llm_response

            with patch.object(WindGuardDiagnosis, "llm", new_callable=lambda: property(lambda self: mock_llm)):
                from src.services.diagnosis_service import run_windguard_diagnosis

                result = run_windguard_diagnosis(df, "WT-TEST", enable_rag=False)

        assert "health_score" in result
        assert "windguard_llm_diagnosis" in result

    def test_run_fleet_diagnosis_exists(self) -> None:
        """確認 run_fleet_diagnosis 函式存在且可匯入。"""
        from src.services.diagnosis_service import run_fleet_diagnosis

        assert callable(run_fleet_diagnosis)


# ── DIAGNOSTIC_TOOLS 定義測試 ─────────────────────────────────


class TestDiagnosticTools:
    """驗證診斷工具定義的完整性。"""

    def test_all_tools_have_required_fields(self) -> None:
        """確認所有工具定義都有 name, description, parameters。"""
        from src.services.windguard_diagnosis import DIAGNOSTIC_TOOLS

        for tool in DIAGNOSTIC_TOOLS:
            assert "name" in tool, f"工具缺少 name 欄位：{tool}"
            assert "description" in tool, f"工具 {tool['name']} 缺少 description"
            assert "parameters" in tool, f"工具 {tool['name']} 缺少 parameters"

    def test_tool_count(self) -> None:
        """確認工具數量符合預期。"""
        from src.services.windguard_diagnosis import DIAGNOSTIC_TOOLS

        assert len(DIAGNOSTIC_TOOLS) == 5
