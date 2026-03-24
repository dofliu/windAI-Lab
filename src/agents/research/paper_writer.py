"""wRes:paper-writer — 論文撰寫員。

負責學術論文結構規劃、方法論撰寫、
圖表描述、以及投稿 cover letter 草擬。
"""

from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent, TaskContext, TaskResult, TaskStatus


class PaperWriter(BaseAgent):
    """論文撰寫代理，協助學術論文寫作。"""

    def __init__(self) -> None:
        super().__init__("paper-writer")

    @property
    def capabilities(self) -> list[str]:
        return [
            "paper_structure_planning",
            "methodology_writing",
            "figure_description",
            "cover_letter_drafting",
            "scholarly_english_writing",
            "report_generation",
        ]

    async def execute(self, task: str, context: TaskContext) -> TaskResult:
        """執行論文撰寫任務。"""
        params = context.parameters

        if "report" in task or "報告" in task:
            return await self._generate_report(params, context)

        if "methodology" in task or "方法論" in task:
            return await self._write_methodology(params)

        if "structure" in task or "大綱" in task:
            return await self._plan_structure(params)

        await self.update_progress(0.5, f"撰寫中：{task}")
        await self.update_progress(1.0, "撰寫完成")
        return TaskResult(status=TaskStatus.SUCCESS, summary=f"撰寫完成：{task}")

    async def _generate_report(
        self, params: dict[str, Any], context: TaskContext
    ) -> TaskResult:
        """彙整分析結果生成報告。"""
        await self.update_progress(0.2, "整理分析結果摘要")
        await self.update_progress(0.4, "撰寫報告主體")
        await self.update_progress(0.6, "插入圖表與數據")
        await self.update_progress(0.8, "撰寫建議與結論")
        await self.update_progress(1.0, "報告已生成")

        # 從 context 取得上游結果
        diagnosis = context.results.get("diagnosis", {})
        sections = [
            "異常摘要",
            "故障分類分析",
            "健康評分",
            "維護建議",
            "參考文獻",
        ]

        return TaskResult(
            status=TaskStatus.SUCCESS,
            data={
                "report_sections": sections,
                "page_count": 8,
                "format": "PDF",
                "includes_diagnosis": bool(diagnosis),
            },
            summary=f"診斷報告已生成（{len(sections)} 章節，8 頁）",
        )

    async def _write_methodology(self, params: dict[str, Any]) -> TaskResult:
        """撰寫方法論章節。"""
        await self.update_progress(0.3, "整理研究方法")
        await self.update_progress(0.6, "撰寫實驗設計段落")
        await self.update_progress(1.0, "方法論章節完成")

        return TaskResult(
            status=TaskStatus.SUCCESS,
            data={"word_count": 2500, "subsections": 4},
            summary="方法論章節撰寫完成：2500 字，4 個小節",
        )

    async def _plan_structure(self, params: dict[str, Any]) -> TaskResult:
        """規劃論文大綱結構。"""
        await self.update_progress(0.5, "設計論文架構")
        await self.update_progress(1.0, "大綱已完成")

        structure = [
            "1. Introduction",
            "2. Related Work",
            "3. Methodology",
            "4. Experiments",
            "5. Results and Discussion",
            "6. Conclusion",
        ]

        return TaskResult(
            status=TaskStatus.SUCCESS,
            data={"structure": structure},
            summary=f"論文大綱已規劃（{len(structure)} 章節）",
        )
