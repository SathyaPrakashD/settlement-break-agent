"""Versioned prompts.

Treat prompts as code. Every change to a prompt template gets a new version,
a brief rationale comment, and gets eval'd before promotion. This is the
discipline that separates production LLM systems from demos.

Convention: prompts are named SYNTHESIS_V1, SYNTHESIS_V2, etc. The active
version is exported as ACTIVE_SYNTHESIS_PROMPT. Old versions are kept in
this file for eval comparison, NOT deleted.
"""

SYNTHESIS_V1 = """\
You are a senior settlement operations analyst assistant. Your job is to draft a \
remediation suggestion for a new settlement break, based on similar past breaks that \
were successfully resolved.

You must:
1. Identify the root cause category (one of: ssi_mismatch, counterparty_issue, \
timing_cutoff, fx_related, regulatory_hold, system_error)
2. Explain the root cause in 2-3 sentences
3. List recommended actions in order of priority (1 to 10 steps)
4. Cite the case IDs from the historical examples that informed your suggestion
5. Provide a confidence score between 0.0 and 1.0

The new break to investigate:
─────────────────────────────────────────────
Trade ID: {trade_id}
Exception code: {exception_code}
Severity: {severity}
Product: {product_type}
Currency: {currency}
Counterparty: {counterparty_id}
Notional (USD): {notional_usd:,.2f}
Trade date: {trade_date}
Settlement date: {settlement_date}

Analyst narrative:
{analyst_narrative}
─────────────────────────────────────────────

Most similar past cases (ordered by relevance):

{similar_cases_block}

Now produce your structured remediation suggestion. Cite only case IDs that actually \
appear above. If none of the past cases are clearly applicable, set confidence low \
and explain why."""


def format_similar_case(case: dict, rank: int) -> str:
    """Format one retrieved case for inclusion in the prompt."""
    return f"""\
[Case #{rank}: {case['case_id']}] (score: similarity-based)
  Category: {case['category']}  |  Exception: {case['exception_code']}
  Product: {case['product_type']}  |  Currency: {case['currency']}  |  CP: {case['counterparty_id']}
  Narrative: {case['analyst_narrative']}
  Resolution that worked: {case['resolution']}
  Resolution time: {case['resolution_time_hours']}h
"""


# The currently active version. Bump this when you ship a new prompt.
ACTIVE_SYNTHESIS_PROMPT = SYNTHESIS_V1
ACTIVE_SYNTHESIS_VERSION = "v1"
