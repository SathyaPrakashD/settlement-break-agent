"""Faker-based synthetic settlement break generator.

Produces N realistic-looking historical breaks with controllable distributions
across the six BreakCategory classes. The narratives and resolutions are templated
with category-specific patterns so that retrieval is genuinely *able* to find
similar past cases — but with enough Faker-injected variance that retrieval is
not trivial.

Realism caveats:
  - Currency / counterparty / product distributions are plausible but stylised.
  - Resolution times are sampled from category-appropriate distributions
    (regulatory holds take longer than SSI mismatches).
  - This is NOT real BFSI data and should not be presented as such.
"""
import json
import random
from datetime import date, timedelta
from pathlib import Path

from faker import Faker

from sba.synthetic.schemas import (
    BreakCategory,
    HistoricalBreak,
    ProductType,
    Severity,
)

fake = Faker()

# Plausible BFSI distributions
CURRENCIES = ["USD", "EUR", "GBP", "JPY", "INR", "SGD", "HKD", "AUD"]
CURRENCY_WEIGHTS = [40, 20, 12, 8, 6, 5, 5, 4]
COUNTERPARTY_POOL = [f"CP-{i:03d}" for i in range(200)]
EXCEPTION_CODES_BY_CATEGORY = {
    BreakCategory.SSI_MISMATCH: ["E101", "E102", "E103"],
    BreakCategory.COUNTERPARTY_ISSUE: ["E201", "E202", "E203"],
    BreakCategory.TIMING_CUTOFF: ["E301", "E302"],
    BreakCategory.FX_RELATED: ["E401", "E402"],
    BreakCategory.REGULATORY_HOLD: ["E501", "E502"],
    BreakCategory.SYSTEM_ERROR: ["E901", "E902", "E903"],
}

# Category-specific narrative templates
NARRATIVE_TEMPLATES: dict[BreakCategory, list[str]] = {
    BreakCategory.SSI_MISMATCH: [
        "Settlement failed at counterparty {cp}. Outgoing SSI references account {acct} "
        "but counterparty confirmed receipt against {acct2}. Beneficiary bank mismatch on the "
        "{ccy} leg. Trade booked {tdate}, intended settlement {sdate}.",
        "SSI on file for {cp} shows correspondent {corr1} but actual settlement attempted via "
        "{corr2}. {ccy} payment rejected. Likely stale SSI — last verified attempt was over "
        "60 days ago.",
        "Mismatch between trade confirmation and SSI database for {cp}. Settlement leg "
        "for {ccy} {notional_str} returned by paying agent citing 'beneficiary account number "
        "invalid'.",
    ],
    BreakCategory.COUNTERPARTY_ISSUE: [
        "Counterparty {cp} unresponsive on settlement instruction confirmation for the {ccy} leg "
        "of {prod} trade. Multiple chase attempts logged. No SWIFT MT599 received within standard "
        "window.",
        "Allocation dispute with {cp}. Block trade was for {notional_str} {ccy} but counterparty "
        "allocations totalled {alloc_str}. Difference under investigation.",
        "{cp} confirmed nostro short on settlement date. Insufficient funds for "
        "the {ccy} leg. Counterparty has requested partial settlement.",
    ],
    BreakCategory.TIMING_CUTOFF: [
        "Trade booked {tdate} late evening, missed local market cutoff for {ccy}. T+1 settlement "
        "now at risk. Instructions sent post-cutoff queued for next business day.",
        "{ccy} CHAPS/CHIPS cutoff missed by 23 minutes. Trade with {cp} for {notional_str} now "
        "rolling to next business day. T+1 obligation breached.",
        "Settlement instruction received {tdate} but submitted to local market after operational "
        "cutoff. Standard rebooking required for next available value date.",
    ],
    BreakCategory.FX_RELATED: [
        "{ccy} leg of FX trade with {cp} failed due to mismatched value date on the cross-currency "
        "swap settlement. Trade booked with value date {sdate} but counterparty applied T+2 instead "
        "of T+1.",
        "FX rate mismatch on confirmation. Booked rate vs counterparty-confirmed rate differs by "
        "12 pips on the {ccy} leg. Rebooking required pending dealer sign-off.",
        "Non-deliverable forward fixing dispute. {ccy} fixing source disagreement between us and "
        "{cp}. Trade settlement on hold pending fixing reconciliation.",
    ],
    BreakCategory.REGULATORY_HOLD: [
        "Settlement of {prod} trade with {cp} for {notional_str} {ccy} placed on hold by Compliance "
        "pending OFAC screening completion. Counterparty has updated beneficial ownership recently.",
        "FATCA documentation lapsed for {cp}. Settlement blocked by tax operations until W-8BEN "
        "refresh confirmed. Trade for {notional_str} {ccy} in hold queue.",
        "EMIR reporting flag triggered on derivative trade. Settlement gated until trade repository "
        "submission acknowledged. Booked with {cp} on {tdate}.",
    ],
    BreakCategory.SYSTEM_ERROR: [
        "Settlement instruction failed validation in downstream payment system. Cryptic error "
        "'NULLPOINTEREXCEPTION at MessageBuilder.line:247'. Trade with {cp} for {ccy} stuck in "
        "queue. IT raised P3 incident.",
        "SWIFT message generation failed for {ccy} settlement leg. MT202COV malformed — missing "
        "field 50K. Manual intervention required from SWIFT operations. Trade ID {trd}.",
        "Counterparty static data table out of sync between trade capture and settlement systems. "
        "{cp} flagged as inactive in settlement but active in trade capture. Booking blocked.",
    ],
}

