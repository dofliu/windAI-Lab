"""RAG 知識庫嵌入技能 — 分塊並嵌入文件至 ChromaDB。

接收 RagDocumentScannerSkill 的掃描結果，或直接指定資料夾路徑。
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from src.services.rag_service import RAGService
from src.skills.base import BaseSkill, ProgressCallback, SkillInput, SkillOutput, SkillStatus


class RagIngestSkill(BaseSkill):
    """分塊並嵌入文件至 ChromaDB 知識庫。"""

    skill_id = "rag_ingest"
    display_name = "RAG 知識庫嵌入器"
    description = "分塊並嵌入文件至 ChromaDB 知識庫（支援 PDF/TXT/MD）"
    version = "1.0.0"

    async def execute(
        self,
        inp: SkillInput,
        progress_cb: ProgressCallback = None,
    ) -> SkillOutput:
        """嵌入文件至知識庫。

        Parameters (inp.parameters):
            folder_path: str | None — 資料夾路徑（若無 files 清單時使用）
            collection_name: str | None — 目標集合名稱
            chunk_size: int — chunk 大小（預設 1000）
            chunk_overlap: int — chunk 重疊（預設 200）

        Context (inp.context):
            data.files: list[dict] — 來自 RagDocumentScannerSkill 的檔案清單
        """
        # 取得檔案清單：優先從 context（上游掃描器），其次從 parameters
        files: list[dict[str, Any]] | None = None
        if inp.context:
            upstream_data = inp.context.get("data", {})
            files = upstream_data.get("files")

        if not files:
            files = inp.parameters.get("files")

        folder_path = inp.parameters.get("folder_path", "")
        collection = inp.parameters.get("collection_name")
        chunk_size = inp.parameters.get("chunk_size", 1000)
        chunk_overlap = inp.parameters.get("chunk_overlap", 200)

        # 若仍無 files，嘗試直接用 folder 匯入
        if not files and folder_path:
            return await self._ingest_via_folder(
                folder_path, collection, chunk_size, chunk_overlap, progress_cb
            )

        if not files:
            return SkillOutput(
                status=SkillStatus.ERROR,
                errors=["未提供檔案清單或資料夾路徑"],
            )

        if progress_cb:
            await progress_cb(0.05, f"準備嵌入 {len(files)} 份文件...")

        loop = asyncio.get_event_loop()
        rag = RAGService()

        total = len(files)
        ingested = 0
        chunks_added = 0
        errors: list[str] = []
        step = max(1, total // 20)

        for i, f in enumerate(files):
            path_str = f["path"] if isinstance(f, dict) else str(f)
            try:
                result = await loop.run_in_executor(
                    None,
                    lambda p=path_str: rag.ingest_file(
                        p,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                        collection_name=collection,
                    ),
                )
                ingested += 1
                chunks_added += result.get("added", 0)
            except Exception as e:
                errors.append(f"{Path(path_str).name}: {e}")

            if progress_cb and (i + 1) % step == 0:
                pct = 0.05 + 0.9 * (i + 1) / total
                await progress_cb(pct, f"已嵌入 {ingested}/{total} 份文件...")

        if progress_cb:
            await progress_cb(1.0, "嵌入完成")

        stats = rag.get_collection_stats(collection)
        return SkillOutput(
            status=SkillStatus.SUCCESS if not errors else SkillStatus.PARTIAL,
            data={
                "ingested": ingested,
                "total": total,
                "chunks_added": chunks_added,
                "errors_count": len(errors),
                "collection": stats.get("name", ""),
                "total_in_collection": stats.get("count", 0),
            },
            summary=(
                f"嵌入完成：{ingested}/{total} 份文件, "
                f"{chunks_added} 個 chunks, "
                f"知識庫共 {stats.get('count', 0)} 筆"
            ),
            errors=errors,
        )

    async def _ingest_via_folder(
        self,
        folder_path: str,
        collection: str | None,
        chunk_size: int,
        chunk_overlap: int,
        progress_cb: ProgressCallback,
    ) -> SkillOutput:
        """直接透過 RAGService.ingest_folder 匯入（無上游掃描器時的備援路徑）。"""
        if progress_cb:
            await progress_cb(0.05, f"直接匯入資料夾：{folder_path}")

        loop = asyncio.get_event_loop()
        rag = RAGService()

        try:
            result = await loop.run_in_executor(
                None,
                lambda: rag.ingest_folder(
                    folder_path,
                    collection_name=collection,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                ),
            )
        except Exception as e:
            return SkillOutput(
                status=SkillStatus.ERROR,
                errors=[f"資料夾匯入失敗：{e}"],
            )

        if progress_cb:
            await progress_cb(1.0, "嵌入完成")

        return SkillOutput(
            status=SkillStatus.SUCCESS if not result.get("errors") else SkillStatus.PARTIAL,
            data=result,
            summary=(
                f"嵌入完成：{result.get('ingested', 0)}/{result.get('total', 0)} 份文件, "
                f"知識庫共 {result.get('total_in_collection', 0)} 筆"
            ),
            errors=result.get("errors", []),
        )
