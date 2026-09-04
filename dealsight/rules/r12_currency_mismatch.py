"""Rule 12: Currency mismatch — non-USD deal whose CV == USD line sum to the cent."""

import pandas as pd
from . import register


@register("currency_mismatch")
def check(deal: pd.Series, lines: pd.DataFrame, config: dict) -> list[tuple[str, str, dict]]:
    cfg = config["rules"]["currency_mismatch"]
    currency = str(deal.get("currency", "USD")).strip().upper()
    if currency == "USD":
        return []
    cv = deal.get("contract_value_usd", 0) or 0
    line_sum = lines["line_total_usd"].sum() if len(lines) > 0 else 0
    # Flag if the non-USD CV exactly equals the USD line sum (likely missing conversion)
    if abs(cv - line_sum) < 0.01:
        return [("currency_mismatch", cfg["severity"], {
            "deal_id": deal["deal_id"],
            "currency": currency,
            "contract_value": cv,
            "usd_line_sum": round(line_sum, 2),
            "explanation": "Non-USD deal has contract value equal to USD line sum — likely missing FX conversion.",
        })]
    return []
