"""Rule 15: Special-terms reconciliation — delegates to parser + guard."""

import pandas as pd
from . import register


@register("special_terms")
def check(deal: pd.Series, lines: pd.DataFrame, config: dict) -> list[tuple[str, str, dict]]:
    # Import here to avoid circular dependency
    from dealsight.parser import parse_special_terms
    from dealsight.parser.guard import reconcile

    cfg = config["rules"]["special_terms"]
    text = deal.get("special_terms", "")
    if pd.isna(text) or str(text).strip() == "":
        return []

    parsed = parse_special_terms(str(text), deal, config)
    guard_result = reconcile(parsed, deal, lines)

    if not guard_result["pass"]:
        return [("special_terms", cfg["severity"], {
            "deal_id": deal["deal_id"],
            "parse_result": parsed,
            "guard_result": guard_result,
            "raw_text": str(text),
        })]

    # Even if guard passes, coterm/ramp deals need manual handling
    if parsed.get("type") in ("coterm", "ramp"):
        return [("special_terms", cfg["severity"], {
            "deal_id": deal["deal_id"],
            "parse_result": parsed,
            "guard_result": guard_result,
            "raw_text": str(text),
            "reason": f"Deal has {parsed['type']} terms requiring manual review",
        })]

    return []
