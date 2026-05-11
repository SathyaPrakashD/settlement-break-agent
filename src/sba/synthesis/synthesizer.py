"""LLM synthesis of remediation suggestions.

Takes the top-K reranked cases and produces a structured RemediationSuggestion
via Gemini's structured output API.

──────────────────────────────────────────────────────────────────────────────
TODO(sathya): implement Synthesizer.synthesize().

Why I left this as a stub: the Gemini structured-output API is currently the
most important hands-on skill for this entire project. Implementing it yourself
forces you to read the google-genai SDK docs, understand how Pydantic schemas
map to the response_schema parameter, and handle the failure modes (rate limits,
schema validation errors, citation hallucinations).

Reference docs:
  https://ai.google.dev/gemini-api/docs/structured-output

Sketch of what your implementation needs:
  1. Build the prompt by filling ACTIVE_SYNTHESIS_PROMPT with the break fields
     and a block of formatted similar cases (use format_similar_case)
  2. Call Gemini with response_mime_type="application/json" and
     response_schema=RemediationSuggestion
  3. Parse the response into a RemediationSuggestion
  4. Validate that every cited_case_id is actually in the retrieved cases
     (anti-hallucination check)
  5. Return the validated RemediationSuggestion

Production hardening to add later (NOT in v0.1):
  - Retry on transient errors with exponential backoff
  - Token cost tracking (input/output tokens × rate)
  - Latency measurement (P50, P95, P99)
  - Prompt versioning logged to evals

When you're done:
  - Test with: uv run sba investigate --trade-id TRD-XXXX (you'll generate
    a real trade ID after running generate-corpus)
  - Confirm the output is a valid RemediationSuggestion
  - Confirm cited_case_ids only contains IDs that were in the retrieved cases
──────────────────────────────────────────────────────────────────────────────
"""
from sba.config import settings
from sba.retrieval.dense import RetrievedCase
from sba.synthesis.prompts import (
    ACTIVE_SYNTHESIS_PROMPT,
    ACTIVE_SYNTHESIS_VERSION,
    format_similar_case,
)
from sba.synthetic.schemas import BreakNotification, RemediationSuggestion


class Synthesizer:
    """Synthesise a structured remediation from retrieved historical cases."""

    def __init__(self) -> None:
        # TODO(sathya): initialize Gemini client here
        # from google import genai
        # self.client = genai.Client(api_key=settings.gemini_api_key)
        self.client = None  # placeholder
        self.prompt_version = ACTIVE_SYNTHESIS_VERSION

    def synthesize(
        self,
        notification: BreakNotification,
        retrieved_cases: list[RetrievedCase],
    ) -> RemediationSuggestion:
        """Produce a structured remediation suggestion.

        Args:
            notification: The incoming break to investigate.
            retrieved_cases: Reranked top-K similar past cases.

        Returns:
            Validated RemediationSuggestion. Citations are guaranteed to point
            at cases that were actually retrieved (anti-hallucination guarantee).
        """
        if self.client is None:
            # Stub: return a placeholder so the pipeline runs end-to-end
            # before you implement the real call. Replace this whole block.
            return self._stub_response(notification, retrieved_cases)

        # ─────── Your implementation goes here ───────
        # 1. Build prompt
        similar_cases_block = "\n\n".join(
            format_similar_case(c.payload, rank=i + 1)
            for i, c in enumerate(retrieved_cases)
        )
        prompt = ACTIVE_SYNTHESIS_PROMPT.format(
            **notification.model_dump(mode="json"),
            similar_cases_block=similar_cases_block,
        )

        # 2. Call Gemini with structured output (response_schema=RemediationSuggestion)
        # 3. Parse response.parsed into RemediationSuggestion
        # 4. Validate citations against retrieved case IDs
        # 5. Return

        raise NotImplementedError("Implement Synthesizer.synthesize — see module docstring")

    @staticmethod
    def _stub_response(
        notification: BreakNotification,
        retrieved_cases: list[RetrievedCase],
    ) -> RemediationSuggestion:
        """Placeholder response so the pipeline runs end-to-end pre-implementation."""
        from sba.synthetic.schemas import BreakCategory

        top_category = (
            retrieved_cases[0].payload.get("category", BreakCategory.SYSTEM_ERROR.value)
            if retrieved_cases
            else BreakCategory.SYSTEM_ERROR.value
        )

        return RemediationSuggestion(
            root_cause_category=BreakCategory(top_category),
            root_cause_explanation=(
                "STUB RESPONSE — implement Synthesizer.synthesize to get real output. "
                f"The most similar retrieved case suggests category: {top_category}."
            ),
            recommended_actions=[
                "STUB: implement the Gemini structured-output call in synthesizer.py",
                "Review the TODO(sathya) block at the top of the module",
            ],
            cited_case_ids=[c.case_id for c in retrieved_cases[:3]],
            confidence=0.0,
            requires_human_approval=True,
        )
