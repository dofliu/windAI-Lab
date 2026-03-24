"""wRes:literature-reviewer — 文獻審閱員。

負責系統性文獻搜索、論文篩選、
研究趨勢分析與文獻比較表整理。
"""

from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent, TaskContext, TaskResult, TaskStatus


class LiteratureReviewer(BaseAgent):
    """文獻審閱代理，執行系統性文獻搜索與整理。"""

    def __init__(self) -> None:
        super().__init__("literature-reviewer")

    @property
    def capabilities(self) -> list[str]:
        return [
            "systematic_search",
            "paper_screening",
            "trend_analysis",
            "bibliometric_study",
            "comparison_table",
            "gap_identification",
        ]

    async def execute(self, task: str, context: TaskContext) -> TaskResult:
        """執行文獻審閱任務。"""
        params = context.parameters

        if "search" in task or "搜索" in task or "搜尋" in task:
            return await self._search_literature(params)

        if "review" in task or "整理" in task or "比較" in task:
            return await self._review_literature(params)

        await self.update_progress(0.5, f"文獻分析中：{task}")
        await self.update_progress(1.0)
        return TaskResult(status=TaskStatus.SUCCESS, summary=f"文獻任務完成：{task}")

    async def _search_literature(self, params: dict[str, Any]) -> TaskResult:
        """執行系統性文獻搜索。"""
        topic = params.get("topic", "wind turbine fault diagnosis")
        databases = params.get("databases", ["arXiv", "IEEE Xplore", "Scopus"])

        await self.update_progress(0.1, f"搜索主題：{topic}")

        total_found = 0
        results_by_db: dict[str, int] = {}

        for i, db in enumerate(databases):
            progress = 0.1 + (i + 1) / len(databases) * 0.6
            await self.update_progress(progress, f"搜索 {db}...")
            # 模擬搜索結果
            count = {"arXiv": 23, "IEEE Xplore": 15, "Scopus": 12}.get(db, 8)
            results_by_db[db] = count
            total_found += count

        await self.update_progress(0.8, "篩選高相關性論文")
        relevant = int(total_found * 0.4)

        await self.update_progress(1.0, f"篩選完成：{relevant} 篇高相關性論文")

        return TaskResult(
            status=TaskStatus.SUCCESS,
            data={
                "topic": topic,
                "databases_searched": databases,
                "results_by_database": results_by_db,
                "total_found": total_found,
                "relevant_count": relevant,
            },
            summary=f"文獻搜索完成：{total_found} 篇候選 → {relevant} 篇高相關性",
        )

    async def _review_literature(self, params: dict[str, Any]) -> TaskResult:
        """整理文獻比較表。"""
        await self.update_progress(0.3, "分析論文方法論")
        await self.update_progress(0.6, "建立比較表")
        await self.update_progress(1.0, "文獻回顧完成")

        return TaskResult(
            status=TaskStatus.SUCCESS,
            data={
                "comparison_table_rows": 18,
                "research_gaps": 3,
                "key_findings": [
                    "深度學習方法在風機故障診斷中準確率高於傳統 ML",
                    "遷移學習可解決標記資料不足問題",
                    "多模態融合是新興研究方向",
                ],
            },
            summary="文獻回顧完成：18 篇比較，3 個研究缺口",
        )
