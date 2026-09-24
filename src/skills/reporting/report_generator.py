"""報告生成技能 — 自動將分析結果彙整為結構化 Markdown 報告。

支援多種報告類型：
- 故障診斷報告（anomaly + health score + recommendations）
- 月度健康評估報告
- 模型效能評估報告
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.skills.base import BaseSkill, ProgressCallback, SkillInput, SkillOutput, SkillStatus


class ReportGeneratorSkill(BaseSkill):
    """自動產出 Markdown 格式分析報告的技能。"""

    skill_id = "report_generator"
    display_name = "報告生成"
    description = "將分析結果彙整為結構化 Markdown 報告，支援故障診斷、月度評估、模型效能等類型"
    version = "1.0.0"

    async def execute(
        self,
        inp: SkillInput,
        progress_cb: ProgressCallback = None,
    ) -> SkillOutput:
        """根據上游技能結果生成報告。

        Parameters（透過 inp.parameters）:
            report_type: 報告類型（"diagnosis" / "monthly" / "model_eval"），預設 "diagnosis"
            turbine_id: 風機 ID

        上游結果來源（透過 inp.context）:
            anomaly_detection / fault_classification / nbm_training / rul_prediction 等技能的輸出
        """
        context = inp.context or {}
        params = inp.parameters or {}
        report_type = params.get("report_type", "diagnosis")
        turbine_id = params.get("turbine_id", "未知")

        if progress_cb:
            await progress_cb(0.1, "分析上游結果...")

        if report_type == "monthly":
            report_md = self._generate_monthly_report(turbine_id, context, params)
        elif report_type == "model_eval":
            report_md = self._generate_model_eval_report(turbine_id, context, params)
        else:
            report_md = self._generate_diagnosis_report(turbine_id, context, params)

        if progress_cb:
            await progress_cb(0.8, "格式化報告...")

        # 計算報告統計
        section_count = report_md.count("\n## ")
        warning_count = report_md.count("⚠️") + report_md.count("🔴")

        if progress_cb:
            await progress_cb(0.9, "儲存報告...")

        # 儲存報告並產生下載連結
        import uuid

        report_id = str(uuid.uuid4())[:8]
        report_title = f"{turbine_id}_{_report_type_label(report_type)}_{datetime.now().strftime('%Y%m%d_%H%M')}"
        download_url = f"/api/reports/{report_id}/download"

        try:
            from src.services.report_store import save_report

            save_report(report_id, report_title, report_md)
        except Exception:
            pass  # 若模組不可用（測試環境），靜默跳過

        if progress_cb:
            await progress_cb(1.0, "報告生成完成")

        return SkillOutput(
            status=SkillStatus.SUCCESS,
            data={
                "report_markdown": report_md,
                "report_type": report_type,
                "turbine_id": turbine_id,
                "section_count": section_count,
                "warning_count": warning_count,
                "generated_at": datetime.now().isoformat(),
                "report_id": report_id,
                "download_url": download_url,
            },
            summary=f"{turbine_id} {_report_type_label(report_type)}已生成（{section_count} 個章節）",
            artifacts={"report_markdown": report_md},
        )

    # ── 故障診斷報告 ──────────────────────────────────────

    def _generate_diagnosis_report(
        self, turbine_id: str, context: dict[str, Any], params: dict[str, Any]
    ) -> str:
        """生成故障診斷報告。"""
        lines: list[str] = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        lines.append(f"# 風機故障診斷報告 — {turbine_id}")
        lines.append(f"\n> 產出時間：{now}")
        lines.append("")

        # ── 健康分數摘要 ──
        anomaly = _get_skill_data(context, "anomaly_detection")
        health_score = anomaly.get("health_score", "N/A")
        lines.append("## 1. 健康分數摘要")
        lines.append("")
        if isinstance(health_score, int | float):
            emoji = "🟢" if health_score >= 80 else "🟡" if health_score >= 60 else "🔴"
            lines.append(f"**綜合健康分數：{emoji} {health_score}/100**")
        else:
            lines.append(f"**綜合健康分數：** {health_score}")

        details = anomaly.get("health_details", {})
        if details:
            lines.append("")
            lines.append("| 指標 | 分數 |")
            lines.append("|------|------|")
            for key, label in [
                ("data_completeness_score", "資料完整度"),
                ("power_curve_score", "功率曲線符合度"),
                ("temperature_score", "溫度穩定度"),
                ("availability_score", "可用率"),
            ]:
                val = details.get(key, "N/A")
                lines.append(f"| {label} | {val} |")
        lines.append("")

        # ── 溫度異常 ──
        lines.append("## 2. 溫度異常偵測")
        lines.append("")
        temp_count = anomaly.get("temperature_anomaly_count", 0)
        components = anomaly.get("components_checked", [])
        lines.append(f"- 檢查元件：{', '.join(components) if components else '無'}")
        lines.append(f"- 異常事件數：**{temp_count}**")

        anomalies = anomaly.get("temperature_anomalies", [])
        if anomalies:
            lines.append("")
            lines.append("| 元件 | 實際溫度 | 期望溫度 | 偏差 (σ) |")
            lines.append("|------|----------|----------|----------|")
            for a in anomalies[:10]:
                lines.append(
                    f"| {a.get('component', '')} | {a.get('actual_temp', '')}°C "
                    f"| {a.get('expected_temp', '')}°C | {a.get('deviation', '')} |"
                )
            if len(anomalies) > 10:
                lines.append(f"\n*（僅顯示前 10 筆，共 {len(anomalies)} 筆）*")
        lines.append("")

        # ── 功率曲線分析 ──
        lines.append("## 3. 功率曲線偏差分析")
        lines.append("")
        pc_dev = anomaly.get("power_curve_deviation_pct", 0)
        eff_loss = anomaly.get("efficiency_loss_pct", 0)
        worst_bin = anomaly.get("worst_wind_speed_bin", "N/A")
        lines.append(f"- 平均偏差：**{pc_dev:.1f}%**")
        lines.append(f"- 效率損失：**{eff_loss:.1f}%**")
        lines.append(f"- 偏差最大風速區間：{worst_bin}")
        lines.append("")

        # ── 故障分類（如有） ──
        fault = _get_skill_data(context, "fault_classification")
        if fault:
            lines.append("## 4. 故障分類結果")
            lines.append("")
            f1 = fault.get("f1_macro", "N/A")
            lines.append(
                f"- F1 Macro Score：**{f1:.4f}**"
                if isinstance(f1, float)
                else f"- F1 Macro Score：{f1}"
            )
            f1_per_class = fault.get("f1_per_class", {})
            if f1_per_class:
                lines.append("")
                lines.append("| 類別 | F1 Score |")
                lines.append("|------|----------|")
                for cls, score in f1_per_class.items():
                    lines.append(f"| {cls} | {score:.4f} |")
            lines.append("")

        # ── NBM（如有） ──
        nbm = _get_skill_data(context, "nbm_training")
        if nbm:
            section_num = 5 if fault else 4
            lines.append(f"## {section_num}. NBM 功率曲線模型")
            lines.append("")
            lines.append(f"- R²：**{nbm.get('r2_score', 'N/A')}**")
            lines.append(f"- MAE：{nbm.get('mae', 'N/A')} kW")
            lines.append(f"- RMSE：{nbm.get('rmse', 'N/A')} kW")
            lines.append("")

        # ── RUL（如有） ──
        rul = _get_skill_data(context, "rul_prediction")
        if rul:
            section_num = (5 if fault else 4) + (1 if nbm else 0)
            lines.append(f"## {section_num}. 剩餘使用壽命預測")
            lines.append("")
            rul_days = rul.get("predicted_rul_days", "N/A")
            lines.append(f"- 預測 RUL：**{rul_days} 天**")
            ci_lower = rul.get("confidence_interval_lower")
            ci_upper = rul.get("confidence_interval_upper")
            if ci_lower is not None and ci_upper is not None:
                lines.append(f"- 95% 信賴區間：{ci_lower} ~ {ci_upper} 天")
            lines.append("")

        # ── 建議 ──
        lines.append("## 建議事項")
        lines.append("")
        lines.extend(_generate_recommendations(anomaly, fault, nbm, rul))
        lines.append("")

        lines.append("---")
        lines.append(f"*報告由 WindAI Lab 自動產出 · {now}*")

        return "\n".join(lines)

    # ── 月度健康評估報告 ──────────────────────────────────

    def _generate_monthly_report(
        self, turbine_id: str, context: dict[str, Any], params: dict[str, Any]
    ) -> str:
        """生成月度健康評估報告。"""
        lines: list[str] = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        lines.append(f"# 月度健康評估報告 — {turbine_id}")
        lines.append(f"\n> 產出時間：{now}")
        lines.append("")

        # 收集各技能結果
        anomaly = _get_skill_data(context, "anomaly_detection")
        alarm = _get_skill_data(context, "alarm_processor")
        fault = _get_skill_data(context, "fault_classification")
        rul = _get_skill_data(context, "rul_prediction")

        # ── 健康總覽 ──
        lines.append("## 1. 健康總覽")
        lines.append("")
        health_score = anomaly.get("health_score", "N/A")
        if isinstance(health_score, int | float):
            emoji = "🟢" if health_score >= 80 else "🟡" if health_score >= 60 else "🔴"
            lines.append(f"**本月健康分數：{emoji} {health_score}/100**")
        lines.append("")

        # ── 警報統計 ──
        if alarm:
            lines.append("## 2. 警報事件統計")
            lines.append("")
            lines.append(f"- 總警報數：{alarm.get('total_alarms', 'N/A')}")
            lines.append(f"- MTBF：{alarm.get('mtbf_hours', 'N/A')} 小時")
            top_codes = alarm.get("top_alarm_codes", [])
            if top_codes:
                lines.append("")
                lines.append("| 排名 | 警報碼 | 次數 |")
                lines.append("|------|--------|------|")
                for i, code in enumerate(top_codes[:5], 1):
                    lines.append(f"| {i} | {code.get('code', '')} | {code.get('count', '')} |")
            lines.append("")

        # ── 功率曲線 + 異常 ──
        if anomaly:
            lines.append("## 3. 異常偵測")
            lines.append("")
            lines.append(f"- 溫度異常：{anomaly.get('temperature_anomaly_count', 0)} 筆")
            lines.append(f"- 功率曲線偏差：{anomaly.get('power_curve_deviation_pct', 0):.1f}%")
            lines.append(f"- 效率損失：{anomaly.get('efficiency_loss_pct', 0):.1f}%")
            lines.append("")

        # ── RUL 更新 ──
        if rul:
            lines.append("## 4. RUL 壽命預測更新")
            lines.append("")
            lines.append(f"- 預測剩餘壽命：**{rul.get('predicted_rul_days', 'N/A')} 天**")
            lines.append("")

        # ── 建議 ──
        lines.append("## 維護建議")
        lines.append("")
        lines.extend(_generate_recommendations(anomaly, fault, None, rul))
        lines.append("")

        lines.append("---")
        lines.append(f"*報告由 WindAI Lab 自動產出 · {now}*")

        return "\n".join(lines)

    # ── 模型效能報告 ─────────────────────────────────────

    def _generate_model_eval_report(
        self, turbine_id: str, context: dict[str, Any], params: dict[str, Any]
    ) -> str:
        """生成模型效能評估報告。"""
        lines: list[str] = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        lines.append(f"# 模型效能評估報告 — {turbine_id}")
        lines.append(f"\n> 產出時間：{now}")
        lines.append("")

        nbm = _get_skill_data(context, "nbm_training")
        fault = _get_skill_data(context, "fault_classification")
        rul = _get_skill_data(context, "rul_prediction")
        experiment = _get_skill_data(context, "auto_experiment")

        if nbm:
            lines.append("## NBM 功率曲線模型")
            lines.append("")
            lines.append("| 指標 | 數值 |")
            lines.append("|------|------|")
            lines.append(f"| R² | {nbm.get('r2_score', 'N/A')} |")
            lines.append(f"| MAE | {nbm.get('mae', 'N/A')} kW |")
            lines.append(f"| RMSE | {nbm.get('rmse', 'N/A')} kW |")
            lines.append(f"| 訓練樣本 | {nbm.get('train_samples', 'N/A')} |")
            lines.append(f"| 測試樣本 | {nbm.get('test_samples', 'N/A')} |")
            lines.append("")

        if fault:
            lines.append("## 故障分類器")
            lines.append("")
            lines.append(f"- F1 Macro：**{fault.get('f1_macro', 'N/A')}**")
            lines.append(
                f"- 訓練 / 測試：{fault.get('n_train', '?')} / {fault.get('n_test', '?')}"
            )
            lines.append("")

        if rul:
            lines.append("## RUL 退化模型")
            lines.append("")
            lines.append(f"- 預測 RUL：**{rul.get('predicted_rul_days', 'N/A')} 天**")
            lines.append(f"- 模型類型：{rul.get('model_type', 'Weibull/Linear')}")
            lines.append("")

        if experiment:
            lines.append("## 自動實驗結果")
            lines.append("")
            total = experiment.get("total_trials", 0)
            best = experiment.get("best_trial", {})
            lines.append(f"- 實驗次數：{total}")
            if best:
                lines.append(f"- 最佳 R²：{best.get('r2_score', 'N/A')}")
                lines.append(f"- 最佳參數：{best.get('params', {})}")
            lines.append("")

        if not any([nbm, fault, rul, experiment]):
            lines.append("*無可用的模型評估結果。請先執行模型訓練。*")
            lines.append("")

        lines.append("---")
        lines.append(f"*報告由 WindAI Lab 自動產出 · {now}*")

        return "\n".join(lines)


# ── 工具函式 ──────────────────────────────────────────────


def _get_skill_data(context: dict[str, Any], skill_id: str) -> dict[str, Any]:
    """從 context 中取得特定技能的 data dict。"""
    skill_result = context.get(skill_id, {})
    if isinstance(skill_result, dict):
        return skill_result.get("data", skill_result)
    return {}


def _report_type_label(report_type: str) -> str:
    """報告類型中文標籤。"""
    labels = {
        "diagnosis": "故障診斷報告",
        "monthly": "月度健康評估報告",
        "model_eval": "模型效能評估報告",
    }
    return labels.get(report_type, "分析報告")


def _generate_recommendations(
    anomaly: dict[str, Any],
    fault: dict[str, Any] | None,
    nbm: dict[str, Any] | None,
    rul: dict[str, Any] | None,
) -> list[str]:
    """根據分析結果生成建議列表。"""
    recs: list[str] = []

    health = anomaly.get("health_score", 100)
    if isinstance(health, int | float):
        if health < 60:
            recs.append("- 🔴 健康分數偏低，建議立即安排現場檢查")
        elif health < 80:
            recs.append("- ⚠️ 健康分數中等，建議加強監控頻率")

    temp_count = anomaly.get("temperature_anomaly_count", 0)
    if temp_count > 10:
        recs.append(f"- 🔴 偵測到 {temp_count} 個溫度異常事件，建議進行軸承油液分析")
    elif temp_count > 0:
        recs.append(f"- ⚠️ 有 {temp_count} 個溫度異常事件，建議持續追蹤")

    eff_loss = anomaly.get("efficiency_loss_pct", 0)
    if isinstance(eff_loss, int | float) and abs(eff_loss) > 10:
        recs.append("- 🔴 效率損失顯著，建議檢查葉片狀態與 yaw alignment")
    elif isinstance(eff_loss, int | float) and abs(eff_loss) > 5:
        recs.append("- ⚠️ 功率曲線略有偏差，建議下次維護時檢查葉片清潔度")

    if rul:
        rul_days = rul.get("predicted_rul_days")
        if isinstance(rul_days, int | float) and rul_days < 90:
            recs.append(f"- 🔴 預測 RUL 僅 {rul_days:.0f} 天，建議提前規劃大修")
        elif isinstance(rul_days, int | float) and rul_days < 180:
            recs.append(f"- ⚠️ 預測 RUL {rul_days:.0f} 天，建議備妥備品")

    if not recs:
        recs.append("- 🟢 風機運行正常，建議維持目前維護排程")

    return recs
