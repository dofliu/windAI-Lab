"""案例推薦器測試（Epic A #48 A2-1）。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.core.database import Database
from src.services.case_learning import CASE_COLLECTION
from src.services.rag_service import SearchResult
from src.skills.rag.case_recommender import CaseRecommender

if TYPE_CHECKING:
    from pathlib import Path


def _res(case_id: str, score: float, turbine: str, fault: str = "齒輪箱") -> SearchResult:
    content = f"案例標題：x\n故障類型：{fault}\n症狀描述：振動\n解決方案：更換軸承 {case_id}\n處理時間：2.0 小時"
    return SearchResult(
        doc_id=f"doc-{case_id}",
        content=content,
        metadata={"case_id": case_id, "fault_type": fault, "turbine_id": turbine},
        distance=1 - score,
        relevance_score=score,
    )


class FakeSearcher:
    def __init__(self, results: list[SearchResult], fail: bool = False) -> None:
        self.results = results
        self.fail = fail
        self.calls: list[dict[str, Any]] = []

    def search(
        self,
        query: str,
        n_results: int = 5,
        collection_name: str | None = None,
        where: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        if self.fail:
            raise RuntimeError("no chromadb")
        self.calls.append({"query": query, "n": n_results, "collection": collection_name})
        return self.results


def test_returns_fields_and_uses_case_collection() -> None:
    searcher = FakeSearcher([_res("c1", 0.9, "WT-01")])
    recs = CaseRecommender(searcher).recommend("齒輪箱振動偏高")
    assert len(recs) == 1
    assert recs[0].case_id == "c1"
    assert recs[0].similarity == 0.9
    assert recs[0].fault_type == "齒輪箱"
    assert recs[0].solution == "更換軸承 c1"
    assert searcher.calls[0]["collection"] == CASE_COLLECTION


def test_same_turbine_is_boosted() -> None:
    searcher = FakeSearcher([_res("far", 0.85, "WT-02"), _res("near", 0.80, "WT-01")])
    recs = CaseRecommender(searcher).recommend("振動", turbine_id="WT-01")
    assert [r.case_id for r in recs] == ["near", "far"]
    assert recs[0].same_turbine is True
    assert recs[1].same_turbine is False


def test_no_turbine_keeps_similarity_order() -> None:
    searcher = FakeSearcher([_res("a", 0.9, "WT-02"), _res("b", 0.8, "WT-01")])
    recs = CaseRecommender(searcher).recommend("振動")
    assert [r.case_id for r in recs] == ["a", "b"]


def test_top_k_limits_results() -> None:
    searcher = FakeSearcher([_res(f"c{i}", 0.9 - i * 0.05, "WT-01") for i in range(8)])
    assert len(CaseRecommender(searcher).recommend("振動")) == 5
    assert len(CaseRecommender(searcher).recommend("振動", top_k=2)) == 2


def test_empty_query_returns_empty_without_search() -> None:
    searcher = FakeSearcher([_res("c1", 0.9, "WT-01")])
    assert CaseRecommender(searcher).recommend("   ") == []
    assert searcher.calls == []


def test_search_failure_returns_empty() -> None:
    assert CaseRecommender(FakeSearcher([], fail=True)).recommend("振動") == []


def _db_with_cases(tmp_path: Path) -> Database:
    db = Database(str(tmp_path / "fallback.db"))
    db.initialize()
    db.create_case(
        "WO-1", "齒輪箱", "s1", symptoms="齒輪箱振動偏高", solution="更換軸承", turbine_id="WT-01"
    )
    db.create_case(
        "WO-2", "葉片", "s2", symptoms="葉片裂紋", solution="修補葉片", turbine_id="WT-02"
    )
    return db


def test_fallback_when_searcher_missing(tmp_path: Path) -> None:
    recs = CaseRecommender(None, store=_db_with_cases(tmp_path)).recommend("齒輪箱振動異常")
    assert recs
    assert recs[0].fault_type == "齒輪箱"
    assert recs[0].solution == "更換軸承"
    assert all(r.fault_type != "葉片" for r in recs)


def test_fallback_when_search_fails_or_empty(tmp_path: Path) -> None:
    db = _db_with_cases(tmp_path)
    failed = CaseRecommender(FakeSearcher([], fail=True), store=db).recommend("葉片裂紋")
    empty = CaseRecommender(FakeSearcher([]), store=db).recommend("葉片裂紋")
    assert failed[0].fault_type == "葉片"
    assert empty[0].fault_type == "葉片"


def test_fallback_same_turbine_boost(tmp_path: Path) -> None:
    db = _db_with_cases(tmp_path)
    db.create_case(
        "WO-3", "齒輪箱", "s3", symptoms="齒輪箱振動", solution="換油", turbine_id="WT-09"
    )
    recs = CaseRecommender(None, store=db).recommend("齒輪箱振動", turbine_id="WT-09")
    assert recs[0].turbine_id == "WT-09"
    assert recs[0].same_turbine is True


def test_fallback_no_match_and_no_store(tmp_path: Path) -> None:
    assert CaseRecommender(None, store=_db_with_cases(tmp_path)).recommend("zzz") == []
    assert CaseRecommender(None).recommend("齒輪箱振動") == []


def test_semantic_results_preferred_over_fallback(tmp_path: Path) -> None:
    searcher = FakeSearcher([_res("sem", 0.9, "WT-01")])
    recs = CaseRecommender(searcher, store=_db_with_cases(tmp_path)).recommend("齒輪箱")
    assert [r.case_id for r in recs] == ["sem"]
