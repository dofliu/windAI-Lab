"""維護排程技能 — 根據 RUL 預測與故障嚴重度自動產出維護排程。

整合來源：
1. RUL 預測結果 → 決定最晚維護期限
2. 故障嚴重度 → 決定優先級
3. 健康分數 → 補充排序依據
4. 天氣/季節（選用）→ 調整維護窗口

輸出：
- 按優先級排序的維護工單清單
- 建議維護窗口（考量停機成本最小化）
- 資源分配建議
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from src.skills.base import BaseSkill, ProgressCallback, SkillInput, SkillOutput, SkillStatus
from src.utils.logger import get_logger

logger = get_logger("skill.maintenance_scheduler")

# 嚴重度 → 最大允許反應天數
_SEVERITY_DEADLINE: dict[str, int] = {
    "Critical": 2,
    "High": 14,
    "Medium": 30,
    "Low": 90,
}

# 維護類型 → 預估停機時間（小時）
_MAINTENANCE_DURATION: dict[str, float] = {
    "emergency_inspection": 4,
    "vibration_measurement": 2,
    "oil_sampling": 1,
    "bearing_replacement": 48,
    "gearbox_repair": 72,
    "blade_inspection": 8,
    "scheduled_maintenance": 12,
    "monitoring_only": 0,
}


class MaintenanceSchedulerSkill(BaseSkill):
    """維護排程技能 — 根據分析結果自動產出維護計畫。"""

    skill_id = "maintenance_scheduler"
    display_name = "智慧維護排程"
    description = "根據 RUL 預測與故障嚴重度自動產出維護排程與資源分配"
    version = "1.0.0"

    async def execute(
        self,
        inp: SkillInput,
        progress_cb: ProgressCallback = None,
    ) -> SkillOutput:
        """產出維護排程。

        Parameters (inp.parameters):
            turbine_id: str — 單台風機（選用）
            turbine_reports: list[dict] — 多台風機報告（選用）

        inp.context:
            上游技能結果（RUL、故障分類、健康評估等）
        """
        if progress_cb:
            await progress_cb(0.1, "收集上游分析結果...")

        # 收集維護需求
        maintenance_items = self._collect_maintenance_needs(
            inp.parameters, inp.context or {}
        )

        if progress_cb:
            await progress_cb(0.4, f"識別到 {len(maintenance_items)} 項維護需求")

        if not maintenance_items:
            return SkillOutput(
                status=SkillStatus.SUCCESS,
                data={"work_orders": [], "summary": "目前無維護需求"},
                summary="維護排程：目前所有風機狀態正常，無需安排維護",
            )

        # 排序與排程
        if progress_cb:
            await progress_cb(0.6, "計算維護優先級與排程...")

        work_orders = self._schedule(maintenance_items)

        if progress_cb:
            await progress_cb(0.8, "計算資源分配...")

        resource_plan = self._plan_resources(work_orders)

        if progress_cb:
            await progress_cb(1.0, f"排程完成 — {len(work_orders)} 筆工單")

        # 統計
        urgent = sum(1 for w in work_orders if w["priority"] in ("Critical", "High"))
        total_downtime = sum(w["estimated_downtime_hours"] for w in work_orders)

        return SkillOutput(
            status=SkillStatus.SUCCESS,
            data={
                "work_orders": work_orders,
                "resource_plan": resource_plan,
                "schedule_summary": {
                    "total_orders": len(work_orders),
                    "urgent_orders": urgent,
                    "total_estimated_downtime_hours": round(total_downtime, 1),
                    "planning_horizon_days": 90,
                    "generated_at": datetime.now().isoformat(),
                },
            },
            summary=(
                f"維護排程：{len(work_orders)} 筆工單 | "
                f"緊急 {urgent} 筆 | "
                f"預估停機 {total_downtime:.0f}h"
            ),
        )

    def _collect_maintenance_needs(
        self,
        parameters: dict[str, Any],
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """從上游結果收集維護需求。"""
        items: list[dict[str, Any]] = []
        turbine_id = parameters.get("turbine_id", "WT-01")

        # 從上游技能結果中提取
        for skill_id, result in context.items():
            if not isinstance(result, dict):
                continue
            data = result.get("data", {})

            # RUL 預測結果
            if skill_id == "rul_prediction" or "predicted_rul_days" in data:
                rul_days = data.get("predicted_rul_days")
                if rul_days is not None:
                    severity = (
                        "Critical" if rul_days < 30
                        else "High" if rul_days < 90
                        else "Medium" if rul_days < 180
                        else "Low"
                    )
                    items.append({
                        "turbine_id": turbine_id,
                        "source": "rul_prediction",
                        "severity": severity,
                        "description": f"RUL 預測剩餘 {rul_days:.0f} 天",
                        "rul_days": rul_days,
                        "maintenance_type": (
                            "bearing_replacement" if rul_days < 30
                            else "vibration_measurement" if rul_days < 90
                            else "scheduled_maintenance"
                        ),
                    })

            # 故障分類結果
            if skill_id == "fault_classification":
                severity_dist = data.get("severity_distribution", {})
                if severity_dist.get("critical", 0) > 0:
                    items.append({
                        "turbine_id": turbine_id,
                        "source": "fault_classification",
                        "severity": "Critical",
                        "description": "ML 分類偵測到 Critical 級故障事件",
                        "maintenance_type": "emergency_inspection",
                    })
                elif severity_dist.get("high", 0) > 0:
                    items.append({
                        "turbine_id": turbine_id,
                        "source": "fault_classification",
                        "severity": "High",
                        "description": "ML 分類偵測到 High 級故障事件",
                        "maintenance_type": "vibration_measurement",
                    })

            # 異常偵測結果
            if skill_id == "anomaly_detection":
                anomaly_ratio = data.get("anomaly_ratio", 0)
                health = data.get("health_score", 100)
                if anomaly_ratio > 0.1 or health < 50:
                    items.append({
                        "turbine_id": turbine_id,
                        "source": "anomaly_detection",
                        "severity": "High" if health < 50 else "Medium",
                        "description": (
                            f"異常比率 {anomaly_ratio:.1%}，健康分數 {health}/100"
                        ),
                        "maintenance_type": "oil_sampling",
                    })

            # NBM 結果
            if skill_id == "nbm_training":
                anomaly_count = data.get("anomaly_count", 0)
                if anomaly_count > 100:
                    items.append({
                        "turbine_id": turbine_id,
                        "source": "nbm_training",
                        "severity": "Medium",
                        "description": f"NBM 偵測到 {anomaly_count} 筆功率曲線異常",
                        "maintenance_type": "blade_inspection",
                    })

        # 多台風機報告
        turbine_reports = parameters.get("turbine_reports", [])
        for report in turbine_reports:
            tid = report.get("turbine_id", "")
            health = report.get("health_score", 100)
            if health < 60:
                items.append({
                    "turbine_id": tid,
                    "source": "health_assessment",
                    "severity": "Critical" if health < 40 else "High",
                    "description": f"健康分數 {health}/100",
                    "maintenance_type": "emergency_inspection" if health < 40 else "vibration_measurement",
                })

        return items

    def _schedule(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """排序並產出工單。"""
        severity_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
        items.sort(key=lambda x: (severity_order.get(x["severity"], 4), x.get("rul_days", 999)))

        now = datetime.now()
        work_orders: list[dict[str, Any]] = []

        for i, item in enumerate(items):
            severity = item["severity"]
            deadline_days = _SEVERITY_DEADLINE.get(severity, 90)
            maint_type = item.get("maintenance_type", "scheduled_maintenance")
            downtime = _MAINTENANCE_DURATION.get(maint_type, 8)

            deadline = now + timedelta(days=deadline_days)
            # 建議執行日 = deadline 前 2 天（留緩衝）
            suggested = deadline - timedelta(days=min(2, deadline_days))

            work_orders.append({
                "order_id": f"WO-{now.strftime('%Y%m%d')}-{i+1:03d}",
                "turbine_id": item["turbine_id"],
                "priority": severity,
                "description": item["description"],
                "source": item["source"],
                "maintenance_type": maint_type,
                "estimated_downtime_hours": downtime,
                "deadline": deadline.strftime("%Y-%m-%d"),
                "suggested_date": suggested.strftime("%Y-%m-%d"),
                "status": "pending",
            })

        return work_orders

    def _plan_resources(self, work_orders: list[dict[str, Any]]) -> dict[str, Any]:
        """計算資源分配建議。"""
        # 按週分組
        week_loads: dict[str, int] = {}
        for wo in work_orders:
            week = wo["suggested_date"][:7]  # YYYY-MM
            week_loads[week] = week_loads.get(week, 0) + 1

        # 計算維護類型分布
        type_counts: dict[str, int] = {}
        for wo in work_orders:
            mt = wo["maintenance_type"]
            type_counts[mt] = type_counts.get(mt, 0) + 1

        # 估算所需人力
        total_hours = sum(wo["estimated_downtime_hours"] for wo in work_orders)
        # 假設每人每天 8 小時
        crew_days = total_hours / 8

        return {
            "total_maintenance_hours": round(total_hours, 1),
            "estimated_crew_days": round(crew_days, 1),
            "monthly_distribution": week_loads,
            "type_distribution": type_counts,
            "recommendation": (
                f"建議安排 {max(1, int(crew_days / 5))} 組維護團隊，"
                f"預計需 {crew_days:.0f} 人天完成所有工單"
            ),
        }
