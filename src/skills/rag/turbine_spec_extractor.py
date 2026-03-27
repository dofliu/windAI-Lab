"""風機規格萃取技能 — 從 RAG 知識庫查詢並以 LLM 萃取結構化規格。

查詢 RAG 中的風機相關文件，萃取出額定功率、切入/切出風速等關鍵規格。
"""

from __future__ import annotations

import asyncio
from typing import Any

from src.skills.base import BaseSkill, ProgressCallback, SkillInput, SkillOutput, SkillStatus


class TurbineSpecExtractorSkill(BaseSkill):
    """從 RAG 知識庫中查詢並萃取結構化風機規格。"""

    skill_id = "turbine_spec_extractor"
    display_name = "風機規格萃取器"
    description = "從 RAG 知識庫中查詢並以 LLM 萃取結構化風機規格"
    version = "1.0.0"

    async def execute(
        self,
        inp: SkillInput,
        progress_cb: ProgressCallback = None,
    ) -> SkillOutput:
        """萃取風機規格。

        Parameters (inp.parameters):
            turbine_hint: str — 風機型號或名稱提示（可選）
        """
        turbine_hint = inp.parameters.get("turbine_hint", "")

        if progress_cb:
            await progress_cb(0.1, f"查詢 RAG 知識庫：{turbine_hint or '風機規格'}")

        loop = asyncio.get_event_loop()

        # Step 1: 語意搜尋
        from src.services.rag_service import RAGService

        rag = RAGService()
        query = f"風機規格 額定功率 切入風速 切出風速 轉子直徑 {turbine_hint}".strip()

        try:
            results = await loop.run_in_executor(
                None, lambda: rag.search(query=query, n_results=5)
            )
        except Exception as e:
            return SkillOutput(
                status=SkillStatus.PARTIAL,
                data={"turbine_specs": {}},
                summary=f"RAG 查詢失敗：{e}",
            )

        if not results:
            if progress_cb:
                await progress_cb(1.0, "知識庫尚無相關文件")
            return SkillOutput(
                status=SkillStatus.PARTIAL,
                data={"turbine_specs": {}},
                summary="知識庫尚無文件，規格萃取跳過",
            )

        if progress_cb:
            await progress_cb(0.5, f"找到 {len(results)} 筆相關文件，LLM 萃取中...")

        # Step 2: 組裝 context
        contexts = [
            {
                "content": r.content,
                "source": r.metadata.get("source", "未知"),
                "relevance": r.relevance_score,
            }
            for r in results
        ]

        # Step 3: LLM 萃取
        from src.services.llm_service import LLMService

        llm = LLMService()
        try:
            specs = await loop.run_in_executor(
                None, lambda: llm.extract_turbine_specs(contexts, turbine_hint)
            )
        except Exception as e:
            return SkillOutput(
                status=SkillStatus.PARTIAL,
                data={"turbine_specs": {}},
                summary=f"LLM 規格萃取失敗：{e}",
            )

        if progress_cb:
            await progress_cb(1.0, "規格萃取完成")

        # 組裝摘要
        summary_parts: list[str] = []
        if specs.get("turbine_model"):
            summary_parts.append(f"型號 {specs['turbine_model']}")
        if specs.get("rated_power_kw"):
            summary_parts.append(f"額定 {specs['rated_power_kw']} kW")
        if specs.get("cut_in_speed_ms"):
            summary_parts.append(f"切入 {specs['cut_in_speed_ms']} m/s")
        if specs.get("cut_out_speed_ms"):
            summary_parts.append(f"切出 {specs['cut_out_speed_ms']} m/s")

        return SkillOutput(
            status=SkillStatus.SUCCESS,
            data={
                "turbine_specs": specs,
                "sources_used": len(results),
            },
            summary=f"規格萃取完成：{', '.join(summary_parts) or '未找到明確規格'}",
        )