# Category-specific resolution templates
RESOLUTION_TEMPLATES: dict[BreakCategory, list[str]] = {
    BreakCategory.SSI_MISMATCH: [
        "Updated SSI for {cp} in master reference data to use account {acct2}. Re-released "
        "settlement instruction. Settled same day. Standing change requested via the SSI control "
        "team to prevent recurrence.",
        "Contacted {cp} ops to confirm correct correspondent. Updated SSI record and resubmitted. "
        "Settled T+1. Created reminder for 90-day SSI re-verification.",
        "Verified beneficiary account number with {cp} directly via authenticated channel. "
        "Corrected the digit transposition error in our SSI record and re-instructed. Settled "
        "with backdated value via compensation.",
    ],
    BreakCategory.COUNTERPARTY_ISSUE: [
        "Escalated to {cp} ops head via established contact. Received SWIFT MT599 within 2 hours. "
        "Settlement completed same business day.",
        "Reconciled allocations with {cp} sales contact. Difference traced to a duplicate allocation "
        "row in their system. Counterparty rebooked correctly and trade settled with no loss.",
        "Accepted partial settlement as proposed by {cp}. Remaining balance settled T+1 with "
        "compensation interest agreed at {ccy} overnight rate.",
    ],
    BreakCategory.TIMING_CUTOFF: [
        "Rebooked trade for next business day value. Notified counterparty and confirmed acceptance "
        "of revised value date. Compensation interest computed and agreed.",
        "Requested same-day exceptional settlement via the {ccy} correspondent. Approved on grounds "
        "of operational error. Settled with appropriate compensation to {cp}.",
        "Rolled settlement to next business day. Communicated to client. Updated SOP to require "
        "earlier instruction submission for {ccy} trades to prevent cutoff misses.",
    ],
    BreakCategory.FX_RELATED: [
        "Confirmed correct value date convention with {cp}. Amended our trade record and re-issued "
        "settlement instruction. Trade settled on the corrected value date.",
        "Dealer reviewed and accepted the rate discrepancy as within tolerance. Trade rebooked at "
        "the corrected rate with mutual sign-off. {cp} ops confirmed acceptance.",
        "Reconciled fixing with {cp} treasury. Used the agreed reference fixing source and "
        "settled the trade on next available business day.",
    ],
    BreakCategory.REGULATORY_HOLD: [
        "Compliance screening completed and cleared after 48 hours. Settlement released. Sent "
        "process improvement note to Compliance to expedite screening for {cp} on subsequent trades.",
        "Tax operations confirmed updated W-8BEN received from {cp}. Lifted block and settled with "
        "compensation interest agreed.",
        "Trade repository submission re-attempted and acknowledged within 24 hours. Settlement "
        "released by Compliance the same day.",
    ],
    BreakCategory.SYSTEM_ERROR: [
        "IT applied hotfix for the null pointer issue in MessageBuilder. Re-queued settlement "
        "instruction. Settled T+1. Permanent fix tracked under JIRA ticket.",
        "SWIFT operations manually corrected the MT202COV. Trade settled. Raised system "
        "improvement to validate MT messages before submission.",
        "Static data team synchronised counterparty status across trade capture and settlement "
        "systems. Manually released the blocked trade. Settled T+1.",
    ],
}


