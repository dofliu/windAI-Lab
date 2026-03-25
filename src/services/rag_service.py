"""RAG 知識庫服務。

基於 ChromaDB 的向量資料庫，提供風力發電領域文獻的嵌入儲存與語意搜尋。
支援文件新增、搜尋、集合管理等操作。
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.utils.logger import get_logger

logger = get_logger("service.rag")


@dataclass
class Document:
    """RAG 文件模型。"""

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    doc_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class SearchResult:
    """語意搜尋結果。"""

    doc_id: str
    content: str
    metadata: dict[str, Any]
    distance: float
    relevance_score: float


class RAGService:
    """RAG 知識庫核心服務。

    使用 ChromaDB 作為向量儲存後端，支援：
    - 文件嵌入與儲存
    - 語意搜尋（餘弦相似度）
    - 集合管理（建立、列出、刪除）
    - 文件 metadata 篩選
    """

    def __init__(self, persist_dir: str | None = None) -> None:
        self._persist_dir = persist_dir or str(
            Path(__file__).resolve().parents[2] / "data" / "chromadb"
        )
        self._client: Any = None
        self._default_collection_name = "windai_knowledge_base"

    @property
    def client(self) -> Any:
        """延遲載入 ChromaDB 客戶端。"""
        if self._client is None:
            try:
                import chromadb

                if self._persist_dir:
                    self._client = chromadb.PersistentClient(path=self._persist_dir)
                    logger.info(f"ChromaDB 已初始化：{self._persist_dir}")
                else:
                    self._client = chromadb.Client()
                    logger.info("ChromaDB 使用記憶體模式")
            except Exception:
                import chromadb

                self._client = chromadb.Client()
                logger.warning("ChromaDB 降級為記憶體模式")
        return self._client

    def _get_collection(self, collection_name: str | None = None) -> Any:
        """取得或建立集合。"""
        name = collection_name or self._default_collection_name
        return self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_documents(
        self,
        documents: list[Document],
        collection_name: str | None = None,
    ) -> dict[str, Any]:
        """批次新增文件至知識庫。

        Args:
            documents: 待新增的文件列表。
            collection_name: 目標集合名稱，預設為主知識庫。

        Returns:
            新增結果摘要。
        """
        collection = self._get_collection(collection_name)

        ids: list[str] = []
        contents: list[str] = []
        metadatas: list[dict[str, Any]] = []

        for doc in documents:
            content_hash = hashlib.md5(doc.content.encode()).hexdigest()  # noqa: S324
            doc_meta = {
                **doc.metadata,
                "added_at": datetime.now(UTC).isoformat(),
                "content_hash": content_hash,
            }
            ids.append(doc.doc_id)
            contents.append(doc.content)
            metadatas.append(doc_meta)

        collection.add(
            ids=ids,
            documents=contents,
            metadatas=metadatas,
        )

        logger.info(f"已新增 {len(documents)} 份文件至集合 '{collection.name}'")
        return {
            "added": len(documents),
            "collection": collection.name,
            "total": collection.count(),
        }

    def search(
        self,
        query: str,
        n_results: int = 5,
        collection_name: str | None = None,
        where: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """語意搜尋。

        Args:
            query: 搜尋查詢字串。
            n_results: 回傳結果數量上限。
            collection_name: 搜尋集合名稱。
            where: metadata 篩選條件（ChromaDB where 語法）。

        Returns:
            依相關度排序的搜尋結果列表。
        """
        collection = self._get_collection(collection_name)

        if collection.count() == 0:
            return []

        query_params: dict[str, Any] = {
            "query_texts": [query],
            "n_results": min(n_results, collection.count()),
        }
        if where:
            query_params["where"] = where

        results = collection.query(**query_params)

        search_results: list[SearchResult] = []
        if results and results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i] if results.get("distances") else 0.0
                relevance = max(0.0, 1.0 - distance)
                search_results.append(
                    SearchResult(
                        doc_id=doc_id,
                        content=results["documents"][0][i] if results.get("documents") else "",
                        metadata=results["metadatas"][0][i] if results.get("metadatas") else {},
                        distance=distance,
                        relevance_score=relevance,
                    )
                )

        logger.info(f"搜尋 '{query[:50]}...' → {len(search_results)} 筆結果")
        return search_results

    def list_collections(self) -> list[dict[str, Any]]:
        """列出所有集合。"""
        collections = self.client.list_collections()
        return [
            {
                "name": c.name,
                "count": c.count(),
                "metadata": c.metadata,
            }
            for c in collections
        ]

    def get_collection_stats(self, collection_name: str | None = None) -> dict[str, Any]:
        """取得集合統計資訊。"""
        collection = self._get_collection(collection_name)
        return {
            "name": collection.name,
            "count": collection.count(),
            "metadata": collection.metadata,
        }

    def delete_document(self, doc_id: str, collection_name: str | None = None) -> dict[str, Any]:
        """刪除指定文件。"""
        collection = self._get_collection(collection_name)
        collection.delete(ids=[doc_id])
        return {"deleted": doc_id, "collection": collection.name}

    def ingest_text_file(
        self,
        file_path: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        metadata: dict[str, Any] | None = None,
        collection_name: str | None = None,
    ) -> dict[str, Any]:
        """讀取文字檔案並分割為 chunks 後嵌入。

        Args:
            file_path: 檔案路徑。
            chunk_size: 每個 chunk 的最大字元數。
            chunk_overlap: chunks 之間的重疊字元數。
            metadata: 附加至每個 chunk 的 metadata。
            collection_name: 目標集合名稱。

        Returns:
            嵌入結果摘要。
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"檔案不存在：{file_path}")

        text = path.read_text(encoding="utf-8")
        chunks = self._split_text(text, chunk_size, chunk_overlap)

        base_meta = {
            "source": str(path.name),
            "file_path": str(path),
            "file_type": path.suffix.lstrip("."),
            **(metadata or {}),
        }

        documents = [
            Document(
                content=chunk,
                metadata={**base_meta, "chunk_index": i, "total_chunks": len(chunks)},
            )
            for i, chunk in enumerate(chunks)
        ]

        return self.add_documents(documents, collection_name)

    @staticmethod
    def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
        """將文字分割為重疊的 chunks。"""
        if len(text) <= chunk_size:
            return [text]

        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk.strip())
            start = end - overlap

        return chunks
