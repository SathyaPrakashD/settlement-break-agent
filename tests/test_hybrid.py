"""Tests for hybrid retrieval fusion."""
from sba.retrieval.dense import RetrievedCase
from sba.retrieval.hybrid import HybridRetriever


def _make(case_id: str, score: float = 0.5) -> RetrievedCase:
    return RetrievedCase(case_id=case_id, score=score, payload={"case_id": case_id})


def test_rrf_promotes_documents_in_both_retrievers() -> None:
    """A doc that appears in both lists should rank above docs in only one."""
    dense = [_make("A"), _make("B"), _make("C")]
    sparse = [_make("B"), _make("D"), _make("E")]

    fused = HybridRetriever._rrf_fuse(dense, sparse, k=60)
    fused_ids = [c.case_id for c in fused]

    # B is in both lists, so should be ranked above A, C, D, E individually
    assert fused_ids.index("B") < fused_ids.index("D")
    assert fused_ids.index("B") < fused_ids.index("E")


def test_rrf_handles_empty_inputs() -> None:
    assert HybridRetriever._rrf_fuse([], [], k=60) == []


def test_rrf_handles_one_empty_input() -> None:
    dense = [_make("A"), _make("B")]
    fused = HybridRetriever._rrf_fuse(dense, [], k=60)
    assert [c.case_id for c in fused] == ["A", "B"]


def test_rrf_score_formula() -> None:
    """Verify the actual RRF score for a known case."""
    dense = [_make("A")]  # rank 1
    sparse = [_make("A")]  # rank 1
    fused = HybridRetriever._rrf_fuse(dense, sparse, k=60)

    # A is rank 1 in both: 1/(60+1) + 1/(60+1) = 2/61
    assert abs(fused[0].score - (2 / 61)) < 1e-9
