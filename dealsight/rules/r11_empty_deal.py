"""Rule 11: Empty deal ($0 or no lines)."""

import pandas as pd
from . import register


@register("empty_deal")
def check(deal: pd.Series, lines: pd.DataFrame, config: dict) -> list[tuple[str, str, dict]]:
    cfg = config["rules"]["empty_deal"]
    cv = deal.get("contract_value_usd", 0) or 0
    if cv == 0 or len(lines) == 0:
        return [("empty_deal", cfg["severity"], {
            "deal_id": deal["deal_id"],
            "contract_value": cv,
            "line_count": len(lines),
        })]
    return []
