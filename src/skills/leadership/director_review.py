"""總監審核技能 — 使用 LLM 對下級代理分析結果進行深層審核與最終判斷。

專案總監不再只是「通過/不通過」的橡皮圖章，
而是能真正理解分析內容、評估品質、提出改進建議的決策者。

審核維度：
1. 資料品質：清洗後的資料是否足夠支撐結論？
2. 分析方法：使用的模型是否適當？指標是否可靠？
3. 結論合理性：診斷結論是否符合物理機制？
4. 行動建議：維護建議是否具體、可行？
5. 風險評估：是否遺漏重要風險？
"""

from __future__ import annotations

import json
from typing import Any

from src.skills.base import BaseSkill, ProgressCallback, SkillInput, SkillOutput, SkillStatus
from src.utils.logger import get_logger

logger = get_logger("skill.director_review")

REVIEW_SYSTEM_PROMPT = """你是 WindAI Lab 的專案總監，負責審核風力發電分析團隊的工作成果。
你有 15 年以上的風電運維與資料分析管理經驗。

## 審核維度

1. **資料品質** (0-100)：資料完整度、清洗品質、取樣頻率是否足夠
2. **分析方法** (0-100)：模型選擇、參數設定、驗證方法是否適當
3. **結論可信度** (0-100)：結論是否有充分數據支撐、是否符合物理機制
4. **行動可行性** (0-100)：維護建議是否具體、可操作、有時程
5. **風險覆蓋度** (0-100)：是否遺漏重要風險或潛在問題

## 輸出格式

請以 JSON 格式回覆：

```json
{
  "overall_verdict": "approved / conditional / rejected",
  "overall_score": 85,
  "dimension_scores": {
    "data_quality": 90,
    "analysis_method": 85,
    "conclusion_reliability": 80,
    "action_feasibility": 75,
    "risk_coverage": 70
  },
  "executive_summary": "一段話概述審核結論（繁體中文）",
  "strengths": ["優點1", "優點2"],
  "concerns": ["問題1", "問題2"],
  "required_actions": ["需補充或修正的事項（若有）"],
  "risk_notes": ["需特別注意的風險"],
  "final_recommendation": "最終建議（繁體中文，2-3 句）"
}
```

## 審核原則

- 不接受沒有數據支撐的結論
- R² < 0.7 的模型需要質疑
- 健康分數低於 60 的風機必須有明確的維護時程
- 嚴重度為 High/Critical 時，不能只說「建議觀察」
- 即使分析結果看起來正常，也要檢查是否有被遺漏的信號"""


