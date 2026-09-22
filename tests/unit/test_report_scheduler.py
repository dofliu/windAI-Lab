"""報告排程與自動生成單元測試。"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from src.services.report_scheduler import ReportScheduler


class TestReportScheduler:
    """ReportScheduler 核心測試。"""

    def test_load_schedules_from_yaml(self, tmp_path) -> None:
        """測試加載 report_scheduler 排程配置。"""
        config_file = tmp_path / "schedule.yaml"
        config_data = {
            "schedules": [
                {
                    "id": "weekly_test",
                    "name": "測試週報",
                    "enabled": True,
                    "interval_seconds": 3600,
                    "report_type": "weekly",
                    "turbine_id": "all",
                },
                {
                    "id": "monthly_test",
                    "name": "測試月報",
                    "enabled": False,
                    "interval_seconds": 86400,
                    "report_type": "monthly",
                    "turbine_id": "WT-01",
                },
            ]
        }
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(config_data, f)

        scheduler = ReportScheduler(config_path=config_file)
        count = scheduler.load_schedules()

        assert count == 1
        assert len(scheduler.schedules) == 1
        assert scheduler.schedules[0]["id"] == "weekly_test"

    @pytest.mark.asyncio
    async def test_generate_and_dispatch_weekly(self) -> None:
        """測試週報生成、KPI 數據彙整與通知發送。"""
        scheduler = ReportScheduler()

        # Mock 數據庫
        db_mock = MagicMock()

        # 準備模擬 alerts 與 work_orders 數據
        db_mock.list_alerts = MagicMock(
            return_value=[
                {
                    "id": "ALT_1",
                    "turbine_id": "WT-01",
                    "severity": "critical",
                    "message": "溫度異常",
                    "status": "resolved",
                    "created_at": datetime.now(UTC).isoformat(),
                },
                {
                    "id": "ALT_2",
                    "turbine_id": "WT-01",
                    "severity": "warning",
                    "message": "微幅偏差",
                    "status": "active",
                    "created_at": datetime.now(UTC).isoformat(),
                },
            ]
        )
        db_mock.list_work_orders = MagicMock(
            return_value=[
                {
                    "id": "WO_1",
                    "turbine_id": "WT-01",
                    "title": "檢查風機",
                    "status": "completed",
                    "created_at": datetime.now(UTC).isoformat(),
                },
                {
                    "id": "WO_2",
                    "turbine_id": "WT-01",
                    "title": "檢查發電機",
                    "status": "in_progress",
                    "created_at": datetime.now(UTC).isoformat(),
                },
            ]
        )

        # Mock 資料庫 Connection，模擬 daily_sheets 統計
        conn_mock = MagicMock()
        cursor_mock = MagicMock()
        cursor_mock.fetchone = MagicMock(return_value=(5, 4))  # 5 份日誌，4 份簽署
        conn_mock.cursor = MagicMock(return_value=cursor_mock)
        db_mock._conn = conn_mock

        # Mock 通知管理器
        notifier_mock = MagicMock()
        notifier_mock.dispatch = AsyncMock()

        with (
            patch("src.core.database.get_database", return_value=db_mock),
            patch(
                "src.services.report_scheduler.get_notification_manager",
                return_value=notifier_mock,
            ),
            patch("src.services.report_store.save_report") as save_mock,
        ):

            res = scheduler.generate_and_dispatch("weekly", "all", "全風場測試週報")

            assert res is not None
            assert "RPT_WEEKLY_" in res["id"]
            assert "全風場測試週報" in res["title"]

            # 驗證是否正確呼叫儲存
            save_mock.assert_called_once()
            call_args = save_mock.call_args[0]
            assert "RPT_WEEKLY_" in call_args[0]
            assert "全風場測試週報" in call_args[1]
            markdown_content = call_args[2]

            # 驗證 Markdown 中的 KPI 欄位值
            assert "100.0%" not in markdown_content  # 4/5 應為 80.0%
            assert "80.0%" in markdown_content
            assert "2** 件" in markdown_content  # 警報總數 2
            assert "1** 件" in markdown_content  # 嚴重警報 1, 完成工單 1, 進行中 1

            # 驗證是否觸發 Email/LINE 通知
            notifier_mock.dispatch.assert_called_once()
