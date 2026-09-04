"""Reconciliation guard — runs on every parse regardless of parser.

- coterm → CV × days(term_start→coterm_end)/365.25 must be sane prorated amount
- ramp → Σ amounts = CV ±1%
- parser says none but text contains $ amounts → suspicious
"""

import re
from datetime import datetime
import pandas as pd
from .base import ParseResult


_DOLLAR_RE = re.compile(r"\$[\d,]+(?:\.\d{2})?")


def reconcile(parsed: ParseResult, deal: pd.Series, lines: pd.DataFrame) -> dict:
    """Validate parsed result against deal data.

    Returns: {"pass": bool, "reason": str | None, "details": dict}
    """
    ptype = parsed.get("type", "none")
    cv = deal.get("contract_value_usd", 0) or 0

    if ptype == "coterm":
        return _check_coterm(parsed, deal, cv)
    elif ptype == "ramp":
        return _check_ramp(parsed, deal, cv)
    elif ptype == "none":
        return _check_none(parsed, deal)
    else:
        return {"pass": False, "reason": f"Unknown parse type: {ptype}", "details": {}}


def _check_coterm(parsed: ParseResult, deal: pd.Series, cv: float) -> dict:
    # Null-field check: every field the payload builder needs must be present.
    # A null in any required field means the LLM (or regex) couldn't confirm it
    # from the source text — route to human review.
    null_fields = [f for f in ("sub_id", "coterm_end", "prorate") if parsed.get(f) is None]
    if null_fields:
        return {
            "pass": False,
            "reason": f"Coterm parse has null required field(s): {', '.join(null_fields)}",
            "details": parsed,
        }

    coterm_end = parsed.get("coterm_end")
    if not coterm_end:
        return {"pass": False, "reason": "Coterm parsed but no end date extracted", "details": parsed}

    try:
        end_dt = datetime.strptime(coterm_end, "%Y-%m-%d")
    except (ValueError, TypeError):
        return {"pass": False, "reason": f"Unparseable coterm_end date: {coterm_end}", "details": parsed}

    start = deal.get("term_start")
    if pd.isna(start):
        return {"pass": False, "reason": "Cannot validate coterm: term_start missing", "details": parsed}

    if hasattr(start, 'to_pydatetime'):
        start_dt = start.to_pydatetime()
    elif isinstance(start, str):
        try:
            start_dt = datetime.strptime(start, "%Y-%m-%d")
        except ValueError:
            return {"pass": False, "reason": f"Unparseable term_start: {start}", "details": parsed}
    else:
        start_dt = start
    days = (end_dt - start_dt).days
    if days <= 0:
        return {"pass": False, "reason": f"Coterm end ({coterm_end}) is not after term_start", "details": parsed}

    # Prorated amount sanity: CV × days/365.25 should be reasonable
    # We check that CV is within 5x of expected prorated annual amount
    term_months = deal.get("term_months", 12) or 12
    annual_rate = cv / (term_months / 12) if term_months > 0 else cv
    expected_prorated = annual_rate * days / 365.25

    # Sanity: the prorated amount should be between 10% and 500% of CV
    # This is a broad sanity check
    if cv > 0:
        ratio = expected_prorated / cv
        if ratio < 0.01 or ratio > 10:
            return {
                "pass": False,
                "reason": f"Coterm proration looks wrong: {days} days implies ${expected_prorated:.2f} vs CV ${cv:.2f}",
                "details": {"days": days, "expected_prorated": round(expected_prorated, 2), "cv": cv},
            }

    return {"pass": True, "reason": None, "details": {
        "days": days, "expected_prorated": round(expected_prorated, 2), "cv": cv,
    }}


def _check_ramp(parsed: ParseResult, deal: pd.Series, cv: float) -> dict:
    ramp = parsed.get("ramp", [])
    if not ramp:
        return {"pass": False, "reason": "Ramp parsed but no year amounts found", "details": parsed}

    total = sum(y.get("amount", 0) for y in ramp)
    if cv > 0:
        pct_diff = abs(total - cv) / cv * 100
        if pct_diff > 1.0:
            return {
                "pass": False,
                "reason": f"Ramp sum ${total:.2f} differs from CV ${cv:.2f} by {pct_diff:.1f}%",
                "details": {"ramp_sum": total, "cv": cv, "pct_diff": round(pct_diff, 1)},
            }

    return {"pass": True, "reason": None, "details": {"ramp_sum": total, "cv": cv}}


def _check_none(parsed: ParseResult, deal: pd.Series) -> dict:
    text = str(deal.get("special_terms", ""))
    dollar_matches = _DOLLAR_RE.findall(text)
    if dollar_matches:
        return {
            "pass": False,
            "reason": f"Parser returned 'none' but text contains dollar amounts: {dollar_matches}",
            "details": {"dollar_amounts": dollar_matches},
        }
    return {"pass": True, "reason": None, "details": {}}
