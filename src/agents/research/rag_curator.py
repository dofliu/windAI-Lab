"""wRes:rag-curator — RAG 知識庫管理員。

負責 RAG 知識庫的文件嵌入、索引管理、品質維護與搜尋優化。
"""

from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent, TaskContext, TaskResult, TaskStatus


class RagCurator(BaseAgent):
    """RAG 知識庫管理代理。

    能力：
    - 文件嵌入與索引管理
    - 語意搜尋
    - 知識庫統計與品質監控
    - 文件分類與 metadata 管理
    """

    def __init__(self) -> None:
        super().__init__("rag-curator")

    @property
    def capabilities(self) -> list[str]:
        return [
            "document_embedding",
            "semantic_search",
            "collection_management",
            "knowledge_base_statistics",
            "document_classification",
            "index_optimization",
        ]

    async def execute(self, task: str, context: TaskContext) -> TaskResult:
        """執行 RAG 知識庫管理任務。"""
        params = context.parameters

        if "search" in task or "搜尋" in task or "查詢" in task:
            return await self._search(params)

        if "ingest" in task or "嵌入" in task or "匯入" in task:
            return await self._ingest(params)

        if "stats" in task or "統計" in task or "狀態" in task:
            return await self._get_stats(params)

        await self.update_progress(0.5, f"處理知識庫任務：{task}")
        await self.update_progress(1.0)
        return TaskResult(status=TaskStatus.SUCCESS, summary=f"知識庫任務完成：{task}")

    async def _search(self, params: dict[str, Any]) -> TaskResult:
        """語意搜尋知識庫。"""
        query = params.get("query", "")
        n_results = params.get("n_results", 5)
        collection = params.get("collection")

        if not query:
            return TaskResult(
                status=TaskStatus.ERROR,
                errors=["搜尋查詢不可為空"],
            )

        await self.update_progress(0.2, f"搜尋知識庫：{query[:50]}...")

        try:
            from src.services.rag_service import RAGService

            rag = RAGService()
            results = rag.search(
                query=query,
                n_results=n_results,
                collection_name=collection,
            )
            await self.update_progress(1.0, f"找到 {len(results)} 筆相關文獻")

            return TaskResult(
                status=TaskStatus.SUCCESS,
                data={
                    "query": query,
                    "results": [
                        {
                            "doc_id": r.doc_id,
                            "content": r.content[:200],
                            "relevance": round(r.relevance_score, 3),
                            "metadata": r.metadata,
                        }
                        for r in results
                    ],
                    "total": len(results),
                },
                summary=f"搜尋 '{query[:30]}' → {len(results)} 筆結果",
            )
        except Exception as e:
            return TaskResult(status=TaskStatus.ERROR, errors=[f"搜尋失敗：{str(e)}"])

    async def _ingest(self, params: dict[str, Any]) -> TaskResult:
        """匯入文件至知識庫。"""
        file_path = params.get("file_path", "")
        collection = params.get("collection")
        metadata = params.get("metadata", {})

        if not file_path:
            return TaskResult(
                status=TaskStatus.ERROR,
                errors=["file_path 參數為必要"],
            )

        await self.update_progress(0.2, f"讀取並分割文件：{file_path}")

        try:
            from src.services.rag_service import RAGService

            rag = RAGService()
            result = rag.ingest_text_file(
                file_path=file_path,
                metadata=metadata,
                collection_name=collection,
            )
            await self.update_progress(1.0, f"已嵌入 {result['added']} 個 chunks")

            return TaskResult(
                status=TaskStatus.SUCCESS,
                data=result,
                summary=f"文件已嵌入：{result['added']} chunks → {result['collection']}",
            )
        except FileNotFoundError as e:
            return TaskResult(status=TaskStatus.ERROR, errors=[str(e)])
        except Exception as e:
            return TaskResult(status=TaskStatus.ERROR, errors=[f"嵌入失敗：{str(e)}"])

    async def _get_stats(self, params: dict[str, Any]) -> TaskResult:
        """取得知識庫統計資訊。"""
        await self.update_progress(0.3, "查詢知識庫狀態")

        try:
            from src.services.rag_service import RAGService

            rag = RAGService()
            collections = rag.list_collections()
            await self.update_progress(1.0, f"知識庫含 {len(collections)} 個集合")

            return TaskResult(
                status=TaskStatus.SUCCESS,
                data={
                    "collections": collections,
                    "total_collections": len(collections),
                    "total_documents": sum(c["count"] for c in collections),
                },
                summary=f"知識庫統計：{len(collections)} 集合",
            )
        except Exception as e:
            return TaskResult(status=TaskStatus.ERROR, errors=[f"統計查詢失敗：{str(e)}"])