def _format_notional(amount: float) -> str:
    """Format a number as $1.2M, $450K, etc."""
    if amount >= 1_000_000:
        return f"{amount / 1_000_000:.1f}M"
    if amount >= 1_000:
        return f"{amount / 1_000:.0f}K"
    return f"{amount:.0f}"


def _sample_severity(category: BreakCategory, notional: float) -> Severity:
    """Severity correlates with category and notional size."""
    if category == BreakCategory.REGULATORY_HOLD:
        return Severity.REGULATORY_FLAG
    if notional >= 50_000_000:
        return Severity.HIGH
    if notional >= 5_000_000:
        return Severity.MEDIUM
    return Severity.LOW


def _sample_resolution_hours(category: BreakCategory) -> float:
    """Resolution time distributions by category."""
    means_by_category = {
        BreakCategory.SSI_MISMATCH: 4.0,
        BreakCategory.COUNTERPARTY_ISSUE: 12.0,
        BreakCategory.TIMING_CUTOFF: 24.0,
        BreakCategory.FX_RELATED: 8.0,
        BreakCategory.REGULATORY_HOLD: 48.0,
        BreakCategory.SYSTEM_ERROR: 6.0,
    }
    mean = means_by_category[category]
    return round(random.gammavariate(2, mean / 2), 1)


def generate_break(case_id: str, category: BreakCategory | None = None) -> HistoricalBreak:
    """Generate one historical break with its resolution.

    Args:
        case_id: Unique case identifier.
        category: If provided, fix the category. If None, sample uniformly.
    """
    category = category or random.choice(list(BreakCategory))
    product = random.choice(list(ProductType))
    ccy = random.choices(CURRENCIES, weights=CURRENCY_WEIGHTS, k=1)[0]
    cp = random.choice(COUNTERPARTY_POOL)
    exception_code = random.choice(EXCEPTION_CODES_BY_CATEGORY[category])

    notional = round(random.lognormvariate(14, 1.5), 2)  # right-skewed, $millions
    trade_date_val = fake.date_between(start_date="-2y", end_date="-1d")
    settlement_date_val = trade_date_val + timedelta(days=random.choice([1, 2]))

    # Template variables for narrative + resolution
    template_vars = {
        "cp": cp,
        "ccy": ccy,
        "prod": product.value.replace("_", " "),
        "acct": fake.bothify("ACC######"),
        "acct2": fake.bothify("ACC######"),
        "corr1": fake.bothify("BANK?????"),
        "corr2": fake.bothify("BANK?????"),
        "tdate": trade_date_val.isoformat(),
        "sdate": settlement_date_val.isoformat(),
        "notional_str": f"{ccy} {_format_notional(notional)}",
        "alloc_str": _format_notional(notional * random.uniform(0.95, 1.05)),
        "trd": f"TRD-{random.randint(100000, 999999)}",
    }

    narrative = random.choice(NARRATIVE_TEMPLATES[category]).format(**template_vars)
    resolution = random.choice(RESOLUTION_TEMPLATES[category]).format(**template_vars)

    return HistoricalBreak(
        case_id=case_id,
        trade_id=template_vars["trd"],
        category=category,
        severity=_sample_severity(category, notional),
        product_type=product,
        currency=ccy,
        counterparty_id=cp,
        exception_code=exception_code,
        trade_date=trade_date_val,
        settlement_date=settlement_date_val,
        notional_usd=notional,
        analyst_narrative=narrative,
        resolution=resolution,
        resolution_time_hours=_sample_resolution_hours(category),
    )


def generate_corpus(count: int, output_path: Path, seed: int | None = None) -> None:
    """Generate `count` breaks and write to JSONL.

    Args:
        count: Number of breaks to generate.
        output_path: Path to write the JSONL corpus.
        seed: Random seed for reproducibility.
    """
    if seed is not None:
        random.seed(seed)
        Faker.seed(seed)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        for i in range(count):
            case_id = f"CASE-{i:06d}"
            brk = generate_break(case_id)
            f.write(brk.model_dump_json() + "\n")
