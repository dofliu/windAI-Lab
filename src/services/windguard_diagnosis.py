"""WindGuard AI 診斷推理服務。

整合統計異常偵測與 LLM 推理能力，實現完整的風機故障診斷流程：
1. 統計/ML 分析產出結構化診斷報告
2. LLM 接收報告，進行深層推理（故障類型、物理機制、嚴重度）
3. LLM 自主呼叫工具（Agentic Function Calling）進行跨風機調查
4. 產出工程級故障診斷結論與維護建議

靈感來源：Kaggle WindGuard AI 專案（Gemma 4 + CARE Dataset）。
"""

from __future__ import annotations

import json
import re
from typing import Any

from src.utils.logger import get_logger

logger = get_logger("service.windguard")

# ── 診斷工具定義（供 LLM Agentic Calling 使用）────────────────

DIAGNOSTIC_TOOLS: list[dict[str, Any]] = [
    {
        "name": "detect_anomalies",
        "description": "對指定風機執行多信號異常偵測（Z-score + IQR），回傳 anomaly rate 與異常信號摘要。",
        "parameters": {
            "turbine_id": "風機 ID 或資料集名稱",
        },
    },
    {
        "name": "run_power_curve_analysis",
        "description": "執行功率曲線 NBM 分析，偵測功率偏差與效率損失。",
        "parameters": {
            "turbine_id": "風機 ID",
        },
    },
    {
        "name": "classify_faults",
        "description": "執行 ML 多標籤故障分類（RandomForest），回傳故障類型與置信度。",
        "parameters": {
            "turbine_id": "風機 ID",
        },
    },
    {
        "name": "get_turbine_health_score",
        "description": "計算風機綜合健康分數（0-100），含資料完整度、功率曲線、溫度穩定度、可用率。",
        "parameters": {
            "turbine_id": "風機 ID",
        },
    },
    {
        "name": "compare_turbines",
        "description": "比較多台風機的健康狀態，回傳排序後的風險清單。",
        "parameters": {
            "turbine_ids": "風機 ID 列表（逗號分隔）",
        },
    },
]

# ── LLM 系統提示（風機故障診斷專家）────────────────────────────

DIAGNOSIS_SYSTEM_PROMPT = """你是一位擁有 20 年經驗的風力發電 O&M 工程師和故障診斷專家。
你的任務是根據 SCADA 資料分析結果，進行深層故障推理。

## 你的專業能力

1. **故障模式識別**：從統計異常模式推斷具體故障類型
   - Generator bearing failure（發電機軸承故障）
   - Gearbox failure（齒輪箱故障）
   - Pitch system defect（變槳系統缺陷）
   - Yaw system malfunction（偏航系統故障）
   - Converter/electrical failure（變流器/電氣故障）
   - Blade damage/icing（葉片損傷/結冰）
   - Hydraulic system failure（液壓系統故障）
   - Communication fault（通訊故障）

2. **物理推理**：從感測器信號推導物理機制
   - 溫度飆升 → 摩擦增加 → 軸承磨損
   - 功率偏差 → 氣動效率下降 → 葉片問題或偏航偏移
   - 多信號同時異常 → 系統級故障

3. **嚴重度評估**：
   - Low：可排入下次定期維護
   - Medium：建議 1-2 週內安排檢修
   - High：建議 48 小時內安排檢修
   - Critical：建議立即停機檢修

## 輸出格式

請以結構化 JSON 格式回覆，包含以下欄位：

```json
{
  "fault_type": "具體故障類型（英文）",
  "fault_type_zh": "故障類型（繁體中文）",
  "severity": "Low / Medium / High / Critical",
  "confidence": 0.0-1.0,
  "reasoning_chain": [
    "推理步驟 1：從數據觀察到...",
    "推理步驟 2：這表示...",
    "推理步驟 3：結合物理機制..."
  ],
  "physical_mechanism": "故障的物理機制說明",
  "maintenance_actions": [
    {"action": "具體維護行動", "priority": "immediate/scheduled/monitoring", "estimated_downtime_hours": 8}
  ],
  "risk_if_ignored": "若不處理的潛在後果",
  "similar_cases": "已知的類似故障案例參考"
}
```

## 重要原則

- 不要只說「有異常」，要推理出**具體是什麼故障**
- 展示完整的推理鏈：數據模式 → 物理機制 → 故障類型 → 嚴重度 → 行動建議
- 如果感測器名稱是匿名的（如 sensor_45），根據數據特徵推理其可能對應的物理量
- 誠實面對不確定性，用置信度表達
- 使用繁體中文說明推理過程"""


