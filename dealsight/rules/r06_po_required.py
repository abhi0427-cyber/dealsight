"""Rule 6: PO required but missing."""

import pandas as pd
from . import register


@register("po_required")
def check(deal: pd.Series, lines: pd.DataFrame, config: dict) -> list[tuple[str, str, dict]]:
    cfg = config["rules"]["po_required"]
    if not deal.get("po_required", False):
        return []
    po = deal.get("po_number")
    if pd.isna(po) or str(po).strip() == "":
        return [("po_required", cfg["severity"], {
            "customer": deal.get("customer_name", ""),
            "deal_id": deal["deal_id"],
        })]
    return []
