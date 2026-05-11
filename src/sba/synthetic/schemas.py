"""Pydantic schemas for settlement breaks and their resolutions.

These models define what a "break" looks like in our system. The shape is informed
by how real settlement operations teams actually describe these in incident
tickets — structured fields for filtering plus a free-text narrative for retrieval.

NOTE: all data is synthetic. No real institutional data is referenced or used.
"""
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class BreakCategory(StrEnum):
    """Top-level root cause classification for settlement breaks.

    These six categories cover ~90% of real settlement breaks in BFSI ops.
    Used as the structured output target for the synthesiser and as the
    primary stratification axis for the synthetic data generator.
    """

    SSI_MISMATCH = "ssi_mismatch"
    COUNTERPARTY_ISSUE = "counterparty_issue"
    TIMING_CUTOFF = "timing_cutoff"
    FX_RELATED = "fx_related"
    REGULATORY_HOLD = "regulatory_hold"
    SYSTEM_ERROR = "system_error"


class Severity(StrEnum):
    """Operational severity. Drives prioritisation and (in v0.3) routing."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    REGULATORY_FLAG = "regulatory_flag"


class ProductType(StrEnum):
    """The product class of the failed trade."""

    EQUITY = "equity"
    BOND = "bond"
    FX_SPOT = "fx_spot"
    FX_FORWARD = "fx_forward"
    REPO = "repo"
    DERIVATIVE = "derivative"


class HistoricalBreak(BaseModel):
    """A single historical settlement break with its resolution.

    This is the unit of retrieval. The corpus is ~500 of these. Both the
    free-text narrative AND the resolution text are embedded for retrieval —
    the resolution often contains the most useful signal for "what worked
    for a similar past case."
    """

    case_id: str = Field(..., description="Unique identifier, e.g. CASE-000123")
    trade_id: str = Field(..., description="Underlying trade ID, e.g. TRD-000456")

    # Structured filterable fields
    category: BreakCategory
    severity: Severity
    product_type: ProductType
    currency: str = Field(..., description="ISO 4217 currency code")
    counterparty_id: str = Field(..., description="Counterparty short code")
    exception_code: str = Field(..., description="System exception code")
    trade_date: date
    settlement_date: date
    notional_usd: float = Field(..., ge=0)

    # Free-text fields (the retrieval targets)
    analyst_narrative: str = Field(
        ..., description="What the operations analyst observed and noted"
    )
    resolution: str = Field(..., description="What action resolved the break")
    resolution_time_hours: float = Field(..., ge=0)


class BreakNotification(BaseModel):
    """An incoming break that needs investigation.

    Same shape as HistoricalBreak minus the resolution — this is what the
    system receives as input.
    """

    trade_id: str
    category_suspected: BreakCategory | None = Field(
        default=None,
        description="Optional analyst-suspected category. None means 'investigate from scratch'.",
    )
    severity: Severity
    product_type: ProductType
    currency: str
    counterparty_id: str
    exception_code: str
    trade_date: date
    settlement_date: date
    notional_usd: float
    analyst_narrative: str


class RemediationSuggestion(BaseModel):
    """Structured output from the synthesiser. This is what the user gets back.

    Schema-enforced via Gemini structured output. The cited_case_ids are
    validated downstream — every ID must exist in the corpus or it's flagged
    as a hallucination.
    """

    root_cause_category: BreakCategory
    root_cause_explanation: str = Field(
        ..., description="2-3 sentence explanation of why this category"
    )
    recommended_actions: list[str] = Field(
        ..., min_length=1, max_length=10, description="Ordered remediation steps"
    )
    cited_case_ids: list[str] = Field(
        default_factory=list,
        description="Historical case IDs that informed this recommendation",
    )
    confidence: float = Field(..., ge=0.0, le=1.0)
    requires_human_approval: bool = Field(
        default=True,
        description="In v0.1 this is always True. v0.3 will gate by severity.",
    )
