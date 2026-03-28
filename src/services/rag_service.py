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

    def list_sources(self, collection_name: str | None = None) -> list[dict[str, Any]]:
        """列出知識庫中所有來源檔案（依 source 分組）。

        Returns:
            [{source, chunks, file_type}] 的列表。
        """
        collection = self._get_collection(collection_name)
        total = collection.count()
        if total == 0:
            return []

        # 取回所有文件的 metadata
        all_docs = collection.get(include=["metadatas"])
        source_map: dict[str, dict[str, Any]] = {}

        for meta in all_docs.get("metadatas", []):
            if not meta:
                continue
            source = meta.get("source", "未知")
            if source not in source_map:
                source_map[source] = {
                    "source": source,
                    "chunks": 0,
                    "file_type": meta.get("file_type", ""),
                    "file_path": meta.get("file_path", ""),
                }
            source_map[source]["chunks"] += 1

        return sorted(source_map.values(), key=lambda x: x["source"])

    def delete_by_source(self, source: str, collection_name: str | None = None) -> dict[str, Any]:
        """刪除指定來源的所有 chunks。

        Args:
            source: 來源檔案名稱（metadata.source 值）。
            collection_name: 集合名稱。

        Returns:
            刪除結果摘要。
        """
        collection = self._get_collection(collection_name)

        # 找出所有屬於此 source 的文件 ID
        all_docs = collection.get(where={"source": source}, include=["metadatas"])
        ids_to_delete = all_docs.get("ids", [])

        if not ids_to_delete:
            return {"deleted": 0, "source": source, "collection": collection.name}

        collection.delete(ids=ids_to_delete)
        logger.info(f"已刪除來源 '{source}' 的 {len(ids_to_delete)} 個 chunks")
        return {
            "deleted": len(ids_to_delete),
            "source": source,
            "collection": collection.name,
            "remaining": collection.count(),
        }

    # ── 支援的文件格式 ─────────────────────────────────────────

    SUPPORTED_EXTENSIONS: set[str] = {
        ".pdf",
        ".txt",
        ".md",
        ".csv",
        ".tsv",
        ".xlsx",
        ".xls",
        ".docx",
    }

    @staticmethod
    def _read_pdf(path: Path) -> str:
        """讀取 PDF 檔案並提取全文。"""
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages)

    @staticmethod
    def _read_tabular_as_text(path: Path) -> str:
        """將表格檔（CSV/Excel）轉為可嵌入的文字格式。

        每行轉為「欄位名: 值」格式，適合語意搜尋。
        """
        import pandas as pd

        ext = path.suffix.lower()
        if ext in (".csv", ".tsv"):
            sep = "\t" if ext == ".tsv" else ","
            df = pd.read_csv(path, sep=sep, encoding="utf-8", on_bad_lines="skip")
        elif ext in (".xlsx", ".xls"):
            df = pd.read_excel(path)
        else:
            return ""

        if df.empty:
            return ""

        # 轉為文字：每行用「欄位: 值」格式
        lines: list[str] = []
        lines.append(f"檔案：{path.name}，共 {len(df)} 筆資料，欄位：{', '.join(df.columns)}")
        lines.append("")

        for _idx, row in df.iterrows():
            parts = [f"{col}: {val}" for col, val in row.items() if pd.notna(val)]
            lines.append(" | ".join(parts))

            # 限制總長度避免過大
            if len("\n".join(lines)) > 50000:
                lines.append(f"... （截斷，共 {len(df)} 筆）")
                break

        return "\n".join(lines)

    def ingest_file(
        self,
        file_path: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        metadata: dict[str, Any] | None = None,
        collection_name: str | None = None,
    ) -> dict[str, Any]:
        """讀取文件並分塊嵌入至知識庫。

        支援：PDF、TXT、MD、CSV、TSV、XLSX、DOCX。
        表格檔會轉為文字格式再分塊嵌入。

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

        suffix = path.suffix.lower()
        if suffix == ".pdf":
            text = self._read_pdf(path)
        elif suffix in (".txt", ".md"):
            text = path.read_text(encoding="utf-8")
        elif suffix in (".csv", ".tsv", ".xlsx", ".xls"):
            text = self._read_tabular_as_text(path)
        elif suffix == ".docx":
            # 簡易 docx 讀取（純文字提取）
            try:
                import zipfile

                with zipfile.ZipFile(path) as z:
                    from xml.etree import ElementTree

                    xml_content = z.read("word/document.xml")
                    tree = ElementTree.fromstring(xml_content)
                    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                    paragraphs = tree.findall(".//w:p", ns)
                    text = "\n".join(
                        "".join(node.text or "" for node in p.findall(".//w:t", ns))
                        for p in paragraphs
                    )
            except Exception:
                text = ""
        else:
            raise ValueError(f"不支援的檔案格式：{suffix}")

        if not text.strip():
            logger.warning(f"檔案內容為空：{file_path}")
            return {"added": 0, "collection": self._default_collection_name, "total": 0}

        chunks = self._split_text(text, chunk_size, chunk_overlap)

        base_meta = {
            "source": str(path.name),
            "file_path": str(path),
            "file_type": suffix.lstrip("."),
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

    def ingest_text_file(
        self,
        file_path: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        metadata: dict[str, Any] | None = None,
        collection_name: str | None = None,
    ) -> dict[str, Any]:
        """讀取文字檔案並分割為 chunks 後嵌入（向下相容）。

        建議改用 ingest_file()，支援 PDF/TXT/MD。
        """
        return self.ingest_file(
            file_path=file_path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            metadata=metadata,
            collection_name=collection_name,
        )

    def ingest_folder(
        self,
        folder_path: str,
        collection_name: str | None = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        progress_cb: Any = None,
    ) -> dict[str, Any]:
        """批次匯入資料夾中所有支援格式的文件。

        Args:
            folder_path: 資料夾路徑。
            collection_name: 目標集合名稱。
            chunk_size: 每個 chunk 的最大字元數。
            chunk_overlap: chunks 之間的重疊字元數。
            progress_cb: 進度回呼函式 (pct: float, msg: str) -> None。

        Returns:
            匯入結果摘要。
        """
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            raise FileNotFoundError(f"資料夾不存在：{folder_path}")

        files = sorted(
            f
            for f in folder.rglob("*")
            if f.is_file()
            and f.suffix.lower() in self.SUPPORTED_EXTENSIONS
            and not f.name.startswith(".")
        )

        results: dict[str, Any] = {
            "total": len(files),
            "ingested": 0,
            "skipped": 0,
            "errors": [],
            "chunks_added": 0,
        }

        if not files:
            logger.warning(f"資料夾中無支援格式文件：{folder_path}")
            return results

        step = max(1, len(files) // 20)
        for i, fpath in enumerate(files):
            try:
                result = self.ingest_file(
                    str(fpath),
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    collection_name=collection_name,
                )
                results["ingested"] += 1
                results["chunks_added"] += result.get("added", 0)
            except Exception as e:
                results["errors"].append(f"{fpath.name}: {e}")
                results["skipped"] += 1

            if progress_cb and (i + 1) % step == 0:
                pct = (i + 1) / len(files)
                progress_cb(pct, f"已處理 {i + 1}/{len(files)} 份文件...")

        stats = self.get_collection_stats(collection_name)
        results["collection"] = stats.get("name", "")
        results["total_in_collection"] = stats.get("count", 0)
        logger.info(
            f"資料夾匯入完成：{results['ingested']}/{results['total']} 份文件, "
            f"{results['chunks_added']} 個 chunks"
        )
        return results

    def ask(
        self,
        query: str,
        n_results: int = 5,
        collection_name: str | None = None,
    ) -> dict[str, Any]:
        """RAG 問答：檢索相關文件 → LLM 生成回答。

        Args:
            query: 使用者的問題。
            n_results: 檢索結果數量。
            collection_name: 搜尋集合名稱。

        Returns:
            包含 answer、sources 的結果字典。
        """
        from src.services.llm_service import LLMService

        # Step 1: 語意搜尋
        results = self.search(query=query, n_results=n_results, collection_name=collection_name)

        if not results:
            return {
                "answer": "知識庫中未找到相關文件，無法回答此問題。請先匯入相關文件。",
                "sources": [],
                "query": query,
            }

        # Step 2: 組裝 context
        contexts = [
            {
                "content": r.content,
                "source": r.metadata.get("source", "未知"),
                "relevance": r.relevance_score,
            }
            for r in results
        ]

        # Step 3: LLM 生成回答
        llm = LLMService()
        answer = llm.rag_answer(query=query, contexts=contexts)

        return {
            "answer": answer,
            "sources": [
                {
                    "doc_id": r.doc_id,
                    "source": r.metadata.get("source", ""),
                    "relevance": round(r.relevance_score, 3),
                    "content_preview": r.content[:200],
                }
                for r in results
            ],
            "query": query,
        }

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
