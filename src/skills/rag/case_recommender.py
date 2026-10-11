"""維修案例推薦器（Epic A #48 — 相似案例推薦）。

輸入告警描述，於 `maintenance_cases` 集合做語意搜尋，回傳相似歷史案例
（故障類型、相似度、解決方案摘要）。同一風機（`turbine_id`）的案例會獲得
加權，優先排序。向量庫以 Protocol 注入，不直接依賴 chromadb。

向量庫不可用（未提供、搜尋失敗或無結果）時，降級以 SQLite `cases` 表做
關鍵字 / 故障類型比對（A2-2），確保無 chromadb 環境仍有結果。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from src.services.case_learning import CASE_COLLECTION
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.services.rag_service import SearchResult

logger = get_logger("skill.case_recommender")

DEFAULT_TOP_K = 5
SAME_TURBINE_BOOST = 0.1
_CANDIDATE_FACTOR = 3
_SOLUTION_PREFIX = "解決方案："
_FALLBACK_SCAN_LIMIT = 500
_FAULT_TYPE_BONUS = 0.3
_TOKEN_RE = re.compile(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+")


class CaseSearcher(Protocol):
    """向量知識庫搜尋介面（`RAGService.search` 的子集）。"""

    def search(
        self,
        query: str,
        n_results: int = 5,
        collection_name: str | None = None,
        where: dict[str, Any] | None = None,
    ) -> list[SearchResult]: ...


class CaseStore(Protocol):
    """結構化案例儲存介面（`Database.list_cases` 的子集）。"""

    def list_cases(
        self,
        limit: int = 50,
        offset: int = 0,
        fault_type: str | None = None,
        turbine_id: str | None = None,
    ) -> list[dict[str, Any]]: ...


@dataclass
class CaseRecommendation:
    """單筆推薦案例。"""

    case_id: str
    similarity: float
    fault_type: str
    solution: str
    turbine_id: str = ""
    same_turbine: bool = False


def _extract_solution(content: str) -> str:
    """從案例摘要文字取出「解決方案」那一行。"""
    for line in content.splitlines():
        if line.startswith(_SOLUTION_PREFIX):
            return line[len(_SOLUTION_PREFIX) :].strip()
    return ""


def _tokens(text: str) -> set[str]:
    """切詞：英數字詞，以及中文字串的 bigram（單字中文片段保留原字）。"""
    out: set[str] = set()
    for chunk in _TOKEN_RE.findall(text.lower()):
        if chunk.isascii() or len(chunk) == 1:
            out.add(chunk)
        else:
            out.update(chunk[i : i + 2] for i in range(len(chunk) - 1))
    return out


class CaseRecommender:
    """以語意搜尋推薦相似維修案例，向量庫不可用時降級為關鍵字比對。"""

    def __init__(
        self,
        searcher: CaseSearcher | None = None,
        top_k: int = DEFAULT_TOP_K,
        store: CaseStore | None = None,
    ) -> None:
        """初始化推薦器。

        Args:
            searcher: 向量知識庫（需提供 `search`），None 表示不可用。
            top_k: 預設回傳筆數。
            store: 結構化案例儲存，作為向量庫不可用時的降級來源。
        """
        self._searcher = searcher
        self._top_k = top_k
        self._store = store

    def recommend(
        self,
        description: str,
        turbine_id: str | None = None,
        top_k: int | None = None,
    ) -> list[CaseRecommendation]:
        """推薦相似案例。

        Args:
            description: 告警描述（症狀文字）。
            turbine_id: 告警所屬風機；相同風機的案例加權優先。
            top_k: 回傳筆數，None 使用預設。

        Returns:
            依（加權後）相似度由高到低排序的推薦；查詢為空或搜尋失敗回傳空列表。
        """
        limit = top_k or self._top_k
        if not description.strip():
            return []
        results: list[SearchResult] = []
        if self._searcher is not None:
            try:
                results = self._searcher.search(
                    description,
                    n_results=limit * _CANDIDATE_FACTOR,
                    collection_name=CASE_COLLECTION,
                )
            except Exception as exc:  # 向量庫為選用依賴，失敗時降級
                logger.warning(f"案例語意搜尋失敗，改用關鍵字比對: {exc}")
        if not results:
            return self._fallback(description, turbine_id, limit)

        scored: list[tuple[float, CaseRecommendation]] = []
        for res in results:
            meta = res.metadata or {}
            case_turbine = str(meta.get("turbine_id") or "")
            same = bool(turbine_id) and case_turbine == turbine_id
            rec = CaseRecommendation(
                case_id=str(meta.get("case_id") or res.doc_id),
                similarity=round(res.relevance_score, 4),
                fault_type=str(meta.get("fault_type") or ""),
                solution=_extract_solution(res.content),
                turbine_id=case_turbine,
                same_turbine=same,
            )
            scored.append((res.relevance_score + (SAME_TURBINE_BOOST if same else 0.0), rec))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [rec for _, rec in scored[:limit]]

    def _fallback(
        self, description: str, turbine_id: str | None, limit: int
    ) -> list[CaseRecommendation]:
        """以 SQLite 案例做關鍵字 / 故障類型比對（相似度 = 查詢詞命中比例）。"""
        if self._store is None:
            return []
        query_tokens = _tokens(description)
        if not query_tokens:
            return []
        try:
            cases = self._store.list_cases(limit=_FALLBACK_SCAN_LIMIT)
        except Exception as exc:
            logger.warning(f"案例關鍵字比對失敗: {exc}")
            return []

        scored: list[tuple[float, CaseRecommendation]] = []
        for case in cases:
            fault_type = str(case.get("fault_type") or "")
            haystack = " ".join(
                str(case.get(k) or "") for k in ("fault_type", "symptoms", "summary", "solution")
            )
            overlap = len(query_tokens & _tokens(haystack)) / len(query_tokens)
            fault_hit = bool(fault_type) and fault_type.lower() in description.lower()
            if overlap == 0 and not fault_hit:
                continue
            similarity = min(1.0, overlap + (_FAULT_TYPE_BONUS if fault_hit else 0.0))
            case_turbine = str(case.get("turbine_id") or "")
            same = bool(turbine_id) and case_turbine == turbine_id
            rec = CaseRecommendation(
                case_id=str(case.get("id") or ""),
                similarity=round(similarity, 4),
                fault_type=fault_type,
                solution=str(case.get("solution") or ""),
                turbine_id=case_turbine,
                same_turbine=same,
            )
            scored.append((similarity + (SAME_TURBINE_BOOST if same else 0.0), rec))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [rec for _, rec in scored[:limit]]
