"""通用技能組合代理 — 根據 YAML task_routing 自動組合技能執行任務。

大多數代理不再需要獨立的 Python class，
只需在 YAML 中定義技能列表和任務路由即可。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.agents.base import BaseAgent, TaskContext, TaskResult, TaskStatus
from src.skills.base import SkillInput, SkillStatus
from src.skills.registry import SkillRegistry  # noqa: TCH001


@dataclass
class TaskRoute:
    """任務路由規則：關鍵字 → 技能管線。"""

    match: list[str]
    pipeline: list[str]


@dataclass
class AgentSpec:
    """從 YAML 載入的代理規格。"""

    id: str
    name: str
    display_name: str
    tier: str
    color: str = "#6b7280"
    icon: str = "🤖"
    core: bool = False
    description: str = ""
    skills: list[str] = field(default_factory=list)
    task_routing: list[TaskRoute] = field(default_factory=list)
    custom_class: str | None = None

    @classmethod
    def from_yaml_dict(cls, data: dict[str, Any]) -> AgentSpec:
        """從 YAML 解析結果建立 AgentSpec。"""
        routes = []
        for route_data in data.get("task_routing", []):
            routes.append(
                TaskRoute(
                    match=route_data.get("match", []),
                    pipeline=route_data.get("pipeline", []),
                )
            )

        return cls(
            id=data["id"],
            name=data.get("name", data["id"]),
            display_name=data.get("display_name", data["id"]),
            tier=data.get("tier", "research"),
            color=data.get("color", "#6b7280"),
            icon=data.get("icon", "🤖"),
            core=data.get("core", False),
            description=data.get("description", ""),
            skills=data.get("skills", []),
            task_routing=routes,
            custom_class=data.get("custom_class"),
        )


class SkillComposingAgent(BaseAgent):
    """根據 YAML 定義的 task_routing 自動組合技能的通用代理。

    工作流程：
    1. 接收任務描述
    2. 用關鍵字匹配找到對應的技能管線
    3. 依序執行管線中的每個技能
    4. 上一個技能的輸出成為下一個的輸入
    5. 彙整所有結果回傳
    """

    def __init__(self, spec: AgentSpec, skill_registry: SkillRegistry) -> None:
        super().__init__(spec.id)
        self._spec = spec
        self._skill_registry = skill_registry
        self._routes = spec.task_routing

    @property
    def capabilities(self) -> list[str]:
        """從技能列表衍生能力。"""
        return list(self._spec.skills)

    @property
    def description(self) -> str:
        return self._spec.description or super().description

    def _match_route(self, task: str) -> TaskRoute | None:
        """根據任務文字匹配最佳路由。"""
        task_lower = task.lower()
        for route in self._routes:
            if any(kw.lower() in task_lower for kw in route.match):
                return route

        # 無匹配時，使用第一個路由（如果有）
        if self._routes:
            return self._routes[0]
        return None

    async def execute(self, task: str, context: TaskContext) -> TaskResult:
        """根據 task_routing 組合技能執行任務。"""
        route = self._match_route(task)

        if route is None or not route.pipeline:
            # 沒有技能管線 → 回傳基本完成訊息
            return TaskResult(
                status=TaskStatus.SUCCESS,
                summary=f"{self._spec.display_name} 已完成任務",
                data={"task": task},
            )

        # 驗證所有技能都存在
        missing = [s for s in route.pipeline if not self._skill_registry.has(s)]
        if missing:
            return TaskResult(
                status=TaskStatus.ERROR,
                errors=[f"缺少技能：{', '.join(missing)}"],
            )

        # 依序執行技能管線
        all_results: dict[str, Any] = {}
        current_df = None
        total_skills = len(route.pipeline)

        for i, skill_id in enumerate(route.pipeline):
            skill = self._skill_registry.get(skill_id)
            if skill is None:
                continue

            # 進度基於管線位置
            base_progress = i / total_skills

            _bp, _sk = base_progress, skill  # bind loop vars for closure

            async def _progress_cb(
                p: float, msg: str, *, _bp: float = _bp, _sk: object = _sk
            ) -> None:
                overall = _bp + p / total_skills
                await self.update_progress(overall, f"[{_sk.display_name}] {msg}")  # type: ignore[union-attr]

            # 組裝輸入：DataFrame 明確透過 dataframe 欄位傳遞
            inp = SkillInput(
                parameters=context.parameters,
                data=current_df,
                context=all_results,
                dataframe=current_df,
            )

            # 執行技能
            output = await skill.execute(inp, progress_cb=_progress_cb)

            # 收集結果
            all_results[skill_id] = {
                "status": output.status.value,
                "data": output.data,
                "summary": output.summary,
                "errors": output.errors,
            }

            # 傳遞 DataFrame 給下一個技能（只用 dataframe，不 fallback 到 data dict）
            if output.dataframe is not None:
                current_df = output.dataframe

            # ── 關鍵：turbine_profiler 的結果注入到 parameters ──
            # 讓後續所有技能自動使用推斷出的風機參數
            if skill_id == "turbine_profiler" and output.data:
                profile = output.data.get("turbine_profile", {})
                if profile:
                    # 注入到 context.parameters，後續技能可直接讀取
                    context.parameters["turbine_profile"] = profile
                    # 同時設定常用參數的 shortcut
                    context.parameters.setdefault("rated_power", profile.get("rated_power_kw"))
                    context.parameters.setdefault("cut_in_speed", profile.get("cut_in_speed_ms"))
                    context.parameters.setdefault("cut_out_speed", profile.get("cut_out_speed_ms"))
                    context.parameters.setdefault(
                        "rated_wind_speed", profile.get("rated_wind_speed_ms")
                    )
                    context.parameters.setdefault(
                        "sampling_interval", profile.get("sampling_interval_seconds")
                    )

            # 如果某個技能失敗，提前結束
            if output.status == SkillStatus.ERROR:
                return TaskResult(
                    status=TaskStatus.ERROR,
                    data=all_results,
                    errors=output.errors,
                    summary=f"管線在 {skill.display_name} 步驟失敗",
                )

        await self.update_progress(1.0, "任務完成")

        # 彙整摘要
        summaries = [r["summary"] for r in all_results.values() if r.get("summary")]

        # ── 將結果轉為圖表格式並推送至前端戰情中心 ──
        await self._broadcast_charts(all_results)

        return TaskResult(
            status=TaskStatus.SUCCESS,
            data=all_results,
            summary=" → ".join(summaries) if summaries else "技能管線執行完成",
        )

    async def _broadcast_charts(self, all_results: dict[str, Any]) -> None:
        """將技能管線結果轉為前端可渲染的圖表並廣播。"""
        from src.api.websocket_manager import manager as ws_manager

        charts: list[dict[str, Any]] = []

        for skill_id, result in all_results.items():
            data = result.get("data", {})
            status = result.get("status", "")
            if status != "success" or not data:
                continue

            # ── SCADA 載入結果 → 資料概覽表 ──
            if skill_id == "scada_ingestion":
                detected = data.get("detected_fields", {})
                if detected:
                    charts.append(
                        {
                            "chart_type": "bar",
                            "title": f"偵測到的欄位（{data.get('row_count', '?')} 筆 × {data.get('col_count', '?')} 欄）",
                            "data": [
                                {"name": field, "value": 1} for field in list(detected.keys())[:15]
                            ],
                        }
                    )

            # ── SCADA 清洗結果 ──
            if skill_id == "scada_cleaning":
                before = data.get("rows_before", 0)
                after = data.get("rows_after", 0)
                if before > 0:
                    charts.append(
                        {
                            "chart_type": "bar",
                            "title": "資料清洗效果",
                            "data": [
                                {"name": "清洗前", "value": before},
                                {"name": "清洗後", "value": after},
                                {"name": "移除筆數", "value": before - after},
                            ],
                        }
                    )

            # ── 故障分類結果 → F1 per class 長條圖 ──
            if skill_id == "fault_classification":
                f1_per_class = data.get("f1_per_class", {})
                if f1_per_class:
                    charts.append(
                        {
                            "chart_type": "bar",
                            "title": f"故障分類 F1 Score（Macro: {data.get('f1_macro', 0):.4f}）",
                            "data": [
                                {"name": str(cls), "value": round(score, 4)}
                                for cls, score in f1_per_class.items()
                            ],
                        }
                    )
                top_features = data.get("top_features", {})
                if top_features:
                    charts.append(
                        {
                            "chart_type": "bar",
                            "title": "Top 特徵重要度",
                            "data": [
                                {"name": feat, "value": round(imp, 4)}
                                for feat, imp in top_features.items()
                            ],
                        }
                    )

            # ── NBM 功率曲線模型結果 ──
            if skill_id == "nbm_training":
                r2 = data.get("r2_score")
                mae = data.get("mae")
                rmse = data.get("rmse")
                if r2 is not None:
                    charts.append(
                        {
                            "chart_type": "bar",
                            "title": "NBM 模型效能指標",
                            "data": [
                                {"name": "R²", "value": round(r2, 4)},
                                {"name": "MAE (kW)", "value": round(mae, 1) if mae else 0},
                                {"name": "RMSE (kW)", "value": round(rmse, 1) if rmse else 0},
                            ],
                            "metadata": {
                                "train_samples": data.get("train_samples", 0),
                                "test_samples": data.get("test_samples", 0),
                            },
                        }
                    )

                # 功率曲線散佈圖（實際 vs 預測）
                pc_points = data.get("power_curve_points", [])
                if pc_points:
                    charts.append(
                        {
                            "chart_type": "power_curve",
                            "title": "功率曲線：實際 vs NBM 預測",
                            "data": pc_points,
                            "metadata": {
                                "x_label": "風速 (m/s)",
                                "y_label": "功率 (kW)",
                                "series": ["actual_power", "predicted_power"],
                                "R²": round(r2, 4) if r2 else 0,
                                "data_points": len(pc_points),
                            },
                        }
                    )

            # ── 領域特徵萃取 ──
            if skill_id == "domain_feature_extraction":
                new_features = data.get("new_features", [])
                if new_features:
                    charts.append(
                        {
                            "chart_type": "bar",
                            "title": f"萃取的領域特徵（共 {len(new_features)} 個）",
                            "data": [{"name": f, "value": 1} for f in new_features[:10]],
                        }
                    )

            # ── RUL 預測 ──
            if skill_id == "rul_prediction":
                rul_days = data.get("predicted_rul_days")
                if rul_days is not None:
                    charts.append(
                        {
                            "chart_type": "bar",
                            "title": "剩餘使用壽命預測 (RUL)",
                            "data": [
                                {"name": "RUL (天)", "value": round(rul_days, 1)},
                            ],
                            "metadata": data,
                        }
                    )

            # ── 報告生成 → 下載連結 ──
            if skill_id == "report_generator":
                download_url = data.get("download_url")
                report_id = data.get("report_id")
                if download_url:
                    charts.append(
                        {
                            "chart_type": "report_link",
                            "title": f"📄 {data.get('turbine_id', '')} 診斷報告",
                            "data": [],
                            "metadata": {
                                "report_id": report_id,
                                "download_url": download_url,
                                "section_count": data.get("section_count", 0),
                                "warning_count": data.get("warning_count", 0),
                                "generated_at": data.get("generated_at", ""),
                            },
                        }
                    )

        # 廣播所有圖表
        for chart in charts:
            await ws_manager.broadcast_analysis_result(chart)
