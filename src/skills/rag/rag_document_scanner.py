"""RAG 文件掃描技能 — 掃描資料夾中所有支援格式文件。

掃描結果供 RagIngestSkill 使用，不執行嵌入。
"""

from __future__ import annotations

from pathlib import Path

from src.services.rag_service import RAGService
from src.skills.base import BaseSkill, ProgressCallback, SkillInput, SkillOutput, SkillStatus


class RagDocumentScannerSkill(BaseSkill):
    """掃描資料夾中所有支援格式（PDF/TXT/MD）的文件。"""

    skill_id = "rag_document_scanner"
    display_name = "RAG 文件掃描器"
    description = "掃描資料夾中所有支援格式文件（PDF/TXT/MD）並回傳清單"
    version = "1.0.0"

    async def execute(
        self,
        inp: SkillInput,
        progress_cb: ProgressCallback = None,
    ) -> SkillOutput:
        """掃描資料夾。

        Parameters (inp.parameters):
            folder_path: str — 要掃描的資料夾路徑
        """
        folder_path = inp.parameters.get("folder_path", "")
        if not folder_path:
            return SkillOutput(
                status=SkillStatus.ERROR,
                errors=["未指定 folder_path"],
            )

        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            return SkillOutput(
                status=SkillStatus.ERROR,
                errors=[f"資料夾不存在：{folder_path}"],
            )

        if progress_cb:
            await progress_cb(0.1, f"掃描資料夾：{folder_path}")

        supported = RAGService.SUPPORTED_EXTENSIONS
        files: list[dict[str, str]] = []
        type_counts: dict[str, int] = {}

        for f in sorted(folder.rglob("*")):
            if f.is_file() and f.suffix.lower() in supported and not f.name.startswith("."):
                ftype = f.suffix.lstrip(".").lower()
                files.append({"path": str(f), "name": f.name, "type": ftype})
                type_counts[ftype] = type_counts.get(ftype, 0) + 1

        if progress_cb:
            await progress_cb(1.0, f"掃描完成：{len(files)} 份文件")

        type_summary = ", ".join(f"{t.upper()} {n} 份" for t, n in type_counts.items())
        return SkillOutput(
            status=SkillStatus.SUCCESS,
            data={
                "files": files,
                "total": len(files),
                "folder": folder_path,
                "type_counts": type_counts,
            },
            summary=f"掃描完成：發現 {len(files)} 份文件（{type_summary or '無'}）",
        )