class DirectorReviewSkill(BaseSkill):
    """總監 LLM 審核技能 — 對分析結果進行深層審核。"""

    skill_id = "director_review"
    display_name = "總監智慧審核"
    description = "使用 LLM 對下級代理的分析結果進行品質審核與最終判斷"
    version = "1.0.0"

    async def execute(
        self,
        inp: SkillInput,
        progress_cb: ProgressCallback = None,
    ) -> SkillOutput:
        """執行 LLM 審核。

        Parameters (inp.parameters):
            task_name: str — 被審核的任務名稱
            turbine_id: str — 風機 ID（選用）

        inp.context:
            上游步驟的所有結果（由 SkillComposingAgent 自動傳入）
        """
        task_name = inp.parameters.get("task_name", "分析任務")
        turbine_id = inp.parameters.get("turbine_id", "")

        if progress_cb:
            await progress_cb(0.1, "彙整上游分析結果...")

        # 從 context 收集所有上游結果
        upstream_results = inp.context or {}
        review_prompt = self._build_review_prompt(task_name, turbine_id, upstream_results)

        if progress_cb:
            await progress_cb(0.3, "啟動 LLM 審核引擎...")

        # 嘗試呼叫 LLM
        try:
            from src.services.llm_service import LLMService

            llm = LLMService()
            raw_response = llm.generate(
                prompt=review_prompt,
                system_instruction=REVIEW_SYSTEM_PROMPT,
                temperature=0.2,
                max_tokens=3072,
            )

            if progress_cb:
                await progress_cb(0.8, "解析審核結果...")

            result = self._parse_review_response(raw_response)
            verdict = result.get("overall_verdict", "approved")
            score = result.get("overall_score", 0)

            if progress_cb:
                await progress_cb(1.0, f"審核完成 — {verdict} ({score}/100)")

            return SkillOutput(
                status=SkillStatus.SUCCESS,
                data=result,
                summary=(
                    f"總監審核：{verdict.upper()} ({score}/100) — "
                    f"{result.get('executive_summary', '審核完成')}"
                ),
            )

        except Exception as e:
            logger.warning(f"LLM 審核失敗，改用規則式審核：{e}")
            if progress_cb:
                await progress_cb(0.5, "LLM 不可用，改用規則式審核...")

            result = self._rule_based_review(task_name, turbine_id, upstream_results)

            if progress_cb:
                await progress_cb(1.0, "規則式審核完成")

            return SkillOutput(
                status=SkillStatus.SUCCESS,
                data=result,
                summary=(
                    f"總監審核（規則式）：{result['overall_verdict'].upper()} "
                    f"({result['overall_score']}/100)"
                ),
            )

    def _build_review_prompt(
        self,
        task_name: str,
        turbine_id: str,
        upstream_results: dict[str, Any],
    ) -> str:
        """組裝審核 prompt。"""
        parts: list[str] = [
            f"## 審核任務：{task_name}",
            f"**風機 ID**：{turbine_id or '未指定'}",
            "",
            "## 上游代理提交的分析結果",
            "",
        ]

        for skill_id, result in upstream_results.items():
            if not isinstance(result, dict):
                continue
            status = result.get("status", "unknown")
            summary = result.get("summary", "")
            data = result.get("data", {})

            parts.append(f"### {skill_id} ({status})")
            if summary:
                parts.append(f"摘要：{summary}")
            if data:
                # 只取關鍵指標，避免 prompt 太長
                key_metrics = {
                    k: v
                    for k, v in data.items()
                    if isinstance(v, (int, float, str, bool)) and k != "raw_llm_response"
                }
                if key_metrics:
                    parts.append(f"關鍵指標：{json.dumps(key_metrics, ensure_ascii=False)}")
            parts.append("")

        parts.extend([
            "---",
            "請根據以上分析結果進行全面審核，給出最終判斷。",
            "以 JSON 格式回覆。",
        ])

        return "\n".join(parts)

    def _parse_review_response(self, raw: str) -> dict[str, Any]:
        """解析 LLM 回覆。"""
        import re

        try:
            cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1:
                cleaned = cleaned[start : end + 1]
            return json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            logger.warning("LLM 審核回覆解析失敗")
            return {
                "overall_verdict": "conditional",
                "overall_score": 60,
                "executive_summary": "LLM 回覆解析失敗，建議人工審核",
                "raw_text": raw[:2000],
            }

    def _rule_based_review(
        self,
        task_name: str,
        turbine_id: str,
        upstream_results: dict[str, Any],
    ) -> dict[str, Any]:
        """規則式審核（LLM 不可用時的 fallback）。"""
        scores: dict[str, float] = {
            "data_quality": 70,
            "analysis_method": 70,
            "conclusion_reliability": 70,
            "action_feasibility": 70,
            "risk_coverage": 60,
        }
        concerns: list[str] = []
        strengths: list[str] = []

        # 檢查各上游結果
        for skill_id, result in upstream_results.items():
            if not isinstance(result, dict):
                continue
            data = result.get("data", {})
            status = result.get("status", "")

            if status == "error":
                concerns.append(f"{skill_id} 執行失敗")
                scores["analysis_method"] -= 15

            # R² 檢查
            r2 = self._find_metric(data, "r2_score")
            if r2 is not None:
                if r2 >= 0.85:
                    strengths.append(f"模型 R² = {r2:.4f}，品質優良")
                    scores["analysis_method"] += 10
                elif r2 < 0.7:
                    concerns.append(f"模型 R² = {r2:.4f}，低於 0.7 門檻")
                    scores["conclusion_reliability"] -= 15

            # 健康分數檢查
            health = self._find_metric(data, "health_score")
            if health is not None:
                if health < 60:
                    concerns.append(f"健康分數 {health}/100，需立即關注")
                    scores["risk_coverage"] += 10  # 有偵測到風險是好事
                elif health >= 80:
                    strengths.append(f"健康分數 {health}/100，狀態良好")

            # F1 檢查
            f1 = self._find_metric(data, "f1_macro")
            if f1 is not None:
                if f1 >= 0.7:
                    strengths.append(f"故障分類 F1 = {f1:.4f}")
                elif f1 < 0.5:
                    concerns.append(f"故障分類 F1 = {f1:.4f}，可信度不足")
                    scores["conclusion_reliability"] -= 10

        # 計算總分
        overall_score = int(sum(scores.values()) / len(scores))
        overall_score = max(0, min(100, overall_score))

        if overall_score >= 75 and not any("失敗" in c for c in concerns):
            verdict = "approved"
        elif overall_score >= 50:
            verdict = "conditional"
        else:
            verdict = "rejected"

        return {
            "overall_verdict": verdict,
            "overall_score": overall_score,
            "dimension_scores": {k: max(0, min(100, int(v))) for k, v in scores.items()},
            "executive_summary": (
                f"{task_name} 審核{'通過' if verdict == 'approved' else '有條件通過' if verdict == 'conditional' else '未通過'}，"
                f"綜合評分 {overall_score}/100"
            ),
            "strengths": strengths or ["分析流程完整"],
            "concerns": concerns or ["無重大問題"],
            "required_actions": (
                [c for c in concerns if "失敗" in c or "不足" in c] or ["無"]
            ),
            "risk_notes": [c for c in concerns if "健康" in c or "立即" in c] or ["無特別風險"],
            "final_recommendation": (
                f"{'建議執行維護建議' if verdict == 'approved' else '建議補充分析後重新審核' if verdict == 'conditional' else '建議重新執行分析'}"
            ),
            "mode": "rule_based",
        }

    @staticmethod
    def _find_metric(data: Any, key: str) -> float | None:
        """在巢狀 dict 中搜索指標。"""
        if isinstance(data, dict):
            if key in data and isinstance(data[key], (int, float)):
                return float(data[key])
            for v in data.values():
                found = DirectorReviewSkill._find_metric(v, key)
                if found is not None:
                    return found
        return None
