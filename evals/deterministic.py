"""Layer 1: deterministic eval checks.

These are free and fast. Run on every commit. Catch the boring failures
before any LLM cost is spent on Layer 2/3.
"""
import re

from sba.config import settings
from sba.retrieval.indexer import load_corpus
from sba.synthetic.schemas import RemediationSuggestion

TRADE_ID_PATTERN = re.compile(r"^TRD-\d{6}$")
CASE_ID_PATTERN = re.compile(r"^CASE-\d{6}$")


def check_schema_valid(remediation: RemediationSuggestion) -> tuple[bool, str]:
    """Pydantic already validated structure if we got this far. Sanity-check fields."""
    if not remediation.recommended_actions:
        return False, "No recommended_actions"
    if not (0.0 <= remediation.confidence <= 1.0):
        return False, f"confidence out of [0,1]: {remediation.confidence}"
    return True, "ok"


def check_citations_real(
    remediation: RemediationSuggestion,
    retrieved_case_ids: set[str],
) -> tuple[bool, str]:
    """Every cited case_id must have been in the retrieved cases.

    This is the anti-hallucination guarantee. If this fails, the synthesiser
    made up a case ID — which would be a critical failure in production.
    """
    fake = [cid for cid in remediation.cited_case_ids if cid not in retrieved_case_ids]
    if fake:
        return False, f"Hallucinated case IDs: {fake}"
    return True, "ok"


def check_citation_format(remediation: RemediationSuggestion) -> tuple[bool, str]:
    """Citations must match the case ID format."""
    bad = [cid for cid in remediation.cited_case_ids if not CASE_ID_PATTERN.match(cid)]
    if bad:
        return False, f"Malformed case IDs: {bad}"
    return True, "ok"


def check_citations_exist_in_corpus(remediation: RemediationSuggestion) -> tuple[bool, str]:
    """All cited cases must exist in the actual corpus."""
    corpus = load_corpus(settings.corpus_path)
    valid_ids = {b.case_id for b in corpus}
    missing = [cid for cid in remediation.cited_case_ids if cid not in valid_ids]
    if missing:
        return False, f"Cited case IDs not in corpus: {missing}"
    return True, "ok"


def run_deterministic_checks(
    remediation: RemediationSuggestion,
    retrieved_case_ids: set[str],
) -> dict[str, tuple[bool, str]]:
    """Run all Layer-1 deterministic checks. Returns dict of check_name → (pass, msg)."""
    return {
        "schema_valid": check_schema_valid(remediation),
        "citations_format": check_citation_format(remediation),
        "citations_real_in_retrieved": check_citations_real(remediation, retrieved_case_ids),
        "citations_exist_in_corpus": check_citations_exist_in_corpus(remediation),
    }