FLEET_ANALYSIS_SYSTEM_PROMPT = """你是一位風電場運維總監，負責管理整個風場的維護優先順序。

你有以下工具可以使用：
{tools_description}

## 工具呼叫格式

當你需要調查某台風機時，請用以下格式呼叫工具：
TOOL_CALL: tool_name(param1="value1", param2="value2")

你可以連續呼叫多個工具。每次呼叫後，系統會回傳結果，你再根據結果做下一步決策。

## 任務

根據工具回傳的數據，綜合考量以下因素排出維護優先順序：
1. anomaly rate（異常率）
2. 故障類型的危險程度（間歇性故障 > 穩定退化）
3. 對發電量的影響（功率損失百分比）
4. 二次損害風險（軸承故障可能導致齒輪箱連帶損毀）

最終回覆格式：
```json
{
  "fleet_risk_ranking": [
    {"turbine_id": "...", "risk_level": "Critical/High/Medium/Low", "anomaly_rate": 0.0, "primary_concern": "...", "recommended_action": "..."}
  ],
  "maintenance_schedule": "建議的維護排程",
  "resource_allocation": "維護資源分配建議"
}
```"""


class WindGuardDiagnosis:
    """WindGuard AI 診斷推理引擎。

    將統計/ML 診斷結果送入 LLM 進行深層推理，產出工程級故障診斷。
    """

    def __init__(self, model_name: str = "gemini-3-flash-preview") -> None:
        self._model_name = model_name
        self._llm: Any = None

    @property
    def llm(self) -> Any:
        """延遲載入 LLM 服務。"""
        if self._llm is None:
            from src.services.llm_service import LLMService

            self._llm = LLMService(model_name=self._model_name)
        return self._llm

    def reason_about_diagnosis(
        self,
        diagnosis_report: dict[str, Any],
        rag_contexts: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """對統計/ML 診斷報告進行 LLM 深層推理。

        Args:
            diagnosis_report: generate_diagnosis_report() 或 run_full_diagnosis() 的輸出。
            rag_contexts: RAG 檢索到的相關維修案例（選用）。

        Returns:
            LLM 推理後的結構化故障診斷結果。
        """
        prompt = self._build_diagnosis_prompt(diagnosis_report, rag_contexts)

        logger.info(
            f"開始 LLM 診斷推理 — 風機：{diagnosis_report.get('turbine_id', '未知')}"
        )

        raw_response = self.llm.generate(
            prompt=prompt,
            system_instruction=DIAGNOSIS_SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=4096,
        )

        result = self._parse_llm_response(raw_response)
        result["turbine_id"] = diagnosis_report.get("turbine_id", "未知")
        result["health_score"] = diagnosis_report.get("health_score", 0)
        result["raw_llm_response"] = raw_response
        result["statistical_report"] = diagnosis_report

        logger.info(
            f"LLM 診斷完成 — 故障類型：{result.get('fault_type', '未判定')}, "
            f"嚴重度：{result.get('severity', '未判定')}"
        )

        return result

    def _build_diagnosis_prompt(
        self,
        report: dict[str, Any],
        rag_contexts: list[dict[str, Any]] | None = None,
    ) -> str:
        """組裝 LLM 診斷推理的 prompt。"""
        turbine_id = report.get("turbine_id", "未知")
        health_score = report.get("health_score", 0)
        total_records = report.get("total_records", 0)
        period = report.get("analysis_period", {})

        # 溫度異常摘要
        temp_anomalies = report.get("temperature_anomalies", [])
        temp_count = report.get("temperature_anomaly_count", 0)
        components_checked = report.get("temperature_components_checked", [])

        # 功率曲線分析
        pc = report.get("power_curve_analysis", {})

        # 運行概況
        ops = report.get("operational_summary", {})

        # ML 分類結果（如有）
        ml = report.get("ml_fault_classification", {})

        # NBM 分析結果（如有）
        nbm = report.get("nbm_analysis", {})

        # 健康分數細項
        health_details = report.get("health_details", {})

        # 現有警告與建議
        warnings = report.get("warnings", [])
        recommendations = report.get("recommendations", [])

        prompt_parts: list[str] = [
            f"## 風機 SCADA 數據分析報告\n",
            f"- **風機 ID**：{turbine_id}",
            f"- **分析期間**：{period.get('start', 'N/A')} ~ {period.get('end', 'N/A')}",
            f"- **總記錄數**：{total_records:,} 筆（10 分鐘間隔）",
            f"- **健康分數**：{health_score}/100",
            "",
            "### 健康分數細項",
            f"- 資料完整度：{health_details.get('data_completeness_score', 'N/A')}/100",
            f"- 功率曲線符合度：{health_details.get('power_curve_score', 'N/A')}/100",
            f"- 溫度穩定度：{health_details.get('temperature_score', 'N/A')}/100",
            f"- 可用率：{health_details.get('availability_score', 'N/A')}/100",
            "",
            "### 溫度異常偵測",
            f"- 已檢查元件：{', '.join(components_checked) if components_checked else '無'}",
            f"- 異常事件數：{temp_count}",
        ]

        if temp_anomalies:
            prompt_parts.append("- 最嚴重的異常事件：")
            sorted_anomalies = sorted(
                temp_anomalies, key=lambda x: abs(x.get("deviation", 0)), reverse=True
            )
            for a in sorted_anomalies[:5]:
                prompt_parts.append(
                    f"  - {a.get('component', '?')}：實際 {a.get('actual_temp', '?')}°C, "
                    f"預期 {a.get('expected_temp', '?')}°C, "
                    f"偏差 {a.get('deviation', '?')}σ"
                )

        prompt_parts.extend([
            "",
            "### 功率曲線分析",
            f"- 平均偏差：{pc.get('mean_deviation_pct', 'N/A')}%",
            f"- 最嚴重風速區間：{pc.get('worst_wind_speed_bin', 'N/A')}",
            f"- 估算效率損失：{pc.get('efficiency_loss_pct', 'N/A')}%",
            "",
            "### 運行概況",
            f"- 運行小時：{ops.get('operating_hours', 'N/A')} 小時",
            f"- 可用率：{ops.get('availability', 'N/A')}%",
            f"- 容量因數：{ops.get('capacity_factor', 'N/A')}%",
        ])

        if ml:
            prompt_parts.extend([
                "",
                "### ML 故障分類結果",
                f"- 模型 F1 macro：{ml.get('model_f1_macro', 'N/A')}",
                f"- 故障比例：{json.dumps(ml.get('fault_ratios', {}), ensure_ascii=False)}",
                f"- 嚴重度分布：{json.dumps(ml.get('severity_distribution', {}), ensure_ascii=False)}",
            ])
            top_faults = ml.get("top_faults", [])
            if top_faults:
                prompt_parts.append("- 最嚴重故障事件：")
                for tf in top_faults[:5]:
                    prompt_parts.append(
                        f"  - {tf.get('timestamp', '?')}: "
                        f"{', '.join(tf.get('fault_names', []))} "
                        f"(置信度：{tf.get('max_probability', 'N/A')})"
                    )

        if nbm:
            prompt_parts.extend([
                "",
                "### NBM 功率曲線模型分析",
                f"- 模型 R²：{nbm.get('model_r2', 'N/A')}",
                f"- 模型 MAE：{nbm.get('model_mae', 'N/A')} kW",
                f"- 異常筆數：{nbm.get('anomaly_count', 'N/A')}",
                f"- 異常比率：{nbm.get('anomaly_ratio', 'N/A')}",
            ])

        if warnings:
            prompt_parts.extend(["", "### 系統警告"])
            for w in warnings:
                prompt_parts.append(f"- ⚠️ {w}")

        if recommendations:
            prompt_parts.extend(["", "### 初步建議（規則式）"])
            for r in recommendations:
                prompt_parts.append(f"- {r}")

        # RAG 補充資料
        if rag_contexts:
            prompt_parts.extend(["", "### 相關維修案例（來自知識庫）"])
            for i, ctx in enumerate(rag_contexts[:3], 1):
                source = ctx.get("source", "未知")
                content = ctx.get("content", "")[:500]
                prompt_parts.append(f"[案例 {i}] 來源：{source}\n{content}")

        prompt_parts.extend([
            "",
            "---",
            "",
            "請根據以上分析結果，以你的專業知識進行深層故障推理。",
            "特別注意：",
            "1. 從統計指標推斷最可能的具體故障類型",
            "2. 說明故障的物理機制",
            "3. 評估嚴重程度並給出置信度",
            "4. 提供具體、可行的維護行動建議",
            "",
            "請以 JSON 格式回覆。",
        ])

        return "\n".join(prompt_parts)

    def _parse_llm_response(self, raw: str) -> dict[str, Any]:
        """解析 LLM 回覆的 JSON 結果。"""
        try:
            cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1:
                cleaned = cleaned[start : end + 1]
            return json.loads(cleaned)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"LLM 回覆 JSON 解析失敗，回傳原始文字：{e}")
            return {
                "fault_type": "parse_error",
                "fault_type_zh": "解析失敗",
                "severity": "Unknown",
                "confidence": 0.0,
                "reasoning_chain": [raw[:2000]],
                "raw_text": raw,
            }

    # ── Agentic Function Calling ─────────────────────────────

    def agentic_investigate(
        self,
        task_description: str,
        available_turbine_ids: list[str],
        tool_executor: Any | None = None,
        max_rounds: int = 5,
    ) -> dict[str, Any]:
        """LLM 自主調查模式（Agentic Function Calling）。

        LLM 根據任務描述自行決定呼叫哪些診斷工具，
        系統執行工具並回傳結果，LLM 再根據結果做下一步決策。

        Args:
            task_description: 調查任務描述（例如「比較 WT-01 和 WT-02 的健康狀態」）。
            available_turbine_ids: 可調查的風機 ID 列表。
            tool_executor: 工具執行器，接受 (tool_name, params) 回傳 dict。
                若為 None，使用預設的內建工具執行器。
            max_rounds: 最大工具呼叫輪數。

        Returns:
            LLM 最終的調查結論。
        """
        if tool_executor is None:
            tool_executor = self._default_tool_executor

        tools_desc = "\n".join(
            f"- **{t['name']}**: {t['description']} 參數: {t['parameters']}"
            for t in DIAGNOSTIC_TOOLS
        )

        system = FLEET_ANALYSIS_SYSTEM_PROMPT.format(tools_description=tools_desc)

        conversation: list[str] = [
            f"## 任務\n{task_description}\n",
            f"## 可用風機\n{', '.join(available_turbine_ids)}\n",
            "請開始調查。你可以呼叫工具取得數據，也可以直接根據已知資訊做判斷。",
        ]

        all_tool_calls: list[dict[str, Any]] = []

        for round_num in range(max_rounds):
            prompt = "\n".join(conversation)
            response = self.llm.generate(
                prompt=prompt,
                system_instruction=system,
                temperature=0.2,
                max_tokens=4096,
            )

            # 檢查是否有工具呼叫
            tool_calls = self._extract_tool_calls(response)

            if not tool_calls:
                # 沒有工具呼叫 = LLM 已做出最終判斷
                logger.info(
                    f"Agentic 調查完成，共 {round_num + 1} 輪, "
                    f"{len(all_tool_calls)} 次工具呼叫"
                )
                result = self._parse_llm_response(response)
                result["investigation_rounds"] = round_num + 1
                result["tool_calls"] = all_tool_calls
                return result

            # 執行工具呼叫
            conversation.append(f"\n### LLM 回應（第 {round_num + 1} 輪）\n{response}")

            for tc in tool_calls:
                tool_name = tc["tool_name"]
                params = tc["params"]
                all_tool_calls.append(tc)

                logger.info(f"Agentic 工具呼叫：{tool_name}({params})")
                try:
                    tool_result = tool_executor(tool_name, params)
                    conversation.append(
                        f"\n### 工具結果：{tool_name}\n"
                        f"```json\n{json.dumps(tool_result, ensure_ascii=False, indent=2)}\n```"
                    )
                except Exception as e:
                    conversation.append(
                        f"\n### 工具執行失敗：{tool_name}\n錯誤：{str(e)}"
                    )

            conversation.append(
                "\n請根據工具結果繼續分析。若已有足夠資訊，請直接給出最終結論（JSON 格式）。"
            )

        # 超過最大輪數
        logger.warning(f"Agentic 調查達到最大輪數 ({max_rounds})")
        return {
            "fault_type": "investigation_incomplete",
            "severity": "Unknown",
            "tool_calls": all_tool_calls,
            "investigation_rounds": max_rounds,
            "note": f"調查未在 {max_rounds} 輪內完成",
        }

    def _extract_tool_calls(self, response: str) -> list[dict[str, Any]]:
        """從 LLM 回覆中提取工具呼叫。

        支援格式：TOOL_CALL: tool_name(param1="value1", param2="value2")
        """
        pattern = r'TOOL_CALL:\s*(\w+)\(([^)]*)\)'
        matches = re.findall(pattern, response)

        tool_calls: list[dict[str, Any]] = []
        for tool_name, params_str in matches:
            params: dict[str, str] = {}
            # 解析參數（支援 key="value" 和 key='value' 格式）
            param_pattern = r'(\w+)\s*=\s*["\']([^"\']*)["\']'
            for key, value in re.findall(param_pattern, params_str):
                params[key] = value

            tool_calls.append({"tool_name": tool_name, "params": params})

        return tool_calls

    def _default_tool_executor(
        self, tool_name: str, params: dict[str, str]
    ) -> dict[str, Any]:
        """預設工具執行器 — 呼叫 windAI-Lab 內建的診斷模組。"""
        turbine_id = params.get("turbine_id", "WT-01")

        if tool_name == "detect_anomalies":
            return self._exec_detect_anomalies(turbine_id)
        elif tool_name == "run_power_curve_analysis":
            return self._exec_power_curve(turbine_id)
        elif tool_name == "classify_faults":
            return self._exec_classify_faults(turbine_id)
        elif tool_name == "get_turbine_health_score":
            return self._exec_health_score(turbine_id)
        elif tool_name == "compare_turbines":
            ids = [
                t.strip()
                for t in params.get("turbine_ids", turbine_id).split(",")
            ]
            return self._exec_compare_turbines(ids)
        else:
            return {"error": f"未知工具：{tool_name}"}

    def _exec_detect_anomalies(self, turbine_id: str) -> dict[str, Any]:
        """執行異常偵測工具。"""
        try:
            from src.services.diagnosis_service import run_full_diagnosis
            from src.data_pipeline.ingestion.kelmarsh_loader import load_turbine_data

            df = load_turbine_data(turbine_id)
            report = run_full_diagnosis(df, turbine_id)

            temp_count = report.get("temperature_anomaly_count", 0)
            total = report.get("total_records", 1)
            anomaly_rate = round(temp_count / max(total, 1) * 100, 2)

            return {
                "turbine_id": turbine_id,
                "total_records": total,
                "anomaly_count": temp_count,
                "anomaly_rate_pct": anomaly_rate,
                "health_score": report.get("health_score", 0),
                "warnings": report.get("warnings", []),
            }
        except Exception as e:
            return {"turbine_id": turbine_id, "error": str(e)}

    def _exec_power_curve(self, turbine_id: str) -> dict[str, Any]:
        """執行功率曲線分析工具。"""
        try:
            from src.data_pipeline.ingestion.kelmarsh_loader import load_turbine_data
            from src.models.evaluation.anomaly_analysis import detect_power_curve_anomalies

            df = load_turbine_data(turbine_id)
            return detect_power_curve_anomalies(df)
        except Exception as e:
            return {"turbine_id": turbine_id, "error": str(e)}

    def _exec_classify_faults(self, turbine_id: str) -> dict[str, Any]:
        """執行故障分類工具。"""
        try:
            from src.data_pipeline.ingestion.kelmarsh_loader import load_turbine_data
            from src.data_pipeline.cleaning.scada_cleaner import clean_scada_data
            from src.features.domain_features.wind_features import (
                compute_power_curve_features,
                compute_temperature_features,
            )
            from src.models.classification.fault_classifier import (
                FaultClassifier,
                generate_fault_labels,
            )

            df = load_turbine_data(turbine_id)
            df_clean, _ = clean_scada_data(df)
            df_feat = compute_power_curve_features(df_clean)
            df_feat = compute_temperature_features(df_feat)

            labels = generate_fault_labels(df_feat)
            clf = FaultClassifier()
            clf.train(df_feat, labels)
            result = clf.classify(df_feat)

            return {
                "turbine_id": turbine_id,
                "fault_counts": result.fault_counts,
                "fault_ratios": result.fault_ratios,
                "severity_distribution": result.severity_distribution,
            }
        except Exception as e:
            return {"turbine_id": turbine_id, "error": str(e)}

    def _exec_health_score(self, turbine_id: str) -> dict[str, Any]:
        """計算健康分數工具。"""
        try:
            from src.data_pipeline.ingestion.kelmarsh_loader import load_turbine_data
            from src.models.evaluation.anomaly_analysis import compute_health_score

            df = load_turbine_data(turbine_id)
            return {"turbine_id": turbine_id, **compute_health_score(df)}
        except Exception as e:
            return {"turbine_id": turbine_id, "error": str(e)}

    def _exec_compare_turbines(self, turbine_ids: list[str]) -> dict[str, Any]:
        """比較多台風機工具。"""
        results: list[dict[str, Any]] = []
        for tid in turbine_ids:
            score = self._exec_health_score(tid)
            results.append(score)

        # 依健康分數排序（低分 = 高風險）
        results.sort(key=lambda x: x.get("health_score", 100))
        return {
            "comparison": results,
            "highest_risk": results[0] if results else {},
            "lowest_risk": results[-1] if results else {},
        }
