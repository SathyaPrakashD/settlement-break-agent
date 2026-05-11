"""Tests for the synthetic data generator."""
from pathlib import Path

import pytest

from sba.synthetic.generator import generate_break, generate_corpus
from sba.synthetic.schemas import BreakCategory, HistoricalBreak


def test_generate_break_returns_valid_pydantic_model() -> None:
    brk = generate_break(case_id="CASE-000001")
    assert isinstance(brk, HistoricalBreak)
    assert brk.case_id == "CASE-000001"
    assert brk.trade_id.startswith("TRD-")
    assert brk.notional_usd >= 0
    assert brk.resolution_time_hours >= 0


def test_generate_break_with_fixed_category() -> None:
    brk = generate_break(case_id="CASE-000002", category=BreakCategory.SSI_MISMATCH)
    assert brk.category == BreakCategory.SSI_MISMATCH


def test_corpus_generation_writes_jsonl(tmp_path: Path) -> None:
    output = tmp_path / "test_corpus.jsonl"
    generate_corpus(count=10, output_path=output, seed=42)

    assert output.exists()
    lines = output.read_text().strip().split("\n")
    assert len(lines) == 10

    # Every line should parse as a HistoricalBreak
    for line in lines:
        HistoricalBreak.model_validate_json(line)


def test_corpus_reproducible_with_seed(tmp_path: Path) -> None:
    """Same seed should produce identical corpora."""
    out1 = tmp_path / "c1.jsonl"
    out2 = tmp_path / "c2.jsonl"
    generate_corpus(count=5, output_path=out1, seed=42)
    generate_corpus(count=5, output_path=out2, seed=42)
    assert out1.read_text() == out2.read_text()


@pytest.mark.parametrize("category", list(BreakCategory))
def test_each_category_generates_valid_break(category: BreakCategory) -> None:
    brk = generate_break(case_id="CASE-TEST", category=category)
    assert brk.category == category
    assert brk.analyst_narrative
    assert brk.resolution
